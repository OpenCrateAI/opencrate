import importlib
import os
from typing import Any


def _lazy_import(module_name: str, error_message: str) -> Any:
    """
    Lazily imports a module and raises a helpful error if it's not installed.

    Args:
        module_name (str): The name of the module to import (e.g., "torch").
        error_message (str): The error message to display if ImportError occurs.

    Returns:
        The imported module object.

    Raises:
        ImportError: If the module cannot be imported.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        raise ImportError(error_message)


def save(obj: Any, path: str, **kwargs: Any) -> None:
    """Saves a model, state dict, or pipeline, inferring the format.

    This function acts as a universal saver, automatically selecting the
    correct saving mechanism based on the file extension of the provided path.
    Required libraries are imported on-the-fly.

    For ONNX export, you must provide a tuple of dummy inputs via the `args`
    keyword argument (e.g., `args=(dummy_tensor,)`).

    Args:
        obj (Any): The object to save (e.g., PyTorch model `state_dict`,
            Keras model, Scikit-Learn pipeline).
        path (str): The destination file path. The extension determines the
            saving format (e.g., `.pt`, `.safetensors`, `.h5`, `.joblib`, `.onnx`).
        **kwargs (Any): Additional keyword arguments to be passed to the
            underlying save function. For ONNX, this must include `args`.

    Raises:
        ImportError: If the required library for the specified format is not
            installed.
        ValueError: If the file extension is not supported or if required
            arguments for a specific format (like `args` for ONNX) are missing.

    Examples:
        Saving PyTorch model checkpoint:
        ```python
        import torch.nn as nn
        pytorch_model = nn.Linear(10, 2)
        oc.io.save(pytorch_model.state_dict(), "model.pt")
        ```
        Saving safetensors checkpoint:
        ```python
        import torch.nn as nn
        pytorch_model = nn.Linear(10, 2)
        oc.io.save(pytorch_model.state_dict(), "model.safetensors")
        ```
        ---
        Saving Scikit-Learn pipeline checkpoint:
        ```python
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        pipe = Pipeline([("scaler", StandardScaler()), ("svc", LogisticRegression())])
        oc.io.save(pipe, "model.joblib")
        ```
        ---
        Saving TensorFlow/Keras model checkpoint:
        ```
        import tensorflow as tf
        keras_model = tf.keras.Sequential([tf.keras.layers.Dense(5)])
        oc.io.save(keras_model, "model.keras")
        ---
        Saving PyTorch model to ONNX checkpoint:
        ```python
        import torch
        import torch.nn as nn
        model = nn.Linear(10, 2)
        model.eval()
        dummy_input = torch.randn(1, 10)
        oc.io.save(
            model,
            "model.onnx",
            args=(dummy_input,),
            input_names=["input"],
            output_names=["output"],
            opset_version=11,
        ) # here you can add any other argument supported by torch.onnx.export
        ```
    """
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    _, extension = os.path.splitext(path)

    if extension in (".pt", ".pth"):
        torch = _lazy_import("torch", "PyTorch not installed. Use 'pip install torch'.")
        torch.save(obj, path, **kwargs)

    elif extension == ".safetensors":
        safetensors_torch = _lazy_import(
            "safetensors.torch",
            "Safetensors not installed. Use 'pip install safetensors'.",
        )
        if not isinstance(obj, dict):
            raise TypeError("For .safetensors, the object must be a state_dict (dict).")
        safetensors_torch.save_file(obj, path, **kwargs)

    elif extension in (".h5", ".keras"):
        obj.save(path, **kwargs)

    elif extension == ".joblib":
        joblib = _lazy_import("joblib", "Joblib not installed. Use 'pip install joblib'.")
        joblib.dump(obj, path, **kwargs)

    elif extension == ".onnx":
        torch = _lazy_import("torch", "PyTorch is required for ONNX export. Use 'pip install torch'.")
        _lazy_import("onnx", "ONNX is required for ONNX export. Use 'pip install onnx'.")

        if not isinstance(obj, torch.nn.Module):
            raise TypeError("ONNX export is currently supported for PyTorch models (`torch.nn.Module`).")
        if "args" not in kwargs:
            raise ValueError("ONNX export requires a dummy input. Please provide it as a tuple via the 'args' keyword argument, e.g., save(model, path, args=(dummy_input,)).")

        dummy_args = kwargs.pop("args")
        torch.onnx.export(obj, dummy_args, path, **kwargs)
    else:
        raise ValueError(f"Unsupported file format: '{extension}'. Supported: .pt, .pth, .safetensors, .h5, .keras, .joblib, .onnx.")


def load(path: str, **kwargs: Any) -> Any:
    """Loads a model, state dict, or pipeline, inferring the format.

    This function acts as a universal loader, automatically selecting the
    correct loading mechanism based on the file extension. Required libraries
    are imported on-the-fly. For ONNX files, it returns an
    `onnxruntime.InferenceSession` ready for execution.

    Args:
        path (str): The source file path. The extension determines the format.
        **kwargs (Any): Additional keyword arguments to be passed to the
            underlying load function (e.g., `map_location` for `torch.load`).

    Returns:
        Any: The loaded object (e.g., a `state_dict`, Keras model,
            Scikit-Learn pipeline, or ONNX inference session).

    Raises:
        ImportError: If the required library for the specified format is not
            installed.
        ValueError: If the file extension is not a supported format.
        FileNotFoundError: If the specified path does not exist.

    Examples:
        Loading PyTorch model checkpoint:
        ```python
        import torch.nn as nn
        # First, save a checkpoint: save(model.state_dict(), "model.pt")
        model = nn.Linear(10, 2)
        state_dict = load("model.pt", map_location="cpu")
        model.load_state_dict(state_dict)
        ```
        ---
        Loading safetensors checkpoint:
        ```python
        import torch.nn as nn
        # First, save a checkpoint: save(model.state_dict(), "model.safetensors")
        model = nn.Linear(10, 2)
        state_dict = load("model.safetensors", device="cpu")
        model.load_state_dict(state_dict)
        ```
        ---
        Loading Scikit-Learn pipeline checkpoint:
        ```python
        # First, save a checkpoint: save(fitted_pipe, "model.joblib")
        loaded_pipeline = load("model.joblib")
        # loaded_pipeline is now ready to .predict()
        ```
        ---
        Loading TensorFlow/Keras model checkpoint:
        ```python
        # First, save a checkpoint: save(keras_model, "model.keras")
        loaded_keras_model = load("model.keras")
        # loaded_keras_model is now a compiled, ready-to-use model
        ```
        ---
        Loading an ONNX model for inference:
        ```python
        import numpy as np
        # First, export the model: save(pytorch_model, "model.onnx", args=...)
        inference_session = load("model.onnx")
        input_name = inference_session.get_inputs()[0].name
        dummy_data = np.random.randn(1, 10).astype(np.float32)
        result = inference_session.run(None, {input_name: dummy_data})
        ```
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file or directory: '{path}'")

    _, extension = os.path.splitext(path)

    if extension in (".pt", ".pth"):
        torch = _lazy_import("torch", "PyTorch not installed. Use 'pip install torch'.")
        return torch.load(path, **kwargs)

    elif extension == ".safetensors":
        safetensors_torch = _lazy_import(
            "safetensors.torch",
            "Safetensors not installed. Use 'pip install safetensors'.",
        )
        return safetensors_torch.load_file(path, **kwargs)

    elif extension in (".h5", ".keras"):
        tf = _lazy_import("tensorflow", "TensorFlow not installed. Use 'pip install tensorflow'.")
        return tf.keras.models.load_model(path, **kwargs)

    elif extension == ".joblib":
        joblib = _lazy_import("joblib", "Joblib not installed. Use 'pip install joblib'.")
        return joblib.load(path, **kwargs)

    elif extension == ".onnx":
        onnxruntime = _lazy_import("onnxruntime", "ONNX Runtime not installed. Use 'pip install onnxruntime'.")
        return onnxruntime.InferenceSession(path, **kwargs)

    else:
        raise ValueError(f"Unsupported file format: '{extension}'. Supported: .pt, .pth, .safetensors, .h5, .keras, .joblib, .onnx.")
