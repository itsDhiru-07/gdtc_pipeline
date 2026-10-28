"""Manual review queue — the fallback when the pinned model is unavailable
or deprecated, per the deck's AI slide.

This is not a hypothetical: it's the thing that fires automatically if
ai/crew_notes/extract.py can't reach the pinned model (deprecated, throttled
past retry budget, or the quarterly gate hasn't cleared a replacement yet).
Notes land here as structured-but-unlabeled rows for a human to classify;
nothing downstream treats a queued note as if it already had an AI label.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class QueuedNote:
    note_id: str
    redacted_text: str
    reason: str
    queued_at: datetime


class FallbackQueue:
    def __init__(self) -> None:
        self._items: list[QueuedNote] = []

    def enqueue(self, note_id: str, redacted_text: str, reason: str) -> None:
        self._items.append(
            QueuedNote(
                note_id=note_id,
                redacted_text=redacted_text,
                reason=reason,
                queued_at=datetime.utcnow(),
            )
        )

    def pending(self) -> list[QueuedNote]:
        return list(self._items)

    def __len__(self) -> int:
        return len(self._items)
