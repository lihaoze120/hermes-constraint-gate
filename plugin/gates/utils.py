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


