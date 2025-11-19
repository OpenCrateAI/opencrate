import os
from typing import Any, Dict, List, Union

import yaml

# Type alias for YAML-serializable data
YAMLData = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def save(data: YAMLData, path: str, **kwargs) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as file:
            yaml.dump(data, file, **kwargs)
    except OSError as e:
        raise OSError(f"Failed to save YAML file to {path}: {e}") from e
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to serialize data to YAML: {e}") from e


def load(path: str) -> YAMLData:
    try:
        with open(path) as file:
            return yaml.safe_load(file)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"YAML file not found: {path}") from e
    except OSError as e:
        raise OSError(f"Failed to read YAML file from {path}: {e}") from e
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse YAML file {path}: {e}") from e
