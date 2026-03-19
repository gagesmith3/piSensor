# piSensor Workspace Guidance

## System Role
- `piSensor` is the heading-side edge ingestion service for inductive count data and sensor heartbeat.
- Its job is to capture reliable machine-floor signals and write them into the database with minimal business interpretation.

## Production Context
- Main runtime is currently `sensor.py` unless a task explicitly targets one of the alternate variants.
- The service writes heading counts and related health data into `iwt_db` tables used by downstream dashboards and compute jobs.

## Connected Projects
- `htdocs` defines much of the current heading business meaning and dashboard behavior.
- `connectCompute` should own derived summaries, trends, and planning-oriented transformations.
- `connectFastAPI` should expose stable metrics based on compute outputs.
- `connectBot` should use API responses rather than raw sensor tables.

## Working Rules
- Keep GPIO capture, count logging, reconnection behavior, and heartbeat logic reliable and simple.
- Avoid embedding reporting logic in the edge service.
- When changing table writes or timing behavior, note downstream effects on compute, API, and dashboard consumers.