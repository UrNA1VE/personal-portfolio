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
    patient_events: pd.DataFrame | None = None,
    admission_chart: pd.DataFrame | None = None,
) -> pd.DataFrame:
    visit = visits[visits["visit_id"] == visit_id].iloc[0]
    discharge_ts = pd.Timestamp(visit["discharge_ts"])

    if patient_events is None or admission_chart is None:
        row = visits[visits["visit_id"] == visit_id].merge(services, on="service_id", how="left").iloc[0]
        return pd.DataFrame(
            [
                {
                    "track": "Service",
                    "label": row["service_name"],
                    "start_ts": pd.Timestamp(row["admission_ts"]),
                    "end_ts": discharge_ts,
                    "detail": "Primary service.",
                }
            ]
        )

    admissions = admission_chart[admission_chart["visit_id"] == visit_id]
    if admissions.empty:
        start_service_id = visit["service_id"]
        admission_ts = pd.Timestamp(visit["admission_ts"])
    else:
        admission = admissions.iloc[0]
        start_service_id = admission["admitted_service_id"]
        admission_ts = pd.Timestamp(admission["admission_ts"])

    service_events = (
        patient_events[
            (patient_events["visit_id"] == visit_id)
            & (patient_events["type"] == "service")
        ][["event_id", "event_ts", "value"]]
        .rename(columns={"event_id": "service_event_id", "value": "service_id"})
        .copy()
    )
    start_event = pd.DataFrame(
        [
            {
                "service_event_id": f"ADM-{visit_id}",
                "event_ts": admission_ts,
                "service_id": start_service_id,
            }
        ]
    )
    changes = (
        pd.concat([start_event, service_events], ignore_index=True)
        .sort_values(["event_ts", "service_event_id"])
        .drop_duplicates(["event_ts", "service_id"], keep="first")
        .reset_index(drop=True)
    )
    changes["start_ts"] = changes["event_ts"]
    changes["end_ts"] = changes["event_ts"].shift(-1).fillna(discharge_ts)
    changes = changes[changes["start_ts"] < changes["end_ts"]]
    changes = changes.merge(services[["service_id", "service_name"]], on="service_id", how="left")
    changes["track"] = "Service"
    changes["label"] = changes["service_name"].fillna(changes["service_id"])
    changes["detail"] = changes["service_id"].map(lambda value: f"Service ID: {value}")
    return changes[["track", "label", "start_ts", "end_ts", "detail"]]


def journey_segments(
    visit_id: str,
    visits: pd.DataFrame,
    unit_changes: pd.DataFrame,
    units: pd.DataFrame,
    services: pd.DataFrame,
    patient_events: pd.DataFrame | None = None,
    admission_chart: pd.DataFrame | None = None,
) -> pd.DataFrame:
    return pd.concat(
        [
            location_segments(visit_id, visits, unit_changes, units),
            service_segments(visit_id, visits, services, patient_events, admission_chart),
        ],
        ignore_index=True,
    )
