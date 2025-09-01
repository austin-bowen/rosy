# Contributing

[poetry](https://python-poetry.org/) is used to manage dependencies and packaging.

Common commands:
- `poetry install` to install dependencies.
- `poetry update` to update dependencies and `poetry.lock` file.
- `poetry build` to build the package.
- `poetry publish [--build]` to publish the package to PyPI.
- `./bin/format` to format the code.
- `./bin/test` to run tests.
  - `./bin/unit-test` to run just unit tests.
  - `./bin/integration-test` to run just integration tests.

## PyPI

To publish to PyPI, configure `poetry` to use your credentials following
[these instructions](https://python-poetry.org/docs/repositories/#configuring-credentials).
