import time
import yaml
from prometheus_client import start_http_server, Counter, Gauge

import socket
import json
import converter
from utils.generate_grafana_dashboards_from_input_config import replace_whitespace


EVENT_REGISTRY_PATH = "config/event_registry.yaml"
DICTIONARY_PATH = "config/oxemon_dictionary.json"

LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 1414


metric_instances = {}


def load_registry(path="event_registry.yaml"):
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
    with open(DICTIONARY_PATH, "r") as f:
        hash_converter = converter.create_conversion_map(json.load(f))

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to the IP and port
    sock.bind((LISTEN_IP, LISTEN_PORT))
    print(f"Listening for UDP packets on {LISTEN_IP}:{LISTEN_PORT}...")

    try:
        while True:
            data, addr = sock.recvfrom(4096)  # 4096 bytes buffer
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

    start_http_server(8000)
    print("Prometheus metrics available at http://oxemon_adapter:8000/metrics")

    main_metric_updates()
