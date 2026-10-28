"""Customer system — SaaS, US-hosted. Holds medical/life-support flags.

This connector deliberately does NOT extract the medical/life-support flag
(C7 in governance/data_classification.yaml). That field is read live and
per-incident by the outage-dispatch workflow via a direct, logged API call —
see ingestion/outage_dispatch_lookup.py. It never appears in a batch extract,
never lands in S3, and never reaches this function.

What this connector lands: customer counts by feeder/state (for the
denominator of the regulatory metric) and non-sensitive account attributes.
No names, no addresses, no meter-to-person mapping beyond the pseudonymous
meter ID already used in C1.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from ingestion.base import LandedBatch, land

FORBIDDEN_COLUMNS = {
    "medical_flag", "life_support_flag", "customer_name", "street_address",
}


def run(source_df: pd.DataFrame, as_of: datetime, out_dir: Path) -> LandedBatch:
    present_forbidden = FORBIDDEN_COLUMNS & set(source_df.columns)
    if present_forbidden:
        raise ValueError(
            f"customer_system connector refused to land forbidden columns: "
            f"{present_forbidden}. These stay in the source system (C7 rule)."
        )
    df = source_df.copy()
    df["received_at"] = as_of
    df["source"] = "customer_system"
    return land(df, source="customer_counts", out_dir=out_dir, received_at=as_of)
