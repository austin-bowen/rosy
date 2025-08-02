import subprocess
from re import match


def assert_rosy_output_matches(
        *args: str,
        pattern: str,
        check: bool = True,
) -> None:
    result = run_rosy(*args, check=check)
    assert match(pattern, result.stdout), (
        f'Output did not match pattern: {pattern}\n'
        f'Output was: {result.stdout}'
    )


def run_rosy(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ['rosy', *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        text=True,
    )

    if check:
        assert not result.stderr

    return result
