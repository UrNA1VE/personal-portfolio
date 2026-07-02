import streamlit as st

import bootstrap  # noqa: F401
from analytics.demographics import demographics_summary
from analytics.projection import bed_needs_projection
from analytics.savings import SAVING_ALGORITHMS, default_saving_rate_table, savings_scenarios
from analytics.utilization import bed_demand_no_adjustment, current_bed_demand
from utils.charts import bed_demand_chart, bed_needs_projection_chart, savings_chart
from utils.database import load_dashboard_data


st.set_page_config(page_title="Service Planning", layout="wide")
tables, source_label = load_dashboard_data()

daily = tables["daily"]
visits = tables["visits"]
services = tables["services"]
facilities = tables["facilities"]
diagnoses = tables["diagnoses"]
population_growth = tables["population_growth"]

st.title("Service Planning")
st.caption(f"Source: {source_label}")

facility = st.selectbox("Facility", ["All"] + sorted(daily["facility_name"].unique().tolist()))
service_options = sorted(daily["service_name"].unique())
selected_services = st.multiselect("Services", service_options, default=service_options)
selected_algorithms = st.multiselect(
    "Savings algorithms",
    list(SAVING_ALGORITHMS),
    default=list(SAVING_ALGORITHMS),
)

filtered_daily = daily[daily["service_name"].isin(selected_services)]
if facility != "All":
    filtered_daily = filtered_daily[filtered_daily["facility_name"] == facility]
if filtered_daily.empty:
    st.warning("Select at least one service for this facility.")
    st.stop()

facility_ids = filtered_daily["facility_id"].unique()
service_ids = filtered_daily["service_id"].unique()
filtered_visits = visits[
    visits["facility_id"].isin(facility_ids) & visits["service_id"].isin(service_ids)
]

rate_table = default_saving_rate_table()
rate_table = rate_table[
    rate_table["service_name"].isin(selected_services)
    & rate_table["saving_type"].isin(selected_algorithms)
].reset_index(drop=True)

st.subheader("Service-Specific Saving Rates")
edited_rates = st.data_editor(
    rate_table,
    hide_index=True,
    use_container_width=True,
    column_config={
        "saving_rate": st.column_config.NumberColumn(
            "saving_rate",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            format="%.2f",
        )
    },
)

demographics = demographics_summary(filtered_visits, services, facilities, diagnoses)
current_demand = current_bed_demand(filtered_daily)
projected_demand = bed_demand_no_adjustment(filtered_daily, demographics, population_growth)
savings = savings_scenarios(
    filtered_visits,
    services,
    facilities,
    diagnoses,
    enabled_algorithms=selected_algorithms,
    saving_rates=edited_rates,
)
projection = bed_needs_projection(
    current_demand,
    savings,
    start_year=int(filtered_daily["calendar_date"].dt.year.min()),
    demographics=demographics,
    population_growth=population_growth,
)

cols = st.columns(4)
cols[0].metric("Current demand", int(current_demand["demand"].sum()))
cols[1].metric("Current funded beds", int(current_demand["funded_capacity"].sum()))
cols[2].metric("Demand reduction", f"{savings['demand_reduction'].sum():.1f}" if not savings.empty else "0.0")
cols[3].metric("2040 adjusted beds", int(projection.loc[projection["year"] == 2040, "adjusted_projection"].sum()))

tab_current, tab_savings, tab_projection, tab_tables = st.tabs(
    ["Current Demand", "Saving Chances", "Projection", "Tables"]
)

with tab_current:
    st.altair_chart(bed_demand_chart(current_demand), use_container_width=True)

with tab_savings:
    st.altair_chart(savings_chart(savings), use_container_width=True)

with tab_projection:
    left, right = st.columns(2)
    left.altair_chart(bed_needs_projection_chart(projection), use_container_width=True)
    right.altair_chart(bed_needs_projection_chart(projection, adjusted=True), use_container_width=True)

with tab_tables:
    st.subheader("Projected Demand With No Adjustment")
    st.dataframe(projected_demand, use_container_width=True, hide_index=True)
    st.subheader("Savings")
    st.dataframe(savings, use_container_width=True, hide_index=True)
