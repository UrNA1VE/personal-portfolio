"""Reusable Altair charts."""

from __future__ import annotations

import altair as alt
import pandas as pd

SERVICE_SCALE = alt.Scale(
    range=[
        "#2563eb",
        "#d97706",
        "#0f766e",
        "#be123c",
        "#7c3aed",
        "#0891b2",
        "#4d7c0f",
    ]
)


def hourly_census_chart(hourly: pd.DataFrame) -> alt.Chart:
    totals = hourly.groupby("hour_ts", as_index=False)["census"].sum()
    return (
        alt.Chart(totals)
        .mark_line(color="#2563eb")
        .encode(
            x=alt.X("hour_ts:T", title="Hour"),
            y=alt.Y("census:Q", title="Patients"),
            tooltip=[alt.Tooltip("hour_ts:T"), alt.Tooltip("census:Q")],
        )
        .properties(height=330)
    )


def daily_census_capacity_chart(daily: pd.DataFrame) -> alt.LayerChart:
    census = (
        daily.groupby(["calendar_date", "service_name"], as_index=False)["peak_census"]
        .sum()
        .rename(columns={"peak_census": "census"})
    )
    capacity = daily.groupby("calendar_date", as_index=False)["staffed_beds"].sum()
    area = (
        alt.Chart(census)
        .mark_area(opacity=0.88)
        .encode(
            x=alt.X("calendar_date:T", title="Date"),
            y=alt.Y("census:Q", stack="zero", title="Daily peak census"),
            color=alt.Color("service_name:N", title="Service", scale=SERVICE_SCALE),
            tooltip=[
                alt.Tooltip("calendar_date:T", title="Date"),
                alt.Tooltip("service_name:N", title="Service"),
                alt.Tooltip("census:Q", title="Census", format=".0f"),
            ],
        )
    )
    line = (
        alt.Chart(capacity)
        .mark_line(color="#dc2626", strokeWidth=3)
        .encode(
            x="calendar_date:T",
            y=alt.Y("staffed_beds:Q", title="Daily peak census"),
            tooltip=[
                alt.Tooltip("calendar_date:T", title="Date"),
                alt.Tooltip("staffed_beds:Q", title="Funded capacity", format=".0f"),
            ],
        )
    )
    return (area + line).properties(height=380)


def utilization_chart(daily: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(daily)
        .mark_line(point=False)
        .encode(
            x=alt.X("calendar_date:T", title="Date"),
            y=alt.Y("peak_utilization:Q", title="Peak utilization", axis=alt.Axis(format="%")),
            color=alt.Color("service_name:N", title="Service"),
            tooltip=[
                alt.Tooltip("calendar_date:T"),
                "facility_name:N",
                "service_name:N",
                alt.Tooltip("peak_utilization:Q", format=".1%"),
            ],
        )
        .properties(height=380)
    )


def bed_demandvsfunded_chart(demand: pd.DataFrame) -> alt.LayerChart:
    funded_totals = (
        demand.groupby("service_name", as_index=False)["funded_capacity"]
        .sum()
        .rename(columns={"funded_capacity": "funded_beds"})
    )
    bars = (
        alt.Chart(demand)
        .mark_bar(opacity=0.9)
        .encode(
            x=alt.X("service_name:N", sort="-y", title="Service"),
            y=alt.Y("demand:Q", title="Demand"),
            color=alt.Color("facility_name:N", title="Facility"),
            tooltip=[
                "facility_name:N",
                "service_name:N",
                alt.Tooltip("demand:Q", title="Demand"),
                alt.Tooltip("funded_capacity:Q", title="Funded capacity"),
                alt.Tooltip("variance:Q", title="Variance"),
            ],
        )
    )
    funded_points = (
        alt.Chart(funded_totals)
        .mark_point(shape="diamond", color="#facc15", filled=True, size=120, stroke="#854d0e", strokeWidth=1.5)
        .encode(
            x=alt.X("service_name:N", sort="-y"),
            y=alt.Y("funded_beds:Q", title="Demand"),
            tooltip=[
                alt.Tooltip("service_name:N", title="Service"),
                alt.Tooltip("funded_beds:Q", title="Funded beds"),
            ],
        )
    )
    return (bars + funded_points).properties(height=360)

