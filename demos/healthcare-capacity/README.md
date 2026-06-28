# Healthcare Capacity Analytics Pipeline

Beginning Azure-style structure for the synthetic hospital capacity analytics draft.

This project is a public-safe technical demo. It currently combines a Python synthetic data generator, dbt SQL models, PostgreSQL local development, and a Streamlit dashboard. The next phase is to adapt the same workflow toward Azure Blob Storage, Azure Function Python ETL, Azure SQL Database, and public dashboard/reporting outputs.

## Current status

Draft imported from:

```text
/Users/qiankangwang/Desktop/python/BedNeedsAnalysis/hospital-capacity-analytics
```

The original draft is preserved as source material under `docs/original-draft-readme.md`, and its sanitized migration plan is under `docs/sanitized-migration-plan.md`.

## Data safety boundary

All demo data must remain synthetic or explicitly public-safe.

Do not add real SHA data, patient data, internal screenshots, internal table names, private operational numbers, credentials, local network paths, or confidential documents.

## Azure-style layout

```text
demos/healthcare-capacity/
├── azure/
│   ├── blob-storage/          Planned synthetic file landing zone notes
│   ├── functions/python-etl/  Planned Azure Function ETL notes
│   ├── sql-database/          Planned Azure SQL schema/model notes
│   └── static-web-apps/       Planned public site deployment notes
├── ci/                        Draft CI workflow reference
├── config/                    Safe environment/profile examples only
├── dashboard/streamlit/       Current dashboard draft
├── data/synthetic/            Synthetic CSV samples
├── docs/                      Draft documentation and migration notes
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

Run the Streamlit dashboard draft:

```sh
streamlit run dashboard/streamlit/streamlit_app.py
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
Synthetic CSVs
  -> Azure Blob Storage landing container
  -> Azure Function Python ETL validation/loading
  -> Azure SQL Database staging/intermediate/mart models
  -> dashboard/reporting outputs
  -> Astro project page documentation
```

## Next implementation steps

1. Add Azure Blob container naming and file conventions.
2. Convert the local loader into an Azure Function-oriented ETL module.
3. Decide whether dbt will target Azure SQL directly or remain as local SQL documentation first.
4. Add dashboard screenshots generated only from synthetic data.
5. Update the Astro project page with implementation details as each piece becomes real.
