"""Compatibility exports for the focused analytics modules."""

from analytics.access import outpatient_surgery_access_placeholder
from analytics.demographics import demographics_summary, visits_with_reference_data
from analytics.pipeline import build_report_tables
from analytics.placeholders import placeholder_registry
from analytics.projection import bed_needs_projection
from analytics.savings import add_readmission_flags, savings_scenarios, visit_saving_opportunities
from analytics.utilization import bed_demand_no_adjustment, capacity_summary, current_bed_demand, service_census_summary

__all__ = [
    "add_readmission_flags",
    "bed_demand_no_adjustment",
    "bed_needs_projection",
    "build_report_tables",
    "capacity_summary",
    "current_bed_demand",
    "demographics_summary",
    "outpatient_surgery_access_placeholder",
    "placeholder_registry",
    "savings_scenarios",
    "service_census_summary",
    "visit_saving_opportunities",
    "visits_with_reference_data",
]
