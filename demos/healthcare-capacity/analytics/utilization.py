"""Capacity, census, and bed-demand calculations."""

from __future__ import annotations
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.streamlit.utils.database import *

import numpy as np
import pandas as pd


DEMAND_PERCENTILES = {
    "General Medicine": 0.95,
    "General Surgery": 0.90,
    "Child Health": 0.90,
    "Maternal Care": 0.85,
    "Mental Health": 0.95,
}


def capacity_summary(daily: pd.DataFrame) -> pd.DataFrame:
    return (
        daily.groupby(["facility_name", "service_name"], as_index=False)
        .agg(
            planned_beds=("staffed_beds", "median"),
            average_census=("average_census", "mean"),
            peak_census=("peak_census", "max"),
        )
        .assign(
            planned_beds=lambda frame: frame["planned_beds"].round(0).astype(int),
            average_census=lambda frame: frame["average_census"].round(1),
            peak_census=lambda frame: frame["peak_census"].round(0).astype(int),
        )
        .sort_values(["facility_name", "planned_beds"], ascending=[True, False])
    )


def service_census_summary(daily: pd.DataFrame) -> pd.DataFrame:
    return (
        daily.groupby(["facility_name", "service_name"], as_index=False)
        .agg(
            low_day=("peak_census", lambda series: series.quantile(0.25)),
            average_day=("peak_census", "mean"),
            high_day=("peak_census", lambda series: series.quantile(0.75)),
            peak_day=("peak_census", lambda series: series.quantile(0.95)),
            planned_beds=("staffed_beds", "mean"),
        )
        .assign(
            occupancy=lambda frame: frame["average_day"] / frame["planned_beds"],
            low_day=lambda frame: frame["low_day"].round(1),
            average_day=lambda frame: frame["average_day"].round(1),
            high_day=lambda frame: frame["high_day"].round(1),
            peak_day=lambda frame: frame["peak_day"].round(1),
            planned_beds=lambda frame: frame["planned_beds"].round(1),
        )
        .sort_values("average_day", ascending=False)
    )


def current_bed_demand(daily: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for (facility_name, service_name), frame in daily.groupby(["facility_name", "service_name"]):
        percentile = DEMAND_PERCENTILES.get(str(service_name), 0.95)
        rows.append(
            {
                "facility_name": facility_name,
                "service_name": service_name,
                "demand": frame["peak_census"].quantile(percentile, interpolation="higher"),
                "funded_capacity": frame["staffed_beds"].median(),
            }
        )

    result = pd.DataFrame(rows)
    result["demand"] = np.ceil(result["demand"]).astype(int)
    result["funded_capacity"] = np.ceil(result["funded_capacity"]).astype(int)
    result["variance"] = result["funded_capacity"] - result["demand"]
    return result.sort_values("demand", ascending=False)


def _population_growth_by_service(
    demographics: pd.DataFrame,
    population_growth: pd.DataFrame,
) -> pd.DataFrame:
    weighted = demographics.merge(
        population_growth,
        on=["region", "age_group", "gender"],
        how="left",
    )
    weighted["weighted_growth"] = weighted["patient_days"] * weighted["growth_index"]
    return (
        weighted.groupby(["facility_name", "service_name", "year"], as_index=False)
        .agg(
            weighted_growth=("weighted_growth", "sum"),
            patient_days=("patient_days", "sum"),
        )
        .assign(growth_index=lambda frame: frame["weighted_growth"] / frame["patient_days"])
        [["facility_name", "service_name", "year", "growth_index"]]
    )


def bed_demand_no_adjustment(
    daily: pd.DataFrame,
    demographics: pd.DataFrame,
    population_growth: pd.DataFrame,
) -> pd.DataFrame:
    base_demand = current_bed_demand(daily)
    growth = _population_growth_by_service(demographics, population_growth)
    projected = base_demand.merge(growth, on=["facility_name", "service_name"], how="left")
    projected["demand"] = np.ceil(projected["demand"] * projected["growth_index"]).astype(int)
    projected["funded_capacity"] = np.ceil(projected["funded_capacity"]).astype(int)
    projected["variance"] = projected["funded_capacity"] - projected["demand"]
    return projected.sort_values(["year", "facility_name", "demand"], ascending=[True, True, False])


# if __name__ == "__main__":
#     tables = build_sample_marts()
#     daily = tables["daily"]
#     from analytics.demographics import demographics_summary

#     demographics = demographics_summary(
#         tables["visits"],
#         tables["services"],
#         tables["facilities"],
#         tables["diagnoses"],
#     )
#     test1 = capacity_summary(daily=daily)
#     test2 = service_census_summary(daily=daily)
#     test3 = bed_demand_no_adjustment(daily, demographics, tables["population_growth"])
