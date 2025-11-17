# Snapshot

The `snapshot` object provides a simple and consistent way to handle logging across your application. It is pre-configured to offer several logging levels, each with a distinct color and format for clear and readable output.

You can import and use the `snapshot` object directly, or use the standalone logging functions.

## Usage

```python
from opencrate import snapshot, info, success, error

# Use the main snapshot object
snapshot.info("This is an informational message.")

# Or use the direct logging functions
info("This is another informational message.")
success("The operation was successful.")
error("An error occurred.")
```

::: opencrate.core.snapshot.Snapshot
    options:
      show_root_heading: true
      show_if_no_docstring: false
      members:
        - setup
        - list_tags
        - exists
        - checkpoint
        - json
        - csv
        - figure
        - reset
        - path