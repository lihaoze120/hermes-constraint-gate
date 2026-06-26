"""Gate: forbidden_words."""
from __future__ import annotations
import re
from typing import Optional
from .base import Gate, Violation

class ForbiddenWordsGate(Gate):
    """Check for forbidden words/phrases (case-insensitive)."""

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        words = cfg.get("words", [])
        if not words:
            return None

        lower_text = response_text.lower()
        for word in words:
            if word.lower() in lower_text:
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=f"Found forbidden word: '{word}'",
                    action=self.action,
                )
        return None

    def transform(self, response_text: str) -> Optional[str]:
        """Strip all forbidden words from the response (case-insensitive)."""
        cfg = self.config.get("config", {})
        words = cfg.get("words", [])
        result = response_text
        for word in words:
            # Case-insensitive replace
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            result = pattern.sub("", result)
        return result if result != response_text else None


