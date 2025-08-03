import pytest

from rosytest.integration.cli.utils import rosy_cli


class TestRosy:
    @pytest.mark.parametrize('flag', ['-v', '--version'])
    def test_rosy_version_flag(self, flag: str):
        with rosy_cli(flag) as proc:
            proc.expect(r'^rosy \d+\.\d+\.\d+\n$')
