"""Crew-note -> structured failure fields.

Deck part 5: "Crew-note extraction: Yes — 350,000 free-text notes a year.
Turning text into failure type, part and severity is what AI does well."

Every output row is tagged `is_ai_derived = true` and carries the exact
model pin used (ai/crew_notes/model_pin.py). This is the mechanical half of
"AI-derived fields are distinguishable from source" — the other half is the
regulatory-model build gate in warehouse/tests/test_no_ai_fields_in_regulatory_models.py,
which fails the build if any regulatory-number model reads a column flagged
is_ai_derived.

Two modes:
  --mock    deterministic, offline, keyword-based stand-in (default; what
            CI and this review run use)
  --bedrock shows the real amazon-bedrock-runtime call shape; only runs if
            boto3 + live AWS credentials are present, which they deliberately
            are not in this repo
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Literal

from ai.crew_notes.model_pin import CURRENT_PIN
from ai.crew_notes.redact import redact

FAILURE_TYPES = ["insulator_failure", "tree_contact", "equipment_age", "animal_contact", "weather_related", "unknown"]
SEVERITIES = ["minor", "moderate", "major"]

_KEYWORD_MAP = {
    "insulator_failure": ["insulator", "flashover", "porcelain"],
    "tree_contact": ["tree", "branch", "limb", "vegetation"],
    "animal_contact": ["squirrel", "bird", "animal", "snake"],
    "weather_related": ["lightning", "wind", "ice", "storm"],
    "equipment_age": ["corrosion", "rust", "worn", "aged", "old transformer"],
}


@dataclass(frozen=True)
class ExtractionResult:
    note_id: str
    failure_type: str
    part: str
    severity: str
    confidence: float
    is_ai_derived: Literal[True]
    model_id: str
    model_pinned_quarter: str
    extracted_at: str
    redaction_counts: dict


def _mock_classify(redacted_text: str) -> tuple[str, str, str, float]:
    """Deterministic keyword stand-in for the pinned Bedrock model.

    Not a real NLP model — it exists so this repo's tests and `scripts/
    run_pipeline.py` are reproducible offline. The real accuracy gate
    (ai/eval/run_gate.py) is written against this interface so swapping in
    the live Bedrock call changes one function, not the gate or the tests.
    """
    text_lower = redacted_text.lower()
    for failure_type, keywords in _KEYWORD_MAP.items():
        if any(kw in text_lower for kw in keywords):
            severity = "major" if any(w in text_lower for w in ("fire", "explo", "fatal")) else "moderate"
            return failure_type, "line_section", severity, 0.72
    return "unknown", "unspecified", "minor", 0.40


def _bedrock_classify(redacted_text: str) -> tuple[str, str, str, float]:
    """Real call shape against the pinned model. Requires boto3 + live
    credentials, neither of which this repo ships — shown for design review
    only, never exercised by tests here.
    """
    import boto3  # local import: optional dependency, not in requirements.txt

    client = boto3.client("bedrock-runtime")
    prompt = (
        "Classify this redacted utility crew note into failure_type "
        f"{FAILURE_TYPES}, a part, and severity {SEVERITIES}. "
        "Return strict JSON only.\n\nNote: " + redacted_text
    )
    response = client.invoke_model(
        modelId=CURRENT_PIN.model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }),
    )
    payload = json.loads(response["body"].read())
    parsed = json.loads(payload["content"][0]["text"])
    return parsed["failure_type"], parsed["part"], parsed["severity"], parsed.get("confidence", 0.5)


def extract(note_id: str, raw_text: str, mode: str = "mock") -> ExtractionResult:
    redacted_text, redaction_counts = redact(raw_text)

    if mode == "mock":
        failure_type, part, severity, confidence = _mock_classify(redacted_text)
    elif mode == "bedrock":
        failure_type, part, severity, confidence = _bedrock_classify(redacted_text)
    else:
        raise ValueError(f"unknown extraction mode: {mode}")

    return ExtractionResult(
        note_id=note_id,
        failure_type=failure_type,
        part=part,
        severity=severity,
        confidence=confidence,
        is_ai_derived=True,
        model_id=CURRENT_PIN.model_id,
        model_pinned_quarter=CURRENT_PIN.pinned_quarter,
        extracted_at=datetime.utcnow().isoformat(),
        redaction_counts=redaction_counts,
    )


def extract_batch(notes: list[tuple[str, str]], mode: str = "mock") -> list[dict]:
    return [asdict(extract(note_id, text, mode=mode)) for note_id, text in notes]
