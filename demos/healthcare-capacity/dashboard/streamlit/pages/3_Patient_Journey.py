import streamlit as st
import pandas as pd

import bootstrap  # noqa: F401
from analytics.journey import journey_segments, patient_visit_summary
from utils.charts import patient_journey_chart
from utils.database import load_dashboard_data


st.set_page_config(page_title="Patient Journey", layout="wide")
tables, source_label = load_dashboard_data()

visits = tables["visits"]
facilities = tables["facilities"]
services = tables["services"]
diagnoses = tables["diagnoses"]
unit_changes = tables["unit_changes"]
units = tables["units"]

st.title("Patient Journey")
st.caption(f"Source: {source_label}")

patient_id = st.selectbox("Patient", sorted(visits["patient_id"].unique()))
patient_visits = visits[visits["patient_id"] == patient_id].sort_values("admission_ts")
visit_id = st.selectbox("Visit", patient_visits["visit_id"].tolist())

summary = patient_visit_summary(visit_id, visits, facilities, services, diagnoses)
segments = journey_segments(visit_id, visits, unit_changes, units, services)

cols = st.columns(5)
cols[0].metric("Age", int(summary["age"]))
cols[1].metric("Gender", summary["gender"])
cols[2].metric("Facility", summary["facility_name"])
cols[3].metric("Service", summary["service_name"])
cols[4].metric("Admission", summary["admission_type"])

st.subheader("Timeline")
st.altair_chart(patient_journey_chart(segments), use_container_width=True)

st.subheader("Visit Details")
details = {
    "Visit ID": summary["visit_id"],
    "Patient ID": summary["patient_id"],
    "Diagnosis": summary["diagnosis_name"],
    "Admission": summary["admission_ts"],
    "Discharge": summary["discharge_ts"],
    "ALC LOS": summary["alclos"],
    "ELOS": summary["elos"],
    "RIWEXCL": summary["riwexcl"],
    "Trim days": summary["trim_days"],
}
st.dataframe(
    pd.DataFrame([{"field": field, "value": value} for field, value in details.items()]),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Location Events")
st.dataframe(
    unit_changes[unit_changes["visit_id"] == visit_id]
    .merge(units[["unit_id", "unit_name", "unit_service"]], on="unit_id", how="left")
    .sort_values("event_ts"),
    use_container_width=True,
    hide_index=True,
)
