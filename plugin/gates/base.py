"""Gate base classes."""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)

@dataclass
class Violation:
    """A single constraint violation found by a gate."""
    gate_name: str
    description: str
    details: str = ""
    action: str = "warn"  # warn, block, transform


# ── Gate types (pluggable) ──────────────────────────────────────────



class Gate(ABC):
    """Base class for constraint gates. Subclass to add new gate types."""

    name: str = ""
    description: str = ""
    action: str = "warn"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.name)
        self.description = config.get("description", self.description)
        self.action = config.get("action", "warn")

    @abstractmethod
    def check(self, response_text: str) -> Optional[Violation]:
        """Return a Violation if the constraint is broken, else None."""
        ...

    def transform(self, response_text: str) -> Optional[str]:
        """Attempt to auto-fix the violation. Returns transformed text, or None if unfixable.

        Override in subclasses that support ``action: transform``.
        Default: no-op — most gates can only warn/block.
        """
        return None


# ── Built-in gate implementations ───────────────────────────────────


