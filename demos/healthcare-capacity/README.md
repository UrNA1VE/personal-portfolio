# Healthcare Capacity Analytics Pipeline

Beginning Azure-style structure for the synthetic hospital capacity analytics draft.

This project is a public-safe technical demo. It currently combines a Python synthetic data generator, container-local raw data, validation reports, DuckDB/dbt-style transformations, dashboard-prepared outputs, and a Streamlit dashboard. The containerized version does not use persistent cloud storage; data edits are intended for demo sessions only.

The raw generated layer is event-level. It stores patient demographics in `patients.csv` and hospital activity in `patient_events.csv`; visit-level tables are derived during ETL rather than stored as raw source files.

## Current status

This project is under active development. The original draft is preserved as source material under `docs/original-draft-readme.md`, and its sanitized migration plan is under `docs/sanitized-migration-plan.md`.

## Data safety boundary

All demo data must remain synthetic or explicitly public-safe.

Do not add real SHA data, patient data, internal screenshots, internal table names, private operational numbers, credentials, local network paths, or confidential documents.

## Azure-style layout

```text
demos/healthcare-capacity/
├── azure/
│   ├── container-apps/        Container deployment notes
│   ├── functions/python-etl/  Future serverless ETL notes
│   ├── sql-database/          Planned Azure SQL schema/model notes
│   └── static-web-apps/       Planned public site deployment notes
├── ci/                        Draft CI workflow reference
├── config/                    Safe environment/profile examples only
├── dashboard/streamlit/       Current dashboard draft
├── data/synthetic/            Synthetic CSV samples
├── data/container/            Container-local raw, backup, and report data
├── data/etl_prepared/         Derived visit-level ETL output
├── data/dashboard_prepared/   Aggregated dashboard output destination
├── docs/                      Draft documentation and migration notes
├── etl/event_editor/          Raw event editor helpers
├── etl/pipeline/              Local ETL pipeline runners
├── etl/synthetic_data_generator/
├── notebooks/
├── sql/dbt_hospital_capacity/
└── tests/python/
```

## Current local workflow

Install Python dependencies from this folder:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Generate synthetic CSV files:

```sh
python etl/synthetic_data_generator/generate_fake_data.py
```

The generated raw source files include:

```text
patients.csv
admission_chart.csv
patient_events.csv
facilities.csv
services.csv
units.csv
diagnoses.csv
capacity.csv
population_growth.csv
```

`admission_chart.csv` stores one admission/start-state row per visit, including admitted unit, service, diagnosis, facility, admission time, and admission type. `patient_events.csv` stores updates after admission with `type` values of `location`, `service`, `diagnosis`, and `discharge`. Open inpatient encounters simply do not have a discharge event. The ETL derives analytical `visits` from admission chart rows plus the latest service, diagnosis, location, and discharge events.

Run the local container/DuckDB pipeline:

```sh
python etl/pipeline/run_container_pipeline.py
```

Each run clears the previous container-local raw/report files and overwrites `data/dashboard_prepared/` with the latest aggregated outputs to limit local storage use.

The ETL also writes derived visit-level tables to:

```text
data/etl_prepared/
└── visits.csv
```

Run the Streamlit dashboard draft:

```sh
streamlit run dashboard/streamlit/streamlit_app.py
```

Run the same dashboard in a local container:

```sh
docker compose up --build
```

Then open:

```text
http://localhost:8501
```

The local compose setup mounts `./data` into the container, so generated raw files, backup files, ETL outputs, and dashboard-prepared CSVs remain available on your machine after the container stops.

Stop the local container:

```sh
docker compose down
```

Run Python tests:

```sh
pytest tests/python
```

## Current dbt workflow

The dbt project is stored at:

```text
sql/dbt_hospital_capacity/
```

The draft currently targets PostgreSQL for local development. Azure SQL adaptation is planned in `azure/sql-database/README.md`.

## Planned Azure workflow

```text
Generate fake data or upload template-based CSVs
  -> container-local raw data
  -> data validation report
  -> DuckDB/dbt-style transformations
  -> dashboard_prepared aggregated outputs
  -> Streamlit dashboard visuals
```

For Azure deployment, the intended low-cost target is Azure Container Apps on the Consumption plan:

```text
Container image
  -> Azure Container Apps
  -> External ingress on port 8501
  -> min replicas = 0
  -> max replicas = 1
```

This keeps the app session-oriented and avoids persistent storage costs. Set an Azure monthly budget alert, such as `$5`, in Cost Management; Azure budgets send alerts but do not hard-stop resources automatically.

## Next implementation steps

1. Add template-based CSV upload next to the current fake-data generator.
2. Deploy the Streamlit dashboard as an Azure Container Apps service.
3. Tune cold-start behavior and container image size.
4. Add clearer data contract documentation for accepted user uploads.
5. Add dashboard screenshots generated only from synthetic data.
