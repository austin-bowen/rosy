from pathlib import Path

import yaml

from rosy.network import get_hostname


def load_config(path: Path) -> dict:
    with path.open('r') as file:
        return yaml.safe_load(file)


def is_enabled(config: dict) -> bool:
    disabled = config.get('disabled', False)
    return not disabled and is_enabled_on_host(config)


def is_enabled_on_host(config: dict) -> bool:
    hostname = get_hostname()
    on_host = config.get('on_host', hostname)
    return on_host == hostname
