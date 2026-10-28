"""The one place the crew-note extraction model version is pinned.

Deck's AI slide: "Which model, and what happens when it changes" — the model
ID is pinned per quarter, change-controlled, and re-run against the 500-note
accuracy gate (ai/eval/run_gate.py) before a new pin is promoted. If AWS
deprecates the pinned version before a replacement clears the gate, the
fallback is the manual review queue (ai/crew_notes/fallback_queue.py), not
an un-gated auto-upgrade to whatever version is current.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPin:
    provider: str
    model_family: str
    model_id: str
    inference_profile: str
    pinned_quarter: str
    promoted_after_gate_run_id: str


# Current pin. Changing this value is the entire "promote a new model
# version" workflow — it should only ever change alongside a passing
# ai/eval/run_gate.py run recorded in CHANGELOG-ai-model.md.
CURRENT_PIN = ModelPin(
    provider="amazon_bedrock",
    model_family="anthropic_claude_haiku_class",
    model_id="anthropic.claude-haiku-4-5-20251001-v1:0",  # illustrative; re-pin per quarter
    inference_profile="us-cross-region",
    pinned_quarter="2026-Q4",
    promoted_after_gate_run_id="gate-2026-10-01-001",
)
