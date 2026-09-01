# Contributing to SMARTX X-BRIDGE

Thank you for contributing! This file explains how to set up a development environment, run tests, format code, and create releases.

## Development setup

1. Install dependencies with Poetry:

```bash
poetry install
```

2. Create or edit `config/config.json` to configure runtime settings (see `README.md`).

3. Run the app locally:

```bash
poetry run python main.py
```

## Testing

Run the test suite with:

```bash
poetry run pytest
```

Use pytest markers to run specific test groups, for example:

```bash
poetry run pytest -m "integration"
```

## Formatting & Linting

Project uses `ruff` for linting and formatting settings are stored in `pyproject.toml`.

```bash
# Run formatter / linter
poetry run ruff . --fix
```

Optionally run the included format script:

```bash
./scripts/format.sh
```

## Building an executable

Requires `PyInstaller` (included in `tool.poetry.group.dev.dependencies`). Build using the helper script:

```bash
poetry run python scripts/build_exe.py
```

## Migrations

Use the migration helper to autogenerate and apply alembic migrations:

```bash
poetry run python scripts/migrate.py
```

## Releases

Update `pyproject.toml` version, run tests, then tag a release and build artifacts as needed.

## Reporting issues

Open an issue with reproduction steps, environment, and expected vs actual behavior.

Thank you for helping improve SMARTX X-BRIDGE!
