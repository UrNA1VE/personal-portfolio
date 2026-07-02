from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "etl"))

from dashboard.streamlit.utils.database import _reporting_window, _unit_changes_overlapping_window, _visits_overlapping_window
from etl.pipeline.run_container_pipeline import build_encounter_tables_from_events
from synthetic_data_generator.generate_fake_data import GeneratorConfig, generate_all


def with_derived_encounters(tables):
    return {**tables, **build_encounter_tables_from_events(tables)}


def test_generated_event_sources_are_valid_and_reproducible():
    config = GeneratorConfig(start_date="2025-01-01", days=7, seed=7)
    first = generate_all(config)
    second = generate_all(config)
    first_derived = with_derived_encounters(first)

    assert first["patients"].equals(second["patients"])
    assert first["admission_chart"].equals(second["admission_chart"])
    assert first["patient_events"].equals(second["patient_events"])
    assert "visits" not in first
    assert "unit_changes" not in first
    assert set(first["patient_events"]["type"]) <= {"location", "service", "diagnosis", "discharge"}
    assert (first["patient_events"]["type"] == "discharge").any()
    assert first["patient_events"]["event_id"].is_unique
    discharged = first_derived["visits"][first_derived["visits"]["discharge_ts"].notna()]
    assert (discharged["discharge_ts"] > discharged["admission_ts"]).all()
    assert first_derived["visits"]["discharge_ts"].isna().any()
    assert first_derived["visits"]["visit_id"].is_unique
    assert (first["capacity"]["staffed_beds"] > 0).all()


def test_generated_visits_include_report_window_carryover_stays():
    config = GeneratorConfig(start_date="2025-01-01", days=7, seed=7, lookback_days=30)
    tables = with_derived_encounters(generate_all(config))
    visits = tables["visits"]
    start = pd.Timestamp(config.start_date)
    end = start + pd.to_timedelta(config.days, unit="D")
    effective_discharge = visits["discharge_ts"].fillna(end)

    assert (visits["admission_ts"] < start).any()
    assert (effective_discharge.loc[visits["admission_ts"] < start] > start).all()


def test_analysis_visits_are_clipped_to_reporting_window():
    config = GeneratorConfig(start_date="2025-01-01", days=7, seed=7, lookback_days=30)
    tables = with_derived_encounters(generate_all(config))
    start, end = _reporting_window(tables["capacity"])
    visits = _visits_overlapping_window(tables["visits"], start, end)
    unit_changes = _unit_changes_overlapping_window(tables["unit_changes"], tables["visits"], visits)

    assert (tables["visits"]["admission_ts"] < start).any()
    assert (visits["admission_ts"] >= start).all()
    assert (visits["discharge_ts"] <= end).all()
    assert (unit_changes["event_ts"] >= start).all()
    assert (unit_changes["event_ts"] < end).all()


def test_generated_foreign_keys_match_reference_tables():
    tables = with_derived_encounters(generate_all(GeneratorConfig(days=3)))
    expected_unit_change_columns = [
        "unit_change_id",
        "visit_id",
        "event_ts",
        "facility_id",
        "unit_id",
    ]

    assert set(tables["visits"]["facility_id"]) <= set(tables["facilities"]["facility_id"])
    assert set(tables["visits"]["service_id"]) <= set(tables["services"]["service_id"])
    assert set(tables["visits"]["diagnosis_code"]) <= set(tables["diagnoses"]["diagnosis_code"])
    assert set(tables["patient_events"]["patient_id"]) <= set(tables["patients"]["patient_id"])
    assert set(tables["patient_events"]["facility_id"]) <= set(tables["facilities"]["facility_id"])
    assert set(tables["admission_chart"]["patient_id"]) <= set(tables["patients"]["patient_id"])
    assert set(tables["admission_chart"]["facility_id"]) <= set(tables["facilities"]["facility_id"])
    assert set(tables["admission_chart"]["admitted_service_id"]) <= set(tables["services"]["service_id"])
    assert set(tables["admission_chart"]["admitted_diagnosis_code"]) <= set(tables["diagnoses"]["diagnosis_code"])
    assert set(tables["admission_chart"]["admitted_unit_id"]) <= set(tables["units"]["unit_id"])
    assert set(tables["units"]["facility_id"]) == set(tables["facilities"]["facility_id"])
    assert set(tables["units"]["service_id"]) == set(tables["services"]["service_id"])
    assert tables["units"]["unit_id"].is_unique
    assert tables["units"].groupby(["facility_id", "service_id"]).size().max() > 1
    assert not tables["units"].duplicated(["facility_id", "unit_name"]).any()
    assert list(tables["unit_changes"].columns) == expected_unit_change_columns
    assert set(tables["unit_changes"]["visit_id"]) == set(tables["visits"]["visit_id"])
    assert set(tables["unit_changes"]["unit_id"]) <= set(tables["units"]["unit_id"])


