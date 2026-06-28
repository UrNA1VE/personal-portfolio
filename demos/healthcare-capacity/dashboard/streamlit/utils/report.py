"""Plain-English executive summary generation."""

from __future__ import annotations

import pandas as pd


def executive_summary(daily: pd.DataFrame, quality: pd.DataFrame) -> str:
    average_utilization = daily["average_utilization"].mean()
    peak_row = daily.loc[daily["peak_utilization"].idxmax()]
    critical_days = daily.loc[daily["peak_utilization"] >= 0.95, "calendar_date"].nunique()
    quality_issues = int(quality["issue_count"].sum())
    return (
        f"Across the selected synthetic period, average utilization was "
        f"{average_utilization:.1%}. The highest observed pressure was "
        f"{peak_row['peak_utilization']:.1%} for {peak_row['service_name']} at "
        f"{peak_row['facility_name']}. There were {critical_days} dates with at least one "
        f"service at or above 95% peak utilization. Automated quality checks found "
        f"{quality_issues} issue(s). These results are demonstrations only and do not "
        f"represent a real hospital or operational recommendation."
    )
