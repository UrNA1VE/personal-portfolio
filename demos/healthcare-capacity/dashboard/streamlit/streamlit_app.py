"""Executive landing page for the hospital capacity dashboard."""

import streamlit as st

import bootstrap  # noqa: F401
from analytics.demographics import demographics_summary
from analytics.projection import bed_needs_projection
from analytics.savings import savings_scenarios
from analytics.utilization import bed_demand_no_adjustment, capacity_summary, current_bed_demand, service_census_summary
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


@st.cache_data
def get_data():
    return load_dashboard_data()


tables, source_label = get_data()
daily = tables["daily"]
visits = tables["visits"]
services = tables["services"]
facilities = tables["facilities"]
diagnoses = tables["diagnoses"]
population_growth = tables["population_growth"]

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

facility = st.selectbox("Facility", ["All"] + sorted(daily["facility_name"].unique().tolist()))
filtered_daily = daily if facility == "All" else daily[daily["facility_name"] == facility]
filtered_visits = visits if facility == "All" else visits[
    visits["facility_id"].isin(filtered_daily["facility_id"].unique())
]

capacity = capacity_summary(filtered_daily)
census = service_census_summary(filtered_daily)
savings = savings_scenarios(filtered_visits, services, facilities, diagnoses)
demographics = demographics_summary(filtered_visits, services, facilities, diagnoses)
demand = bed_demand_no_adjustment(filtered_daily, demographics, population_growth)
current_demand = current_bed_demand(filtered_daily)
start_year = int(filtered_daily["calendar_date"].dt.year.min())
projection = bed_needs_projection(
    current_demand,
    savings,
    start_year=start_year,
    demographics=demographics,
    population_growth=population_growth,
)

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
