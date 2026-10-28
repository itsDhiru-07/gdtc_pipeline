"""Accuracy gate a model version must clear before ai/crew_notes/model_pin.py
is updated to point at it.

Deck's AI slide: re-run of a 500-note accuracy gate before promoting a new
pinned model version. ai/eval/labeled_set.jsonl ships 12 hand-labeled notes
in this repo — enough to prove the gate mechanism for a design review, not
a claim that 12 notes is the real gate's sample size. Swap in the real
500-note labeled set before this gate is used to promote an actual
production pin; `MIN_LABELED_SET_SIZE` below exists so that swap-in is
enforced, not just documented.

Usage:
    python -m ai.eval.run_gate --threshold 0.85
Exit code is non-zero if the pinned model's accuracy on the labeled set
falls below the threshold -- wire this into CI as the promotion gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ai.crew_notes.extract import extract
from ai.crew_notes.model_pin import CURRENT_PIN

LABELED_SET_PATH = Path(__file__).parent / "labeled_set.jsonl"
MIN_LABELED_SET_SIZE_FOR_PRODUCTION = 500  # deck's stated gate size


def load_labeled_set(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_gate(threshold: float, mode: str = "mock") -> dict:
    labeled = load_labeled_set(LABELED_SET_PATH)
    correct = 0
    rows = []
    for item in labeled:
        result = extract(item["note_id"], item["text"], mode=mode)
        is_correct = result.failure_type == item["expected_failure_type"]
        correct += int(is_correct)
        rows.append({
            "note_id": item["note_id"],
            "expected": item["expected_failure_type"],
            "predicted": result.failure_type,
            "correct": is_correct,
        })

    accuracy = correct / len(labeled) if labeled else 0.0
    passed = accuracy >= threshold

    return {
        "model_id": CURRENT_PIN.model_id,
        "pinned_quarter": CURRENT_PIN.pinned_quarter,
        "sample_size": len(labeled),
        "sample_size_is_production_scale": len(labeled) >= MIN_LABELED_SET_SIZE_FOR_PRODUCTION,
        "accuracy": round(accuracy, 4),
        "threshold": threshold,
        "passed": passed,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--mode", choices=["mock", "bedrock"], default="mock")
    args = parser.parse_args()

    result = run_gate(args.threshold, mode=args.mode)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))

    if not result["sample_size_is_production_scale"]:
        print(
            f"\nNOTE: sample size ({result['sample_size']}) is below the "
            f"production gate size ({MIN_LABELED_SET_SIZE_FOR_PRODUCTION}). "
            "This run demonstrates the gate mechanism; it is not a valid "
            "promotion decision for a real model version.",
            file=sys.stderr,
        )

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
