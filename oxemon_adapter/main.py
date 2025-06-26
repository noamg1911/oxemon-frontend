import time
import yaml
from prometheus_client import start_http_server, Counter, Gauge
import signal
import requests

import socket
import json
import converter
from upload_dashboards import upload_module_dashboards, load_module_dashboards


EVENT_REGISTRY_PATH = "config/event_registry.yaml"
DICTIONARY_PATH = "config/oxemon_dictionary.json"
DASHBOARDS_PATH = "config/dashboards/"

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 1414

LOKI_BASE_URL = "http://loki:3100"
LOKI_LOG_MESSAGE_TEMPLATE = {
    "streams": [{
        "stream": {
            "module": "module",
            "level": "info"
        },
        "values": [["", "message"]]
    }]
}

metric_instances = {}
shutdown = False


def handle_signal(signum, frame):
    global shutdown
    print(f"Received signal {signum}, preparing to exit...")
    shutdown = True


# Very basic sanitization for Prometheus metric names (same as in `generate_grafana_dashboards_from_input_config.py`)
def replace_whitespace(name):
    return name.strip().lower().replace(" ", "_")


def get_string_of_current_time():
    return str(int(time.time() * 1e9))


def load_registry(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def create_metric_families(registry_data):
    for event_id, event_data in registry_data.items():
        metric_family_name = replace_whitespace(event_id)
        metric_type = event_data["type"]

        if metric_type == "counter":
            metric_family = Counter(metric_family_name, event_id, ["module"])

        elif metric_type == "gauge" or metric_type == "enum":
            metric_family = Gauge(metric_family_name, event_id, ["module"])

        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        metric_instances[metric_family_name] = {}

        for module_id in event_data["modules"]:
            module_name = replace_whitespace(module_id)
            metric_instance = metric_family.labels(module=module_name)
            metric_instances[metric_family_name][module_name] = metric_instance


def push_event(event: converter.EventUpdate):
    module_name = replace_whitespace(event.module_name)
    event_name = replace_whitespace(event.event_name)

    if event.event_type == "log":
        log_message = LOKI_LOG_MESSAGE_TEMPLATE
        log_message["streams"][0]["stream"]["module"] = module_name
        log_message["streams"][0]["values"] = [[get_string_of_current_time(), event.event_name]]
        requests.post(f"{LOKI_BASE_URL}/loki/api/v1/push", json=log_message, timeout = 5)
        return

    try:
        metric = metric_instances[event_name][module_name]
        if isinstance(metric, Counter):
            print(f"setting counter {metric} to {event.value}")
            metric.inc(event.value)
        else:
            print(f"setting enum {metric} to {event.value}")
            metric.set(event.value)
    except KeyError:
        pass


def main_metric_updates():
    global shutdown
    with open(DICTIONARY_PATH, "r") as f:
        hash_converter = converter.create_conversion_map(json.load(f))

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the IP and port
    sock.bind((LISTEN_IP, LISTEN_PORT))
    sock.settimeout(1.0)  # Set timeout to 1 second (for gracefully exiting)
    print(f"Listening for UDP packets on {LISTEN_IP}:{LISTEN_PORT}...")

    try:
        while not shutdown:
            try:
                data, addr = sock.recvfrom(4096)
                print(f"Received data from {addr}: {data}")
            except socket.timeout:
                # Just loop again and check shutdown flag
                continue

            print(f"\nReceived {len(data)} bytes from {addr}:")
            print(f"Raw bytes: {data}")

            try:
                event = converter.convert_incoming_message(message=data, conversion_map=hash_converter)
                print(event)
                push_event(event)
            except ValueError as e:
                print("Got invalid message: ", e)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock.close()


if __name__ == "__main__":
    registry = load_registry(EVENT_REGISTRY_PATH)
    create_metric_families(registry)

    dashboards = load_module_dashboards(DASHBOARDS_PATH)
    upload_module_dashboards(dashboards)

    start_http_server(8000)
    print("Prometheus metrics available at http://oxemon_adapter:8000/metrics")

    # To exit graefully when "docker-compose down"
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    main_metric_updates()
