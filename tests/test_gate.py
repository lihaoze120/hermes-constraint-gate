"""Tests for constraint-gate plugin — covers all 7 gate types + engine."""

import sys
import os

# Ensure plugin/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugin"))

import pytest
from plugin.gates import (
    ConstraintEngine,
    LanguageRatioGate,
    RegexGate,
    ForbiddenWordsGate,
    LengthGate,
    StartsWithGate,
    EndsWithGate,
    TraditionalChineseGate,
    ScanResult,
    Violation,
    reset_engine,
)


# ── LanguageRatioGate ─────────────────────────────────────────────────

class TestLanguageRatioGate:
    def test_primary_script_passes(self):
        gate = LanguageRatioGate({
            "name": "enforce_latin",
            "type": "language_ratio",
            "config": {"primary_script": "Latin", "min_ratio": 0.5},
        })
        assert gate.check("Hello world, this is English text.") is None

    def test_primary_script_fails(self):
        gate = LanguageRatioGate({
            "name": "enforce_latin",
            "type": "language_ratio",
            "config": {"primary_script": "Latin", "min_ratio": 0.9},
        })
        result = gate.check("こんにちは世界 hello")
        assert result is not None
        assert "Latin" in result.details

    def test_foreign_script_passes(self):
        gate = LanguageRatioGate({
            "name": "kana_limit",
            "type": "language_ratio",
            "config": {"foreign_script": "Japanese-Kana", "max_ratio": 0.3},
        })
        # Mostly Han with minimal kana
        assert gate.check("這是中文，只有一點點ね") is None

    def test_foreign_script_fails(self):
        gate = LanguageRatioGate({
            "name": "kana_limit",
            "type": "language_ratio",
            "config": {"foreign_script": "Japanese-Kana", "max_ratio": 0.1},
        })
        result = gate.check("こんにちは、お元気ですか？")
        assert result is not None
        assert "Japanese-Kana" in result.details

    def test_empty_text(self):
        gate = LanguageRatioGate({
            "name": "test",
            "type": "language_ratio",
            "config": {"primary_script": "Latin", "min_ratio": 0.5},
        })
        assert gate.check("") is None

    def test_no_meaningful_chars(self):
        gate = LanguageRatioGate({
            "name": "test",
            "type": "language_ratio",
            "config": {"primary_script": "Latin", "min_ratio": 0.5},
        })
        assert gate.check("123 !@#$%") is None

    def test_both_primary_and_foreign(self):
        gate = LanguageRatioGate({
            "name": "combo",
            "type": "language_ratio",
            "config": {
                "primary_script": "Latin",
                "min_ratio": 0.3,
                "foreign_script": "Japanese-Kana",
                "max_ratio": 0.9,
            },
        })
        # English with no kana passes both
        assert gate.check("This is English text.") is None


# ── RegexGate ─────────────────────────────────────────────────────────

class TestRegexGate:
    def test_single_pattern_match(self):
        gate = RegexGate({
            "name": "no_bold",
            "type": "regex",
            "config": {"pattern": r"\*\*[^*]+\*\*"},
        })
        result = gate.check("This has **bold** text.")
        assert result is not None
        assert "Matched pattern" in result.details

    def test_single_pattern_no_match(self):
        gate = RegexGate({
            "name": "no_bold",
            "type": "regex",
            "config": {"pattern": r"\*\*[^*]+\*\*"},
        })
        assert gate.check("This has no bold text.") is None

    def test_multiple_patterns(self):
        gate = RegexGate({
            "name": "no_formatting",
            "type": "regex",
            "config": {"patterns": [r"\*\*", r"```", r"^#+\s"]},
        })
        result = gate.check("## Heading")
        assert result is not None

    def test_invalid_regex_handled(self):
        gate = RegexGate({
            "name": "bad",
            "type": "regex",
            "config": {"pattern": "[unclosed"},
        })
        # Should not raise, just skip
        assert gate.check("anything") is None


# ── ForbiddenWordsGate ────────────────────────────────────────────────

class TestForbiddenWordsGate:
    def test_word_found(self):
        gate = ForbiddenWordsGate({
            "name": "no_docker",
            "type": "forbidden_words",
            "config": {"words": ["docker", "kubernetes"]},
        })
        result = gate.check("You should use Docker for this.")
        assert result is not None
        assert "docker" in result.details.lower()

    def test_case_insensitive(self):
        gate = ForbiddenWordsGate({
            "name": "no_docker",
            "type": "forbidden_words",
            "config": {"words": ["docker"]},
        })
        assert gate.check("Try DOCKER.") is not None

    def test_no_match(self):
        gate = ForbiddenWordsGate({
            "name": "no_docker",
            "type": "forbidden_words",
            "config": {"words": ["docker", "kubernetes"]},
        })
        assert gate.check("Use native apps.") is None

    def test_empty_words(self):
        gate = ForbiddenWordsGate({
            "name": "empty",
            "type": "forbidden_words",
            "config": {},
        })
        assert gate.check("anything") is None


# ── LengthGate ────────────────────────────────────────────────────────

