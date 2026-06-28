"""Executive landing page for the hospital capacity dashboard."""

from pathlib import Path

import pandas as pd
import streamlit as st

import bootstrap  # noqa: F401
from utils.charts import (
    bed_demand_chart,
    bed_needs_projection_chart,
    daily_census_capacity_chart,
    demographics_chart,
    savings_chart,
)
from utils.database import load_dashboard_data
from utils.report import executive_summary


st.set_page_config(page_title="Executive Report", page_icon="🏥", layout="wide")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PREPARED_DATA_DIR = PROJECT_ROOT / "data" / "dashboard_prepared"


def load_prepared_dashboard_data():
    required = [
        "daily",
        "pressure",
        "quality",
        "facility_filters",
        "capacity",
        "census",
        "savings",
        "demographics",
        "demand",
        "current_demand",
        "projection",
    ]
    if not all((PREPARED_DATA_DIR / f"{name}.csv").exists() for name in required):
        raise FileNotFoundError("Prepared dashboard tables are missing.")

    tables = {
        "daily": pd.read_csv(PREPARED_DATA_DIR / "daily.csv", parse_dates=["calendar_date"]),
        "pressure": pd.read_csv(PREPARED_DATA_DIR / "pressure.csv", parse_dates=["calendar_date"]),
        "quality": pd.read_csv(PREPARED_DATA_DIR / "quality.csv"),
        "facility_filters": pd.read_csv(PREPARED_DATA_DIR / "facility_filters.csv"),
        "capacity": pd.read_csv(PREPARED_DATA_DIR / "capacity.csv"),
        "census": pd.read_csv(PREPARED_DATA_DIR / "census.csv"),
        "savings": pd.read_csv(PREPARED_DATA_DIR / "savings.csv"),
        "demographics": pd.read_csv(PREPARED_DATA_DIR / "demographics.csv"),
        "demand": pd.read_csv(PREPARED_DATA_DIR / "demand.csv"),
        "current_demand": pd.read_csv(PREPARED_DATA_DIR / "current_demand.csv"),
        "projection": pd.read_csv(PREPARED_DATA_DIR / "projection.csv"),
    }
    return tables, "prepared synthetic dashboard tables"


@st.cache_data
def get_data():
    try:
        return load_prepared_dashboard_data()
    except FileNotFoundError:
        tables, source_label = load_dashboard_data()
        return _build_fallback_dashboard_tables(tables), f"{source_label} computed at runtime"


def _build_fallback_dashboard_tables(raw_tables):
    from analytics.demographics import demographics_summary
    from analytics.projection import bed_needs_projection
    from analytics.savings import savings_scenarios
    from analytics.utilization import (
        bed_demand_no_adjustment,
        capacity_summary,
        current_bed_demand,
        service_census_summary,
    )

    daily = raw_tables["daily"]
    visits = raw_tables["visits"]
    services = raw_tables["services"]
    facilities = raw_tables["facilities"]
    diagnoses = raw_tables["diagnoses"]
    population_growth = raw_tables["population_growth"]
    facility_filters = ["All"] + sorted(daily["facility_name"].unique().tolist())
    prepared = {"daily": daily, "pressure": raw_tables["pressure"], "quality": raw_tables["quality"]}

    for name in ["capacity", "census", "savings", "demographics", "demand", "current_demand", "projection"]:
        prepared[name] = []

    for facility_filter in facility_filters:
        filtered_daily = daily if facility_filter == "All" else daily[daily["facility_name"] == facility_filter]
        filtered_visits = visits if facility_filter == "All" else visits[
            visits["facility_id"].isin(filtered_daily["facility_id"].unique())
        ]
        capacity = capacity_summary(filtered_daily)
        census = service_census_summary(filtered_daily)
        savings = savings_scenarios(filtered_visits, services, facilities, diagnoses)
        demographics = demographics_summary(filtered_visits, services, facilities, diagnoses)
        demand = bed_demand_no_adjustment(filtered_daily, demographics, population_growth)
        current_demand = current_bed_demand(filtered_daily)
        projection = bed_needs_projection(
            current_demand,
            savings,
            start_year=int(filtered_daily["calendar_date"].dt.year.min()),
            demographics=demographics,
            population_growth=population_growth,
        )
        for name, frame in {
            "capacity": capacity,
            "census": census,
            "savings": savings,
            "demographics": demographics,
            "demand": demand,
            "current_demand": current_demand,
            "projection": projection,
        }.items():
            result = frame.copy()
            result.insert(0, "facility_filter", facility_filter)
            prepared[name].append(result)

    for name, frames in list(prepared.items()):
        if isinstance(frames, list):
            prepared[name] = pd.concat(frames, ignore_index=True)
    prepared["facility_filters"] = pd.DataFrame({"facility_filter": facility_filters})
    return prepared


