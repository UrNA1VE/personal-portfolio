"""Bed-needs projections using synthetic population growth."""

from __future__ import annotations

import pandas as pd


PROGRAM_GROWTH = {
    "General Medicine": 0.018,
    "General Surgery": 0.014,
    "Child Health": 0.007,
    "Maternal Care": 0.004,
    "Mental Health": 0.022,
}


def _population_growth_by_service(
    demographics: pd.DataFrame,
    population_growth: pd.DataFrame,
) -> pd.DataFrame:
    weighted = demographics.merge(
        population_growth,
        left_on=["region", "age_group", "gender"],
        right_on=["region", "age_group", "gender"],
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


def bed_needs_projection(
    demand: pd.DataFrame,
    savings: pd.DataFrame,
    start_year: int,
    end_year: int = 2040,
    demographics: pd.DataFrame | None = None,
    population_growth: pd.DataFrame | None = None,
) -> pd.DataFrame:
    savings_by_service = (
        savings.groupby(["facility_name", "service_name"], as_index=False)["demand_reduction"].sum()
        if not savings.empty
        else pd.DataFrame(columns=["facility_name", "service_name", "demand_reduction"])
    )
    base = demand.merge(savings_by_service, on=["facility_name", "service_name"], how="left")
    base["demand_reduction"] = base["demand_reduction"].fillna(0)

    growth_lookup = pd.DataFrame()
    if demographics is not None and population_growth is not None:
        growth_lookup = _population_growth_by_service(demographics, population_growth)

    rows: list[dict[str, object]] = []
    for item in base.itertuples(index=False):
        annual_growth = PROGRAM_GROWTH.get(str(item.service_name), 0.012)
        service_growth = growth_lookup[
            (growth_lookup["facility_name"] == item.facility_name)
            & (growth_lookup["service_name"] == item.service_name)
        ]
        for year in range(start_year, end_year + 1):
            if not service_growth.empty:
                matches = service_growth[service_growth["year"] == year]
                growth_index = float(matches["growth_index"].iloc[0]) if not matches.empty else 1.0
            else:
                growth_index = (1 + annual_growth) ** (year - start_year)
            projection = float(item.demand) * growth_index
            adjustment_phase_in = min(max(year - start_year, 0) / 5, 1)
            adjusted = projection - float(item.demand_reduction) * adjustment_phase_in
            rows.append(
                {
                    "facility_name": item.facility_name,
                    "service_name": item.service_name,
                    "year": year,
                    "projection": round(projection),
                    "adjusted_projection": max(round(adjusted), 0),
                }
            )

    return pd.DataFrame(rows)
