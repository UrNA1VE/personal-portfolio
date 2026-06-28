from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "dashboard" / "streamlit"))

from analytics.demographics import demographics_summary  # noqa: E402
from analytics.journey import journey_segments, patient_visit_summary  # noqa: E402
from analytics.projection import bed_needs_projection  # noqa: E402
from analytics.savings import (  # noqa: E402
    SAVING_ALGORITHMS,
    SERVICE_SAVING_RATES,
    add_readmission_flags,
    savings_scenarios,
)
from analytics.utilization import bed_demand_no_adjustment, capacity_summary, current_bed_demand  # noqa: E402
from utils.database import build_sample_marts  # noqa: E402


def test_sanitized_bed_analysis_outputs_are_nonempty():
    tables = build_sample_marts()
    daily = tables["daily"]
    visits = tables["visits"]
    services = tables["services"]
    facilities = tables["facilities"]
    diagnoses = tables["diagnoses"]
    population_growth = tables["population_growth"]

    capacity = capacity_summary(daily)
    demographics = demographics_summary(visits, services, facilities, diagnoses)
    demand = bed_demand_no_adjustment(daily, demographics, population_growth)
    current_demand = current_bed_demand(daily)
    savings = savings_scenarios(visits, services, facilities, diagnoses)
    projection = bed_needs_projection(
        current_demand,
        savings,
        start_year=int(daily["calendar_date"].dt.year.min()),
        demographics=demographics,
        population_growth=population_growth,
    )

    assert {"facility_name", "service_name", "planned_beds"} <= set(capacity.columns)
    assert {"year", "demand", "funded_capacity", "variance", "growth_index"} <= set(demand.columns)
    assert {"demand", "funded_capacity", "variance"} <= set(current_demand.columns)
    assert {"saving_type", "maximal_beds", "saving_rate", "demand_reduction"} <= set(savings.columns)
    assert {"gender", "age_group", "region", "patient_days"} <= set(demographics.columns)
    assert {"year", "projection", "adjusted_projection"} <= set(projection.columns)
    assert demand["demand"].gt(0).all()
    assert demand["year"].max() == 2040
    assert projection["year"].max() == 2040
    assert set(SERVICE_SAVING_RATES) == set(services["service_name"])
    assert set(SAVING_ALGORITHMS) == set(next(iter(SERVICE_SAVING_RATES.values())))
    assert savings["saving_rate"].between(0, 1).all()
    assert {"readmit_7_day", "readmit_30_day"} <= set(add_readmission_flags(visits).columns)


def test_saving_algorithms_can_be_selected():
    tables = build_sample_marts()
    selected = savings_scenarios(
        tables["visits"],
        tables["services"],
        tables["facilities"],
        tables["diagnoses"],
        enabled_algorithms=["ALC"],
    )

    assert set(selected["saving_type"]) <= {"ALC"}


def test_patient_journey_segments_include_location_and_service_tracks():
    tables = build_sample_marts()
    visit_id = tables["visits"]["visit_id"].iloc[0]

    summary = patient_visit_summary(
        visit_id,
        tables["visits"],
        tables["facilities"],
        tables["services"],
        tables["diagnoses"],
    )
    segments = journey_segments(
        visit_id,
        tables["visits"],
        tables["unit_changes"],
        tables["units"],
        tables["services"],
    )

    assert summary["visit_id"] == visit_id
    assert {"Location", "Service"} <= set(segments["track"])
    assert (segments["end_ts"] > segments["start_ts"]).all()
