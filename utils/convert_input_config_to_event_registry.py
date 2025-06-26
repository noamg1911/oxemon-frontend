from pathlib import Path
from argparse import ArgumentParser
from collections import defaultdict
from yaml import safe_load, safe_dump

DEFAULT_EVENT_REGISTRY_PATH = "event_registry.yaml"
REQUIRED_ENTRY_KEYS = ["type", "module_id", "event_id", "operations"]
VALID_ENTRY_TYPES = {"counter", "gauge", "enum"}
VALID_ENTRY_OPERATIONS = {"sum", "average", "rolling_average", "show_current"}


def validate_entry(name: str, entry: dict):
    """
    Validates/asserts that a monitoring entry contains the necessary fields/field values.

    Args:
        name: Name of the entry
        entry: The entry dictionary.
    """
    for key in REQUIRED_ENTRY_KEYS:
        assert key in entry, f"Missing key '{key}' in '{name}'"

    assert entry["type"] in VALID_ENTRY_TYPES, f"Invalid type {entry['type']} in '{name}'"

    assert isinstance(entry["operations"], list), f"'operations' must be a list in '{name}'"
    for operation in entry["operations"]:
        assert operation in VALID_ENTRY_OPERATIONS, f"Invalid operation {operation} in '{name}'"

    if entry["type"] == "enum":
        assert "values" in entry, f"Missing 'values' for enum type in '{name}'"
        assert isinstance(entry["values"], dict), f"'values' must be a dict in '{name}'"


def validate_config(config_data: dict):
    """
    Validates the monitoring configuration data (YAML configuration).
    """
    for name, entry in config_data.items():
        validate_entry(name, entry)


def convert_monitoring_entries_to_event_registry(monitoring_entries: dict) -> defaultdict:
    """
    Creates an "event-centric" dictionary from a given dictionary of monitoring entries.
    """
    registry = defaultdict(lambda: {"modules": []})
    for entry in monitoring_entries.values():
        event_id = entry["event_id"]
        registry[event_id]["type"] = entry["type"]
        registry[event_id]["modules"].append(entry["module_id"])
        if entry["type"] == "enum":
            registry[event_id]["values"] = entry["values"]

    return dict(registry)


def save_event_registry(event_registry_data: dict, file_path: str):
    """
    Saves the event registry data to some file.
    """
    with open(file_path, "w") as f:
        safe_dump(event_registry_data, f, sort_keys=False)


def create_event_registry_from_config(monitoring_entries_config_path: str, event_registry_path: str):
    """
    Creates an event registry from a given monitoring entries configuration file.
    """
    config_data = safe_load(Path(monitoring_entries_config_path).read_text())
    validate_config(config_data)
    event_registry = convert_monitoring_entries_to_event_registry(config_data)
    save_event_registry(event_registry, event_registry_path)


def parse_args():
    parser = ArgumentParser(description="Convert module-event config into metric registry format")

    parser.add_argument("-i", "--input", type=Path, required=True, 
                        help="Input YAML config (e.g. monitor_config.yaml)")
    parser.add_argument("-o", "--output", type=Path, default=Path(DEFAULT_EVENT_REGISTRY_PATH),
                        help="Output YAML (e.g. event_registry.yaml)")

    args = parser.parse_args()

    input_path = args.input
    if not (input_path.exists() and input_path.is_file() and input_path.suffix == ".yaml"):
        raise ValueError(f"File {input_path} is an invalid yaml file")

    if args.output:
        if not args.output.suffix == ".yaml":
            raise ValueError("Output file must be a .yaml file")
    return args


if __name__ == "__main__":
    arguments = parse_args()
    create_event_registry_from_config(arguments.input, arguments.output)
