"""Gate: starts_with."""
from __future__ import annotations
from typing import Optional
from .base import Gate, Violation

class StartsWithGate(Gate):
    """Ensure response does not start with prohibited prefixes."""

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        prefixes = cfg.get("prefixes", [])
        stripped = response_text.lstrip()

        for prefix in prefixes:
            if stripped.startswith(prefix):
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=f"Response starts with: '{prefix}'",
                    action=self.action,
                )
        return None

    def transform(self, response_text: str) -> Optional[str]:
        """Strip the banned prefix from the response text."""
        cfg = self.config.get("config", {})
        prefixes = cfg.get("prefixes", [])
        stripped = response_text.lstrip()
        for prefix in prefixes:
            if stripped.startswith(prefix):
                leading = response_text[: len(response_text) - len(stripped)]
                return leading + stripped[len(prefix):]
        return None


