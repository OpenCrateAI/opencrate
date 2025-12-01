import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class CustomJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle additional data types.
    - datetime.datetime and datetime.date: converted to ISO 8601 strings.
    - pathlib.Path: converted to strings.
    - set: converted to lists.
    """

    def default(self, o):
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, set):
            return list(o)
        return super().default(o)


def save(data, path, encoder: Optional[json.JSONEncoder] = None, **kwargs: Any):
    """Saves data to a JSON file with extended support for additional types.

    This function serializes a Python object to a JSON-formatted file. It extends
    the standard `json.dump` with a custom encoder that can handle `datetime`,
    `pathlib.Path`, and `set` objects.

    Args:
        path (str or Path): The file path where the JSON data will be saved.
            The directory will be created if it does not exist.
        data (Any): The Python object to serialize.
        **kwargs (Any): Additional keyword arguments to pass to `json.dump()`, such as
            `indent` for pretty-printing or `sort_keys`.

    Raises:
        TypeError: If the data contains an object that cannot be serialized.
        OSError: If there is an issue writing to the file path.

    Example:
        Save a simple dictionary:
        ---
        ```python
        import opencrate as oc

        user_data = {"name": "John Doe", "email": "john.doe@example.com"}
        oc.io.json.save(user_data, "user.json", indent=4)
        ```

        Save data containing datetime and other types:
        ---
        ```python
        import opencrate as oc
        from datetime import datetime
        from pathlib import Path

        complex_data = {
            "report_id": 123,
            "timestamp": datetime.now(),
            "source_files": {Path("/src/data.csv"), Path("/src/log.txt")},
            "status": "completed"
        }
        oc.io.json.save(complex_data, "report.json", indent=4, sort_keys=True)
        ```
    """

    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Use the custom encoder if no other encoder is specified
    if "cls" not in kwargs:
        if encoder is None:
            kwargs["cls"] = CustomJSONEncoder
        else:
            kwargs["cls"] = encoder

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, **kwargs)


def load(path, encoding: str = "utf-8", **kwargs: Any) -> Dict[Any, Any]:
    """Loads data from a JSON file.

    This function deserializes a JSON file into a Python object. It is a
    wrapper around the standard `json.load` function.

    Note:
        This function does not automatically convert strings back into complex
        types like `datetime` or `Path`. If you need to deserialize these,
        you can pass a custom `object_hook` in `**kwargs`.

    Args:
        path (str or Path): The path to the JSON file to load.
        encoding (str, optional): The file encoding to use. Defaults to "utf-8".
        **kwargs (Any): Additional keyword arguments to pass to `json.load()`, such
            as `object_hook` for custom deserialization.

    Returns:
        Dict[Any, Any]: The deserialized Python object from the JSON file.

    Raises:
        FileNotFoundError: If the specified file path does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        OSError: If there is an issue reading from the file path.

    Example:
        Load a standard JSON file:
        ---
        ```python
        import opencrate as oc

        # Assuming 'user.json' contains: {"name": "John Doe"}
        user_data = oc.io.json.load("user.json")
        print(user_data)
        # Output: {'name': 'John Doe'}
        ```

        Handle a file that does not exist:
        ---
        ```python
        import opencrate as oc
        import json as json_lib

        data = oc.io.json.load("non_existent_file.json")
        ```

        Custom arguments that will be passed on to the json.loads internally
        ---
        ```python
        import opencrate as oc
        from datetime import datetime
        import re

        def datetime_parser(dct):
            # A simple object_hook to find and convert ISO date strings
            for k, v in dct.items():
                if isinstance(v, str) and re.match(r'^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d+$', v):
                    try:
                        dct[k] = datetime.fromisoformat(v)
                    except (ValueError, TypeError):
                        pass  # Ignore if conversion fails
            return dct

        report_data = oc.io.json.load("report.json", object_hook=datetime_parser)
        print(type(report_data.get("timestamp")))
        # Output: <class 'datetime.datetime'>
        ```
    """

    try:
        with open(path, encoding=encoding) as file:
            return json.load(file, **kwargs)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        raise
