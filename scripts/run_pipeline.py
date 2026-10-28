"""End-to-end reference run: ingest sample sources -> stage -> build the
regulatory-number mart -> write the evidence pack.

Run it twice with the same --as-of and it prints identical ratios both
times -- that's the reproducibility claim in the deck, checked, not just
asserted.

Usage:
    python scripts/run_pipeline.py --as-of 2026-09-30
    python scripts/run_pipeline.py --as-of 2026-09-30 --verify-reproducible
"""
from __future__ import annotations

import argparse
from datetime import datetime

import duckdb

from scripts.build_evidence_pack import build_evidence_pack
from scripts.load_seeds import load_all
from scripts.sql_runner import SqlRunner


def run_once(as_of: datetime, run_as_of_str: str):
    con = duckdb.connect()
    source_hashes = load_all(con, as_of)

    row_counts = {}
    for table in ["raw_meter_reads", "raw_outage_records", "raw_gis_network_map", "stg_customer_counts"]:
        row_counts[table] = con.execute(f"select count(*) from {table}").fetchone()[0]

    runner = SqlRunner(con, run_as_of=run_as_of_str)
    results_df = runner.fetch_df("fct_reliability_metrics")

    con.close()
    return source_hashes, row_counts, results_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", required=True, help="e.g. 2026-09-30")
    parser.add_argument(
        "--verify-reproducible", action="store_true",
        help="run the pipeline twice and diff the outputs byte-for-byte",
    )
    args = parser.parse_args()

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    run_as_of_str = as_of.strftime("%Y-%m-%d %H:%M:%S")

    source_hashes, row_counts, results_df = run_once(as_of, run_as_of_str)

    print(f"\nRegulatory metrics as of {run_as_of_str}:\n")
    print(results_df.to_string(index=False))

    if args.verify_reproducible:
        _, _, results_df_2 = run_once(as_of, run_as_of_str)
        identical = results_df.equals(results_df_2)
        print(f"\nReproducibility check (same cutoff, re-run): {'PASS' if identical else 'FAIL'}")
        if not identical:
            raise SystemExit(1)

    pack_path = build_evidence_pack(
        run_as_of=run_as_of_str,
        source_hashes=source_hashes,
        source_row_counts=row_counts,
        results_df=results_df,
        test_results={"reproducibility_verified": args.verify_reproducible},
    )
    print(f"\nEvidence pack written to {pack_path}")


if __name__ == "__main__":
    main()
