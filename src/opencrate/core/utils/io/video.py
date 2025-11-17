import os
from itertools import chain
from typing import Any, Dict, Iterable, Iterator, Optional, Union

import numpy as np
from numpy.typing import NDArray


def _lazy_import(module_name: str, package_name: Optional[str] = None) -> Any:
    """
    Lazily imports a module and raises a helpful error if it's not installed.
    """
    package_name = package_name or module_name
    try:
        return __import__(module_name)
    except ImportError:
        raise ImportError(f"The '{package_name}' library is required for this functionality. Please install it using 'pip install {package_name}'.")


def load(path: str, lib: str = "cv2", **kwargs: Any) -> Dict[str, Any]:
    """Loads a video file and returns its frames, audio, and metadata.

    This function provides a unified interface for loading videos using different
    libraries, returning a standardized dictionary.

    Args:
        path (str): The file path to the video file.
        lib (str): The library to use for loading. Supported: "cv2", "moviepy",
            "torchvision", "av". Defaults to "cv2".
        **kwargs: Additional keyword arguments passed to the loading function of the
            selected library.

    Returns:
        A dictionary with the following keys:
        - "frames" (List[np.ndarray]): A list of video frames as NumPy arrays (H, W, C).
        - "audio" (np.ndarray | None): The audio waveform as a NumPy array, or None.
        - "fps" (float): Frames per second of the video.
        - "frame_count" (int): Total number of frames in the video.
        - "duration" (float): Duration of the video in seconds.
        - "width" (int): Width of the video frames.
        - "height" (int): Height of the video frames.
        - "audio_fps" (int | None): Sample rate of the audio, or None.
        - "object" (Any): The original object loaded by the library.

    Raises:
        FileNotFoundError: If the specified file path does not exist.
        ValueError: If an unsupported library is specified.
        ImportError: If the required video library is not installed.

    Examples:
        Load a video using OpenCV (cv2):
        ---
        ```python
        import opencrate as oc
        video_info = oc.io.video.load("my_video.mp4", lib="cv2")
        print(f"Loaded {video_info['frame_count']} frames at {video_info['fps']:.2f} FPS.")
        # Note: 'cv2' does not load audio.
        ```

        Load a video with audio using moviepy:
        ---
        ```python
        import opencrate as oc
        video_info = oc.io.video.load("my_video.mp4", lib="moviepy")
        if video_info['audio'] is not None:
            print(f"Audio loaded with sample rate: {video_info['audio_fps']}")
        ```

        Load a video using torchvision (efficient):
        ---
        ```python
        import opencrate as oc
        video_info = oc.io.video.load("my_video.mp4", lib="torchvision")
        print(f"Loaded video of size {video_info['width']}x{video_info['height']}.")
        ```
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file or directory: '{path}'")

    if lib == "cv2":
        cv2 = _lazy_import("cv2", package_name="opencv-python")
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise OSError(f"Could not open video file: {path}")

        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        return {
            "frames": frames,
            "audio": None,  # OpenCV does not handle audio
            "fps": fps,
            "frame_count": frame_count,
            "duration": frame_count / fps if fps > 0 else 0,
            "width": width,
            "height": height,
            "audio_fps": None,
            "object": cap,
        }

    elif lib == "moviepy":
        moviepy_editor = _lazy_import("moviepy.editor")
        clip = moviepy_editor.VideoFileClip(path, **kwargs)
        frames = list(clip.iter_frames())
        audio_data = clip.audio.to_soundarray(fps=clip.audio.fps) if clip.audio else None

        result = {
            "frames": frames,
            "audio": audio_data,
            "fps": clip.fps,
            "frame_count": int(clip.duration * clip.fps),
            "duration": clip.duration,
            "width": clip.w,
            "height": clip.h,
            "audio_fps": clip.audio.fps if clip.audio else None,
            "object": clip,
        }
        clip.close()
        return result

    elif lib == "torchvision":
        torchvision = _lazy_import("torchvision")
        vframes, aframes, info = torchvision.io.read_video(path, pts_unit="sec", **kwargs)

        # Convert Tensors to NumPy arrays (C, T, H, W) -> (T, H, W, C)
        frames_np = vframes.permute(0, 2, 3, 1).numpy()
        audio_np = aframes.t().numpy() if aframes.numel() > 0 else None

        return {
            "frames": list(frames_np),
            "audio": audio_np,
            "fps": info.get("video_fps"),
            "frame_count": len(frames_np),
            "duration": len(frames_np) / info.get("video_fps", 1),
            "width": frames_np.shape[2],
            "height": frames_np.shape[1],
            "audio_fps": info.get("audio_fps"),
            "object": (vframes, aframes, info),
        }

    elif lib == "av":
        av = _lazy_import("av", package_name="av")
        with av.open(path) as container:
            video_stream = container.streams.video[0]
            frames = [frame.to_ndarray(format="rgb24") for frame in container.decode(video=0)]

            audio_data = None
            audio_fps = None
            if container.streams.audio:
                audio_stream = container.streams.audio[0]
                audio_frames = b"".join(p.to_bytes() for p in container.decode(audio_stream))
                audio_data = np.frombuffer(audio_frames, dtype=np.int16)
                audio_fps = audio_stream.rate

            return {
                "frames": frames,
                "audio": audio_data,
                "fps": float(video_stream.average_rate),
                "frame_count": len(frames),
                "duration": float(video_stream.duration * video_stream.time_base),
                "width": video_stream.width,
                "height": video_stream.height,
                "audio_fps": audio_fps,
                "object": container,
            }

    else:
        raise ValueError(f"Unsupported library: '{lib}'. Supported are 'cv2', 'moviepy', 'torchvision', 'av'.")


def save(
    frames: Union[Iterable[NDArray[Any]], NDArray[Any]],
    path: str,
    fps: float,
    lib: str = "cv2",
    audio: Optional[NDArray[Any]] = None,
    audio_fps: Optional[int] = None,
    **kwargs: Any,
) -> None:
    """Saves a sequence of frames as a video file.

    Args:
        frames (Iterable[np.ndarray] or np.ndarray): An iterable of frames (H, W, C)
            or a single NumPy array of shape (T, H, W, C). Frames should be in RGB format.
        path (str): The destination file path for the video file.
        fps (float): The frames per second for the output video.
        lib (str): The library to use for saving. Supported: "cv2", "moviepy",
            "torchvision". Defaults to "cv2".
        audio (np.ndarray, optional): An optional audio track to add to the video.
        audio_fps (int, optional): The sample rate of the audio track. Required if
            `audio` is provided.
        **kwargs: Additional keyword arguments passed to the saving function.
            For 'cv2', `fourcc` can be specified (e.g., `fourcc='mp4v'`).
            For 'moviepy', `codec` can be specified (e.g., `codec='libx264'`).

    Raises:
        ValueError: If input parameters are invalid or an unsupported library is specified.
        ImportError: If the required video library is not installed.
        IOError: If there is an error writing the file.
    """
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if isinstance(frames, np.ndarray) and frames.ndim == 4:
        frame_iter: Iterator[NDArray[Any]] = iter(frames)
    else:
        frame_iter = iter(frames)

    # Peek at the first frame to get dimensions
    try:
        first_frame = next(frame_iter)
        height, width, _ = first_frame.shape
        # Chain the first frame back to the iterator
        frame_iter = chain([first_frame], frame_iter)
    except StopIteration:
        raise ValueError("Cannot save an empty sequence of frames.")

    try:
        if lib == "cv2":
            cv2 = _lazy_import("cv2", package_name="opencv-python")
            fourcc_map = {
                "mp4": "mp4v",
                "avi": "XVID",
            }
            ext = os.path.splitext(path)[1][1:].lower()
            fourcc_str = kwargs.get("fourcc", fourcc_map.get(ext, "mp4v"))
            fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
            writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

            for frame in frame_iter:
                writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            writer.release()

            if audio is not None:
                print("Warning: 'cv2' backend does not support writing audio. Audio track ignored.")

        elif lib == "moviepy":
            moviepy_editor = _lazy_import("moviepy.editor")
            clip = moviepy_editor.ImageSequenceClip(list(frame_iter), fps=fps)

            if audio is not None and audio_fps is not None:
                audio_clip = moviepy_editor.AudioFileClip.from_soundarray(audio, fps=audio_fps)
                clip = clip.set_audio(audio_clip)

            codec = kwargs.get("codec", "libx264")
            clip.write_videofile(path, codec=codec, fps=fps, **kwargs)
            clip.close()

        elif lib == "torchvision":
            torchvision = _lazy_import("torchvision")
            torch = _lazy_import("torch")
            # Convert all frames to a single tensor (T, H, W, C) -> (T, C, H, W)
            video_tensor = torch.from_numpy(np.stack(list(frame_iter))).permute(0, 3, 1, 2)
            torchvision.io.write_video(path, video_tensor, fps, **kwargs)

            if audio is not None:
                print("Warning: 'torchvision' backend does not support writing audio directly with video. Audio track ignored.")

        else:
            raise ValueError(f"Unsupported library: '{lib}'. Supported are 'cv2', 'moviepy', 'torchvision'.")
    except Exception as e:
        raise OSError(f"Failed to save video to {path}: {e}")
