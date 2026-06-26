"""Gate: language_ratio."""
from __future__ import annotations
from typing import Optional
from .base import Gate, Violation
from .utils import count_meaningful_chars, count_script_chars, SCRIPT_REGISTRY

class LanguageRatioGate(Gate):
    """Check language script ratio constraints.

    Supports two modes (at least one must be configured):

    1. ``primary_script`` + ``min_ratio`` — ensure script X is AT LEAST N% of
       meaningful characters.  Good for: "Latin must be >= 80%".

    2. ``foreign_script`` + ``max_ratio`` — ensure script X is AT MOST N% of
       meaningful characters.  Good for: "Japanese-Kana must be <= 30%"
       (use this to catch Japanese-heavy responses from a Chinese-primary
        assistant, since Han characters are shared between CN and JP).

    Both modes can be combined in a single gate config.
    """

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        primary_script = cfg.get("primary_script", "")
        min_ratio = cfg.get("min_ratio")
        foreign_script = cfg.get("foreign_script", "")
        max_ratio = cfg.get("max_ratio")

        total = count_meaningful_chars(response_text)
        if total == 0:
            return None

        # Mode 1: primary script minimum
        if primary_script and min_ratio is not None:
            primary_count = count_script_chars(response_text, primary_script)
            actual_ratio = primary_count / total
            if actual_ratio < float(min_ratio):
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=(
                        f"{primary_script} ratio {actual_ratio:.1%} < required {float(min_ratio):.0%}"
                        f" ({primary_count}/{total} meaningful chars)"
                    ),
                    action=self.action,
                )

        # Mode 2: foreign script maximum
        if foreign_script and max_ratio is not None:
            foreign_count = count_script_chars(response_text, foreign_script)
            actual_ratio = foreign_count / total
            if actual_ratio > float(max_ratio):
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=(
                        f"{foreign_script} ratio {actual_ratio:.1%} > allowed {float(max_ratio):.0%}"
                        f" ({foreign_count}/{total} meaningful chars)"
                    ),
                    action=self.action,
                )

        return None


