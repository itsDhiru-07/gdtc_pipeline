"""Outage records — ~90k/year, hand-entered restore times.

Source: OMS (outage management system).
Lands to C2 — no names, pipeline-role access only, 7-year retention.

Hand-entered restore times are a known weak point (deck part 4): this
connector does not attempt to "fix" anything, it just lands what OMS has.
Cross-checking against meter power-on events happens downstream in the mart
layer, as a reconciliation list, not a silent correction.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.base import LandedBatch, land


def run(source_df: pd.DataFrame, as_of: datetime, out_dir: Path) -> LandedBatch:
    df = source_df.copy()
    df["received_at"] = as_of
    df["source"] = "oms"
    return land(df, source="outage_records", out_dir=out_dir, received_at=as_of)
