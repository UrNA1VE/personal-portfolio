# Azure Function Python ETL Plan

Placeholder for converting the local Python loader into a serverless ETL step.

Planned responsibilities:

- Read synthetic CSV files from Azure Blob Storage
- Validate schema, required fields, date ranges, and nonnegative capacity values
- Load clean records into Azure SQL staging tables
- Write validation summaries and error records to SQL/reporting outputs

The first implementation can reuse logic from `etl/synthetic_data_generator/` and the current local PostgreSQL loader as reference material.
