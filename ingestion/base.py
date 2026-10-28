"""Shared contract for every source connector.

Every connector writes rows with both event_time (when it happened) and
received_at (when this platform saw it) — the "two clocks" rule from the deck.
A correction is a new row, never an overwrite: nothing in this layer does an
UPDATE or DELETE against landed data.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class LandedBatch:
    source: str
    path: Path
    row_count: int
    file_hash: str
    received_at: datetime


def land(df: pd.DataFrame, source: str, out_dir: Path, received_at: datetime) -> LandedBatch:
    """Write a source extract as an immutable, hashed parquet file.

    The file hash and row count are what the evidence pack pins per filing —
    not the live table, which can keep growing after the cutoff.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = received_at.strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"{source}_{stamp}.parquet"
    df.to_parquet(out_path, index=False)

    file_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    return LandedBatch(
        source=source,
        path=out_path,
        row_count=len(df),
        file_hash=file_hash,
        received_at=received_at,
    )
