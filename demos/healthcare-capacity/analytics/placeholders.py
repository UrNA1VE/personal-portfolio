"""Explicit placeholders for private or not-yet-modeled source logic."""

from __future__ import annotations

import pandas as pd


PLACEHOLDERS = [
    {
        "component": "ADT/DAD extraction",
        "status": "placeholder",
        "reason": "Original R logic used private SQL sources and credentials; replace with Azure-safe raw table contracts.",
    },
    {
        "component": "Outpatient surgery waitlist/access",
        "status": "placeholder",
        "reason": "Awaiting a synthetic or public-safe waitlist schema before modeling access bed demand.",
    },
    {
        "component": "Hospital-specific capacity adjustments",
        "status": "placeholder",
        "reason": "Site-specific rules were intentionally omitted from the public demo.",
    },
    {
        "component": "Repatriation adjustments",
        "status": "placeholder",
        "reason": "Original logic depended on named facilities and private operational rules.",
    },
    {
        "component": "Official population projections",
        "status": "synthetic substitute",
        "reason": "Current projection uses fake region, age-group, and gender growth indexes.",
    },
]


def placeholder_registry() -> pd.DataFrame:
    return pd.DataFrame(PLACEHOLDERS)
