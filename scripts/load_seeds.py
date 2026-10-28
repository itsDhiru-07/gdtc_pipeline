"""Load ingested parquet batches into DuckDB as the 'raw_*' seed tables
that warehouse/models/staging/ models ref(). This is the stand-in for
"land in S3, then COPY INTO Redshift" -- same shape, one less hop, for a
reference build that runs on a laptop.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from ingestion import asset_management, crew_notes, customer_system, gis_network_map, meter_reads, outage_records, weather

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"
LANDED_DIR = Path(__file__).resolve().parents[1] / "out" / "landed"


def load_all(con: duckdb.DuckDBPyConnection, as_of: datetime) -> dict[str, str]:
    """Run every ingestion connector against the sample extracts, land the
    hashed batches, and register them as DuckDB tables. Returns a dict of
    source -> file_hash for the evidence pack.
    """
    hashes: dict[str, str] = {}

    meters_src = pd.read_parquet(SAMPLE_DIR / "meter_reads.parquet")
    batch = meter_reads.run(meters_src, as_of, LANDED_DIR)
    df = pd.read_parquet(batch.path)
    df["source_file_hash"] = batch.file_hash
    con.register("raw_meter_reads_df", df)
    con.execute("CREATE OR REPLACE TABLE raw_meter_reads AS SELECT * FROM raw_meter_reads_df")
    hashes["meter_reads"] = batch.file_hash

    outages_src = pd.read_parquet(SAMPLE_DIR / "outage_records.parquet")
    batch = outage_records.run(outages_src, as_of, LANDED_DIR)
    df = pd.read_parquet(batch.path)
    df["source_file_hash"] = batch.file_hash
    con.register("raw_outage_records_df", df)
    con.execute("CREATE OR REPLACE TABLE raw_outage_records AS SELECT * FROM raw_outage_records_df")
    hashes["outage_records"] = batch.file_hash

    gis_src = pd.read_parquet(SAMPLE_DIR / "gis_network_map.parquet")
    batch = gis_network_map.run(gis_src, as_of, LANDED_DIR)
    df = pd.read_parquet(batch.path)
    df["source_file_hash"] = batch.file_hash
    con.register("raw_gis_network_map_df", df)
    con.execute("CREATE OR REPLACE TABLE raw_gis_network_map AS SELECT * FROM raw_gis_network_map_df")
    hashes["gis_network_map"] = batch.file_hash

    assets_src = pd.read_parquet(SAMPLE_DIR / "asset_management.parquet")
    batch = asset_management.run(assets_src, as_of, LANDED_DIR)
    hashes["asset_management"] = batch.file_hash

    counts_src = pd.read_parquet(SAMPLE_DIR / "customer_counts.parquet")
    batch = customer_system.run(counts_src, as_of, LANDED_DIR)
    df = pd.read_parquet(batch.path)
    con.register("stg_customer_counts_df", df)
    con.execute("CREATE OR REPLACE TABLE stg_customer_counts AS SELECT * FROM stg_customer_counts_df")
    hashes["customer_counts"] = batch.file_hash

    notes_src = pd.read_parquet(SAMPLE_DIR / "crew_notes.parquet")
    batch = crew_notes.run(notes_src, as_of, LANDED_DIR)
    hashes["crew_notes"] = batch.file_hash

    # Reference tables these models ref() but no connector lands, because
    # they're small, human-governed tables, not source-system extracts.
    con.execute("""
        CREATE OR REPLACE TABLE storm_days (storm_date DATE)
    """)  # empty in this sample run -- no declared storm days in the window

    con.execute("""
        CREATE OR REPLACE TABLE link_overrides (
            outage_id VARCHAR, resolved_feeder_id VARCHAR,
            owner VARCHAR, override_version VARCHAR
        )
    """)  # empty -- no overrides applied in this sample run

    return hashes
