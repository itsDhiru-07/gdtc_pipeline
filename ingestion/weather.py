"""Weather API — internal-analytics-only license.

Lands to C2. The license restricts use to internal analytics (e.g. storm-day
detection, see warehouse/macros/exclude_storm_days.sql) — not to any external
or customer-facing product. This connector doesn't enforce the license (that's
a contracts/legal control), but it tags the data so downstream consumers can.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.base import LandedBatch, land


def run(source_df: pd.DataFrame, as_of: datetime, out_dir: Path) -> LandedBatch:
    df = source_df.copy()
    df["received_at"] = as_of
    df["source"] = "weather_api"
    df["license_scope"] = "internal_analytics_only"
    return land(df, source="weather", out_dir=out_dir, received_at=as_of)
