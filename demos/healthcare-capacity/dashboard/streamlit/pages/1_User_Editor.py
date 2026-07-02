"""User editor for raw healthcare-capacity event data."""

from pathlib import Path

import pandas as pd
import streamlit as st

import bootstrap  # noqa: F401
from etl.event_editor.editor import add_admission, add_event, add_patient, remove_event, retrieve_back_up, update_event
from etl.pipeline.run_container_pipeline import RAW_DATA_DIR, run_etl_from_existing_raw


st.set_page_config(page_title="User Editor", page_icon="✏️", layout="wide")
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def raw_file_exists(file_name: str) -> bool:
    return (RAW_DATA_DIR / file_name).exists()


def load_raw_table(file_name: str, **kwargs) -> pd.DataFrame:
    path = RAW_DATA_DIR / file_name
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame()


def option_label(frame: pd.DataFrame, id_column: str, label_column: str):
    labels = dict(zip(frame[id_column], frame[label_column]))
    return lambda value: f"{value} - {labels.get(value, '')}".rstrip(" -")


def log_change(message: str) -> None:
    st.session_state["change_log"].append(message)
    st.session_state["pending_updates"] = True


def clear_editor_state() -> None:
    st.session_state["change_log"] = []
    st.session_state["pending_updates"] = False


if "change_log" not in st.session_state:
    st.session_state["change_log"] = []
if "pending_updates" not in st.session_state:
    st.session_state["pending_updates"] = False

patients = load_raw_table("patients.csv")
admission_chart = load_raw_table("admission_chart.csv", parse_dates=["admission_ts"])
patient_events = load_raw_table("patient_events.csv", parse_dates=["event_ts"])
facilities = load_raw_table("facilities.csv")
services = load_raw_table("services.csv")
units = load_raw_table("units.csv")
diagnoses = load_raw_table("diagnoses.csv")

raw_ready = all(
    raw_file_exists(file_name)
    for file_name in ["patients.csv", "admission_chart.csv", "patient_events.csv"]
)
reference_ready = all(not frame.empty for frame in [facilities, services, units, diagnoses])

st.title("User Editor")
st.caption("Add admissions and events to the raw event-level data, then submit once to rebuild the dashboard tables.")

editor_col, submit_col = st.columns([4, 1.35])

