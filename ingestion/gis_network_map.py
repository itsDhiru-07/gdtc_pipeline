"""GIS network map — nightly refresh, 2-4% wrong meter-to-equipment links.

Source: GIS platform (outside this platform).
Lands to C2. The deck's rule: never edit the source map, keep every nightly
snapshot, and let disagreements against the outage record go to a review
list (warehouse/models/marts/fct_link_exceptions.sql) rather than being
silently patched here.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.base import LandedBatch, land


def run(source_df: pd.DataFrame, as_of: datetime, out_dir: Path) -> LandedBatch:
    df = source_df.copy()
    df["received_at"] = as_of
    df["source"] = "gis"
    df["snapshot_date"] = as_of.date()
    return land(df, source="gis_network_map", out_dir=out_dir, received_at=as_of)
