from rosytest.util import REPO_ROOT


def test_pyproject_version_matches_rosy_version():
    pyproject_version = _get_pyproject_version()

    from rosy.version import __version__ as rosy_version

    assert pyproject_version == rosy_version


def _get_pyproject_version() -> str:
    pyproject_path = REPO_ROOT / "pyproject.toml"

    with open(pyproject_path, "r") as f:
        for line in f:
            if line.startswith("version"):
                return line.split("=")[1].strip().strip('"')

    raise RuntimeError("Could not find version in pyproject.toml")
