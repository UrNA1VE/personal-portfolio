"""Generate fully synthetic hospital capacity demo data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "sample_data"


@dataclass(frozen=True)
class GeneratorConfig:
    start_date: str = "2025-01-01"
    days: int = 30
    seed: int = 42
    lookback_days: int = 30


FACILITIES = [
    {"facility_id": "FAC-001", "facility_name": "North General Hospital", "region": "North"},
    {"facility_id": "FAC-002", "facility_name": "Central Community Hospital", "region": "Central"},
    {"facility_id": "FAC-003", "facility_name": "South Medical Center", "region": "South"},
]

SERVICES = [
    {"service_id": "SVC-MED", "service_name": "General Medicine", "service_group": "Medical"},
    {"service_id": "SVC-SRG", "service_name": "General Surgery", "service_group": "Surgical"},
    {"service_id": "SVC-CHD", "service_name": "Child Health", "service_group": "Specialty"},
    {"service_id": "SVC-MAT", "service_name": "Maternal Care", "service_group": "Specialty"},
    {"service_id": "SVC-MHU", "service_name": "Mental Health", "service_group": "Medical"},
]

DIAGNOSES = [
    {
        "diagnosis_code": "DX-MED-CHF",
        "diagnosis_name": "Heart failure exacerbation",
        "service_id": "SVC-MED",
        "elos_days": 5.2,
        "trim_days": 12,
        "adult_weight": 0.32,
    },
    {
        "diagnosis_code": "DX-MED-PNE",
        "diagnosis_name": "Respiratory infection",
        "service_id": "SVC-MED",
        "elos_days": 4.4,
        "trim_days": 10,
        "adult_weight": 0.28,
    },
    {
        "diagnosis_code": "DX-MED-DIA",
        "diagnosis_name": "Diabetes complication",
        "service_id": "SVC-MED",
        "elos_days": 3.8,
        "trim_days": 9,
        "adult_weight": 0.22,
    },
    {
        "diagnosis_code": "DX-SRG-ORT",
        "diagnosis_name": "Orthopedic procedure",
        "service_id": "SVC-SRG",
        "elos_days": 3.5,
        "trim_days": 8,
        "adult_weight": 0.34,
    },
    {
        "diagnosis_code": "DX-SRG-ABD",
        "diagnosis_name": "Abdominal surgery",
        "service_id": "SVC-SRG",
        "elos_days": 4.0,
        "trim_days": 9,
        "adult_weight": 0.30,
    },
    {
        "diagnosis_code": "DX-SRG-URO",
        "diagnosis_name": "Urology procedure",
        "service_id": "SVC-SRG",
        "elos_days": 2.2,
        "trim_days": 6,
        "adult_weight": 0.18,
    },
    {
        "diagnosis_code": "DX-CHD-RSV",
        "diagnosis_name": "Pediatric respiratory illness",
        "service_id": "SVC-CHD",
        "elos_days": 2.8,
        "trim_days": 7,
        "adult_weight": 0.05,
    },
    {
        "diagnosis_code": "DX-CHD-GI",
        "diagnosis_name": "Pediatric gastroenteritis",
        "service_id": "SVC-CHD",
        "elos_days": 1.7,
        "trim_days": 5,
        "adult_weight": 0.04,
    },
    {
        "diagnosis_code": "DX-CHD-OBS",
        "diagnosis_name": "Pediatric observation",
        "service_id": "SVC-CHD",
        "elos_days": 1.2,
        "trim_days": 4,
        "adult_weight": 0.03,
    },
    {
        "diagnosis_code": "DX-MAT-DEL",
        "diagnosis_name": "Delivery episode",
        "service_id": "SVC-MAT",
        "elos_days": 1.8,
        "trim_days": 5,
        "adult_weight": 0.36,
    },
    {
        "diagnosis_code": "DX-MAT-CSE",
        "diagnosis_name": "Cesarean delivery",
        "service_id": "SVC-MAT",
        "elos_days": 3.2,
        "trim_days": 7,
        "adult_weight": 0.26,
    },
    {
        "diagnosis_code": "DX-MAT-ANT",
        "diagnosis_name": "Antenatal complication",
        "service_id": "SVC-MAT",
        "elos_days": 2.6,
        "trim_days": 6,
        "adult_weight": 0.18,
    },
    {
        "diagnosis_code": "DX-MHU-MDD",
        "diagnosis_name": "Mood disorder admission",
        "service_id": "SVC-MHU",
        "elos_days": 8.5,
        "trim_days": 21,
        "adult_weight": 0.30,
    },
    {
        "diagnosis_code": "DX-MHU-PSY",
        "diagnosis_name": "Psychosis stabilization",
        "service_id": "SVC-MHU",
        "elos_days": 11.0,
        "trim_days": 28,
        "adult_weight": 0.24,
    },
    {
        "diagnosis_code": "DX-MHU-SUD",
        "diagnosis_name": "Substance use crisis",
        "service_id": "SVC-MHU",
        "elos_days": 4.8,
        "trim_days": 12,
        "adult_weight": 0.20,
    },
]

BASE_CAPACITY = {
    "SVC-MED": 42,
    "SVC-SRG": 30,
    "SVC-CHD": 18,
    "SVC-MAT": 20,
    "SVC-MHU": 16,
}

FACILITY_SCALE = {"FAC-001": 1.0, "FAC-002": 0.8, "FAC-003": 0.65}

UNIT_NAME_PARTS = {
    "prefixes": ["North", "South", "East", "West", "Central", "River", "Prairie", "Summit"],
    "suffixes": ["A", "B", "C", "North Wing", "South Wing", "East Wing", "West Wing"],
}
ADMISSION_TYPES = ["Emergency", "Urgent", "Elective"]
AGE_GROUPS = ["0-17", "18-44", "45-69", "70+"]
GENDERS = ["Female", "Male"]
AREA_GROWTH = {"North": 0.012, "Central": 0.016, "South": 0.010}
AGE_GROWTH = {"0-17": 0.006, "18-44": 0.011, "45-69": 0.017, "70+": 0.031}
GENDER_GROWTH = {"Female": 0.002, "Male": 0.001}
# Arrival weights account for both relative service capacity and typical stay length.
SERVICE_WEIGHTS = np.array([0.228, 0.217, 0.196, 0.290, 0.069])


def build_units_table(config: GeneratorConfig) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed + 2)
    rows: list[dict[str, str]] = []
    unit_numbers = rng.choice(np.arange(1000, 9999), size=1000, replace=False)
    unit_number_index = 0

    for facility in FACILITIES:
        for service in SERVICES:
            admission_focuses = list(rng.permutation(ADMISSION_TYPES))
            admission_focuses += [str(rng.choice(ADMISSION_TYPES)) for _ in range(int(rng.integers(0, 2)))]
            for unit_sequence, admission_focus in enumerate(admission_focuses, start=1):
                unit_number = int(unit_numbers[unit_number_index])
                unit_number_index += 1
                unit_name = " ".join(
                    [
                        str(rng.choice(UNIT_NAME_PARTS["prefixes"])),
                        admission_focus,
                        service["service_name"],
                        str(rng.choice(UNIT_NAME_PARTS["suffixes"])),
                        f"{unit_sequence}",
                    ]
                )
                rows.append(
                    {
                        "unit_id": f"UNT-{unit_number}",
                        "unit_name": unit_name,
                        "facility_id": facility["facility_id"],
                        "hospital_name": facility["facility_name"],
                        "service_id": service["service_id"],
                        "unit_service": service["service_name"],
                        "admission_type_focus": admission_focus,
                    }
                )

    return pd.DataFrame(rows)


def build_diagnoses_table() -> pd.DataFrame:
    return pd.DataFrame(DIAGNOSES)


def build_population_growth_table(config: GeneratorConfig) -> pd.DataFrame:
    base_year = pd.Timestamp(config.start_date).year
    years = range(base_year, 2041)
    rows: list[dict[str, object]] = []

    for facility in FACILITIES:
        for age_group in AGE_GROUPS:
            for gender in GENDERS:
                annual_growth = AREA_GROWTH[facility["region"]] + AGE_GROWTH[age_group] + GENDER_GROWTH[gender]
                for year in years:
                    rows.append(
                        {
                            "region": facility["region"],
                            "age_group": age_group,
                            "gender": gender,
                            "year": year,
                            "growth_index": round((1 + annual_growth) ** (year - base_year), 4),
                        }
                    )

    return pd.DataFrame(rows)


def build_reference_tables(
    config: GeneratorConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        pd.DataFrame(FACILITIES),
        pd.DataFrame(SERVICES),
        build_units_table(config),
        build_diagnoses_table(),
        build_population_growth_table(config),
    )


def generate_capacity(config: GeneratorConfig) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed)
    dates = pd.date_range(config.start_date, periods=config.days, freq="D")
    rows: list[dict[str, object]] = []

    for date in dates:
        for facility in FACILITIES:
            for service in SERVICES:
                baseline = BASE_CAPACITY[service["service_id"]] * FACILITY_SCALE[facility["facility_id"]]
                weekend_reduction = 0.94 if date.dayofweek >= 5 else 1.0
                planned_capacity = max(4, round(baseline * weekend_reduction + rng.normal(0, 1)))
                rows.append(
                    {
                        "capacity_date": date.date(),
                        "facility_id": facility["facility_id"],
                        "service_id": service["service_id"],
                        "staffed_beds": planned_capacity,
                    }
                )

    return pd.DataFrame(rows)


def choose_diagnosis(diagnoses: pd.DataFrame, rng: np.random.Generator, service_id: str) -> pd.Series:
    candidates = diagnoses[diagnoses["service_id"] == service_id].reset_index(drop=True)
    weights = candidates["adult_weight"].to_numpy(dtype=float)
    weights = weights / weights.sum()
    return candidates.iloc[int(rng.choice(np.arange(len(candidates)), p=weights))]


def choose_age_gender(rng: np.random.Generator, service_id: str) -> tuple[int, str]:
    age_probabilities = {
        "SVC-MED": [0.02, 0.14, 0.36, 0.48],
        "SVC-SRG": [0.04, 0.22, 0.44, 0.30],
        "SVC-CHD": [0.94, 0.05, 0.01, 0.00],
        "SVC-MAT": [0.00, 0.88, 0.12, 0.00],
        "SVC-MHU": [0.07, 0.43, 0.34, 0.16],
    }[service_id]
    age_group = str(rng.choice(AGE_GROUPS, p=age_probabilities))
    age_ranges = {
        "0-17": (0, 18),
        "18-44": (18, 45),
        "45-69": (45, 70),
        "70+": (70, 96),
    }
    low, high = age_ranges[age_group]
    gender_probabilities = [0.98, 0.02] if service_id == "SVC-MAT" else [0.52, 0.48]
    return int(rng.integers(low, high)), str(rng.choice(GENDERS, p=gender_probabilities))


def riwexcl_for_visit(rng: np.random.Generator, length_days: float, elos_days: float, trim_days: float) -> str:
    if length_days > trim_days and rng.random() < 0.85:
        return "10"
    if length_days <= elos_days and rng.random() < 0.90:
        return "00"
    return str(rng.choice(["00", "01"], p=[0.65, 0.35]))


def generate_visits(config: GeneratorConfig, capacity: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed + 1)
    diagnoses = build_diagnoses_table()
    start = pd.Timestamp(config.start_date)
    end = start + timedelta(days=config.days)
    generation_start = start - timedelta(days=config.lookback_days)
    generation_days = config.days + config.lookback_days
    total_beds = capacity.groupby("capacity_date")["staffed_beds"].sum().mean()
    visit_count = int(total_beds * generation_days * 0.82 / 2.9)
    service_ids = [item["service_id"] for item in SERVICES]
    facility_ids = [item["facility_id"] for item in FACILITIES]
    facility_weights = np.array([0.42, 0.33, 0.25])
    rows: list[dict[str, object]] = []
    patient_pools: dict[tuple[str, str], list[str]] = {}
    next_patient_number = 1

    for visit_number in range(1, visit_count + 1):
        admission = generation_start + timedelta(minutes=int(rng.integers(0, generation_days * 24 * 60)))
        service_id = str(rng.choice(service_ids, p=SERVICE_WEIGHTS))
        facility_id = str(rng.choice(facility_ids, p=facility_weights))
        diagnosis = choose_diagnosis(diagnoses, rng, service_id)
        diagnosis_code = str(diagnosis["diagnosis_code"])
        elos_days = float(diagnosis["elos_days"])
        trim_days = float(diagnosis["trim_days"])
        age, gender = choose_age_gender(rng, service_id)
        patient_key = (service_id, diagnosis_code)
        patient_pool = patient_pools.setdefault(patient_key, [])
        if patient_pool and rng.random() < 0.16:
            patient_id = str(rng.choice(patient_pool))
        else:
            patient_id = f"PAT-{next_patient_number:06d}"
            next_patient_number += 1
            patient_pool.append(patient_id)

        mean_hours = elos_days * 24
        length_hours = float(np.clip(rng.gamma(shape=2.2, scale=mean_hours / 2.2), 4, 480))
        discharge = admission + timedelta(hours=length_hours)
        if discharge <= start:
            continue
        length_days = max((discharge - admission).total_seconds() / 86_400, 1 / 24)
        alclos = 0.0
        if length_days > elos_days and rng.random() < min(0.45, 0.08 + (age >= 70) * 0.14):
            alclos = min(length_days - elos_days, float(rng.gamma(shape=1.6, scale=1.4)))
        rows.append(
            {
                "visit_id": f"VIS-{len(rows) + 1:06d}",
                "patient_id": patient_id,
                "facility_id": facility_id,
                "service_id": service_id,
                "diagnosis_code": diagnosis_code,
                "age": age,
                "gender": gender,
                "admission_ts": admission.floor("min"),
                "discharge_ts": discharge.floor("min"),
                "admission_type": str(rng.choice(["Emergency", "Urgent", "Elective"], p=[0.55, 0.25, 0.20])),
                "alclos": round(alclos, 2),
                "elos": round(elos_days, 2),
                "riwexcl": riwexcl_for_visit(rng, length_days, elos_days, trim_days),
                "trim_days": round(trim_days, 2),
            }
        )

    return pd.DataFrame(rows)


def choose_unit(
    units: pd.DataFrame,
    rng: np.random.Generator,
    facility_id: str,
    patient_service_id: str,
    admission_type: str,
    *,
    off_service: bool,
    prefer_admission_match: bool,
) -> pd.Series:
    candidates = units[units["facility_id"] == facility_id]
    if off_service:
        candidates = candidates[candidates["service_id"] != patient_service_id]
    else:
        candidates = candidates[candidates["service_id"] == patient_service_id]

    if prefer_admission_match:
        matching_candidates = candidates[candidates["admission_type_focus"] == admission_type]
        if not matching_candidates.empty:
            candidates = matching_candidates

    if candidates.empty:
        candidates = units[(units["facility_id"] == facility_id) & (units["service_id"] == patient_service_id)]

    return candidates.iloc[int(rng.integers(0, len(candidates)))]


def generate_unit_changes(config: GeneratorConfig, visits: pd.DataFrame, units: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(config.seed + 3)
    rows: list[dict[str, object]] = []

    for _, visit in visits.iterrows():
        visit_id = str(visit["visit_id"])
        facility_id = str(visit["facility_id"])
        patient_service_id = str(visit["service_id"])
        admission_type = str(visit["admission_type"])
        admission_ts = pd.Timestamp(visit["admission_ts"])
        discharge_ts = pd.Timestamp(visit["discharge_ts"])
        stay_hours = max((discharge_ts - admission_ts).total_seconds() / 3600, 1)
        if stay_hours < 18:
            event_count = 1
        elif stay_hours < 72:
            event_count = int(rng.choice([1, 2], p=[0.82, 0.18]))
        else:
            event_count = int(rng.choice([1, 2, 3], p=[0.70, 0.24, 0.06]))

        event_times = [admission_ts]
        if event_count > 1:
            latest_transfer_hour = max(int(stay_hours) - 4, 8)
            transfer_hours = sorted(rng.choice(np.arange(6, latest_transfer_hour + 1), size=event_count - 1, replace=False))
            event_times += [admission_ts + timedelta(hours=int(hour)) for hour in transfer_hours]

        for sequence, event_ts in enumerate(event_times, start=1):
            is_first_location = sequence == 1
            off_service = bool(rng.random() < (0.10 if is_first_location else 0.18))
            prefer_admission_match = bool(is_first_location and rng.random() < 0.88)
            unit = choose_unit(
                units,
                rng,
                facility_id,
                patient_service_id,
                admission_type,
                off_service=off_service,
                prefer_admission_match=prefer_admission_match,
            )
            rows.append(
                {
                    "unit_change_id": f"UCHG-{len(rows) + 1:07d}",
                    "visit_id": visit_id,
                    "event_ts": event_ts.floor("min"),
                    "facility_id": facility_id,
                    "unit_id": unit["unit_id"],
                }
            )

    return pd.DataFrame(rows)


def generate_all(config: GeneratorConfig) -> dict[str, pd.DataFrame]:
    facilities, services, units, diagnoses, population_growth = build_reference_tables(config)
    capacity = generate_capacity(config)
    visits = generate_visits(config, capacity)
    unit_changes = generate_unit_changes(config, visits, units)
    return {
        "facilities": facilities,
        "services": services,
        "units": units,
        "diagnoses": diagnoses,
        "population_growth": population_growth,
        "capacity": capacity,
        "visits": visits,
        "unit_changes": unit_changes,
    }


def write_csvs(tables: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in tables.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start-date", default="2025-01-01")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lookback-days", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GeneratorConfig(
        start_date=args.start_date,
        days=args.days,
        seed=args.seed,
        lookback_days=args.lookback_days,
    )
    tables = generate_all(config)
    write_csvs(tables, args.output_dir)
    print(f"Wrote synthetic data to {args.output_dir}")


if __name__ == "__main__":
    main()
