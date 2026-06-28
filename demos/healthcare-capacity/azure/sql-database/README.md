# Azure SQL Database Plan

Placeholder for adapting the local PostgreSQL/dbt draft to Azure SQL.

Current draft location:

```text
sql/dbt_hospital_capacity/
```

Planned schemas:

- `raw`: synthetic ingested records
- `analytics_staging`: cleaned source-aligned views
- `analytics_intermediate`: hourly expansion and enrichment
- `analytics_marts`: dashboard-ready fact tables and validation summaries

Future work should confirm SQL dialect differences before running dbt models against Azure SQL.
