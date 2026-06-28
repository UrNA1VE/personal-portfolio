"""Synthetic demographic summaries used by projection models."""

from __future__ import annotations

import pandas as pd


def age_group(age: int | float) -> str:
    if age < 18:
        return "0-17"
    if age < 45:
        return "18-44"
    if age < 70:
        return "45-69"
    return "70+"


def visits_with_reference_data(
    visits: pd.DataFrame,
    services: pd.DataFrame,
    facilities: pd.DataFrame,
    diagnoses: pd.DataFrame | None = None,
) -> pd.DataFrame:
    enriched = visits.merge(services[["service_id", "service_name"]], on="service_id", how="left").merge(
        facilities[["facility_id", "facility_name", "region"]],
        on="facility_id",
        how="left",
    )
    if diagnoses is not None and "diagnosis_name" not in enriched.columns:
        enriched = enriched.merge(
            diagnoses[["diagnosis_code", "diagnosis_name"]],
            on="diagnosis_code",
            how="left",
        )
    enriched["length_of_stay_days"] = (
        enriched["discharge_ts"] - enriched["admission_ts"]
    ).dt.total_seconds() / 86_400
    enriched["age_group"] = enriched["age"].map(age_group)
    return enriched


def demographics_summary(
    visits: pd.DataFrame,
    services: pd.DataFrame,
    facilities: pd.DataFrame,
    diagnoses: pd.DataFrame | None = None,
) -> pd.DataFrame:
    enriched = visits_with_reference_data(visits, services, facilities, diagnoses)
    return (
        enriched.groupby(
            ["facility_name", "region", "service_name", "gender", "age_group"],
            as_index=False,
        )
        .agg(patient_days=("length_of_stay_days", "sum"), visits=("visit_id", "nunique"))
        .assign(patient_days=lambda frame: frame["patient_days"].round(1))
        .sort_values(["facility_name", "service_name", "age_group", "gender"])
    )
