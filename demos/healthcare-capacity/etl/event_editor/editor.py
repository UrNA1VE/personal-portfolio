"""Helpers for editing raw healthcare-capacity source files."""

from __future__ import annotations

import sys
import shutil
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
RAW_DATA_DIR = PROJECT_ROOT / "data" / "container" / "raw"
BACKUP_DATA_DIR = PROJECT_ROOT / "data" / "container" / "backup"
EDITABLE_RAW_FILES = ["patients.csv", "admission_chart.csv", "patient_events.csv"]
from etl.synthetic_data_generator.generate_fake_data import write_csvs


def _next_id(frame: pd.DataFrame, column: str, prefix: str, width: int) -> str:
    if frame.empty:
        next_number = 1
    else:
        next_number = int(pd.to_numeric(frame[column].str.removeprefix(prefix)).max()) + 1
    return f"{prefix}{next_number:0{width}d}"


def add_patient(age: int, gender: str, region: str) -> str:
    raw_table = {"patients": pd.read_csv(RAW_DATA_DIR / "patients.csv")}
    patients = raw_table["patients"]
    patient_id = _next_id(patients, "patient_id", "PAT-", 6)
    new_patient = pd.DataFrame([
        {
            "patient_id": patient_id,
            "age": age,
            "gender": gender,
            "region": region,
        }
    ])

    patients = pd.concat([patients, new_patient], ignore_index=True)
    raw_table["patients"] = patients
    write_csvs(raw_table, RAW_DATA_DIR)
    return patient_id


def add_admission(
    patient_id: str,
    facility_id: str,
    admitted_unit_id: str,
    admitted_service_id: str,
    admitted_diagnosis_code: str,
    admission_type: str,
) -> str:
    raw_table = {"admission_chart": pd.read_csv(RAW_DATA_DIR / "admission_chart.csv")}
    admission_chart = raw_table["admission_chart"]
    admission_ts = pd.Timestamp.now().floor("min")

    visit_id = _next_id(admission_chart, "visit_id", "ENC-", 6)
    new_admission = pd.DataFrame([{
        "visit_id": visit_id,
        "patient_id": patient_id,
        "facility_id": facility_id,
        "admitted_unit_id": admitted_unit_id,
        "admitted_service_id": admitted_service_id,
        "admitted_diagnosis_code": admitted_diagnosis_code,
        "admission_ts": admission_ts,
        "admission_type": admission_type,
    }])
    admission_chart = pd.concat([admission_chart, new_admission], ignore_index=True)
    raw_table["admission_chart"] = admission_chart
    write_csvs(raw_table, RAW_DATA_DIR)
    return visit_id


def add_event(visit_id: str, event_type: str, value: str) -> str:
    allowed_event_types = {"location", "service", "diagnosis", "discharge"}
    if event_type not in allowed_event_types:
        raise ValueError(f"event_type must be one of {sorted(allowed_event_types)}")

    raw_table = {"patient_events": pd.read_csv(RAW_DATA_DIR / "patient_events.csv")}
    patient_events = raw_table["patient_events"]
    event_id = _next_id(patient_events, "event_id", "EVT-", 8)
    event_ts = pd.Timestamp.now().floor("min")

    admission_chart = pd.read_csv(RAW_DATA_DIR / "admission_chart.csv")
    matches = admission_chart.loc[admission_chart["visit_id"] == visit_id]
    if matches.empty:
        raise ValueError(f"visit_id not found in admission_chart.csv: {visit_id}")
    admission = matches.iloc[0]

    new_event = pd.DataFrame([
        {
            "event_id": event_id,
            "visit_id": visit_id,
            "patient_id": admission["patient_id"],
            "event_ts": event_ts,
            "type": event_type,
            "value": value,
            "facility_id": admission["facility_id"],
        }
    ])

    patient_events = pd.concat([patient_events, new_event], ignore_index=True)
    raw_table["patient_events"] = patient_events
    write_csvs(raw_table, RAW_DATA_DIR)
    return event_id


def update_event(event_id: str, value: str) -> None:
    raw_table = {"patient_events": pd.read_csv(RAW_DATA_DIR / "patient_events.csv")}
    patient_events = raw_table["patient_events"]
    if not patient_events["event_id"].eq(event_id).any():
        raise ValueError(f"event_id not found in patient_events.csv: {event_id}")
    patient_events.loc[patient_events["event_id"] == event_id, "value"] = value
    raw_table["patient_events"] = patient_events
    write_csvs(raw_table, RAW_DATA_DIR)


def remove_event(event_id: str) -> None:
    raw_table = {"patient_events": pd.read_csv(RAW_DATA_DIR / "patient_events.csv")}
    patient_events = raw_table["patient_events"]
    if not patient_events["event_id"].eq(event_id).any():
        raise ValueError(f"event_id not found in patient_events.csv: {event_id}")
    patient_events = patient_events[patient_events["event_id"] != event_id]
    raw_table["patient_events"] = patient_events
    write_csvs(raw_table, RAW_DATA_DIR)


def retrieve_back_up() -> None:
    if not BACKUP_DATA_DIR.exists():
        raise FileNotFoundError(f"Backup folder not found: {BACKUP_DATA_DIR}")

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for file_name in EDITABLE_RAW_FILES:
        source = BACKUP_DATA_DIR / file_name
        if not source.exists():
            raise FileNotFoundError(f"Backup file not found: {source}")
        shutil.copy2(source, RAW_DATA_DIR / file_name)


# if __name__ == "__main__":
#     add_patient(20, "male", "X")
