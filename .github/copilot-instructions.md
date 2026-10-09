# piSensor Workspace Guidance

## System Role
- `piSensor` is the heading-side edge ingestion service for inductive count data and sensor heartbeat.
- Its job is to capture reliable machine-floor signals and report them to connectCoreAPI with minimal business interpretation.

## Production Context
- Main runtime is `sensor.py` (root crontab `@reboot`); `sensor_screen.py` is the OLED variant. Both report through `connect_client.py`.
- Since v4 (2026-10-09) the service never touches the database: it posts counts and heartbeats to `POST /api/v1/heading/headers/{HEAD_ID}/telemetry` with its device token, and the API writes the `iwt_db` tables (`heading_rates`, `heading_data`) that downstream dashboards and compute jobs read. Counts wait in a local SQLite buffer until the API acknowledges them.

## Connected Projects
- `htdocs` defines much of the current heading business meaning and dashboard behavior.
- `connectCompute` should own derived summaries, trends, and planning-oriented transformations.
- `connectFastAPI` should expose stable metrics based on compute outputs.
- `connectBot` should use API responses rather than raw sensor tables.

## Working Rules
- Keep GPIO capture, count buffering, reporting, and heartbeat logic reliable and simple.
- Never add a database connection or credential back: a change the sensor needs on the server is an API change in connectCoreAPI.
- Avoid embedding reporting logic in the edge service.
- When changing table writes or timing behavior, note downstream effects on compute, API, and dashboard consumers.