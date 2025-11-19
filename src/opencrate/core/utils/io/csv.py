import csv
import os
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd
from numpy.typing import NDArray

# Define a type hint for data that can be saved to CSV
CsvDataType = Union[List[Any], NDArray[Any], "pd.DataFrame"]


def load(path: str, lib: str = "pandas", **kwargs: Any) -> CsvDataType:
    """
    Loads data from a CSV file using different libraries.

    Args:
        path (str): The path to the CSV file.
        lib (str, optional): The library to use for loading. Defaults to "csv".
            - "csv": Uses Python's built-in csv module. Returns a list of lists.
            - "numpy": Uses NumPy to load data. Returns a NumPy array.
            - "pandas": Uses pandas to load data. Returns a pandas DataFrame.
        **kwargs: Additional keyword arguments passed to the loading function.

    Returns:
        Union[List[list], "np.ndarray", "pd.DataFrame"]: The loaded data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If an unsupported library is specified.
        ImportError: If the required library (NumPy or pandas) is not installed.
        IOError: If there is an issue reading the file.

    Examples:
        ```python
        # Load with csv library (default)
        data_csv = load("data.csv")
        # Returns: [['col1', 'col2'], ['1', '2'], ['3', '4']]

        # Load with numpy
        data_numpy = load("data.csv", lib="numpy", skiprows=1)
        # Returns: numpy array with numeric data

        # Load with pandas
        data_pandas = load("data.csv", lib="pandas")
        # Returns: pandas DataFrame
        ```
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"No such file or directory: '{path}'")

    try:
        if lib == "csv":
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f, **kwargs)
                return list(reader)

        elif lib == "numpy":
            return np.genfromtxt(path, delimiter=",", **kwargs)

        elif lib == "pandas":
            return pd.read_csv(path, **kwargs)

        else:
            raise ValueError(f"Unsupported library: {lib}. Supported libraries are 'csv', 'numpy', and 'pandas'.")

    except Exception as e:
        raise OSError(f"Failed to load CSV from {path}: {e}")


def save(data: CsvDataType, path: str, lib: Optional[str] = None, **kwargs: Any) -> None:
    """
    Saves data to a CSV file using different libraries.

    The library can be specified explicitly or inferred from the data type.

    Args:
        path (str): The path where the CSV file will be saved.
        data (CsvDataType): The data to save. Can be a list of lists,
            a NumPy array, or a pandas DataFrame.
        lib (str, optional): The library to use for saving. If None, it's
            inferred from the data type. Defaults to None.
            - "csv": Saves a list of lists.
            - "numpy": Saves a NumPy array.
            - "pandas": Saves a pandas DataFrame.
        **kwargs: Additional keyword arguments passed to the saving function.

    Raises:
        ValueError: If the library is not specified and cannot be inferred,
            or if an unsupported library is specified.
        ImportError: If the required library (NumPy or pandas) is not installed.
        IOError: If there is an issue writing the file.

    Examples:
        ```python

        # 1. Save a list of lists using 'csv'
        list_data = [["col1", "col2"], [1, 2], [3, 4]]
        save("list.csv", list_data)
        print(os.path.exists("list.csv"))
        # True

        # 2. Save a NumPy array
        numpy_data = np.array([[1, 2], [3, 4]])
        save("numpy.csv", numpy_data, lib="numpy", fmt="%d")
        print(os.path.exists("numpy.csv"))
        # True

        # 3. Save a pandas DataFrame
        df_data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        save("pandas.csv", df_data, index=False)
        print(os.path.exists("pandas.csv"))
        # True
        ```
    """
    # Infer library from data type if not provided
    if lib is None:
        if isinstance(data, list):
            lib = "csv"
        elif isinstance(data, np.ndarray):
            lib = "numpy"
        elif isinstance(data, pd.DataFrame):
            lib = "pandas"
        else:
            raise ValueError(f"Could not infer library from data type. Data type: {type(data)}, supported types are list, np.ndarray, pd.DataFrame.")

    # Ensure the output directory exists
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        if lib == "csv":
            if not isinstance(data, list):
                raise TypeError("Data must be a list of lists for lib='csv'")
            with open(path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, **kwargs)
                writer.writerows(data)

        elif lib == "numpy":
            if not isinstance(data, np.ndarray):
                raise TypeError("Data must be a NumPy array for lib='numpy'")
            np.savetxt(path, data, delimiter=",", **kwargs)

        elif lib == "pandas":
            if not isinstance(data, pd.DataFrame):
                raise TypeError("Data must be a pandas DataFrame for lib='pandas'")
            data.to_csv(path, **kwargs)

        else:
            raise ValueError(f"Unsupported library: {lib}. Supported libraries are 'csv', 'numpy', and 'pandas'.")

    except Exception as e:
        raise OSError(f"Failed to save CSV to {path}: {e}")
