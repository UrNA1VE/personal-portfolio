"""Access-demand placeholders for future outpatient surgery waitlist logic."""

from __future__ import annotations

import pandas as pd

from analytics.placeholders import placeholder_registry


def outpatient_surgery_access_placeholder() -> pd.DataFrame:
    placeholder = placeholder_registry()
    reason = placeholder.loc[
        placeholder["component"] == "Outpatient surgery waitlist/access",
        "reason",
    ].iloc[0]
    return pd.DataFrame(
        [
            {
                "service_name": "General Surgery",
                "access_type": "Outpatient surgery waitlist",
                "demand": 0.0,
                "placeholder_reason": reason,
            }
        ]
    )
