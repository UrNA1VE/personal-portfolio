"""Convenience builders for report-ready synthetic analytics tables."""

from __future__ import annotations

import pandas as pd

from analytics.access import outpatient_surgery_access_placeholder
from analytics.demographics import demographics_summary
from analytics.projection import bed_needs_projection
from analytics.savings import savings_scenarios
from analytics.utilization import bed_demand_no_adjustment, capacity_summary, current_bed_demand, service_census_summary


def build_report_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    daily = tables["daily"]
    visits = tables["visits"]
    services = tables["services"]
    facilities = tables["facilities"]
    diagnoses = tables.get("diagnoses")
    population_growth = tables.get("population_growth")

    capacity = capacity_summary(daily)
    census = service_census_summary(daily)
    demographics = demographics_summary(visits, services, facilities, diagnoses)
    demand = bed_demand_no_adjustment(daily, demographics, population_growth)
    current_demand = current_bed_demand(daily)
    savings = savings_scenarios(visits, services, facilities, diagnoses)
    projection = bed_needs_projection(
        current_demand,
        savings,
        start_year=int(daily["calendar_date"].dt.year.min()),
        demographics=demographics,
        population_growth=population_growth,
    )
    return {
        "capacity": capacity,
        "census": census,
        "demand": demand,
        "current_demand": current_demand,
        "savings": savings,
        "demographics": demographics,
        "projection": projection,
        "access_placeholder": outpatient_surgery_access_placeholder(),
    }
