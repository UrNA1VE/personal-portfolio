"""Bed-savings and readmission calculations using synthetic visit fields."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import pandas as pd

from analytics.demographics import visits_with_reference_data


DEFAULT_SAVING_RATES = {
    "ALC": 0.30,
    "LOS & other": 0.20,
    "Readmission 7 day": 0.15,
    "Readmission 30 day": 0.10,
    "Short stay review": 0.12,
}

SERVICE_SAVING_RATES = {
    "General Medicine": {
        "ALC": 0.42,
        "LOS & other": 0.24,
        "Readmission 7 day": 0.18,
        "Readmission 30 day": 0.12,
        "Short stay review": 0.14,
    },
    "General Surgery": {
        "ALC": 0.22,
        "LOS & other": 0.18,
        "Readmission 7 day": 0.12,
        "Readmission 30 day": 0.08,
        "Short stay review": 0.20,
    },
    "Child Health": {
        "ALC": 0.12,
        "LOS & other": 0.14,
        "Readmission 7 day": 0.10,
        "Readmission 30 day": 0.07,
        "Short stay review": 0.18,
    },
    "Maternal Care": {
        "ALC": 0.08,
        "LOS & other": 0.10,
        "Readmission 7 day": 0.08,
        "Readmission 30 day": 0.05,
        "Short stay review": 0.16,
    },
    "Mental Health": {
        "ALC": 0.28,
        "LOS & other": 0.26,
        "Readmission 7 day": 0.22,
        "Readmission 30 day": 0.16,
        "Short stay review": 0.08,
    },
}


def saving_rate_for(
    service_name: str,
    saving_type: str,
    custom_rates: pd.DataFrame | None = None,
) -> float:
    if custom_rates is not None and not custom_rates.empty:
        matches = custom_rates[
            (custom_rates["service_name"] == service_name)
            & (custom_rates["saving_type"] == saving_type)
        ]
        if not matches.empty:
            return float(matches["saving_rate"].iloc[0])

    return SERVICE_SAVING_RATES.get(service_name, {}).get(
        saving_type,
        DEFAULT_SAVING_RATES[saving_type],
    )


def default_saving_rate_table() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for service_name, saving_rates in SERVICE_SAVING_RATES.items():
        for saving_type, saving_rate in saving_rates.items():
            rows.append(
                {
                    "service_name": service_name,
                    "saving_type": saving_type,
                    "saving_rate": saving_rate,
                }
            )
    return pd.DataFrame(rows)


def add_readmission_flags(visits: pd.DataFrame) -> pd.DataFrame:
    ordered = visits.sort_values(["patient_id", "diagnosis_code", "admission_ts"]).copy()
    ordered["previous_discharge_ts"] = ordered.groupby(["patient_id", "diagnosis_code"])["discharge_ts"].shift()
    days_since_previous = (
        ordered["admission_ts"] - ordered["previous_discharge_ts"]
    ).dt.total_seconds() / 86_400
    ordered["readmit_7_day"] = days_since_previous.between(0, 7, inclusive="both")
    ordered["readmit_30_day"] = days_since_previous.between(0, 30, inclusive="both")
    return ordered.drop(columns=["previous_discharge_ts"])


SavingAlgorithm = Callable[[Any], float]


def length_of_stay(row: Any) -> float:
    return max(float(row.length_of_stay_days), 0.0)


def alc_saving_days(row: Any) -> float:
    return min(max(float(row.alclos), 0.0), length_of_stay(row))


def los_other_saving_days(row: Any) -> float:
    stay_days = length_of_stay(row)
    typical_case_days = max(stay_days - float(row.elos), 0.0) if str(row.riwexcl) == "00" else 0.0
    outlier_days = max(stay_days - float(row.trim_days), 0.0) if str(row.riwexcl) == "10" else 0.0
    return max(typical_case_days, outlier_days)


def readmission_7_day_saving_days(row: Any) -> float:
    return length_of_stay(row) if bool(row.readmit_7_day) else 0.0


def readmission_30_day_saving_days(row: Any) -> float:
    if bool(row.readmit_7_day):
        return 0.0
    return length_of_stay(row) if bool(row.readmit_30_day) else 0.0


def short_stay_review_saving_days(row: Any) -> float:
    stay_days = length_of_stay(row)
    return stay_days if row.admission_type == "Emergency" and stay_days < 1.5 else 0.0


SAVING_ALGORITHMS: dict[str, SavingAlgorithm] = {
    "ALC": alc_saving_days,
    "LOS & other": los_other_saving_days,
    "Readmission 7 day": readmission_7_day_saving_days,
    "Readmission 30 day": readmission_30_day_saving_days,
    "Short stay review": short_stay_review_saving_days,
}


def selected_saving_algorithms(enabled_algorithms: Iterable[str] | None = None) -> dict[str, SavingAlgorithm]:
    if enabled_algorithms is None:
        return SAVING_ALGORITHMS

    missing = set(enabled_algorithms) - set(SAVING_ALGORITHMS)
    if missing:
        raise ValueError(f"Unsupported saving algorithm(s): {sorted(missing)}")

    return {name: SAVING_ALGORITHMS[name] for name in enabled_algorithms}


def visit_saving_opportunities(
    visits: pd.DataFrame,
    services: pd.DataFrame,
    facilities: pd.DataFrame,
    diagnoses: pd.DataFrame | None = None,
    enabled_algorithms: Iterable[str] | None = None,
) -> pd.DataFrame:
    enriched = visits_with_reference_data(add_readmission_flags(visits), services, facilities, diagnoses)
    algorithms = selected_saving_algorithms(enabled_algorithms)
    rows: list[dict[str, object]] = []

    for row in enriched.itertuples(index=False):
        for saving_type, algorithm in algorithms.items():
            avoidable_days = algorithm(row)
            if avoidable_days <= 0:
                continue
            rows.append(
                {
                    "visit_id": row.visit_id,
                    "patient_id": row.patient_id,
                    "diagnosis_code": row.diagnosis_code,
                    "facility_name": row.facility_name,
                    "service_name": row.service_name,
                    "saving_type": saving_type,
                    "avoidable_days": avoidable_days,
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "visit_id",
            "patient_id",
            "diagnosis_code",
            "facility_name",
            "service_name",
            "saving_type",
            "avoidable_days",
        ],
    )


def savings_scenarios(
    visits: pd.DataFrame,
    services: pd.DataFrame,
    facilities: pd.DataFrame,
    diagnoses: pd.DataFrame | None = None,
    enabled_algorithms: Iterable[str] | None = None,
    saving_rates: pd.DataFrame | None = None,
) -> pd.DataFrame:
    opportunities = visit_saving_opportunities(
        visits,
        services,
        facilities,
        diagnoses,
        enabled_algorithms=enabled_algorithms,
    )
    if opportunities.empty:
        return pd.DataFrame(
            columns=[
                "facility_name",
                "service_name",
                "saving_type",
                "maximal_beds",
                "saving_rate",
                "demand_reduction",
            ]
        )

    day_count = max(visits["admission_ts"].dt.normalize().nunique(), 1)
    results = (
        opportunities.groupby(["facility_name", "service_name", "saving_type"], as_index=False)["avoidable_days"]
        .sum()
        .assign(
            maximal_beds=lambda frame: frame["avoidable_days"] / day_count,
            saving_rate=lambda frame: frame.apply(
                lambda row: saving_rate_for(str(row["service_name"]), str(row["saving_type"]), saving_rates),
                axis=1,
            ),
            demand_reduction=lambda frame: frame.apply(
                lambda row: row["maximal_beds"] * row["saving_rate"],
                axis=1,
            ),
        )
        .drop(columns=["avoidable_days"])
    )
    return results.assign(
        maximal_beds=lambda frame: frame["maximal_beds"].round(1),
        demand_reduction=lambda frame: frame["demand_reduction"].round(1),
    )
