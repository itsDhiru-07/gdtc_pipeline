"""Crew notes — ~350,000 free-text notes/year, may contain names and phones.

Lands to C3 (raw_notes): own KMS key, auto-delete after 30 days, redacted
before any downstream use. This connector lands the raw text only long
enough for redaction (ai/crew_notes/redact.py) to run; nothing downstream
of redaction ever sees the raw note again.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.base import LandedBatch, land


def run(source_df: pd.DataFrame, as_of: datetime, out_dir: Path) -> LandedBatch:
    df = source_df.copy()
    df["received_at"] = as_of
    df["source"] = "crew_notes_mobile_app"
    return land(df, source="crew_notes_raw", out_dir=out_dir, received_at=as_of)