def bed_demand_chart(demand: pd.DataFrame) -> alt.LayerChart:
    bars = (
        alt.Chart(demand)
        .mark_bar(opacity=0.9)
        .encode(
            x=alt.X("service_name:N", sort="-y", title="Service"),
            y=alt.Y("demand:Q", title="Demand"),
            color=alt.Color("facility_name:N", title="Facility"),
            tooltip=[
                "facility_name:N",
                "service_name:N",
                alt.Tooltip("demand:Q", title="Demand"),
                alt.Tooltip("funded_capacity:Q", title="Funded capacity"),
                alt.Tooltip("variance:Q", title="Variance"),
            ],
        )
    )
    return (bars).properties(height=360)


def savings_chart(savings: pd.DataFrame, column: str = "demand_reduction") -> alt.LayerChart:
    if savings.empty:
        return alt.Chart(pd.DataFrame({"message": ["No savings scenario rows"]})).mark_text().encode(text="message:N")
    totals = savings.groupby("service_name", as_index=False)[column].sum()
    value_title = "Demand reduction" if column == "demand_reduction" else "Beds"
    bars = (
        alt.Chart(savings)
        .mark_bar()
        .encode(
            x=alt.X("service_name:N", sort="-y", title="Service"),
            y=alt.Y(f"{column}:Q", title="Beds"),
            color=alt.Color("saving_type:N", title="Scenario"),
            tooltip=[
                "facility_name:N",
                "service_name:N",
                "saving_type:N",
                alt.Tooltip(f"{column}:Q", title=value_title, format=".1f"),
            ],
        )
    )
    points = (
        alt.Chart(totals)
        .mark_point(color="#facc15", filled=True, size=90)
        .encode(x=alt.X("service_name:N", sort="-y"), y=f"{column}:Q")
    )
    return (bars + points).properties(height=360)


def demographics_chart(demographics: pd.DataFrame) -> alt.Chart:
    totals = demographics.groupby(["service_name", "age_group"], as_index=False)["patient_days"].sum()
    return (
        alt.Chart(totals)
        .mark_rect()
        .encode(
            x=alt.X("age_group:N", title="Age group"),
            y=alt.Y("service_name:N", title="Service"),
            color=alt.Color("patient_days:Q", title="Patient days", scale=alt.Scale(scheme="teals")),
            tooltip=["service_name:N", "age_group:N", alt.Tooltip("patient_days:Q", format=".1f")],
        )
        .properties(height=280)
    )


def bed_needs_projection_chart(projection: pd.DataFrame, adjusted: bool = False) -> alt.Chart:
    value_col = "adjusted_projection" if adjusted else "projection"
    years = projection[projection["year"].isin([2025, 2030, 2035, 2040])]
    totals = years.groupby("year", as_index=False)[value_col].sum()
    bars = (
        alt.Chart(years)
        .mark_bar(opacity=0.92)
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y(f"{value_col}:Q", title="Projected beds", stack="zero"),
            color=alt.Color("service_name:N", title="Service", scale=SERVICE_SCALE),
            tooltip=[
                "facility_name:N",
                "service_name:N",
                "year:O",
                alt.Tooltip(f"{value_col}:Q", title="Beds"),
            ],
        )
    )
    labels = (
        alt.Chart(totals)
        .mark_text(dy=-8, fontWeight="bold")
        .encode(x="year:O", y=f"{value_col}:Q", text=alt.Text(f"{value_col}:Q", format=".0f"))
    )
    return (bars + labels).properties(height=360)


def patient_journey_chart(segments: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(segments)
        .mark_bar(size=28)
        .encode(
            x=alt.X("start_ts:T", title="Time"),
            x2="end_ts:T",
            y=alt.Y("track:N", title=None, sort=["Location", "Service"]),
            color=alt.Color("label:N", title=None),
            tooltip=[
                "track:N",
                "label:N",
                "detail:N",
                alt.Tooltip("start_ts:T", title="Start"),
                alt.Tooltip("end_ts:T", title="End"),
            ],
        )
        .properties(height=180)
    )
