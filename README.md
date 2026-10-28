# GDTC Reliability & Asset-Health Platform — Reference Pipeline

Reference implementation for the architecture described in `docs/architecture-deck.pdf`
(Senior AWS Solutions Architect design exercise, fictional ~2.1M-customer regulated
utility). This is a **design exercise codebase** — it demonstrates the data model,
reproducibility mechanics, and AI-boundary controls described in the deck, running
against synthetic sample data. It does not connect to any real client system.

## What this proves out

The deck makes specific, checkable claims. This repo is where they get checked:

| Claim in the deck | Where it's implemented |
|---|---|
| Two clocks — `event_time` vs `received_at`, corrections never overwrite | `warehouse/models/staging/stg_meter_reads.sql`, `ingestion/meter_reads.py` |
| "As of" cutoffs give the same answer every time | `warehouse/models/marts/fct_reliability_metrics.sql` (`run_as_of` macro) |
| Storm days excluded from the regulatory number | `warehouse/macros/exclude_storm_days.sql` |
| Engine/code version pinned alongside data in the evidence pack | `scripts/build_evidence_pack.py` |
| Wrong meter-to-equipment links (2-4%) go to a review list, not silently fixed | `warehouse/models/marts/fct_link_exceptions.sql` |
| AI never touches the regulatory number (build-time gate) | `warehouse/tests/test_no_ai_fields_in_regulatory_models.py` |
| Crew-note extraction: bounded, versioned, accuracy-gated, human fallback | `ai/crew_notes/extract.py`, `ai/eval/run_gate.py` |
| Medical/life-support flag never joins to analytics tables (C7) | `governance/data_classification.yaml`, `warehouse/tests/test_c7_isolation.py` |
| dbt-not-approved contingency (stored-proc fallback) | `docs/dbt-contingency.md`, `warehouse/sql_fallback/` |

## Layout

```
ingestion/           Source connectors (stubs) for the 7 data sources in the deck
warehouse/           dbt-style project: staging -> marts, reproducibility macros, tests
ai/crew_notes/       Crew-note -> structured failure fields (Bedrock/Claude Haiku class)
ai/eval/             Accuracy gate that must pass before a model version is promoted
governance/          Data classification register (C1-C7) and SEC/LEG/EA control map
scripts/             Evidence pack builder, drift check, synthetic data generator
data/sample/         Synthetic sample data (no real customer, meter, or employer data)
docs/                Design notes, including the dbt contingency plan
```

## Running it locally

Requires Python 3.11+ and DuckDB (stands in for Redshift in this reference build —
same SQL dialect family, zero infra to stand up for a take-home review).

```bash
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

python scripts/generate_sample_data.py              # synthesize meters, outages, assets, GIS, notes
python scripts/run_pipeline.py --as-of 2026-09-30    # stage -> mart -> evidence pack
python scripts/run_pipeline.py --as-of 2026-09-30    # run again: byte-identical evidence pack

pytest warehouse/tests ai/eval -q                    # data-quality + AI-boundary + eval gate
```

`scripts/run_pipeline.py` prints the two regulatory ratios (with and without disputed
GIS links, per the deck's "honest range" rule) and writes a timestamped evidence pack
to `out/evidence/`.

## What's deliberately out of scope here

- No real AWS account, no Redshift cluster, no Bedrock calls — this is a design-review
  codebase, not a deployed system. `ai/crew_notes/extract.py` has a `--mock` mode
  (default) that runs a deterministic stand-in and a `--bedrock` mode that shows the
  real call shape, unused unless credentials are supplied.
- No OT network path — release 1 of the real plan uses no telemetry (see deck part 3);
  this repo accordingly has no OT ingestion code, only a comment where it would attach.
- No real customer, meter, or employer data anywhere, per the exercise rules.
