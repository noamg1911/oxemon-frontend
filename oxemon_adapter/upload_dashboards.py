import requests
import json
from pathlib import Path
import time
from grafana_api_handling import create_grafana_api_key


GRAFANA_URL = "http://grafana:3000"


def check_dashboard_exists(title: str, grafana_api_header: dict):
    try:
        response = requests.get(f"{GRAFANA_URL}/api/search?query={title}", headers=grafana_api_header, timeout=5)
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
    

def upload_module_dashboards(module_dashboards_data: list, folder_id=0, overwrite=True):
    grafana_api_key = create_grafana_api_key()
    print(grafana_api_key)
    api_header = {
        "Authorization": f"Bearer {grafana_api_key}",
        "Content-Type": "application/json"
    }
    for dashboard in module_dashboards_data:
        existing_dashboard_uid = check_dashboard_exists(dashboard["title"], api_header)
        if existing_dashboard_uid:
            dashboard["uid"] = existing_dashboard_uid

        payload = {
            "dashboard": dashboard,
            "folderId": folder_id,
            "overwrite": overwrite
        }

        response = requests.post(f"{GRAFANA_URL}/api/dashboards/db", headers=api_header, data=json.dumps(payload),
                                 timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed to upload dashboard: {response.status_code}")
            print(response.text)


def load_module_dashboards(dashboards_directory: str):
    """
    Saves the given dashboards in some directory.
    """
    dashboards = []
    for dashboard_path in Path(dashboards_directory).iterdir():
        with dashboard_path.open("r") as f:
            dashboards.append(json.load(f))

    return dashboards