class TestLengthGate:
    def test_max_chars_exceeded(self):
        gate = LengthGate({
            "name": "short",
            "type": "length",
            "config": {"max_chars": 5},
        })
        result = gate.check("too long")
        assert result is not None

    def test_max_chars_ok(self):
        gate = LengthGate({
            "name": "short",
            "type": "length",
            "config": {"max_chars": 100},
        })
        assert gate.check("ok") is None

    def test_min_chars_not_met(self):
        gate = LengthGate({
            "name": "min",
            "type": "length",
            "config": {"min_chars": 10},
        })
        result = gate.check("short")
        assert result is not None

    def test_max_lines_exceeded(self):
        gate = LengthGate({
            "name": "lines",
            "type": "length",
            "config": {"max_lines": 2},
        })
        result = gate.check("line1\nline2\nline3")
        assert result is not None


# ── StartsWithGate ────────────────────────────────────────────────────

class TestStartsWithGate:
    def test_prefix_found(self):
        gate = StartsWithGate({
            "name": "no_hello",
            "type": "starts_with",
            "config": {"prefixes": ["Hello", "Sure!"]},
        })
        result = gate.check("Sure! Let me help you.")
        assert result is not None

    def test_prefix_not_found(self):
        gate = StartsWithGate({
            "name": "no_hello",
            "type": "starts_with",
            "config": {"prefixes": ["Hello", "Sure!"]},
        })
        assert gate.check("Here is the answer.") is None

    def test_leading_whitespace_ignored(self):
        gate = StartsWithGate({
            "name": "test",
            "type": "starts_with",
            "config": {"prefixes": ["好的！"]},
        })
        result = gate.check("  好的！没问题")
        assert result is not None


# ── EndsWithGate ──────────────────────────────────────────────────────

class TestEndsWithGate:
    def test_suffix_found(self):
        gate = EndsWithGate({
            "name": "no_trailing",
            "type": "ends_with",
            "config": {"suffixes": ["Let me know if", "Would you like"]},
        })
        result = gate.check("Here's the answer. Would you like")
        assert result is not None

    def test_suffix_not_found(self):
        gate = EndsWithGate({
            "name": "no_trailing",
            "type": "ends_with",
            "config": {"suffixes": ["Let me know if"]},
        })
        assert gate.check("Here's the answer.") is None

    def test_trailing_whitespace_ignored(self):
        gate = EndsWithGate({
            "name": "test",
            "type": "ends_with",
            "config": {"suffixes": ["thanks"]},
        })
        result = gate.check("Here is the answer. thanks  \n")
        assert result is not None


# ── TraditionalChineseGate ────────────────────────────────────────────

class TestTraditionalChineseGate:
    def test_traditional_detected(self):
        gate = TraditionalChineseGate({
            "name": "simplified_only",
            "type": "traditional_chinese",
            "config": {},
        })
        result = gate.check("這是個問題。")
        assert result is not None
        assert "traditional" in result.details.lower()

    def test_simplified_passes(self):
        gate = TraditionalChineseGate({
            "name": "simplified_only",
            "type": "traditional_chinese",
            "config": {},
        })
        assert gate.check("这是个问题。") is None

    def test_english_passes(self):
        gate = TraditionalChineseGate({
            "name": "simplified_only",
            "type": "traditional_chinese",
            "config": {},
        })
        assert gate.check("Hello world.") is None

    def test_extra_chars(self):
        gate = TraditionalChineseGate({
            "name": "custom",
            "type": "traditional_chinese",
            "config": {"extra_chars": ["A", "B"]},
        })
        result = gate.check("Hello A world.")
        assert result is not None

    def test_duplicate_chars_reported_once(self):
        gate = TraditionalChineseGate({
            "name": "test",
            "type": "traditional_chinese",
            "config": {},
        })
        result = gate.check("個個個個個")
        assert result is not None
        # Should report 1 unique char, not 5
        assert "1" in result.details  # "Found 1 traditional Chinese char(s)"


# ── Transform (auto-fix) ──────────────────────────────────────────────

