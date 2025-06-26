from pathlib import Path
from argparse import ArgumentParser
from collections import defaultdict
import requests
from hashlib import sha256
from copy import deepcopy
from json import dump, dumps
from yaml import safe_load
from convert_input_config_to_event_registry import validate_config

PROMETHEUS_SOURCE_UID = "prometheus_ds"
GRAFANA_URL = "http://localhost:3000"
GRAFANA_API_KEY = "glsa_qn9KbdNF0UGiOyVOgb8ZhX3w53PyaTrl_99c955e9"
GRAFANA_API_HEADER = {
    "Authorization": f"Bearer {GRAFANA_API_KEY}",
    "Content-Type": "application/json"
}
DEFAULT_DASHBOARDS_DIRECTORY_NAME = "dashboards"
PANEL_HEIGHT = 8
PANEL_WIDTH = 12
TEMPLATE_PANEL = {
    "id": "id",
    "type": "timeseries",
    "title": "title",
    "datasource": {"type": "prometheus", "uid": PROMETHEUS_SOURCE_UID},
    "targets": [{"expr": "expr", "legendFormat": "{{module}}", "interval": "", "refId": "refId"}],
    "gridPos": {"h": PANEL_HEIGHT, "w": PANEL_WIDTH, "x": 0, "y": 0},
    "fieldConfig": {"defaults": {"mappings": []}},
}


# Very basic sanitization for Prometheus metric names
def replace_whitespace(name):
    return name.strip().lower().replace(" ", "_")


def generate_promql_expression(metric_name: str, module_label: str, operation: str) -> str:
    """
    Figures out the relevant PromQL expression according to the given metric operation.

    Args:
        metric_name: The name of the metric in prometheus.
        module_label: The value of the module label in prometheus.
        operation: The given operation.
    """
    default_promql_expression = f'{metric_name}{{module="{module_label}"}}'
    possible_promql_expressions = {
        "rolling_average": f"rate({default_promql_expression}[1m])",
        "sum": f"sum({default_promql_expression})",
        "show_current": default_promql_expression,
    }
    return possible_promql_expressions.get(operation, default_promql_expression)


def generate_grafana_enum_mapping_from_config_entry(entry: dict) -> list:
    """
    Maps an entry's enum values to their string values in Grafana.
    """
    return [
        {
            "type": "value",
            "options": {str(num): {"index": int(num), "text": value} for num, value in entry["values"].items()}
        }
    ]


def create_dashboard(name: str, panels: list) -> dict:
    """
    Creates a Grafana dashboard dictionary.

    Args:
        name: Name/title of the dashboard.
        panels: The panels that will be in the dashboard.
    """
    return {
        "uid": sha256(name.encode()).hexdigest()[:20],
        "title": name,
        "panels": panels,
        "schemaVersion": 37,
        "version": 1,
        "refresh": "5s",
        "timezone": "browser",
    }


def convert_monitoring_entries_to_module_dashboards(monitoring_entries: dict) -> list:
    """
    Creates a list of module-centric dashboards from a given dictionary of monitoring entries.
    """
    module_panels = defaultdict(list)
    panel_id = 0

    for entry_name, entry in monitoring_entries.items():
        base_panel = deepcopy(TEMPLATE_PANEL)
        if entry["type"] == "enum":
            base_panel["fieldConfig"]["defaults"]["mappings"] = generate_grafana_enum_mapping_from_config_entry(entry)
        metric_name = replace_whitespace(entry["event_id"])
        module_label_name = replace_whitespace(entry["module_id"])
        if entry["type"] == "counter":
            metric_name = f"{metric_name}_total"
        metric_operations = entry.get("operations", ["value"])
        for operation in metric_operations:
            operation = replace_whitespace(operation)
            panel = deepcopy(base_panel)
            panel["id"] = panel_id
            panel["title"] = f"{entry_name} - {operation}"
            panel["targets"][0]["expr"] = generate_promql_expression(metric_name, module_label_name, operation)
            panel["targets"][0]["title"] = panel["title"]
            panel["gridPos"]["y"] = panel_id * PANEL_HEIGHT
            module_panels[entry["module_id"]].append(panel)
            panel_id += 1

    return [create_dashboard(module_name, panels) for module_name, panels in module_panels.items()]


def save_module_dashboards(module_dashboards_data: list, dashboards_directory: str):
    """
    Saves the given dashboards in some directory.
    """
    for dashboard in module_dashboards_data:
        dashboard_file_path = Path(dashboards_directory) / f"{dashboard['title'].replace(' ', '_')}_dashboard.json"
        with open(dashboard_file_path, "w") as f:
            dump(dashboard, f, indent=2)


def upload_module_dashboards(module_dashboards_data: list, folder_id=0, overwrite=True):
    for dashboard in module_dashboards_data:
        existing_dashboard_uid = check_dashboard_exists(dashboard["title"])
        if existing_dashboard_uid:
            dashboard["uid"] = existing_dashboard_uid

        payload = {
            "dashboard": dashboard,
            "folderId": folder_id,
            "overwrite": overwrite
        }

        response = requests.post(f"{GRAFANA_URL}/api/dashboards/db", headers=GRAFANA_API_HEADER, data=dumps(payload),
                                 timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed to upload dashboard: {response.status_code}")
            print(response.text)


def check_dashboard_exists(title: str):
    try:
        response = requests.get(f"{GRAFANA_URL}/api/search?query={title}", headers=GRAFANA_API_HEADER, timeout=5)
        if response.status_code != 200:
            return None
        results = response.json()

        for existing_dashboards in results:
            if existing_dashboards.get("title") == title and existing_dashboards.get("type") == "dash-db":
                return existing_dashboards.get("uid")
        return None
    except Exception as e:
        print(f"Error while checking dashboard: {e}")
        return None


def create_module_dashboards_from_config(monitoring_entries_config_path: str, dashboards_directory: str):
    """
    Creates module-centric dashboards from a given monitoring entries configuration file.
    """
    config_data = safe_load(Path(monitoring_entries_config_path).read_text())
    validate_config(config_data)
    Path(dashboards_directory).mkdir(parents=True, exist_ok=True)
    module_dashboards = convert_monitoring_entries_to_module_dashboards(config_data)
    save_module_dashboards(module_dashboards, dashboards_directory)
    upload_module_dashboards(module_dashboards)


def parse_args():
    parser = ArgumentParser(description="Convert module-event config into module-centric Grafana dashboard files")
    parser.add_argument("-i", "--input", type=Path, required=True,
                        help="Input YAML config (e.g. monitor_config.yaml)")
    parser.add_argument("-o", "--output", type=Path, default=Path(DEFAULT_DASHBOARDS_DIRECTORY_NAME),
                        help="Output directory (e.g. outputs)")
    args = parser.parse_args()

    input_path = args.input
    if not (input_path.exists() and input_path.is_file() and input_path.suffix == ".yaml"):
        raise ValueError(f"File {input_path} is an invalid yaml file")

    return args


if __name__ == "__main__":
    arguments = parse_args()
    create_module_dashboards_from_config(arguments.input, arguments.output)
