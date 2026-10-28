"""Build the evidence pack for a filing, per the deck (part 4, "Every
filing"):

  Inputs:  file hashes and row counts
  Code:    the exact method version
  Settings: customers-served basis, storm-day rule, cut-off
  Outputs: both ratios, by state and total

Plus the residual-risk addition from the review: the evidence pack also
pins the ENGINE version (DuckDB version here, Redshift engine version in
production), not just the SQL/dbt code version -- an engine upgrade can
shift rounding or join order at the margins even with frozen inputs and
frozen code.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "out" / "evidence"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unversioned (not a git checkout)"


def _hash_models_dir() -> str:
    """One hash covering every model + macro file -- stands in for dbt's
    manifest.json as the 'exact method version' the deck requires.
    """
    hasher = hashlib.sha256()
    for path in sorted((REPO_ROOT / "warehouse").rglob("*.sql")):
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def build_evidence_pack(
    run_as_of: str,
    source_hashes: dict[str, str],
    source_row_counts: dict[str, int],
    results_df,
    test_results: dict,
) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(timezone.utc).isoformat()

    pack = {
        "filing_run_as_of": run_as_of,
        "built_at_utc": built_at,
        "inputs": {
            "source_file_hashes": source_hashes,
            "source_row_counts": source_row_counts,
        },
        "code": {
            "git_commit": _git_commit(),
            "models_and_macros_hash": _hash_models_dir(),
        },
        "engine": {
            "runner": "duckdb (reference build; production pins Redshift engine version)",
            "duckdb_version": duckdb.__version__,
        },
        "settings": {
            "customers_served_basis": "stg_customer_counts as-of run_as_of",
            "storm_day_rule": "exclude dates present in storm_days reference table",
            "aggregation_floor": 15,
            "cutoff": run_as_of,
        },
        "outputs": results_df.to_dict(orient="records"),
        "tests": test_results,
    }

    stamp = run_as_of.replace(":", "").replace("-", "").replace(" ", "T")
    out_path = OUT_DIR / f"evidence_pack_{stamp}.json"
    out_path.write_text(json.dumps(pack, indent=2, default=str), encoding="utf-8")
    return out_path
