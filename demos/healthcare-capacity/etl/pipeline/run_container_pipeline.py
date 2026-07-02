"""Container-local data -> DuckDB/dbt-style pipeline for the dashboard demo.

This is a lightweight runtime workflow for the containerized Streamlit app:

container raw data -> validation report -> DuckDB/dbt-style transforms -> dashboard_prepared.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.demographics import demographics_summary  # noqa: E402
from analytics.projection import bed_needs_projection  # noqa: E402
from analytics.savings import savings_scenarios  # noqa: E402
from analytics.utilization import (  # noqa: E402
    bed_demand_no_adjustment,
    capacity_summary,
    current_bed_demand,
    service_census_summary,
)
from dashboard.streamlit.utils.database import (  # noqa: E402
    _hourly_snapshots,
    _reporting_window,
    _unit_changes_overlapping_window,
    _visits_overlapping_window,
)
from etl.synthetic_data_generator.generate_fake_data import (  # noqa: E402
    GeneratorConfig,
    generate_all,
    write_csvs,
)


CONTAINER_DATA_ROOT = PROJECT_ROOT / "data" / "container"
RAW_DATA_DIR = CONTAINER_DATA_ROOT / "raw"
BACKUP_DATA_DIR = CONTAINER_DATA_ROOT / "backup"
REPORT_DATA_DIR = CONTAINER_DATA_ROOT / "reports"
ETL_PREPARED_DIR = PROJECT_ROOT / "data" / "etl_prepared"
DASHBOARD_PREPARED_DIR = PROJECT_ROOT / "data" / "dashboard_prepared"
EDITABLE_RAW_FILES = ["patients.csv", "admission_chart.csv", "patient_events.csv"]


REQUIRED_COLUMNS = {
    "facilities": {"facility_id", "facility_name", "region"},
    "services": {"service_id", "service_name", "service_group"},
    "units": {"unit_id", "unit_name", "facility_id", "service_id"},
    "diagnoses": {"diagnosis_code", "diagnosis_name", "service_id", "elos_days", "trim_days"},
    "population_growth": {"region", "age_group", "gender", "year", "growth_index"},
    "capacity": {"capacity_date", "facility_id", "service_id", "staffed_beds"},
    "patients": {"patient_id", "age", "gender", "region"},
    "admission_chart": {
        "visit_id",
        "patient_id",
        "facility_id",
        "admitted_unit_id",
        "admitted_service_id",
        "admitted_diagnosis_code",
        "admission_ts",
        "admission_type",
    },
    "patient_events": {
        "event_id",
        "visit_id",
        "patient_id",
        "event_ts",
        "type",
        "value",
        "facility_id",
    },
}


@dataclass(frozen=True)
class PipelineResult:
    seed: int
    raw_dir: str
    report_dir: str
    etl_prepared_dir: str
    prepared_dir: str
    validation_status: str
    validation_issue_count: int


def read_raw_sources(raw_dir: Path) -> dict[str, pd.DataFrame]:
    sources = {
        "patients": pd.read_csv(raw_dir / "patients.csv"),
        "admission_chart": pd.read_csv(raw_dir / "admission_chart.csv", parse_dates=["admission_ts"]),
        "patient_events": pd.read_csv(raw_dir / "patient_events.csv", parse_dates=["event_ts"]),
        "facilities": pd.read_csv(raw_dir / "facilities.csv"),
        "services": pd.read_csv(raw_dir / "services.csv"),
        "units": pd.read_csv(raw_dir / "units.csv"),
        "diagnoses": pd.read_csv(raw_dir / "diagnoses.csv"),
        "population_growth": pd.read_csv(raw_dir / "population_growth.csv"),
        "capacity": pd.read_csv(raw_dir / "capacity.csv", parse_dates=["capacity_date"]),
    }
    derived = build_encounter_tables_from_events(sources)
    return {**sources, **derived}


def _first_event(events: pd.DataFrame, event_type: str) -> pd.DataFrame:
    return (
        events[events["type"] == event_type]
        .sort_values(["visit_id", "event_ts", "event_id"])
        .drop_duplicates("visit_id", keep="first")
    )


def _last_event(events: pd.DataFrame, event_type: str) -> pd.DataFrame:
    return (
        events[events["type"] == event_type]
        .sort_values(["visit_id", "event_ts", "event_id"])
        .drop_duplicates("visit_id", keep="last")
    )


def build_encounter_tables_from_events(sources: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    events = sources["patient_events"].copy()
    admission_chart = sources["admission_chart"].copy()
    patients = sources["patients"]
    diagnoses = sources["diagnoses"]
    units = sources["units"]

    location_events = events[events["type"] == "location"].copy()
    discharge_events = events[events["type"] == "discharge"].copy()
    last_services = _last_event(events, "service")
    last_diagnoses = _last_event(events, "diagnosis")
    discharge_lookup = (
        discharge_events.sort_values(["visit_id", "event_ts", "event_id"])
        .drop_duplicates("visit_id", keep="last")
        [["visit_id", "event_ts"]]
        .rename(columns={"event_ts": "discharge_ts"})
    )

    visits = (
        admission_chart[
            [
                "visit_id",
                "patient_id",
                "facility_id",
                "admitted_service_id",
                "admitted_diagnosis_code",
                "admission_ts",
                "admission_type",
            ]
        ]
        .merge(
            last_services[["visit_id", "value"]].rename(
                columns={"value": "event_service_id"}
            ),
            on="visit_id",
            how="left",
        )
        .merge(
            last_diagnoses[["visit_id", "value"]].rename(
                columns={"value": "event_diagnosis_code"}
            ),
            on="visit_id",
            how="left",
        )
        .merge(discharge_lookup, on="visit_id", how="left")
        .merge(patients[["patient_id", "age", "gender"]], on="patient_id", how="left")
    )
    visits["service_id"] = visits["event_service_id"].fillna(visits["admitted_service_id"])
    visits["diagnosis_code"] = visits["event_diagnosis_code"].fillna(visits["admitted_diagnosis_code"])
    visits = visits.merge(diagnoses[["diagnosis_code", "elos_days", "trim_days"]], on="diagnosis_code", how="left")
    visits["length_days"] = (
        visits["discharge_ts"].fillna(visits["admission_ts"] + pd.to_timedelta(1, unit="D")) - visits["admission_ts"]
    ).dt.total_seconds() / 86_400
    visits["alclos"] = (visits["length_days"] - visits["elos_days"]).clip(lower=0).fillna(0).round(2)
    visits["elos"] = visits["elos_days"].round(2)
    visits["riwexcl"] = "01"
    visits.loc[visits["length_days"] <= visits["elos_days"], "riwexcl"] = "00"
    visits.loc[visits["length_days"] > visits["trim_days"], "riwexcl"] = "10"
    visits["trim_days"] = visits["trim_days"].round(2)
    visits = visits[
        [
            "visit_id",
            "patient_id",
            "facility_id",
            "service_id",
            "diagnosis_code",
            "age",
            "gender",
            "admission_ts",
            "discharge_ts",
            "admission_type",
            "alclos",
            "elos",
            "riwexcl",
            "trim_days",
        ]
    ].sort_values("admission_ts").reset_index(drop=True)

    unit_changes = (
        pd.concat(
            [
                admission_chart[
                    ["visit_id", "admission_ts", "facility_id", "admitted_unit_id"]
                ].rename(
                    columns={
                        "admission_ts": "event_ts",
                        "admitted_unit_id": "unit_id",
                    }
                ).assign(unit_change_id=lambda frame: "ADM-" + frame["visit_id"].astype(str)),
                location_events[["event_id", "visit_id", "event_ts", "facility_id", "value"]].rename(
                    columns={
                        "event_id": "unit_change_id",
                        "value": "unit_id",
                    }
                ),
            ],
            ignore_index=True,
        )
        .loc[:, ["unit_change_id", "visit_id", "event_ts", "facility_id", "unit_id"]]
        .sort_values(["visit_id", "event_ts", "unit_change_id"])
        .reset_index(drop=True)
    )
    unit_changes = unit_changes[unit_changes["unit_id"].isin(units["unit_id"])]
    return {"visits": visits, "unit_changes": unit_changes.reset_index(drop=True)}


def validate_sources(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks: list[dict[str, object]] = []

    for table_name, required in REQUIRED_COLUMNS.items():
        frame = sources.get(table_name)
        if frame is None:
            checks.append(
                {
                    "check_name": f"{table_name}_file_exists",
                    "severity": "error",
                    "issue_count": 1,
                    "details": "Missing required input file.",
                }
            )
            continue
        missing = sorted(required - set(frame.columns))
        checks.append(
            {
                "check_name": f"{table_name}_required_columns",
                "severity": "error",
                "issue_count": len(missing),
                "details": ", ".join(missing) if missing else "pass",
            }
        )

    visits = sources["visits"]
    capacity = sources["capacity"]
    facilities = sources["facilities"]
    services = sources["services"]
    diagnoses = sources["diagnoses"]
    discharged_visits = visits[visits["discharge_ts"].notna()]

    checks.extend(
        [
            {
                "check_name": "visit_id_unique",
                "severity": "error",
                "issue_count": int(visits["visit_id"].duplicated().sum()),
                "details": "Duplicate visit IDs.",
            },
            {
                "check_name": "visit_date_range_valid",
                "severity": "error",
                "issue_count": int((discharged_visits["discharge_ts"] <= discharged_visits["admission_ts"]).sum()),
                "details": "Discharge must be after admission when discharge_ts is populated.",
            },
            {
                "check_name": "open_inpatient_records",
                "severity": "warning",
                "issue_count": int(visits["discharge_ts"].isna().sum()),
                "details": "Visits without discharge_ts are treated as active during the reporting window.",
            },
            {
                "check_name": "capacity_positive",
                "severity": "error",
                "issue_count": int((capacity["staffed_beds"] <= 0).sum()),
                "details": "staffed_beds must be positive.",
            },
            {
                "check_name": "visits_facility_reference",
                "severity": "error",
                "issue_count": int((~visits["facility_id"].isin(facilities["facility_id"])).sum()),
                "details": "Every visit facility_id must exist in facilities.",
            },
            {
                "check_name": "visits_service_reference",
                "severity": "error",
                "issue_count": int((~visits["service_id"].isin(services["service_id"])).sum()),
                "details": "Every visit service_id must exist in services.",
            },
            {
                "check_name": "visits_diagnosis_reference",
                "severity": "warning",
                "issue_count": int((~visits["diagnosis_code"].isin(diagnoses["diagnosis_code"])).sum()),
                "details": "Every visit diagnosis_code should exist in diagnoses.",
            },
        ]
    )

    report = pd.DataFrame(checks)
    report["status"] = report.apply(
        lambda row: "pass" if row["issue_count"] == 0 else str(row["severity"]),
        axis=1,
    )
    return report


def build_marts_from_sources(sources: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    raw_visits = sources["visits"]
    facilities = sources["facilities"]
    services = sources["services"]
    capacity = sources["capacity"]

    reporting_start, reporting_end = _reporting_window(capacity)
    visits = _visits_overlapping_window(raw_visits, reporting_start, reporting_end)
    unit_changes = _unit_changes_overlapping_window(sources["unit_changes"], raw_visits, visits)
    snapshots = _hourly_snapshots(visits, start=reporting_start, end=reporting_end)
    grouped_snapshots = snapshots.groupby(
        ["hour_ts", "facility_id", "service_id"],
        as_index=False,
    ).agg(census=("visit_id", "nunique"))
    hourly = grouped_snapshots.merge(
        facilities[["facility_id", "facility_name"]],
        on="facility_id",
        how="left",
    )
    hourly = hourly.merge(
        services[["service_id", "service_name"]],
        on="service_id",
        how="left",
    )
    hourly["calendar_date"] = hourly["hour_ts"].dt.normalize()
    hourly["hour_of_day"] = hourly["hour_ts"].dt.hour

    daily = (
        hourly.groupby(
            ["calendar_date", "facility_id", "facility_name", "service_id", "service_name"],
            as_index=False,
        )
        .agg(average_census=("census", "mean"), peak_census=("census", "max"))
        .merge(
            capacity,
            left_on=["calendar_date", "facility_id", "service_id"],
            right_on=["capacity_date", "facility_id", "service_id"],
            how="left",
        )
    )
    daily["average_utilization"] = daily["average_census"] / daily["staffed_beds"]
    daily["peak_utilization"] = daily["peak_census"] / daily["staffed_beds"]
    daily = daily.drop(columns=["capacity_date"])

    pressure = daily.copy()
    pressure["pressure_level"] = pd.cut(
        pressure["peak_utilization"],
        bins=[-float("inf"), 0.85, 0.90, 0.95, float("inf")],
        labels=["Normal", "High", "Severe", "Critical"],
        right=False,
    ).astype(str)
    for threshold in (85, 90, 95):
        pressure[f"above_{threshold}_percent"] = pressure["peak_utilization"] >= threshold / 100

    quality = validate_sources({**sources, "visits": visits, "unit_changes": unit_changes})
    return {
        "hourly": hourly,
        "daily": daily,
        "pressure": pressure,
        "quality": quality,
        "raw_visits": raw_visits,
        **sources,
        "visits": visits,
        "unit_changes": unit_changes,
    }


def _with_filter(frame: pd.DataFrame, facility_filter: str) -> pd.DataFrame:
    result = frame.copy()
    result.insert(0, "facility_filter", facility_filter)
    return result


def build_dashboard_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    daily = tables["daily"]
    visits = tables["visits"]
    services = tables["services"]
    facilities = tables["facilities"]
    diagnoses = tables["diagnoses"]
    population_growth = tables["population_growth"]
    facility_filters = ["All"] + sorted(daily["facility_name"].dropna().unique().tolist())

    prepared: dict[str, list[pd.DataFrame]] = {
        "capacity": [],
        "census": [],
        "savings": [],
        "demographics": [],
        "demand": [],
        "current_demand": [],
        "projection": [],
    }
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
            prepared[name].append(_with_filter(frame, facility_filter))

    return {
        "daily": daily,
        "pressure": tables["pressure"],
        "quality": tables["quality"],
        "facility_filters": pd.DataFrame({"facility_filter": facility_filters}),
        **{name: pd.concat(frames, ignore_index=True) for name, frames in prepared.items()},
    }


def write_tables_with_duckdb(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(":memory:")
    try:
        for name, frame in tables.items():
            connection.register(name, frame)
            connection.sql(f"COPY (SELECT * FROM {name}) TO '{output_dir / f'{name}.csv'}' (HEADER, DELIMITER ',')")
    finally:
        connection.close()


def clear_container_run_data() -> None:
    for folder in (RAW_DATA_DIR, REPORT_DATA_DIR):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)


def clear_dashboard_prepared() -> None:
    if DASHBOARD_PREPARED_DIR.exists():
        shutil.rmtree(DASHBOARD_PREPARED_DIR)
    DASHBOARD_PREPARED_DIR.mkdir(parents=True, exist_ok=True)


def clear_etl_prepared() -> None:
    if ETL_PREPARED_DIR.exists():
        shutil.rmtree(ETL_PREPARED_DIR)
    ETL_PREPARED_DIR.mkdir(parents=True, exist_ok=True)


def write_etl_prepared_tables(sources: dict[str, pd.DataFrame]) -> None:
    write_tables_with_duckdb(
        {
            "visits": sources["visits"],
        },
        ETL_PREPARED_DIR,
    )


def refresh_raw_backup() -> None:
    if BACKUP_DATA_DIR.exists():
        shutil.rmtree(BACKUP_DATA_DIR)
    BACKUP_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for file_name in EDITABLE_RAW_FILES:
        shutil.copy2(RAW_DATA_DIR / file_name, BACKUP_DATA_DIR / file_name)


def run_etl_from_existing_raw() -> dict[str, object]:
    raw_dir = RAW_DATA_DIR
    report_dir = REPORT_DATA_DIR
    clear_etl_prepared()
    clear_dashboard_prepared()
    report_dir.mkdir(parents=True, exist_ok=True)

    sources = read_raw_sources(raw_dir)
    validation_report = validate_sources(sources)
    validation_report.to_csv(report_dir / "data_check_report.csv", index=False)

    issue_count = int(
        validation_report.loc[
            validation_report["severity"] == "error",
            "issue_count",
        ].sum()
    )
    status = "pass" if issue_count == 0 else "fail"

    write_etl_prepared_tables(sources)

    marts = build_marts_from_sources(sources)
    dashboard_tables = build_dashboard_tables(marts)
    write_tables_with_duckdb(dashboard_tables, DASHBOARD_PREPARED_DIR)
    refresh_raw_backup()

    return {
        "issue_count": issue_count,
        "status": status,
        "raw_dir": raw_dir,
        "report_dir": report_dir,
        "etl_prepared_dir": ETL_PREPARED_DIR,
        "prepared_dir": DASHBOARD_PREPARED_DIR,
    }

def run_fake_data_pipeline(seed: int, days: int = 30, start_date: str = "2025-01-01") -> PipelineResult:
    clear_container_run_data()

    raw_dir = RAW_DATA_DIR
    report_dir = REPORT_DATA_DIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    config = GeneratorConfig(start_date=start_date, days=days, seed=seed)
    raw_tables = generate_all(config)
    write_csvs(raw_tables, raw_dir)

    etl_result = run_etl_from_existing_raw()

    result = PipelineResult(
        seed=seed,
        raw_dir=str(etl_result["raw_dir"]),
        report_dir=str(etl_result["report_dir"]),
        etl_prepared_dir=str(etl_result["etl_prepared_dir"]),
        prepared_dir=str(etl_result["prepared_dir"]),
        validation_status=str(etl_result["status"]),
        validation_issue_count=int(etl_result["issue_count"]),
    )

    (report_dir / "pipeline_result.json").write_text(
        json.dumps(asdict(result), indent=2),
        encoding="utf-8",
    )
    return result



if __name__ == "__main__":
    result = run_fake_data_pipeline(seed=42)
    print(json.dumps(asdict(result), indent=2))
