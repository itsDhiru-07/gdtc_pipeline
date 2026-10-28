"""C7 (medical/life-support flag) must never appear in any warehouse model
or ingestion connector other than the dedicated, logged, live lookup path.

This mirrors the enforcement note in governance/data_classification.yaml:
"Any PR that adds a column, view, or join path touching this ID should
fail review on sight." This test makes that mechanical instead of relying
on a human reviewer catching it every time.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_TERMS = [
    "medical_flag",
    "life_support_flag",
    "medical_life_support",
    "c7_flag",
]

# Files allowed to mention these terms:
#  - the dedicated lookup module, which deliberately has no land-to-warehouse
#    path (see its own docstring)
#  - customer_system.py, which names them only in a refusal guard that
#    raises if any of these columns show up in what it's about to land
ALLOWED_FILES = {
    "ingestion/outage_dispatch_lookup.py",
    "ingestion/customer_system.py",
}

SCAN_DIRS = ["warehouse", "ingestion", "ai"]


def _all_source_files() -> list[Path]:
    files = []
    for d in SCAN_DIRS:
        files.extend((REPO_ROOT / d).rglob("*.sql"))
        files.extend((REPO_ROOT / d).rglob("*.py"))
    return files


@pytest.mark.parametrize("path", _all_source_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_c7_reference_outside_dispatch_lookup(path: Path) -> None:
    rel = path.relative_to(REPO_ROOT).as_posix()
    if rel in ALLOWED_FILES or rel.endswith("test_c7_isolation.py"):
        return
    text = path.read_text(encoding="utf-8").lower()
    for term in FORBIDDEN_TERMS:
        assert term not in text, (
            f"{rel} references '{term}'. The medical/life-support flag (C7) "
            f"must only be touched via {sorted(ALLOWED_FILES)} -- see "
            "governance/data_classification.yaml."
        )


def test_governance_register_marks_c7_as_not_replicated() -> None:
    register = yaml.safe_load((REPO_ROOT / "governance/data_classification.yaml").read_text(encoding="utf-8"))
    c7 = next(c for c in register["copies"] if c["id"] == "C7")
    assert c7["store"] == "customer_system_only"
    assert "never_replicated_into_s3_or_redshift" in c7["controls"]
