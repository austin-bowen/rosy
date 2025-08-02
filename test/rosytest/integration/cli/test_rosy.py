import pytest

from rosytest.integration.cli.utils import assert_rosy_output_matches


class TestRosy:
    @pytest.mark.parametrize('flag', ['-v', '--version'])
    def test_rosy_version_flag(self, flag: str):
        assert_rosy_output_matches(
            flag,
            pattern=r'^rosy \d+\.\d+\.\d+\n$',
        )
