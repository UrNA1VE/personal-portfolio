import streamlit as st

import bootstrap  # noqa: F401
from analytics.utilization import current_bed_demand, service_census_summary
from utils.charts import bed_demand_chart, daily_census_capacity_chart, utilization_chart, bed_demandvsfunded_chart
from utils.database import load_dashboard_data


st.set_page_config(page_title="Utilization Dashboard", layout="wide")
tables, source_label = load_dashboard_data()
daily = tables["daily"]

st.title("Utilization Dashboard")
st.caption(f"Source: {source_label}")

facility = st.selectbox("Facility", ["All"] + sorted(daily["facility_name"].unique().tolist()))
filtered = daily if facility == "All" else daily[daily["facility_name"] == facility]

st.subheader("Daily census and capacity")
st.altair_chart(daily_census_capacity_chart(filtered), use_container_width=True)

st.subheader("Peak utilization trend")
st.altair_chart(utilization_chart(filtered), use_container_width=True)

st.subheader("Capacity pressure")
cols = st.columns(3)
for column, threshold in zip(cols, (85, 90, 95)):
    count = filtered.loc[
        filtered["peak_utilization"] >= threshold / 100, "calendar_date"
    ].nunique()
    column.metric(f"Days ≥ {threshold}%", count)

st.subheader("Demand versus funded capacity")
demand = current_bed_demand(filtered)
st.altair_chart(bed_demandvsfunded_chart(demand), use_container_width=True)

st.subheader("Service census summary")
st.dataframe(service_census_summary(filtered), use_container_width=True, hide_index=True)

st.dataframe(
    filtered.sort_values("peak_utilization", ascending=False),
    use_container_width=True,
    hide_index=True,
)
