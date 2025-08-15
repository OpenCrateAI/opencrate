import inspect
import os
import re
import time
from functools import wraps
from typing import Any, Dict

import yaml
from rich.console import Console
from rich.tree import Tree

from .snapshot import Snapshot


class LiteralSafeDumper(yaml.SafeDumper):
    """
    Custom YAML Dumper to force literal block style for multi-line strings.
    This prevents escaped newlines (`\n`) in the output YAML for docstrings.
    """

    def represent_scalar(self, tag, value, style=None):
        if isinstance(value, str) and "\n" in value:
            # Force literal block style ('|') for strings containing newlines
            # This also ensures proper indentation for the multi-line string.
            return super().represent_scalar(tag, value, style="|")
        return super().represent_scalar(tag, value, style=style)


class Configuration:
    def __init__(self) -> None:
        self._config: Dict[str, Dict[str, Any]] = {}
        # Default mapping for built-in types.
        self.default_type_mapping = {
            "int": int,
            "str": str,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "complex": complex,
            "bytes": bytes,
            "bytearray": bytearray,
        }
        self.globals = globals()
        self.globals["__builtins__"] = __builtins__
        self.opencrate_init_done = False
        self.config_eval_on = True
        self.config_eval_start = 0.0
        self.config_eval_timeout = 60
        self.snapshot: Snapshot

    def _extract_validation_info(self, docstring):
        """
        Extracts validation rules while preserving multi-argument lambdas.
        New format: Validation rules are at the end of each argument description in square brackets.
        """
        validation_info = {}
        # New pattern: Capture arg_name (Group 1), arg_type (Group 2),
        # arg_description (Group 3, non-greedy, up to '[' or end of line),
        # and validation_bracket (Group 4, content inside rules []).
        pattern = re.compile(r"^\s*(\w+)\s*\(([\w\.]+)\):\s*([^\n]*?)(?:\[([^\]]+)\])?\s*$", re.MULTILINE)
        matches = pattern.findall(docstring)

        for arg_name, arg_type, arg_description_raw, validation_bracket_raw in matches:
            # Clean and store the description
            arg_description = arg_description_raw.strip()

            validation = validation_bracket_raw.strip("[]")
            rules = []
            buffer = []
            in_lambda = False

            # Only process rules if the validation_bracket_raw was not empty
            if validation:
                for part in re.split(r"(,|(lambda\b))", validation):
                    if not part:
                        continue
                    if part == "lambda":
                        in_lambda = True
                        buffer = ["lambda"]
                    elif in_lambda:
                        buffer.append(part)
                        if ":" in part:
                            in_lambda = False
                            rules.append("".join(buffer).strip())
                            buffer = []
                    else:
                        if part == ",":
                            if buffer:
                                rules.append("".join(buffer).strip())
                                buffer = []
                        else:
                            buffer.append(part)
                if buffer:
                    rules.append("".join(buffer).strip())

            validation_info[arg_name] = {
                "type": arg_type.strip(),
                "description": arg_description,  # Add the extracted description
                "rules": [r for r in rules if r],  # Ensure rules is always a list
            }

        return validation_info

    def _perform_validation(self, validation_rules, arg_name, arg_value, param_type, all_args):
        for rule in validation_rules:
            rule = rule.strip()

            if rule.startswith("lambda"):
                if ":" not in rule:
                    raise SyntaxError("\n\nMissing colon in lambda.\n")
                lambda_body = rule.split(":", 1)[1].strip()
                if not lambda_body:
                    raise SyntaxError("\n\nLambda missing expression body.\n")
                compiled = eval(rule, self.globals, {})
                sig = inspect.signature(compiled)
                params = list(sig.parameters.keys())
                if not params:
                    raise ValueError("\n\nLambda must take at least one parameter.\n")
                missing = [p for p in params[1:] if p not in all_args]
                if missing:
                    raise ValueError(f"\n\nValidation `{rule.split(':')[-1].strip()}` failed for `{arg_name}` with missing parameter(s): `{'`, `'.join(missing)}`.\n")
                additional_params_values = [all_args[p] for p in params[1:]]
                args = [arg_value] + additional_params_values
                try:
                    lambda_validation_result = compiled(*args)
                except NameError as e:
                    raise NameError(f"\n\nValidation `{rule.split(':')[-1].strip()}` failed for `{arg_name}` with missing parameter: {e}.\n")
                if not lambda_validation_result:
                    additional_params_names_with_values = ", ".join([f"`{p}`: {all_args[p]}" for p in params[1:]])
                    if len(additional_params_names_with_values):
                        raise ValueError(
                            f"\n\nValidation `{rule.split(':')[-1].strip()}` failed for `{arg_name}` with value `{arg_value}` and {additional_params_names_with_values}.\n"
                        )
                    else:
                        raise ValueError(f"\n\nValidation `{rule.split(':')[-1].strip()}` failed for `{arg_name}` with value `{arg_value}`.\n")

            elif rule.startswith((">", "<", ">=", "<=")):
                match = re.match(r"([>=<]+)\s*([\d.]+)", rule)
                if not match:
                    raise ValueError(f"\n\nInvalid validation rule format: {rule}.\n")
                operator_part, threshold_str = match.groups()
                try:
                    if param_type:
                        threshold = param_type(float(threshold_str)) if param_type is int else param_type(threshold_str)
                    else:
                        threshold = float(threshold_str)
                except (ValueError, TypeError):
                    raise ValueError(f"\n\nInvalid threshold value '{threshold_str}' for type {param_type if param_type else 'numeric'}.\n")
                if not isinstance(arg_value, (int, float)):
                    raise TypeError(f"\n\n`{arg_name}` must be `int` or `float` for comparison, but got `{type(arg_value)}`.\n")
                if operator_part == ">=" and arg_value < threshold:
                    raise ValueError(f"\n\n`{arg_name}` must be >= {threshold}, but got `{arg_value}`.\n")
                elif operator_part == "<=" and arg_value > threshold:
                    raise ValueError(f"\n\n`{arg_name}` must be <= {threshold}, but got `{arg_value}`.\n")
                elif operator_part == ">" and arg_value <= threshold:
                    raise ValueError(f"\n\n`{arg_name}` must be > {threshold}, but got `{arg_value}`.\n")
                elif operator_part == "<" and arg_value >= threshold:
                    raise ValueError(f"\n\n`{arg_name}` must be < {threshold}, but got `{arg_value}`.\n")

            elif rule.startswith('"') and rule.endswith('"'):
                allowed = [v.strip().strip('"') for v in validation_rules]
                if str(arg_value) not in allowed:
                    raise ValueError(f"\n\n`{arg_name}` must be one of {allowed}, but got `{arg_value}`.\n")
                break

            else:
                raise ValueError(f"\n\nUnsupported validation rule: {rule} for `{arg_name}`.\n")

    def _resolve_type(self, type_str):
        """
        If the type string isn’t a built-in type,
        use exec to resolve it into a usable Python type.
        """
        # Try the default mapping first
        t = self.default_type_mapping.get(type_str.lower())
        if t is not None:
            return t

        # Otherwise, attempt to resolve the custom type.
        local_namespace: Dict[str, Any] = {}
        try:
            # Now resolve the type using the updated self.globals
            src = f"resolved_type = {type_str}"
            exec(src, self.globals, local_namespace)

            resolved_type = local_namespace["resolved_type"]
            # Optionally, add it to the default mapping for future lookups.
            self.default_type_mapping[type_str.lower()] = resolved_type
            return resolved_type
        except Exception as e:
            raise ValueError(f"Could not resolve type '{type_str}'. Error: {e}")

    def _validate_arguments(self, validation_info, bound_args, parameters):
        for arg_name, arg_value in bound_args.items():
            if arg_name in validation_info:
                func_type = parameters[arg_name].annotation
                doc_type_str = validation_info[arg_name]["type"]
                rules = validation_info[arg_name]["rules"]

                if func_type != inspect.Parameter.empty:
                    effective_type = func_type
                elif doc_type_str:
                    # Use our helper to resolve the type
                    effective_type = self.default_type_mapping.get(doc_type_str.lower())
                    if effective_type is None:
                        effective_type = self._resolve_type(doc_type_str)
                else:
                    effective_type = None

                self._perform_validation(rules, arg_name, arg_value, effective_type, bound_args)

    def _get_func_meta(self, func):
        func_name = func.__name__

        # Check if this is a method of a class
        if hasattr(func, "__qualname__"):
            qualified_name = func.__qualname__
            if "." in qualified_name:
                parts = qualified_name.split(".")
                class_name = parts[0]
                # If this is __init__, return just the class name
                if func_name == "__init__":
                    func_name = class_name
                else:
                    # Otherwise return "class:method" format
                    func_name = f"{class_name}:{func_name}"

        return (
            func_name,
            inspect.getsourcefile(func),
            inspect.getsourcelines(func)[1],
        )

    def config(self, **imports):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if self.config_eval_on:
                    func_name, file_path, line_number = self._get_func_meta(func)

                    # Convert file_path to be relative to the current working directory.
                    # Only do this if it's not the special 'jupyter_notebook' path.
                    if "tmp/" in file_path:  # pyright: ignore
                        file_path = "jupyter_notebook"
                    else:
                        try:
                            # Get the path relative to the current working directory.
                            # This assumes os.getcwd() is the project's root.
                            file_path = os.path.relpath(file_path, os.getcwd())  # pyright: ignore
                        except ValueError:
                            # If the path cannot be made relative (e.g., on a different drive or
                            # outside the current working directory's scope),
                            # keep the absolute path as a fallback.
                            pass  # file_path remains the absolute path if relpath fails

                    if func_name not in self._config:
                        doc = func.__doc__
                        # Use inspect.cleandoc to remove common leading whitespace from the docstring
                        if doc:
                            doc = inspect.cleandoc(doc)
                        # format the doc to be shown correctly in the yaml config file
                        # remove args and returns sections
                        if doc:
                            # Split docstring into lines and process
                            lines = doc.strip().split("\n")
                            formatted_lines = []
                            skip_section = False
                            current_section = None

                            for line in lines:
                                stripped = line.strip()

                                # Check if this is a section header (Args, Arguments, Parameters, etc.)
                                if stripped.lower().startswith(("args:", "arguments:", "parameters:", "param:")):
                                    skip_section = True
                                    current_section = "args"
                                    continue
                                elif stripped.lower().startswith(("returns:", "return:")):
                                    skip_section = False
                                    current_section = "returns"
                                    formatted_lines.append(line)
                                    continue
                                elif stripped.lower().startswith(("raises:", "raise:", "exceptions:", "exception:")):
                                    skip_section = False
                                    current_section = "raises"
                                    formatted_lines.append(line)
                                    continue
                                elif stripped.lower().startswith(("note:", "notes:", "example:", "examples:")):
                                    skip_section = False
                                    current_section = "other"
                                    formatted_lines.append(line)
                                    continue

                                # If we encounter a new section or empty line, check if we should reset
                                if not stripped:
                                    # Empty line - keep it if not in args section
                                    if not skip_section:
                                        formatted_lines.append(line)
                                elif stripped and not line.startswith(" ") and not line.startswith("\t"):
                                    # New paragraph/section starting at column 0
                                    if current_section == "args" and not any(
                                        stripped.lower().startswith(s)
                                        for s in [
                                            "returns:",
                                            "return:",
                                            "raises:",
                                            "raise:",
                                            "exceptions:",
                                            "exception:",
                                        ]
                                    ):
                                        # This might be the end of args section
                                        skip_section = False
                                        current_section = None
                                        formatted_lines.append(line)
                                    elif not skip_section:
                                        formatted_lines.append(line)
                                else:
                                    # Regular content line - include if not in args section
                                    if not skip_section:
                                        formatted_lines.append(line)

                            # Join and clean up the formatted docstring
                            doc = "\n".join(formatted_lines).strip()

                            # Remove excessive blank lines
                            doc = re.sub(r"\n\s*\n\s*\n", "\n\n", doc)

                            # Ensure proper YAML formatting by handling special characters
                            # Replace tabs with spaces for consistent indentation
                            doc = doc.replace("\t", "    ")

                            # If the doc is empty after processing, provide a default
                            if not doc.strip():
                                doc = "No documentation provided."
                        else:
                            doc = "No documentation provided."
                        self._config[func_name] = {
                            "meta": {
                                "doc": doc,
                                "file": file_path,
                                "line": line_number,
                            },
                            "config": {},
                        }
                    elif not self.opencrate_init_done:
                        config_kwargs = self._config[func_name]["config"]
                        kwargs = {param_name: config_kwargs[param_name]["value"] for param_name in config_kwargs}
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    validation_info = self._extract_validation_info(func.__doc__ or "")

                    # Add provided imports to self.globals if missing.
                    for module_as_name, module in imports.items():
                        if module_as_name not in self.globals:
                            self.globals[module_as_name] = module

                    update_config = len(self._config[func_name]["config"]) == 0

                    # Loop over parameters (skipping 'self') to check type consistency and enforce types.
                    for param in sig.parameters.values():
                        if param.name == "self":
                            continue

                        arg_name = param.name
                        func_type = param.annotation
                        doc_info = validation_info.get(arg_name, {})
                        doc_type_str = doc_info.get("type")
                        param_doc_description = doc_info.get("description", "")  # Get the extracted description

                        effective_type = None  # Initialize effective_type

                        # Prioritize function type annotation
                        if func_type != inspect.Parameter.empty:
                            effective_type = func_type
                            # If docstring also has a type, ensure it matches
                            if doc_type_str:
                                doc_type_resolved = self.default_type_mapping.get(doc_type_str.lower()) or self._resolve_type(doc_type_str)
                                if doc_type_resolved != func_type:
                                    raise AssertionError(f"\n\nType mismatch for `{arg_name}`: Annotation `{func_type}` vs Docstring `{doc_type_str}`.\n")
                        # If no function annotation, try to use docstring type
                        elif doc_type_str:
                            effective_type = self.default_type_mapping.get(doc_type_str.lower()) or self._resolve_type(doc_type_str)
                        else:
                            # If neither annotation nor docstring provides type, log a warning.
                            # effective_type remains None.
                            print(f"Warning: No type information found for `{arg_name}` in function annotation or docstring.")

                        arg_value = bound_args.arguments[arg_name]
                        if effective_type and not isinstance(arg_value, effective_type):
                            raise TypeError(f"\n\n`{arg_name}` must be `{effective_type}`, but got `{arg_value}` of type `{type(arg_value)}`.\n")

                        if update_config:
                            param_config = {}
                            if param_doc_description:  # Only add 'doc' if description is not empty
                                param_config["doc"] = param_doc_description
                            param_config["value"] = arg_value
                            if effective_type:
                                param_config["type"] = effective_type
                            param_config["rules"] = doc_info.get("rules", [])  # Pass rules as a list
                            self._config[func_name]["config"][arg_name] = param_config

                    self._validate_arguments(validation_info, bound_args.arguments, sig.parameters)

                    self.config_eval_on = (time.perf_counter() - self.config_eval_start) < self.config_eval_timeout
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def display(self, prefix_title: str = ""):
        """
        Prints the given configuration dictionary in a tree-like structure with nested branches
        based on filenames and folder paths. The tree shows paths relative to the current working directory.
        """

        console = Console()
        file_tree: Dict[str, Any] = {}
        base_dir = os.getcwd()

        for name, details in self._config.items():
            meta = details.get("meta", {})
            file_path = meta.get("file", "N/A")
            line_num = meta.get("line", "N/A")
            config_data = details.get("config", {})

            if file_path != "N/A" and "/tmp" not in file_path:
                # Convert to absolute path if it's not already
                abs_path = os.path.abspath(file_path)

                # Make path relative to current working directory
                try:
                    rel_path = os.path.relpath(abs_path, base_dir)
                    # Split the relative path into components
                    parts = [p for p in rel_path.split(os.sep) if p]

                    # If path is outside the base directory, mark it clearly
                    if rel_path.startswith(".."):
                        first_part = "<external>"
                        parts = [first_part] + parts[1:]  # Skip the '..'
                except ValueError:
                    # Handle paths on different drives (Windows)
                    parts = ["<external>", os.path.basename(file_path)]

                current = file_tree
                # Build the tree structure for directories and file node
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                file_node = parts[-1]
                current.setdefault(file_node, []).append((name, line_num, config_data))
            else:
                file_tree.setdefault("", []).append((name, line_num, config_data))

        def add_nodes(rich_tree, subtree):
            if isinstance(subtree, dict):
                for key in sorted(subtree.keys()):
                    branch = rich_tree.add(f"[bold]{key}[/bold]")
                    add_nodes(branch, subtree[key])
            elif isinstance(subtree, list):
                for config_name, line_num, config_data in subtree:
                    config_branch = rich_tree.add(f"[bold]{config_name}[/bold] (line: {line_num})")
                    if config_data:
                        for param, param_details in config_data.items():
                            ptype = param_details.get("type", None)
                            pvalue = param_details.get("value", None)
                            type_name = ptype.__name__ if hasattr(ptype, "__name__") else str(ptype)
                            config_branch.add(f"[bold]{param}[/bold] ({type_name}) = {pvalue}")

        # Create the root tree and populate it with the file tree
        root = Tree(f"{prefix_title}")
        add_nodes(root, file_tree)
        console.print(root)
        print()

    def write(self, filename, replace_config: bool = False):
        """
        Write a structured YAML configuration file using self._config.
        The YAML file will contain all meta and config details.
        """
        # Prepare a serializable version of the configuration
        config_yaml: Dict[str, Dict[str, Any]] = {}

        for comp_name, comp_details in self._config.items():
            config_yaml[comp_name] = {}
            # Include meta information directly.
            config_yaml[comp_name]["meta"] = comp_details.get("meta", {})

            # Process the configuration details
            config_yaml[comp_name]["config"] = {}
            for param, param_details in comp_details.get("config", {}).items():
                # Make a shallow copy so as not to modify the original
                param_copy = param_details.copy()
                # Convert any type objects to their name (e.g. <class 'float'> -> "float")
                t = param_copy.get("type")
                if t and hasattr(t, "__name__"):
                    param_copy["type"] = t.__name__

                # Remove 'rules' key if the list is empty or None
                if not param_copy.get("rules"):
                    param_copy.pop("rules", None)

                # Remove 'doc' key if the string is empty or None
                if not param_copy.get("doc"):
                    param_copy.pop("doc", None)

                config_yaml[comp_name]["config"][param] = param_copy

        # Write the structured dictionary to a YAML file
        if replace_config:
            os.makedirs("config", exist_ok=True)
            with open(f"config/{filename}.yml", "w") as f:
                yaml.dump(
                    config_yaml,
                    f,
                    Dumper=LiteralSafeDumper,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=4,
                )
                self.snapshot.debug(f"Updated configuration in: 'config/{filename}.yml'")

        snapshot_config_path = self.snapshot._get_version_path("")
        if not os.path.isdir(snapshot_config_path):
            os.makedirs(snapshot_config_path)

        with open(f"{snapshot_config_path}{filename}.yml", "w") as f:
            yaml.dump(
                config_yaml,
                f,
                Dumper=LiteralSafeDumper,
                default_flow_style=False,
                sort_keys=False,
                indent=4,
            )
            self.snapshot.debug(f"Saved configuration to the snapshot version: '{snapshot_config_path}{filename}.yml'")

    def read(self, filename, load_from_use_version=False):
        """
        Read a structured YAML configuration file using self._config.
        The YAML file will contain all meta and config details.
        """

        if load_from_use_version:
            with open(f"{self.snapshot.dir_path}/{filename}.yml") as f:
                config_yaml = yaml.safe_load(f)
        else:
            os.makedirs("config", exist_ok=True)
            with open(f"config/{filename}.yml") as f:
                config_yaml = yaml.safe_load(f)

        self._config = {}
        for comp_name, comp_details in config_yaml.items():
            self._config[comp_name] = {}
            self._config[comp_name]["meta"] = comp_details.get("meta", {})
            self._config[comp_name]["config"] = {}
            for param, param_details in comp_details.get("config", {}).items():
                param_copy = param_details.copy()
                type_str = param_copy.get("type")
                if type_str:
                    param_copy["type"] = self.default_type_mapping.get(type_str, type_str)
                self._config[comp_name]["config"][param] = param_copy

        if load_from_use_version:
            self.snapshot.debug(f"Loaded configuration from the snapshot version: {self.snapshot.version_name}")
        else:
            self.snapshot.debug(f"Loaded configuration from custom configuration file: 'config/{filename}.yml'")
