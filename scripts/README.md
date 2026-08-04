# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

## Python environment (uv)

Python scripts in this folder use **[uv](https://docs.astral.sh/uv/)** for dependency management. Configuration lives at the **repository root** — not in this folder.

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Declares Python version and dependencies (e.g. `pandas`) |
| `uv.lock` | Locked dependency versions — commit this file |
| `.python-version` | Pin for local Python 3.12 |
| `.venv/` | Virtual environment created by `uv sync` (gitignored) |

### Setup

From the repository root:

```bash
uv sync
```

### Running a script

```bash
uv run python scripts/analyze.py scripts/incidents.csv
```

### Adding a dependency

From the repository root:

```bash
uv add <package-name>
```

> _Spanish version: [README.es.md](./README.es.md)._
