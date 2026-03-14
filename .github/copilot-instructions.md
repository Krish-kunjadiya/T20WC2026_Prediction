# Project Guidelines

## Scope
- Primary application code lives in `t20_wc_2026/`.
- Root-level `Data/` is a curated dataset snapshot, while `t20_wc_2026/data/` is the working data-lake layout for the app.

## Code Style
- Use Python 3 with type hints for new/updated functions.
- Keep module docstrings concise and present for executable scripts.
- Prefer environment-driven configuration via `python-dotenv`; do not hardcode credentials or hostnames.
- Match existing ingestion style shown in `t20_wc_2026/src/ingestion/db_init.py` and `t20_wc_2026/src/ingestion/simulator.py`.

## Architecture
- `t20_wc_2026/src/ingestion/`: currently implemented runtime scripts for data simulation and database initialization.
- `t20_wc_2026/src/etl/`: transformations from raw to bronze/silver/gold.
- `t20_wc_2026/src/ml/`: model training/inference code.
- `t20_wc_2026/src/api/`: FastAPI serving layer.
- `t20_wc_2026/src/dashboard/`: Streamlit UI.
- `t20_wc_2026/src/genai/`: LLM/RAG and assistant flows.

Keep boundaries clear: ingestion writes source/live events, ETL produces curated tables/files, ML consumes curated features, API/dashboard read model outputs and serving artifacts.

## Build and Test
Run commands from `t20_wc_2026/` unless a task explicitly targets root data files.

- Install deps: `pip install -r requirements.txt`
- Validate DB connectivity: `python src/ingestion/db_init.py`
- Run live simulator: `python src/ingestion/simulator.py`

Current status:
- No formal automated test suite is configured yet.
- `docker-compose.yml` exists but is currently empty.

## Data Conventions
- Data lake folders under `t20_wc_2026/data/` follow layered semantics:
  - `raw/` for source extracts (including CricSheet CSVs)
  - `bronze/` for ingested raw-normalized outputs
  - `silver/` for cleaned/validated datasets
  - `gold/` for analytics/model-ready marts
- Do not commit generated large artifacts unless explicitly requested.

## Agent Behavior
- Before adding new frameworks, check if required packages are already in `t20_wc_2026/requirements.txt`.
- Prefer small, incremental edits over broad scaffolding rewrites.
- If creating new modules in currently empty areas (`api`, `etl`, `ml`, `dashboard`, `genai`), include a minimal runnable entry point and clear docstring so follow-up tasks can build on it.
