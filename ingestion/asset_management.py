"""Asset management / Oracle EAM — 1.4M assets, 250k field equipment.

Source: Oracle EAM (enterprise asset management, outside this platform).
Lands to C2. 60% of work orders have a blank or "other" failure cause, which
is exactly the gap crew-note extraction (ai/crew_notes/) exists to fill —
this connector does not paper over it.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.base import LandedBatch, land


def run(source_df: pd.DataFrame, as_of: datetime, out_dir: Path) -> LandedBatch:
    df = source_df.copy()
    df["received_at"] = as_of
    df["source"] = "oracle_eam"
    blank_cause_rate = (df["failure_cause"].isin(["", "other", None])).mean()
    df.attrs["blank_cause_rate"] = blank_cause_rate
    return land(df, source="asset_management", out_dir=out_dir, received_at=as_of)
