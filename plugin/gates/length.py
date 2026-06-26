"""Gate: length."""
from __future__ import annotations
from typing import Optional
from .base import Gate, Violation

class LengthGate(Gate):
    """Check response length constraints."""

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        max_chars = cfg.get("max_chars")
        min_chars = cfg.get("min_chars")
        max_lines = cfg.get("max_lines")

        if max_chars and len(response_text) > max_chars:
            return Violation(
                gate_name=self.name,
                description=self.description,
                details=f"Response length {len(response_text)} > max {max_chars}",
                action=self.action,
            )
        if min_chars and len(response_text) < min_chars:
            return Violation(
                gate_name=self.name,
                description=self.description,
                details=f"Response length {len(response_text)} < min {min_chars}",
                action=self.action,
            )
        if max_lines:
            line_count = response_text.count("\n") + 1
            if line_count > max_lines:
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=f"Response lines {line_count} > max {max_lines}",
                    action=self.action,
                )
        return None


