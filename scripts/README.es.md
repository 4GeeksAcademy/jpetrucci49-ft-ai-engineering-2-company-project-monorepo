# Carpeta `scripts`

Esta carpeta contiene **scripts auxiliares** del monorepo: automatizaciones de desarrollo, utilidades de mantenimiento, tareas repetitivas (setup, lint, migraciones, generación de datos, etc.) y tooling interno.

- **Propósito principal**: agrupar herramientas de soporte que no pertenecen a una app/agente/pipeline específico, pero facilitan el trabajo del equipo.
- **Recomendación**: documenta cada script (qué hace, parámetros, requisitos, ejemplos de uso) y procura que sean reproducibles (y seguros) en distintos entornos.

## Entorno Python (uv)

Los scripts Python usan **[uv](https://docs.astral.sh/uv/)**. La configuración está en la **raíz del repositorio** (`pyproject.toml`, `uv.lock`).

```bash
uv sync
uv run python scripts/analyze.py data/raw/incidents.csv
```
