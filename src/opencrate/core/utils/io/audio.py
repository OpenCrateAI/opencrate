import os
from typing import Any, Dict

import numpy as np


def _lazy_import(module_name: str) -> Any:
    """Lazily imports a module and raises a helpful error if it's not installed."""
    try:
        return __import__(module_name)
    except ImportError:
        raise ImportError(f"The '{module_name}' library is required for this functionality. Please install it using 'pip install {module_name}'.")


def load(path: str, lib: str = "librosa", **kwargs: Any) -> Dict[str, Any]:
    """Loads an audio file and returns its data and metadata.

    This function provides a unified interface for loading audio using different
    libraries, returning a standardized dictionary containing the audio waveform
    and key properties.

    Args:
        path (str): The file path to the audio file.
        lib (str): The library to use for loading. Supported: "librosa", "pydub", "scipy", "soundfile", "torchaudio".
            Defaults to "librosa".
        **kwargs: Additional keyword arguments passed to the loading function of the
            selected library (e.g., `sr=22050` for librosa).

    Returns:
        A dictionary with the following keys:
        - "data" (np.ndarray): The audio waveform as a NumPy array.
        - "sample_rate" (int): The sample rate of the audio.
        - "duration" (float): The duration of the audio in seconds.
        - "channels" (int): The number of audio channels.
        - "library_object" (Any): The original object loaded by the library.

    Raises:
        FileNotFoundError: If the specified file path does not exist.
        ValueError: If an unsupported library is specified.
        ImportError: If the required audio library is not installed.

    Examples:
        Load an audio file using librosa (default):
        ---
        ```python
        import opencrate as oc
        audio_info = oc.io.audio.load("speech.wav")
        print(f"Sample Rate: {audio_info['sample_rate']}")
        print(f"Duration: {audio_info['duration']:.2f}s")
        ```

        Load an audio file using pydub:
        ---
        ```python
        import opencrate as oc
        audio_info = oc.io.audio.load("music.mp3", lib="pydub")
        # The returned data is always a NumPy array for consistency
        print(f"Waveform shape: {audio_info['data'].shape}")
        ```

        Load a WAV file using scipy (fast for .wav):
        ---
        ```python
        import opencrate as oc
        audio_info = oc.io.audio.load("speech.wav", lib="scipy")
        print(f"Loaded {audio_info['duration']:.2f}s of audio.")
        ```

        Load an audio file using torchaudio:
        ---
        ```python
        import opencrate as oc
        audio_info = oc.io.audio.load("music.wav", lib="torchaudio")
        print(f"Channels: {audio_info['channels']}")
        ```
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file or directory: '{path}'")

    if lib == "librosa":
        librosa = _lazy_import("librosa")
        y, sr = librosa.load(path, **kwargs)

        return {
            "data": y,
            "sample_rate": sr,
            "duration": librosa.get_duration(y=y, sr=sr),
            "channels": y.shape[0] if y.ndim > 1 else 1,
            "library_object": (y, sr),
        }

    elif lib == "pydub":
        pydub = _lazy_import("pydub")
        audio_segment = pydub.AudioSegment.from_file(path, **kwargs)
        samples = audio_segment.get_array_of_samples()

        return {
            "data": np.array(samples, dtype=np.float32),
            "sample_rate": audio_segment.frame_rate,
            "duration": audio_segment.duration_seconds,
            "channels": audio_segment.channels,
            "library_object": audio_segment,
        }

    elif lib == "scipy":
        scipy_io = _lazy_import("scipy.io.wavfile")
        sample_rate, data = scipy_io.read(path)

        return {
            "data": data,
            "sample_rate": sample_rate,
            "duration": data.shape[0] / sample_rate,
            "channels": data.shape[1] if data.ndim > 1 else 1,
            "library_object": (sample_rate, data),
        }
    elif lib == "soundfile":
        soundfile = _lazy_import("soundfile")
        data, sample_rate = soundfile.read(path, **kwargs)
        return {
            "data": data,
            "sample_rate": sample_rate,
            "duration": data.shape[0] / sample_rate,
            "channels": data.shape[1] if data.ndim > 1 else 1,
            "library_object": (sample_rate, data),
        }

    elif lib == "torchaudio":
        torchaudio = _lazy_import("torchaudio")
        waveform, sample_rate = torchaudio.load(path, **kwargs)
        # Convert torch tensor to numpy array
        data = waveform.numpy()
        # torchaudio returns (channels, samples) format, transpose to (samples, channels) for consistency
        if data.ndim > 1:
            data = data.T

        return {
            "data": data,
            "sample_rate": sample_rate,
            "duration": data.shape[0] / sample_rate,
            "channels": waveform.shape[0],
            "library_object": (waveform, sample_rate),
        }

    else:
        raise ValueError(f"Unsupported library: '{lib}'. Supported libraries are 'librosa', 'pydub', 'scipy', 'soundfile', 'torchaudio'.")


def save(
    data,
    path: str,
    sample_rate: int,
    lib: str = "soundfile",
    **kwargs: Any,
) -> None:
    """Saves a NumPy array as an audio file.

    Args:
        data (np.ndarray): The audio waveform to save. Must be a NumPy array.
        path (str): The destination file path for the audio file.
        sample_rate (int): The sample rate of the audio data.
        lib (str): The library to use for saving. Supported: "soundfile", "scipy", "librosa", "torchaudio".
            Defaults to "soundfile".
        **kwargs: Additional keyword arguments to pass to the saving function.

    Raises:
        ValueError: If the data is not a NumPy array or an unsupported library is specified.
        ImportError: If the required audio library is not installed.
        IOError: If there is an error writing the file.

    Examples:
        Generate a sine wave and save it as a WAV file:
        ---
        ```python
        import opencrate as oc
        import numpy as np
        sr = 22050
        duration = 5
        frequency = 440.0
        t = np.linspace(0., duration, int(sr * duration))
        amplitude = np.iinfo(np.int16).max * 0.5
        data = (amplitude * np.sin(2. * np.pi * frequency * t)).astype(np.int16)

        oc.io.audio.save(data, "sine_wave.wav", sr, lib="soundfile")
        ```

        Save using torchaudio:
        ---
        ```python
        import opencrate as oc
        import numpy as np

        # Generate some audio data
        data = np.random.randn(22050)  # 1 second of random audio
        oc.io.audio.save(data, "output.wav", 22050, lib="torchaudio")
        ```
    """

    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    if not isinstance(data, np.ndarray):
        raise ValueError(f"Input data must be a NumPy array, but got {type(data)}.")

    try:
        if lib == "soundfile":
            soundfile = _lazy_import("soundfile")
            soundfile.write(path, data, sample_rate, **kwargs)
        elif lib == "scipy":
            scipy_io = _lazy_import("scipy.io.wavfile")
            scipy_io.write(path, sample_rate, data)
        elif lib == "librosa":
            soundfile = _lazy_import("soundfile")
            # librosa uses soundfile for saving
            soundfile.write(path, data, sample_rate, **kwargs)
        elif lib == "torchaudio":
            torchaudio = _lazy_import("torchaudio")
            torch = _lazy_import("torch")

            # Convert numpy to torch tensor
            tensor_data = torch.from_numpy(data)

            # Ensure proper shape: torchaudio expects (channels, samples)
            if tensor_data.ndim == 1:
                tensor_data = tensor_data.unsqueeze(0)  # Add channel dimension
            elif tensor_data.ndim == 2 and tensor_data.shape[1] > tensor_data.shape[0]:
                # If shape is (samples, channels), transpose to (channels, samples)
                tensor_data = tensor_data.T

            torchaudio.save(path, tensor_data, sample_rate, **kwargs)
        else:
            raise ValueError(f"Unsupported library: '{lib}'. Supported libraries for saving are 'soundfile', 'scipy', 'librosa', 'torchaudio'.")
    except Exception as e:
        raise OSError(f"Failed to save audio to {path}: {e}")
