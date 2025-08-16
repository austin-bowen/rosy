import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from rosy.cli.launch.config import is_enabled, load_config


def test_load_config():
    with tempfile.NamedTemporaryFile() as f:
        f.write(b"""
domain_id: my_domain
nodes:
  my_node:
    command: python my_node.py
""".strip())
        f.flush()

        path = Path(f.name)
        result = load_config(path)

    assert result == dict(
        domain_id='my_domain',
        nodes=dict(
            my_node=dict(
                command='python my_node.py',
            ),
        ),
    )


@pytest.mark.parametrize('config,expected', [
    (dict(), True),
    (dict(disabled=False), True),
    (dict(on_host='this-host'), True),
    (dict(disabled=False, on_host='this-host'), True),
    (dict(disabled=True), False),
    (dict(on_host='other-host'), False),
    (dict(disabled=True, on_host='this-host'), False),
    (dict(disabled=False, on_host='other-host'), False),
])
@patch('rosy.cli.launch.config.get_hostname')
def test_is_enabled(
        get_hostname_mock,
        config: dict,
        expected: bool,
):
    get_hostname_mock.return_value = 'this-host'
    assert is_enabled(config) is expected
