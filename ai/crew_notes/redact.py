"""Redact crew notes before anything touches the AI step.

LEG-02 control: before AI processing, we need to know where processed, what
retained, and the provider's rights. Redaction happens BEFORE the Bedrock
call, not after — the model never sees a raw name or phone number in the
first place. This is intentionally a conservative regex pass, not an AI
redaction step; adding AI-on-AI here would just move the sensitive-data
boundary instead of closing it.
"""
from __future__ import annotations

import re

PHONE_RE = re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
# Deliberately coarse: any capitalized two-token sequence is treated as a
# possible name and redacted. Over-redaction is the safe failure mode here.
NAME_LIKE_RE = re.compile(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b")


def redact(note_text: str) -> tuple[str, dict]:
    redactions = {"phone": 0, "name_like": 0}

    def _sub_phone(m: re.Match) -> str:
        redactions["phone"] += 1
        return "[PHONE]"

    def _sub_name(m: re.Match) -> str:
        redactions["name_like"] += 1
        return "[NAME]"

    text = PHONE_RE.sub(_sub_phone, note_text)
    text = NAME_LIKE_RE.sub(_sub_name, text)
    return text, redactions