class TestTransform:
    def test_starts_with_transform(self):
        gate = StartsWithGate({
            "name": "no_hello",
            "type": "starts_with",
            "action": "transform",
            "config": {"prefixes": ["好的！", "没问题！"]},
        })
        result = gate.transform("好的！我来帮你。")
        assert result == "我来帮你。"

    def test_ends_with_transform(self):
        gate = EndsWithGate({
            "name": "no_trailing",
            "type": "ends_with",
            "action": "transform",
            "config": {"suffixes": ["Would you like me to"]},
        })
        result = gate.transform("Done. Would you like me to")
        assert result == "Done. "

    def test_regex_transform(self):
        gate = RegexGate({
            "name": "strip_markdown",
            "type": "regex",
            "action": "transform",
            "config": {"patterns": [r"\*\*[^*]+\*\*"]},
        })
        result = gate.transform("This is **bold** text.")
        assert "**" not in result
        assert "This is  text." in result

    def test_forbidden_words_transform(self):
        gate = ForbiddenWordsGate({
            "name": "strip_docker",
            "type": "forbidden_words",
            "action": "transform",
            "config": {"words": ["docker", "Docker"]},
        })
        result = gate.transform("Use Docker for this.")
        assert "Docker" not in result
        assert "docker" not in result.lower()

    def test_transform_no_match_noop(self):
        gate = StartsWithGate({
            "name": "no_hello",
            "type": "starts_with",
            "action": "transform",
            "config": {"prefixes": ["好的！"]},
        })
        assert gate.transform("Clean text.") is None

    def test_engine_applies_transform(self):
        config = {
            "enabled": True,
            "gates": [
                {
                    "name": "strip_prefix",
                    "type": "starts_with",
                    "action": "transform",
                    "config": {"prefixes": ["好的！"]},
                },
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("好的！这是正文。")
        assert result.transformed
        assert result.transformed_text == "这是正文。"
        assert len(result.violations) > 0  # Violations still recorded

    def test_engine_transform_chain(self):
        config = {
            "enabled": True,
            "gates": [
                {
                    "name": "strip_prefix",
                    "type": "starts_with",
                    "action": "transform",
                    "config": {"prefixes": ["好的！"]},
                },
                {
                    "name": "strip_suffix",
                    "type": "ends_with",
                    "action": "transform",
                    "config": {"suffixes": ["需要我继续吗？"]},
                },
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("好的！正文内容。需要我继续吗？")
        assert result.transformed
        assert result.transformed_text == "正文内容。"
        assert len(result.violations) == 2


# ── ConstraintEngine ─────────────────────────────────────────────────

class TestConstraintEngine:
    def test_all_gates_pass(self):
        config = {
            "enabled": True,
            "gates": [
                {
                    "name": "enforce_latin",
                    "type": "language_ratio",
                    "config": {"primary_script": "Latin", "min_ratio": 0.5},
                },
                {
                    "name": "no_bold",
                    "type": "regex",
                    "config": {"pattern": r"\*\*[^*]+\*\*"},
                },
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("This is fine text.")
        assert result.passed
        assert len(result.violations) == 0

    def test_one_gate_fails(self):
        config = {
            "enabled": True,
            "gates": [
                {
                    "name": "no_docker",
                    "type": "forbidden_words",
                    "action": "block",
                    "config": {"words": ["docker"]},
                },
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("Use Docker for this.")
        assert not result.passed
        assert len(result.violations) == 1
        assert result.violations[0].gate_name == "no_docker"

    def test_disabled_engine(self):
        config = {"enabled": False, "gates": []}
        engine = ConstraintEngine(config)
        result = engine.scan("anything")
        assert result.passed

    def test_empty_config(self):
        engine = ConstraintEngine()
        result = engine.scan("anything")
        assert result.passed

    def test_unknown_gate_type_skipped(self):
        config = {
            "enabled": True,
            "gates": [
                {"name": "ghost", "type": "nonexistent", "config": {}},
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("anything")
        assert result.passed  # Unknown gate skipped, no crash

    def test_disabled_gate_skipped(self):
        config = {
            "enabled": True,
            "gates": [
                {
                    "name": "no_docker",
                    "type": "forbidden_words",
                    "enabled": False,
                    "config": {"words": ["docker"]},
                },
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("Use Docker.")
        assert result.passed  # Gate disabled, should not trigger

    def test_violation_report(self):
        config = {
            "enabled": True,
            "gates": [
                {
                    "name": "no_docker",
                    "type": "forbidden_words",
                    "action": "block",
                    "config": {"words": ["docker"]},
                },
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("Use Docker.")
        report = engine.build_violation_report(result)
        assert "Constraint Gate" in report
        assert "no_docker" in report

    def test_reset_engine(self):
        config = {"enabled": False, "gates": []}
        engine1 = ConstraintEngine(config)
        from plugin.gates.engine import get_engine
        # Force singleton
        import plugin.gates.engine as eng
        eng._engine = engine1
        assert get_engine() is engine1
        reset_engine()
        assert eng._engine is None


# ── Edge cases ────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_response(self):
        engine = ConstraintEngine({
            "enabled": True,
            "gates": [
                {"name": "test", "type": "forbidden_words", "config": {"words": ["x"]}},
            ],
        })
        result = engine.scan("")
        assert result.passed

    def test_pure_punctuation(self):
        engine = ConstraintEngine({
            "enabled": True,
            "gates": [
                {"name": "min_latin", "type": "language_ratio", "config": {"primary_script": "Latin", "min_ratio": 0.5}},
            ],
        })
        # No meaningful chars → passes (avoids division by zero)
        result = engine.scan("!@#$%^&*()")
        assert result.passed

    def test_multiple_violations(self):
        config = {
            "enabled": True,
            "gates": [
                {"name": "g1", "type": "forbidden_words", "config": {"words": ["docker"]}},
                {"name": "g2", "type": "regex", "config": {"pattern": r"\*\*"}},
            ],
        }
        engine = ConstraintEngine(config)
        result = engine.scan("Use Docker with **bold** text.")
        assert not result.passed
        assert len(result.violations) == 2
