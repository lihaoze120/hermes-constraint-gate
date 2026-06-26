"""Constraint engine with gate registry."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from .base import Violation, Gate

logger = logging.getLogger(__name__)

from .language_ratio import LanguageRatioGate
from .regex import RegexGate
from .forbidden_words import ForbiddenWordsGate
from .length import LengthGate
from .starts_with import StartsWithGate
from .ends_with import EndsWithGate
from .traditional_chinese import TraditionalChineseGate

# ── Gate type registry (extensible by users) ────────────────────────

_GATE_TYPES: Dict[str, type] = {
    "language_ratio": LanguageRatioGate,
    "regex": RegexGate,
    "forbidden_words": ForbiddenWordsGate,
    "length": LengthGate,
    "starts_with": StartsWithGate,
    "ends_with": EndsWithGate,
    "traditional_chinese": TraditionalChineseGate,
}



def register_gate_type(name: str, gate_cls: type) -> None:
    """Register a custom gate type so config.yaml can reference it by name."""
    if not issubclass(gate_cls, Gate):
        raise TypeError(f"{gate_cls} must be a subclass of Gate")
    _GATE_TYPES[name] = gate_cls



# ── Constraint Engine ───────────────────────────────────────────────


@dataclass
class ScanResult:
    """Result of a full constraint scan against a response."""
    passed: bool
    violations: List[Violation] = field(default_factory=list)
    transformed: bool = False
    transformed_text: str = ""


class ConstraintEngine:
    """Loads gates from config and scans responses."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.gates: List[Gate] = []
        self.enabled = self.config.get("enabled", True)
        self.log_violations = self.config.get("log_violations", False)
        self.log_path: Optional[Path] = None
        if self.log_violations:
            raw_path = self.config.get("log_path", "")
            if raw_path:
                self.log_path = Path(raw_path).expanduser()
        self._load_gates()

    def _load_gates(self) -> None:
        """Instantiate gates from config."""
        gate_configs = self.config.get("gates", [])
        if not gate_configs:
            logger.debug("No gates configured in constraint_gate section.")
            return

        for gc in gate_configs:
            if isinstance(gc, dict) and gc.get("enabled", True):
                gate_type = gc.get("type", "")
                gate_cls = _GATE_TYPES.get(gate_type)
                if gate_cls is None:
                    logger.warning(
                        "Unknown gate type '%s' for gate '%s'. Skipping.",
                        gate_type, gc.get("name", "?")
                    )
                    continue
                try:
                    gate = gate_cls(gc)
                    self.gates.append(gate)
                    logger.debug("Loaded gate: %s (type=%s)", gate.name, gate_type)
                except Exception as e:
                    logger.error("Failed to create gate '%s': %s", gc.get("name", "?"), e)

    def scan(self, response_text: str) -> ScanResult:
        """Run all enabled gates against *response_text*.

        For violations with action=transform, calls gate.transform()
        to auto-fix the response. Transforms are applied in gate order.
        """
        if not self.enabled or not self.gates:
            return ScanResult(passed=True)

        violations: List[Violation] = []
        gate_violation_map: dict = {}  # gate -> violation for transform lookup
        current_text = response_text

        for gate in self.gates:
            try:
                violation = gate.check(current_text)
                if violation:
                    violations.append(violation)
                    gate_violation_map[id(gate)] = violation

                    # Apply transform immediately if action=transform
                    if violation.action == "transform":
                        transformed = gate.transform(current_text)
                        if transformed is not None:
                            current_text = transformed
            except Exception as e:
                logger.warning("Gate '%s' raised during check: %s", gate.name, e)

        passed = len(violations) == 0
        transformed = current_text != response_text

        if violations and self.log_violations and self.log_path:
            self._log_violations(violations)

        return ScanResult(
            passed=passed,
            violations=violations,
            transformed=transformed,
            transformed_text=current_text if transformed else response_text,
        )

    def _log_violations(self, violations: List[Violation]) -> None:
        """Log violations to the configured log file."""
        if not self.log_path:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().isoformat()
            with open(self.log_path, "a", encoding="utf-8") as f:
                for v in violations:
                    f.write(
                        f"[{ts}] GATE={v.gate_name} ACTION={v.action} "
                        f"DETAIL={v.details} DESC={v.description}\n"
                    )
        except Exception as e:
            logger.debug("Failed to write constraint log: %s", e)

    def build_violation_report(self, result: ScanResult) -> str:
        """Build a concise violation report to prepend to the response."""
        if result.passed:
            return ""

        lines = ["[Constraint Gate — violations detected]"]
        for v in result.violations:
            lines.append(f"  • {v.gate_name}: {v.details}")
        lines.append("Please correct the response before sending.\n")
        return "\n".join(lines)


# ── Convenience: load config from Hermes config.yaml ────────────────


def load_constraint_config() -> Dict[str, Any]:
    """Load constraint_gate config section from Hermes config.yaml."""
    try:
        from hermes_cli.config import load_config
        config = load_config()
        return config.get("constraint_gate", {})
    except Exception:
        return {}


# ── Singleton engine (lazy init per plugin load) ────────────────────

_engine: Optional[ConstraintEngine] = None


def get_engine() -> ConstraintEngine:
    """Get or create the singleton ConstraintEngine."""
    global _engine
    if _engine is None:
        config = load_constraint_config()
        _engine = ConstraintEngine(config)
    return _engine


def reset_engine() -> None:
    """Reset the singleton engine (for testing or config reload)."""
    global _engine
    _engine = None
