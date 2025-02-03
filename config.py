from pathlib import Path

import yaml


def get_config_local(filename: Path) -> dict:
    with open(filename) as file:
        return yaml.safe_load(file)
