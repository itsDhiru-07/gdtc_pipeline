"""The build-time gate the deck promises: "A build test fails if any
regulatory model reads an AI field."

This test reads the raw SQL of every model tagged as a regulatory model
(see REGULATORY_MODELS below) and fails if it references a column or
source known to be AI-derived. It's a static check, not a runtime one,
because the whole point is to catch the mistake before any query runs
against real data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

WAREHOUSE_ROOT = Path(__file__).resolve().parents[1]

# Models that compute, or roll up into, the filed regulatory number. If a
# new mart is added to this family, add it here -- that's the point of
# keeping this list explicit instead of pattern-matching filenames.
REGULATORY_MODELS = [
    "models/marts/fct_reliability_metrics.sql",
    "models/marts/fct_link_exceptions.sql",
]

# Columns/sources that only exist because an AI step produced them.
# ai/crew_notes/extract.py tags every output row is_ai_derived = true;
# this is the mechanical list a static grep can check for.
AI_DERIVED_MARKERS = [
    "is_ai_derived",
    "ai_failure_type",
    "ai_confidence",
    "stg_crew_notes_extracted",  # the model that holds AI output, if added
]


@pytest.mark.parametrize("model_path", REGULATORY_MODELS)
def test_regulatory_model_has_no_ai_derived_reference(model_path: str) -> None:
    sql_text = (WAREHOUSE_ROOT / model_path).read_text(encoding="utf-8")
    lowered = sql_text.lower()
    for marker in AI_DERIVED_MARKERS:
        assert marker.lower() not in lowered, (
            f"{model_path} references '{marker}', an AI-derived marker. "
            "Regulatory models must never read AI-derived fields -- this "
            "is the deck's hard wall between AI and the filed number."
        )
