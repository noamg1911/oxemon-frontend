import shutil
import time
from argparse import ArgumentParser
from pathlib import Path
from contextlib import contextmanager

import convert_input_config_to_event_registry
import generate_grafana_dashboards_from_input_config


def parse_args():
    parser = ArgumentParser()

    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    arguments = parser.parse_args()

    # Validate arguments
    if not (arguments.dictionary.exists() and 
            arguments.dictionary.is_file() and 
            arguments.dictionary.suffix == ".json"):
        raise ValueError(f"Dictionary path is invalid {arguments.dictionary}")    
    
    if not (arguments.metrics.exists() and 
            arguments.metrics.is_file() and 
            arguments.metrics.suffix in (".yaml", ".yml")):
        raise ValueError(f"Metrics path is invalid {arguments.metrics}")
    
    if arguments.output.exists() and not arguments.output.is_dir():
        raise ValueError(f"Output directory is invalid {arguments.output}")

    return arguments


@contextmanager
def log_step(name: str, *, verbose: bool = True):
    if verbose:
        print(f"Starting \"{name}\"")
        start_time = time.perf_counter()
    else:
        print(f"Performing \"{name}\"")
    yield
    if verbose:
        end_time = time.perf_counter()
        print(f"    time took: {end_time - start_time:.3f}s")


if __name__ == '__main__':
    args = parse_args()

    with log_step("Create output directory", verbose=False):
        args.output.mkdir(exist_ok=True)

    with log_step("Create event registry"):
        convert_input_config_to_event_registry.create_event_registry_from_config(
            args.metrics,
            args.output / "event_registry.yaml",
        )

    with log_step("Create dashboard configurations"):
        generate_grafana_dashboards_from_input_config.create_module_dashboards_from_config(
            args.metrics,
            args.output / "dashboards"
        )

    with log_step("Copy dictionary file", verbose=False):
        shutil.copy2(str(args.dictionary), str(args.output))
