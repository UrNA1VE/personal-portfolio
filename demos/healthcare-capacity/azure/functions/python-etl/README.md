# Future Serverless ETL Plan

Placeholder for possible future serverless ETL work.

Current demo scope keeps ETL inside the Streamlit container. The app writes generated data and transformed outputs to container-local folders only, with no long-term cloud storage.

Future responsibilities could include:

- Validate schema, required fields, date ranges, and nonnegative capacity values
- Run DuckDB/dbt-style transformations outside the Streamlit request cycle
- Export validation summaries and reporting outputs
- Optionally connect to persistent storage if future requirements need it

The current implementation reuses logic from `etl/synthetic_data_generator/` and `etl/pipeline/run_container_pipeline.py`.
