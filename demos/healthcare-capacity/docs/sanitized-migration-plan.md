# Sanitized Migration Plan

## Source workflow observed

The private R project follows a script-based pipeline:

1. Connect to internal source systems and reference files.
2. Normalize encounter, location, and service events.
3. derive visit admission/discharge intervals.
4. Expand visit intervals into hourly census snapshots.
5. Align service-level census with capacity.
6. Calculate utilization, percentile demand, and pressure indicators.
7. Render charts, tables, and narrative reporting.

## Public Version 1 mapping

| Existing logic pattern | Public implementation |
|---|---|
| Operational extracts | Synthetic CSVs loaded to PostgreSQL `raw` tables |
| Source cleanup | dbt staging models |
| Hour sequence | `int_hourly_calendar` |
| Visit interval expansion | `int_visit_hours` |
| Enriched census snapshot | `int_patient_hourly_snapshot` |
| Census aggregation | `fct_hourly_census` |
| Capacity comparison | `fct_daily_utilization` |
| Pressure thresholds | `fct_service_capacity_pressure` |
| Validation checks | dbt tests and `fct_data_quality_summary` |
| R Markdown/dashboard output | Streamlit multipage app |

## Confidential material excluded

The public project does not reproduce source-system table names, employer or facility
names, operational codes, patient/linkage identifiers, network or local paths,
credentials, geographic rules, mapping files, facility-specific adjustments, or
internal planning assumptions. All names, records, dates, and values in the demo are
synthetic.

## Version 1 boundary

Included: visits, generic facilities/services, capacity, admission/discharge logic,
hourly expansion, census, utilization, pressure metrics, data quality, and dashboard
marts.

Deferred: patient data, specialized bypass/access rules, waitlist assumptions,
length-of-stay savings scenarios, demographic forecasting, authentication,
orchestration, and production deployment.