def test_generated_visits_include_patient_and_diagnosis_fields():
    tables = with_derived_encounters(generate_all(GeneratorConfig(days=14)))
    visits = tables["visits"]
    expected_visit_columns = {
        "patient_id",
        "diagnosis_code",
        "age",
        "gender",
        "alclos",
        "elos",
        "riwexcl",
        "trim_days",
    }

    assert expected_visit_columns <= set(visits.columns)
    assert visits["patient_id"].str.startswith("PAT-").all()
    assert visits["age"].between(0, 95).all()
    assert set(visits["gender"]) <= {"Female", "Male"}
    assert visits["alclos"].ge(0).all()
    assert visits["elos"].gt(0).all()
    assert visits["trim_days"].gt(visits["elos"]).all()
    assert set(visits["riwexcl"]) <= {"00", "01", "10"}

    diagnosed = visits.merge(tables["diagnoses"], on="diagnosis_code", suffixes=("_visit", "_diagnosis"))
    assert (diagnosed["service_id_visit"] == diagnosed["service_id_diagnosis"]).all()
    assert diagnosed.groupby(["patient_id", "diagnosis_code"]).size().max() > 1


def test_population_growth_reference_covers_projection_dimensions():
    tables = generate_all(GeneratorConfig(start_date="2025-01-01", days=3))
    population_growth = tables["population_growth"]

    assert {"region", "age_group", "gender", "year", "growth_index"} <= set(population_growth.columns)
    assert set(population_growth["region"]) == set(tables["facilities"]["region"])
    assert set(population_growth["gender"]) == {"Female", "Male"}
    assert population_growth["year"].min() == 2025
    assert population_growth["year"].max() == 2040
    assert population_growth["growth_index"].ge(1).all()


def test_unit_changes_follow_location_rules():
    tables = with_derived_encounters(generate_all(GeneratorConfig(days=14)))
    unit_changes = tables["unit_changes"]
    visits = tables["visits"]

    assert unit_changes["unit_change_id"].is_unique
    first_location_indexes = unit_changes.groupby("visit_id")["event_ts"].idxmin()
    first_locations = unit_changes.loc[first_location_indexes]
    assert first_locations["visit_id"].is_unique

    timeline = unit_changes.merge(
        visits[["visit_id", "admission_ts", "discharge_ts"]],
        on="visit_id",
        how="left",
    )
    effective_discharge = timeline["discharge_ts"].fillna(
        pd.Timestamp("2025-01-01") + pd.to_timedelta(14, unit="D")
    )
    assert (timeline["event_ts"] >= timeline["admission_ts"]).all()
    assert (timeline["event_ts"] < effective_discharge).all()

    located_units = (
        unit_changes.merge(
            visits[["visit_id", "service_id", "admission_type"]],
            on="visit_id",
            how="left",
        ).merge(
            tables["units"][["unit_id", "service_id", "admission_type_focus"]],
            on="unit_id",
            how="left",
            suffixes=("_visit", "_unit"),
        )
    )
    first_located_units = located_units.loc[first_location_indexes]
    assert first_located_units["admission_type_focus"].eq(first_located_units["admission_type"]).mean() >= 0.75
    assert (located_units["service_id_visit"] != located_units["service_id_unit"]).any()
