"""
Constraint Gate Engine — pluggable response constraint checker.

Gates are defined in config.yaml under ``constraint_gate.gates``.
Each gate has a type, config, and action (warn/block/transform).
The engine scans assistant responses before delivery and enforces rules.
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Unicode script ranges — fine-grained for CJK disambiguation ─────

# Han characters (CJK Unified Ideographs) — shared by Chinese, Japanese, Korean
_HAN_RANGES: List[Tuple[int, int]] = [
    (0x4E00, 0x9FFF),   # CJK Unified Ideographs
    (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
    (0x20000, 0x2A6DF), # CJK Unified Ideographs Extension B
    (0x2A700, 0x2B73F), # CJK Unified Ideographs Extension C
    (0x2B740, 0x2B81F), # CJK Unified Ideographs Extension D
    (0x2B820, 0x2CEAF), # CJK Unified Ideographs Extension E
    (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
    (0x2F800, 0x2FA1F), # CJK Compatibility Ideographs Supplement
]

# Hiragana — uniquely Japanese
_HIRAGANA_RANGES: List[Tuple[int, int]] = [
    (0x3040, 0x309F),   # Hiragana
]

# Katakana — uniquely Japanese
_KATAKANA_RANGES: List[Tuple[int, int]] = [
    (0x30A0, 0x30FF),   # Katakana
    (0x31F0, 0x31FF),   # Katakana Phonetic Extensions
]

# CJK punctuation and symbols — shared
_CJK_SYMBOL_RANGES: List[Tuple[int, int]] = [
    (0x3000, 0x303F),   # CJK Symbols and Punctuation
    (0xFF00, 0xFFEF),   # Halfwidth and Fullwidth Forms
]

# Hangul — uniquely Korean
_HANGUL_RANGES: List[Tuple[int, int]] = [
    (0xAC00, 0xD7AF),   # Hangul Syllables
    (0x1100, 0x11FF),   # Hangul Jamo
]

_LATIN_RANGES: List[Tuple[int, int]] = [
    (0x0041, 0x005A),   # A-Z
    (0x0061, 0x007A),   # a-z
    (0x00C0, 0x024F),   # Latin Extended
    (0x1E00, 0x1EFF),   # Latin Extended Additional
]

_CYRILLIC_RANGES: List[Tuple[int, int]] = [
    (0x0400, 0x04FF),   # Cyrillic
    (0x0500, 0x052F),   # Cyrillic Supplement
]

_ARABIC_RANGES: List[Tuple[int, int]] = [
    (0x0600, 0x06FF),   # Arabic
    (0x0750, 0x077F),   # Arabic Supplement
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
]

_DEVANAGARI_RANGES: List[Tuple[int, int]] = [
    (0x0900, 0x097F),   # Devanagari
]

# Script name registry — fine-grained
SCRIPT_REGISTRY: Dict[str, List[Tuple[int, int]]] = {
    # Atomic scripts
    "Han": _HAN_RANGES,
    "Hiragana": _HIRAGANA_RANGES,
    "Katakana": _KATAKANA_RANGES,
    "Hangul": _HANGUL_RANGES,
    "Latin": _LATIN_RANGES,
    "Cyrillic": _CYRILLIC_RANGES,
    "Arabic": _ARABIC_RANGES,
    "Devanagari": _DEVANAGARI_RANGES,
    # Composite scripts (convenience aliases)
    "Japanese-Kana": _HIRAGANA_RANGES + _KATAKANA_RANGES,
}


def _char_in_ranges(char: str, ranges: List[Tuple[int, int]]) -> bool:
    """Check if a single character falls in any of the given Unicode ranges."""
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in ranges)


def count_script_chars(text: str, script_name: str) -> int:
    """Count characters in *text* belonging to *script_name*.

    Supports atomic scripts (Han, Hiragana, Katakana, Latin, etc.)
    and composite aliases (Japanese-Kana = Hiragana + Katakana).
    """
    ranges = SCRIPT_REGISTRY.get(script_name, [])
    if not ranges:
        return 0
    return sum(1 for ch in text if _char_in_ranges(ch, ranges))


def count_meaningful_chars(text: str) -> int:
    """Count characters that are actual script content (not punctuation/whitespace/emoji/symbols).

    Counts: Han, Hiragana, Katakana, Hangul, Latin, Cyrillic, Arabic, Devanagari letters.
    Excludes: ASCII punctuation, CJK punctuation, spaces, emoji, kaomoji symbols.
    """
    # Gather all script ranges for quick membership test
    _all_script_ranges: List[Tuple[int, int]] = []
    for ranges in SCRIPT_REGISTRY.values():
        _all_script_ranges.extend(ranges)

    meaningful = 0
    for ch in text:
        if _char_in_ranges(ch, _all_script_ranges):
            meaningful += 1
    return meaningful


# ── Violation record ────────────────────────────────────────────────


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


class EndsWithGate(Gate):
    """Ensure response does not end with prohibited suffixes."""

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        suffixes = cfg.get("suffixes", [])
        stripped = response_text.rstrip()

        for suffix in suffixes:
            if stripped.endswith(suffix):
                return Violation(
                    gate_name=self.name,
                    description=self.description,
                    details=f"Response ends with: '{suffix}'",
                    action=self.action,
                )
        return None

    def transform(self, response_text: str) -> Optional[str]:
        """Strip the banned suffix from the response text."""
        cfg = self.config.get("config", {})
        suffixes = cfg.get("suffixes", [])
        stripped = response_text.rstrip()
        for suffix in suffixes:
            if stripped.endswith(suffix):
                trailing = response_text[len(stripped):]
                return stripped[: -len(suffix)] + trailing
        return None


# ── Traditional Chinese character set ───────────────────────────────

# Common traditional Chinese characters with their simplified equivalents.
# Built from the Table of General Standard Chinese Characters (通用规范汉字表)
# contrastive pairs. Models occasionally slip traditional chars into
# otherwise-simplified output; this catches them.
_DEFAULT_TRADITIONAL_CHARS: set = set(
    # Only characters with distinct simplified equivalents (not shared forms).
    # Traditional → Simplified pairs from 通用规范汉字表 contrastive set.
    "個們麼這說來時會過開關頭兒長"
    "見貝車門馬魚鳥龍龜風飛"
    "體國書學實寫寶愛戰戲"
    "專創態檔臺爲後"
    "發盡數歲廳應幾"
    "斷曆樓機權殺決沒況準"
    "進運達錢鐵銀銅鋼"
    "電靈靜頁順須顯"
    "東對導從無興"
    "亞萬與業義"
    "將尋異"
    "輕轉農連遊鄉"
    "雲雜錦雖鍾"
    "丟亂乾億僕價"
    "優償嚇壞壓"
    "夠妝孫宮審寵"
    "層屬岡峽帥並廢廣"
    "張強彈徵徹復"
    "憐懷戀戶擁擊擠擬"
    "斂曬殘毀毆氣溝"
    "漢滿漁烏煙煩燒"
    "熱燈爭爺爾牆獲獎獨"
    "現環產當畫療疊"
    "盜眾睜瞭確"
    "禮禍禪稱競筆簡"
    "節範糧糾紀約"
    "紙級紡紋納"
    "純組結絕絲"
    "統經綠緊緒線"
    "術樣"
    "嬪嫻嬈孫"
    "礙礎禮"
    "穩積"
    "貢責"
    "貨貿"
    "質"
)


class TraditionalChineseGate(Gate):
    """Detect traditional Chinese characters in otherwise-simplified output.

    Uses a built-in reference set of common traditional characters
    (extensible via ``extra_chars`` in config). Any match triggers
    a violation — the assistant should rewrite with simplified Chinese.
    """

    def check(self, response_text: str) -> Optional[Violation]:
        cfg = self.config.get("config", {})
        extra = set(cfg.get("extra_chars", []))
        char_set = _DEFAULT_TRADITIONAL_CHARS | extra

        found: list[str] = []
        seen: set[str] = set()
        for ch in response_text:
            if ch in char_set and ch not in seen:
                found.append(ch)
                seen.add(ch)
                if len(found) >= 20:  # cap report at 20 unique chars
                    break

        if found:
            return Violation(
                gate_name=self.name,
                description=self.description,
                details=(
                    f"Found {len(found)} traditional Chinese char(s): "
                    f"{', '.join(found)}"
                ),
                action=self.action,
            )
        return None


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
