"""
constraint-gate plugin — pre-response constraint enforcement.

Hooks into Hermes's ``transform_llm_output`` to scan every assistant response
before delivery. Gates are configured in config.yaml under ``constraint_gate:``.

Gate types: language_ratio, regex, forbidden_words, length, starts_with.
Actions: warn (log only), block (inject reminder), transform (auto-fix where possible).

Architecture:
    Assistant generates response
        → transform_llm_output hook fires
            → ConstraintEngine scans the text
                → PASS: text unchanged
                → FAIL: violation logged; text may be annotated or left as-is
            → Response delivered to user
    Next turn: assistant reads its own annotated response and self-corrects
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from .gates.engine import (
        ConstraintEngine,
        get_engine,
        reset_engine,
        load_constraint_config,
    )
    from .gates.base import Violation
except ImportError:
    from plugin.gates.engine import (
        ConstraintEngine,
        get_engine,
        reset_engine,
        load_constraint_config,
    )
    from plugin.gates.base import Violation

logger = logging.getLogger(__name__)


def _build_injection(violations: list[Violation]) -> str:
    """Build a compact violation note to inject into the response.

    This appears in the assistant's own message in conversation history,
    so on the next turn the assistant reads it and can self-correct.
    Format: invisible-ish so the user isn't bothered by it.
    """
    parts = ["[📋 Constraint Gate — previous response had violations:]"]
    for v in violations:
        parts.append(f"  • {v.gate_name}: {v.details}")
    parts.append("  Please correct these in your next response.\n")
    return "\n".join(parts)


def _on_transform_llm_output(
    response_text: str = "",
    session_id: str = "",
    model: str = "",
    platform: str = "",
    **kwargs: Any,
) -> Optional[str]:
    """Hook: scan response and enforce constraints.

    Returns:
        - None: no transformation needed (all gates passed)
        - str: transformed response (violation note injected)
    """
    if not response_text or not response_text.strip():
        return None

    try:
        engine = get_engine()
    except Exception as e:
        logger.debug("Constraint engine init failed: %s", e)
        return None

    result = engine.scan(response_text)

    if result.passed:
        return None  # All clear, no transform

    # Violations found — handle per-action
    has_block = any(v.action == "block" for v in result.violations)
    has_transform = any(v.action == "transform" for v in result.violations)

    if has_block:
        injection = _build_injection(result.violations)
        logger.info(
            "Constraint Gate BLOCKED %d violation(s) in session=%s model=%s",
            len(result.violations), session_id, model,
        )
        return injection + "\n\n" + response_text

    if has_transform:
        if result.transformed:
            logger.info(
                "Constraint Gate TRANSFORMED %d violation(s) in session=%s",
                len(result.violations), session_id,
            )
            return result.transformed_text
        logger.info(
            "Constraint Gate transform requested but not applicable for %d violation(s)",
            len(result.violations),
        )

    if result.violations:
        injection = _build_injection(result.violations)
        logger.info(
            "Constraint Gate WARNED %d violation(s) in session=%s model=%s",
            len(result.violations), session_id, model,
        )
        return injection + "\n\n" + response_text

    return None


def register(ctx) -> None:
    """Plugin entry point — called by Hermes plugin loader.

    Args:
        ctx: PluginContext with register_hook(), register_tool(), etc.
    """
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    logger.info("constraint-gate plugin registered (transform_llm_output hook)")
