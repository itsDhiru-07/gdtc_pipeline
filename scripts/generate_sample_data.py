"""Generate small, synthetic sample data for every source in the deck.

No real customer, meter, employer, or utility data anywhere -- purely
synthetic, generated with fixed seeds for reproducibility. Scaled down
massively from the deck's real numbers (2.1M meters, 90k outages/year,
1.4M assets) so this runs in seconds on a laptop; the SHAPE of the data
(late reads, wrong GIS links, blank failure causes) matches the deck's
stated rates so the data-quality tests in warehouse/tests/ mean something.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"
SEED = 20261029
N_METERS = 2_000
N_FEEDERS = 40
N_OUTAGES = 500
N_ASSETS = 3_000
N_CREW_NOTES = 300
STATES = ["StateA", "StateB", "StateC"]  # fictional, per the exercise rules


def _rng():
    random.seed(SEED)
    np.random.seed(SEED)
    return Faker()


def generate_meters() -> pd.DataFrame:
    meter_ids = [f"MTR-{i:07d}" for i in range(N_METERS)]
    feeders = [f"FDR-{i:04d}" for i in range(N_FEEDERS)]
    return pd.DataFrame({
        "meter_id": meter_ids,
        "feeder_id": np.random.choice(feeders, N_METERS),
        "state": np.random.choice(STATES, N_METERS),
    })


def generate_meter_reads(meters: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    rows = []
    window_start = as_of - timedelta(days=3)
    for _, m in meters.iterrows():
        for step in range(0, 3 * 24 * 4, 16):  # thinned 15-min intervals for sample size
            event_time = window_start + timedelta(minutes=15 * step)
            if event_time > as_of:
                break
            # ~3% of reads arrive late, up to the stated 72h worst case
            if np.random.random() < 0.03:
                lag_hours = np.random.uniform(1, 72)
            else:
                lag_hours = np.random.uniform(0, 0.5)
            rows.append({
                "meter_id": m["meter_id"],
                "event_time": event_time,
                "received_at": event_time + timedelta(hours=lag_hours),
                "read_value": round(np.random.uniform(0.1, 5.0), 3),
                "source_file_hash": "placeholder",  # filled in by ingestion.base.land
            })
    return pd.DataFrame(rows)


def generate_outages(meters: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    feeders = meters["feeder_id"].unique()
    rows = []
    for i in range(N_OUTAGES):
        event_time = as_of - timedelta(days=np.random.uniform(0, 90))
        restored_minutes = np.random.exponential(scale=90)
        rows.append({
            "outage_id": f"OUT-{i:06d}",
            "feeder_id": np.random.choice(feeders),
            "event_time": event_time,
            "restored_at": event_time + timedelta(minutes=restored_minutes),
            "customers_affected": np.random.randint(1, 500),
            "cause_code": np.random.choice(["tree", "equipment", "weather", "unknown"]),
        })
    return pd.DataFrame(rows)


def generate_assets() -> pd.DataFrame:
    rows = []
    for i in range(N_ASSETS):
        # Deck: 60% of work orders have blank/"other" failure cause.
        if np.random.random() < 0.6:
            cause = np.random.choice(["", "other"])
        else:
            cause = np.random.choice(["insulator_failure", "tree_contact", "equipment_age", "animal_contact"])
        rows.append({
            "asset_id": f"AST-{i:06d}",
            "asset_type": np.random.choice(["transformer", "recloser", "pole", "switch"]),
            "failure_cause": cause,
        })
    return pd.DataFrame(rows)


def generate_gis_links(meters: pd.DataFrame, as_of: datetime) -> pd.DataFrame:
    rows = []
    for _, m in meters.iterrows():
        # Deck: 2-4% wrong meter-to-equipment links.
        is_wrong = np.random.random() < 0.03
        rows.append({
            "meter_id": m["meter_id"],
            "equipment_id": f"EQ-{np.random.randint(0, N_ASSETS):06d}",
            "feeder_id": m["feeder_id"] if not is_wrong else f"FDR-{np.random.randint(0, N_FEEDERS):04d}",
            "is_wrong_link": is_wrong,
            "snapshot_date": as_of.date(),
        })
    return pd.DataFrame(rows)


def generate_customer_counts(meters: pd.DataFrame) -> pd.DataFrame:
    return (
        meters.groupby(["state", "feeder_id"])
        .size()
        .reset_index(name="customer_count")
    )


def generate_crew_notes() -> pd.DataFrame:
    fake = _rng()
    templates = [
        "Found flashover on insulator at pole {n}, replaced unit.",
        "Tree limb down across primary conductor after wind event.",
        "Squirrel contact on transformer bushing, minor outage.",
        "Lightning strike on lateral, fuse blown.",
        "Corroded connector at old transformer, visible rust on terminals.",
        "Crew found no clear cause, equipment reset itself on inspection.",
        "Called {name} at {phone} to confirm access to the pole.",
    ]
    rows = []
    for i in range(N_CREW_NOTES):
        template = np.random.choice(templates)
        text = template.format(
            n=np.random.randint(1, 999),
            name=fake.name(),
            phone=fake.phone_number(),
        )
        rows.append({"note_id": f"NOTE-{i:06d}", "raw_text": text})
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    as_of = datetime(2026, 9, 30, 23, 59, 59)

    meters = generate_meters()
    meter_reads = generate_meter_reads(meters, as_of)
    outages = generate_outages(meters, as_of)
    assets = generate_assets()
    gis_links = generate_gis_links(meters, as_of)
    customer_counts = generate_customer_counts(meters)
    crew_notes = generate_crew_notes()

    meter_reads.to_parquet(OUT_DIR / "meter_reads.parquet", index=False)
    outages.to_parquet(OUT_DIR / "outage_records.parquet", index=False)
    assets.to_parquet(OUT_DIR / "asset_management.parquet", index=False)
    gis_links.to_parquet(OUT_DIR / "gis_network_map.parquet", index=False)
    customer_counts.to_parquet(OUT_DIR / "customer_counts.parquet", index=False)
    crew_notes.to_parquet(OUT_DIR / "crew_notes.parquet", index=False)

    print(f"Generated sample data in {OUT_DIR}")
    for name, df in [
        ("meter_reads", meter_reads), ("outage_records", outages),
        ("asset_management", assets), ("gis_network_map", gis_links),
        ("customer_counts", customer_counts), ("crew_notes", crew_notes),
    ]:
        print(f"  {name}: {len(df)} rows")


if __name__ == "__main__":
    main()
