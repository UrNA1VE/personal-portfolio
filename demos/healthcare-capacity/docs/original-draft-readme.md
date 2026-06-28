# Hospital Capacity Analytics

A public portfolio project demonstrating an end-to-end healthcare capacity analytics
workflow:

**synthetic hospital activity → PostgreSQL raw tables → dbt transformations and tests
→ Streamlit dashboard**

Every person, facility, service, date, and operational value in this repository is
fake. The project is educational and must not be used for clinical or operational
decisions.

## What the project demonstrates

- Reproducible synthetic data generation with Python
- Environment-based PostgreSQL connections
- Layered dbt modeling across staging, intermediate, and mart schemas
- Hourly interval expansion using admission and discharge timestamps
- Hourly census, daily utilization, and capacity-pressure calculations
- dbt data tests and dashboard-facing quality checks
- A multipage Streamlit dashboard and plain-English executive summary
- A GitHub Actions check against an ephemeral PostgreSQL service

## Architecture

```text
Python generator
    ↓ synthetic CSV files
PostgreSQL raw schema
    ↓
dbt staging models
    ↓
hourly calendar → visit-hour expansion → enriched hourly snapshot
    ↓
hourly census → daily utilization → capacity pressure + quality marts
    ↓
Streamlit dashboard and report
```

The hourly census uses snapshot-boundary logic. A visit admitted between clock hours
first appears at the next hourly boundary and is included while
`snapshot_hour < discharge_ts`.

## Project layout

```text
app/                         Streamlit app, pages, and shared utilities
data_generator/              Synthetic data generation and PostgreSQL loading
dbt_hospital_capacity/       dbt sources, models, tests, and profile example
sample_data/                 Generated public demo CSVs
notebooks/                   Optional exploration space
tests/                       Python generator tests
.github/workflows/           Automated Python and dbt checks
```

The sanitized source-to-target assessment is documented in
[`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

## Quick start: dashboard with built-in sample data

Python 3.11 or 3.12 is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python data_generator/generate_fake_data.py
streamlit run app/streamlit_app.py
```

If `DATABASE_URL` is not configured, the app computes demo marts from the generated
CSV files. This makes the portfolio dashboard usable before PostgreSQL is set up.

## Full PostgreSQL + dbt workflow

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Start PostgreSQL:

   ```bash
   docker compose up -d postgres
   ```

3. Generate and load synthetic raw data:

   ```bash
   python data_generator/generate_fake_data.py
   python data_generator/load_to_postgres.py
   ```

4. Configure and run dbt:

   ```bash
   cp dbt_hospital_capacity/profiles.yml.example dbt_hospital_capacity/profiles.yml
   cd dbt_hospital_capacity
   dbt build --profiles-dir .
   cd ..
   ```

5. Run the dashboard:

   ```bash
   streamlit run app/streamlit_app.py
   ```

dbt creates schemas such as `analytics_staging`, `analytics_intermediate`, and
`analytics_marts`. The Streamlit database helper reads final tables from
`analytics_marts`.

## Main analytical models

- `int_hourly_calendar`: complete hourly time spine
- `int_visit_hours`: one row per visit and occupied hourly boundary
- `int_patient_hourly_snapshot`: generic facility/service enrichment
- `fct_hourly_census`: census by facility, service, and hour
- `fct_daily_utilization`: average and peak census compared with staffed beds
- `fct_service_capacity_pressure`: 85%, 90%, and 95% pressure indicators
- `fct_data_quality_summary`: dashboard-ready validation results

## Testing

```bash
pytest
python -m compileall app data_generator tests
cd dbt_hospital_capacity && dbt build --profiles-dir .
```

## Version 2 ideas

- File-upload support with validation and column mapping
- Unit-level movement history and changing service assignments
- Zero-census capacity rows and richer conformance dimensions
- Scenario modeling for temporary capacity changes
- Forecasting with explicit uncertainty intervals
- Containerized app deployment and observability
- More comprehensive Python and dbt integration tests

Version 2 should continue to use synthetic or explicitly approved public data only.
