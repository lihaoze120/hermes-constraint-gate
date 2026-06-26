"""Gate: regex."""
from __future__ import annotations
import logging
import re

logger = logging.getLogger(__name__)
from typing import Optional
from .base import Gate, Violation

class RegexGate(Gate):
    """Check response against one or more regex patterns."""

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        pattern_str = cfg.get("pattern", "")
        patterns = cfg.get("patterns", [pattern_str] if pattern_str else [])

        if not patterns:
            return None

        for pat in patterns:
            try:
                if re.search(pat, response_text, re.MULTILINE | re.UNICODE):
                    return Violation(
                        gate_name=self.name,
                        description=self.description,
                        details=f"Matched pattern: {pat}",
                        action=self.action,
                    )
            except re.error as e:
                logger.warning("Invalid regex in gate '%s': %s — %s", self.name, pat, e)
        return None

    def transform(self, response_text: str) -> Optional[str]:
        """Strip matched regex patterns from the response.

        Use ``replacement`` in config to control what replaces matches:
        - unset: empty string (full removal)
        - ``\\1``: keep first capture group (useful for markdown stripping)
        """
        cfg = self.config.get("config", {})
        pattern_str = cfg.get("pattern", "")
        patterns = cfg.get("patterns", [pattern_str] if pattern_str else [])
        replacement = cfg.get("replacement", "")
        result = response_text
        for pat in patterns:
            try:
                result = re.sub(pat, replacement, result, flags=re.MULTILINE | re.UNICODE)
            except re.error:
                pass
        return result if result != response_text else None