def by_facility(tables, name, facility_filter):
    frame = tables[name]
    if "facility_filter" not in frame.columns:
        return frame
    return frame[frame["facility_filter"] == facility_filter].drop(columns=["facility_filter"]).reset_index(drop=True)


tables, source_label = get_data()
daily = tables["daily"]

st.title("Executive Report")
st.caption(f"Source: {source_label}")
summary = executive_summary(tables["daily"], tables["quality"])
st.markdown(summary)
st.download_button(
    "Download summary",
    data=summary,
    file_name="synthetic_capacity_executive_summary.txt",
    mime="text/plain",
)

facility_options = tables["facility_filters"]["facility_filter"].tolist()
facility = st.selectbox("Facility", facility_options)
filtered_daily = daily if facility == "All" else daily[daily["facility_name"] == facility]
capacity = by_facility(tables, "capacity", facility)
census = by_facility(tables, "census", facility)
savings = by_facility(tables, "savings", facility)
demographics = by_facility(tables, "demographics", facility)
demand = by_facility(tables, "demand", facility)
current_demand = by_facility(tables, "current_demand", facility)
projection = by_facility(tables, "projection", facility)

capacity_total = int(capacity["planned_beds"].sum())
demand_total = int(current_demand["demand"].sum())
savings_total = float(savings["demand_reduction"].sum()) if not savings.empty else 0.0
projected_2040 = int(projection.loc[projection["year"] == 2040, "projection"].sum())
adjusted_2040 = int(projection.loc[projection["year"] == 2040, "adjusted_projection"].sum())

cols = st.columns(4)
cols[0].metric("Planned beds", f"{capacity_total:,}")
cols[1].metric("Demand", f"{demand_total:,}", f"{demand_total - capacity_total:+,}")
cols[2].metric("Demand reduction", f"{savings_total:.1f}")
cols[3].metric("2040 projection", f"{adjusted_2040:,}", f"{adjusted_2040 - projected_2040:+,} adjusted")

tab_util, tab_adjust, tab_needs, tab_tables = st.tabs(
    ["Utilization", "Adjustment", "Bed Needs", "Tables"]
)

with tab_util:
    st.subheader("Daily Census Trend")
    st.altair_chart(daily_census_capacity_chart(filtered_daily), use_container_width=True)

    st.subheader("Demand With No Adjustments")
    st.altair_chart(bed_demand_chart(current_demand), use_container_width=True)

with tab_adjust:
    st.subheader("Maximal Savings")
    st.altair_chart(savings_chart(savings, "maximal_beds"), use_container_width=True)

    st.subheader("Demand Reduction")
    st.altair_chart(savings_chart(savings, "demand_reduction"), use_container_width=True)

with tab_needs:
    st.subheader("Demographics")
    st.altair_chart(demographics_chart(demographics), use_container_width=True)

    st.subheader("Projected Bed Needs")
    left, right = st.columns(2)
    left.altair_chart(bed_needs_projection_chart(projection), use_container_width=True)
    right.altair_chart(bed_needs_projection_chart(projection, adjusted=True), use_container_width=True)

with tab_tables:
    st.subheader("Capacity")
    st.dataframe(capacity, use_container_width=True, hide_index=True)

    st.subheader("Service Census")
    st.dataframe(census, use_container_width=True, hide_index=True)

    st.subheader("Demand")
    st.dataframe(demand, use_container_width=True, hide_index=True)

    st.subheader("Highest-pressure observations")
    st.dataframe(
        tables["pressure"].sort_values("peak_utilization", ascending=False).head(20),
        use_container_width=True,
        hide_index=True,
    )