with editor_col:
    with st.expander("New Admission", expanded=False):
        if not raw_ready or not reference_ready:
            st.info("Generate fake data on the main page before using the editor.")
        else:
            patient_mode = st.radio("Patient", ["New patient", "Returning patient"], horizontal=True)
            if patient_mode == "New patient":
                age = st.selectbox("Age", list(range(0, 96)))
                gender = st.selectbox("Gender", ["Female", "Male"])
                region = st.selectbox("Region", sorted(facilities["region"].dropna().unique().tolist()))
                selected_patient_id = None
            else:
                selected_patient_id = st.selectbox("Patient ID", patients["patient_id"].tolist())
                age = gender = region = None

            facility_id = st.selectbox(
                "Facility",
                facilities["facility_id"].tolist(),
                format_func=option_label(facilities, "facility_id", "facility_name"),
            )
            facility_units = units[units["facility_id"] == facility_id]
            admitted_unit_id = st.selectbox(
                "Admitted unit",
                facility_units["unit_id"].tolist(),
                format_func=option_label(facility_units, "unit_id", "unit_name"),
            )
            admitted_service_id = st.selectbox(
                "Admitted service",
                services["service_id"].tolist(),
                format_func=option_label(services, "service_id", "service_name"),
            )
            service_diagnoses = diagnoses[diagnoses["service_id"] == admitted_service_id]
            admitted_diagnosis_code = st.selectbox(
                "Admitted diagnosis",
                service_diagnoses["diagnosis_code"].tolist(),
                format_func=option_label(service_diagnoses, "diagnosis_code", "diagnosis_name"),
            )
            admission_type = st.selectbox("Admission type", ["Emergency", "Urgent", "Elective"])

            if st.button("Add admission"):
                if patient_mode == "New patient":
                    selected_patient_id = add_patient(int(age), str(gender), str(region))
                    log_change(f"Added patient {selected_patient_id}")
                visit_id = add_admission(
                    patient_id=str(selected_patient_id),
                    facility_id=str(facility_id),
                    admitted_unit_id=str(admitted_unit_id),
                    admitted_service_id=str(admitted_service_id),
                    admitted_diagnosis_code=str(admitted_diagnosis_code),
                    admission_type=str(admission_type),
                )
                log_change(f"Added admission {visit_id} for patient {selected_patient_id}")
                st.success(f"Added admission {visit_id}")

    with st.expander("New Event", expanded=False):
        if not raw_ready or not reference_ready:
            st.info("Generate fake data on the main page before using the editor.")
        else:
            visit_id = st.selectbox("Visit", admission_chart["visit_id"].tolist(), key="new-event-visit")
            event_type = st.selectbox("Event type", ["location", "service", "diagnosis", "discharge"])

            if event_type == "location":
                visit_facility = admission_chart.loc[admission_chart["visit_id"] == visit_id, "facility_id"].iloc[0]
                event_units = units[units["facility_id"] == visit_facility]
                event_value = st.selectbox(
                    "Event value",
                    event_units["unit_id"].tolist(),
                    format_func=option_label(event_units, "unit_id", "unit_name"),
                    key="new-event-location-value",
                )
            elif event_type == "service":
                event_value = st.selectbox(
                    "Event value",
                    services["service_id"].tolist(),
                    format_func=option_label(services, "service_id", "service_name"),
                    key="new-event-service-value",
                )
            elif event_type == "diagnosis":
                event_value = st.selectbox(
                    "Event value",
                    diagnoses["diagnosis_code"].tolist(),
                    format_func=option_label(diagnoses, "diagnosis_code", "diagnosis_name"),
                    key="new-event-diagnosis-value",
                )
            else:
                event_value = st.selectbox(
                    "Event value",
                    ["discharged", "home", "transfer", "expired"],
                    key="new-event-discharge-value",
                )

            if st.button("Add event"):
                event_id = add_event(str(visit_id), str(event_type), str(event_value))
                log_change(f"Added {event_type} event {event_id} for visit {visit_id}: {event_value}")
                st.success(f"Added event {event_id}")

    with st.expander("Edit Historical Event", expanded=False):
        if not raw_ready or not reference_ready:
            st.info("Generate fake data on the main page before using the editor.")
        else:
            patient_id = st.selectbox("Patient ID", patients["patient_id"].tolist(), key="patient-id")
            visit_options = admission_chart.loc[
                admission_chart["patient_id"] == patient_id,
                "visit_id",
            ].tolist()
            if not visit_options:
                st.info("No visits available for this patient.")
            else:
                visit_id = st.selectbox("Visit ID", visit_options, key="visit-id")
                event_options = patient_events.loc[
                    (patient_events["patient_id"] == patient_id)
                    & (patient_events["visit_id"] == visit_id),
                    "event_id",
                ].tolist()
                if not event_options:
                    st.info("No events available for this visit.")
                else:
                    event_id = st.selectbox("Event ID", event_options, key="edited-event")
                    selected_event = patient_events[patient_events["event_id"] == event_id]
                    st.dataframe(selected_event, use_container_width=True, hide_index=True)

                    event_type = selected_event["type"].iloc[0]

                    if event_type == "location":
                        visit_facility = admission_chart.loc[
                            admission_chart["visit_id"] == visit_id,
                            "facility_id",
                        ].iloc[0]
                        event_units = units[units["facility_id"] == visit_facility]
                        event_value = st.selectbox(
                            "Event value",
                            event_units["unit_id"].tolist(),
                            format_func=option_label(event_units, "unit_id", "unit_name"),
                            key="edit-event-location-value",
                        )
                    elif event_type == "service":
                        event_value = st.selectbox(
                            "Event value",
                            services["service_id"].tolist(),
                            format_func=option_label(services, "service_id", "service_name"),
                            key="edit-event-service-value",
                        )
                    elif event_type == "diagnosis":
                        event_value = st.selectbox(
                            "Event value",
                            diagnoses["diagnosis_code"].tolist(),
                            format_func=option_label(diagnoses, "diagnosis_code", "diagnosis_name"),
                            key="edit-event-diagnosis-value",
                        )
                    else:
                        event_value = st.selectbox(
                            "Event value",
                            ["discharged", "home", "transfer", "expired"],
                            key="edit-event-discharge-value",
                        )

                    if st.button("Update event"):
                        update_event(str(event_id), str(event_value))
                        log_change(
                            f"Updated {patient_id} event {event_id} "
                            f"for visit {visit_id}: {event_value}"
                        )
                        st.success(f"Updated event {event_id}")


    with st.expander("Remove Previous Event", expanded=False):
        if patient_events.empty:
            st.info("Generate fake data on the main page before removing events.")
        else:
            removable_events = patient_events.sort_values("event_ts", ascending=False)
            event_id = st.selectbox("Event", removable_events["event_id"].tolist())
            selected_event = removable_events[removable_events["event_id"] == event_id]
            st.dataframe(selected_event, use_container_width=True, hide_index=True)
            confirm_remove = st.checkbox("Confirm removal")

            if st.button("Remove event", disabled=not confirm_remove):
                event_row = selected_event.iloc[0]
                remove_event(str(event_id))
                log_change(
                    f"Removed {event_row['type']} event {event_id} "
                    f"for visit {event_row['visit_id']}: {event_row['value']}"
                )
                st.success(f"Removed event {event_id}")

with submit_col:
    st.subheader("Submit")
    if st.session_state["change_log"]:
        st.warning("Pending changes")
        for item in st.session_state["change_log"]:
            st.caption(f"- {item}")
    else:
        st.info("No pending changes.")

    if st.button("Submit Updates", type="primary", use_container_width=True):
        with st.spinner("Rebuilding ETL and dashboard tables..."):
            result = run_etl_from_existing_raw()
        clear_editor_state()
        st.success(f"Tables rebuilt: {result['status']}")

    if st.button("Clear All Pending Changes", use_container_width=True):
        retrieve_back_up()
        clear_editor_state()
        st.success("Raw files restored from backup.")
