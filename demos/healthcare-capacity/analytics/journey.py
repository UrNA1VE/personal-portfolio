"""Patient journey helpers for synthetic visit and unit-change data."""

from __future__ import annotations

import pandas as pd


def patient_visit_summary(
    visit_id: str,
    visits: pd.DataFrame,
    facilities: pd.DataFrame,
    services: pd.DataFrame,
    diagnoses: pd.DataFrame,
) -> pd.Series:
    matches = (
        visits[visits["visit_id"] == visit_id]
        .merge(facilities[["facility_id", "facility_name", "region"]], on="facility_id", how="left")
        .merge(services[["service_id", "service_name"]], on="service_id", how="left")
        .merge(diagnoses[["diagnosis_code", "diagnosis_name"]], on="diagnosis_code", how="left")
    )
    if matches.empty:
        raise ValueError(f"Unknown visit_id: {visit_id}")
    return matches.iloc[0]


def location_segments(
    visit_id: str,
    visits: pd.DataFrame,
    unit_changes: pd.DataFrame,
    units: pd.DataFrame,
) -> pd.DataFrame:
    visit = visits.loc[visits["visit_id"] == visit_id].iloc[0]
    changes = (
        unit_changes[unit_changes["visit_id"] == visit_id]
        .sort_values("event_ts")
        .merge(units[["unit_id", "unit_name", "unit_service"]], on="unit_id", how="left")
        .reset_index(drop=True)
    )
    if changes.empty:
        return pd.DataFrame(columns=["track", "label", "start_ts", "end_ts", "detail"])

    next_times = changes["event_ts"].shift(-1)
    changes["start_ts"] = changes["event_ts"]
    changes["end_ts"] = next_times.fillna(pd.Timestamp(visit["discharge_ts"]))
    changes["track"] = "Location"
    changes["label"] = changes["unit_name"].fillna(changes["unit_id"])
    changes["detail"] = changes["unit_service"].fillna("Unknown service")
    return changes[["track", "label", "start_ts", "end_ts", "detail"]]


def service_segments(
    visit_id: str,
    visits: pd.DataFrame,
    services: pd.DataFrame,
) -> pd.DataFrame:
    row = visits[visits["visit_id"] == visit_id].merge(services, on="service_id", how="left").iloc[0]
    return pd.DataFrame(
        [
            {
                "track": "Service",
                "label": row["service_name"],
                "start_ts": pd.Timestamp(row["admission_ts"]),
                "end_ts": pd.Timestamp(row["discharge_ts"]),
                "detail": "Primary service; service-change events are a future input placeholder.",
            }
        ]
    )


def journey_segments(
    visit_id: str,
    visits: pd.DataFrame,
    unit_changes: pd.DataFrame,
    units: pd.DataFrame,
    services: pd.DataFrame,
) -> pd.DataFrame:
    return pd.concat(
        [
            location_segments(visit_id, visits, unit_changes, units),
            service_segments(visit_id, visits, services),
        ],
        ignore_index=True,
    )
