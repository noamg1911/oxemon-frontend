import time
from pathlib import Path
import yaml
from prometheus_client import start_http_server, Counter, Gauge, REGISTRY

import socket
import json
from icd_converter import converter

metric_instances = {}


def load_registry(path='event_registry.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def create_metric_families(registry_data):
    for event_id, event_data in registry_data.items():
        metric_family_name = replace_whitespace_in_name(f"{event_id}")
        metric_type = event_data["type"]

        if metric_type == "counter":
            metric_family = Counter(metric_family_name, f"{event_id}", ["module"])

        elif metric_type == "gauge" or metric_type == "enum":
            metric_family = Gauge(metric_family_name, f"{event_id}", ["module"])

        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        metric_instances[metric_family_name] = {}

        for module_id in event_data["modules"]:
            module_name = replace_whitespace_in_name(module_id)
            metric_instance = metric_family.labels(module=module_name)
            metric_instances[metric_family_name][module_name] = metric_instance


# Very basic sanitization for Prometheus metric names
def replace_whitespace_in_name(name):
    return name.strip().lower().replace(" ", "_")

# Simulated update loop (replace this with real UART/UDP input handling)
def simulate_metric_updates():
    import random

    while True:
        for event_id, module_dict in metric_instances.items():
            for metric_family_name, metric_instance in module_dict.items():
                value = random.randint(1, 5)
                if isinstance(metric_instance, Counter):
                    print(f"setting {metric_instance} to {value}")
                    metric_instance.inc(value)
                else:
                    print(f"setting {metric_instance} to {value}")
                    metric_instance.set(value)
        time.sleep(1)


def push_event(event: converter.EventUpdate):
    module_name = replace_whitespace_in_name(event.module_name)
    event_name = replace_whitespace_in_name(event.event_name)

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


# Configuration
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 8765

def main_metric_updates():
    with open("example/oxemon_dictionary.json", "r") as f:
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
                event = converter.convert_incoming_message(
                    message=data,
                    conversion_map=hash_converter
                )
                print(event)
                push_event(event)
            except ValueError as e:
                print("Got invalid message: ", e)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        sock.close()

if __name__ == "__main__":
    registry = load_registry("event_registry.yaml")
    create_metric_families(registry)

    start_http_server(8000)
    print("Prometheus metrics available at http://localhost:8000/metrics")

    main_metric_updates()
