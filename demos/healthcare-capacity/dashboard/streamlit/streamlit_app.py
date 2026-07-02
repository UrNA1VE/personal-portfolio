"""Pipeline landing page for the hospital capacity data demo."""

from pathlib import Path

import pandas as pd
import streamlit as st

import bootstrap  # noqa: F401
from etl.pipeline.run_container_pipeline import RAW_DATA_DIR, REPORT_DATA_DIR, run_fake_data_pipeline


st.set_page_config(page_title="Healthcare Capacity Pipeline", page_icon="🏥", layout="wide")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREPARED_DATA_DIR = PROJECT_ROOT / "data" / "dashboard_prepared"
EVENT_SOURCE_FILES = {"patients.csv", "admission_chart.csv", "patient_events.csv"}
REFERENCE_SOURCE_FILES = {
    "capacity.csv",
    "diagnoses.csv",
    "facilities.csv",
    "population_growth.csv",
    "services.csv",
    "units.csv",
}


@st.cache_data
def read_csv_preview(path: str) -> pd.DataFrame:
    return pd.read_csv(path).head(100)


def list_csvs(folder: Path) -> list[Path]:
    return sorted(folder.glob("*.csv")) if folder.exists() else []


def data_viewer(label: str, folder: Path, allowed_files: set[str] | None = None) -> None:
    files = list_csvs(folder)
    if allowed_files is not None:
        files = [path for path in files if path.name in allowed_files]
    if not files:
        st.info(f"No {label} files available yet.")
        return
    selected = st.selectbox(
        f"{label} file",
        files,
        format_func=lambda path: path.name,
        key=f"{label}-{folder}",
    )
    st.caption(str(selected.relative_to(PROJECT_ROOT)))
    st.dataframe(read_csv_preview(str(selected)), use_container_width=True, hide_index=True)


st.title("Healthcare Capacity Analytics Pipeline")
st.caption("Generate synthetic event-level source data, validate it, and build dashboard-ready aggregated tables.")

with st.expander("Data Generator", expanded=True):
    seed = st.number_input("Seed", min_value=1, max_value=999999, value=42, step=1)
    if st.button("Generate fake data", type="primary"):
        with st.spinner("Generating container-local raw data, validating, and transforming..."):
            result = run_fake_data_pipeline(seed=int(seed))
        read_csv_preview.clear()
        st.success(
            f"Pipeline complete: {result.validation_status.upper()} "
            f"({result.validation_issue_count} blocking validation issues)."
        )
        st.caption(f"Raw: {Path(result.raw_dir).relative_to(PROJECT_ROOT)}")
        st.caption(f"Report: {Path(result.report_dir).relative_to(PROJECT_ROOT)}")
        st.caption(f"Aggregated: {Path(result.prepared_dir).relative_to(PROJECT_ROOT)}")

tab_event, tab_reference, tab_aggregated = st.tabs(["Event Data", "Reference Data", "Aggregated Data"])

with tab_event:
    st.subheader("Event Data")
    data_viewer("Event", RAW_DATA_DIR, EVENT_SOURCE_FILES)

    st.subheader("Data Check Report")
    data_viewer("Report", REPORT_DATA_DIR)

with tab_reference:
    st.subheader("Reference Data")
    data_viewer("Reference", RAW_DATA_DIR, REFERENCE_SOURCE_FILES)

with tab_aggregated:
    st.subheader("Aggregated Data")
    data_viewer("Aggregated", PREPARED_DATA_DIR)
