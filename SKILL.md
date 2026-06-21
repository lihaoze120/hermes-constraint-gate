---
name: constraint-gate
description: Use BEFORE EVERY response. A universal pre-response constraint scanner — configurable gates enforce language ratio, banned patterns, interaction style, and technical vetos. Backed by the constraint-gate plugin for code-level enforcement.
version: 0.10.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [constraints, self-check, quality-gate, pre-send, universal]
---

# Constraint Gate — Universal Pre-Response Scanner

**Load at session start. Execute before every response.**

Two-layer enforcement:
- **Skill** = mental self-check before sending
- **Plugin** = code-level scan via `transform_llm_output` hook

---

## Available Gate Types (7)

| Type | What it checks | Config keys |
|------|---------------|------------|
| `language_ratio` | Script ratio in text | `primary_script`+`min_ratio` OR `foreign_script`+`max_ratio` |
| `regex` | Regex pattern match | `pattern` (single) or `patterns` (list) |
| `forbidden_words` | Case-insensitive word match | `words` (list) |
| `length` | Char/line count limits | `max_chars`, `min_chars`, `max_lines` |
| `starts_with` | Response prefix check | `prefixes` (list) |
| `ends_with` | Response suffix check | `suffixes` (list) |
| `traditional_chinese` | Detect traditional Chinese chars | `extra_chars` (list, optional) |

### Script names for `language_ratio`

Atomic: `Han`, `Hiragana`, `Katakana`, `Hangul`, `Latin`, `Cyrillic`, `Arabic`, `Devanagari`

Composite: `Japanese-Kana` (Hiragana + Katakana)

### Action types

| Action | Effect |
|--------|--------|
| `warn` | Log violation, inject note into history for next-turn self-correction |
| `block` | Same as warn + prepend violation report to user-visible response |
| `transform` | Auto-fix — strip banned patterns, clean the response |

---

## Pre-Response Checklist

Before sending, run through YOUR configured gates:

1. **Language ratio** — is the foreign script under your threshold?
2. **Banned patterns** — any regex matches?
3. **Forbidden words** — any blacklisted terms?
4. **Length** — within line/char limits?
5. **Opening** — not starting with a banned prefix?
6. **Ending** — not ending with a banned suffix?

If any gate triggers: fix the response, re-check, then send.

---

## Configuration Examples

### Universal (English)

```yaml
constraint_gate:
  enabled: true
  gates:
    - name: enforce_english
      type: language_ratio
      config:
        primary_script: Latin
        min_ratio: 0.8
    - name: no_formal
      type: starts_with
      config:
        prefixes: ["Dear", "Hello", "Greetings"]
    - name: keep_concise
      type: length
      config:
        max_lines: 25
```

### CJK (Chinese/Japanese)

```yaml
constraint_gate:
  enabled: true
  gates:
    - name: kana_limit
      type: language_ratio
      config:
        foreign_script: Japanese-Kana
        max_ratio: 0.30
    - name: simplified_only
      type: traditional_chinese
      action: block
      config: {}
```

### Developer (Ban suggestions)

```yaml
constraint_gate:
  enabled: true
  gates:
    - name: no_api_keys
      type: regex
      config:
        patterns:
          - "(?:sign up|create an account|get an API key)"
    - name: no_docker
      type: forbidden_words
      config:
        words: ["docker", "containerize"]
```

Full config files in `examples/`:
- `config-example.yaml` — universal
- `config-example-cjk.yaml` — CJK specific

---

## Plugin Integration

Install at `~/.hermes/plugins/constraint-gate/`. Hooks into `transform_llm_output`.

```
Assistant generates response
  → turn_finalizer.py: transform_llm_output hook fires
    → constraint-gate plugin scans the text
      → PASS: text unchanged
      → FAIL: violation report injected into response
        → Next turn: assistant reads its own annotated message, self-corrects
```

Installation:
1. Copy `constraint-gate/` to `~/.hermes/plugins/`
2. Add `constraint-gate` to `plugins.enabled` in config.yaml
3. Configure gates under `constraint_gate:` in config.yaml
4. Restart Hermes

---

## Common Pitfalls

1. **Setting thresholds too tight** — 90% language ratio may trigger on code blocks or normal variation.
2. **Regex patterns too broad** — `.*` or unanchored patterns match everything. Anchor with `^` or use specific strings.
3. **Forgetting to restart** — plugins load at Hermes startup. Config changes need restart.
4. **Self-check only, no plugin** — mental check is fallible. The plugin catches what you miss.

---

## Extending

Register custom gate types:

```python
from gate import Gate, Violation, register_gate_type

class SentimentGate(Gate):
    def check(self, text):
        negative = self.config.get("config", {}).get("words", [])
        for word in negative:
            if word.lower() in text.lower():
                return Violation(
                    gate_name=self.name,
                    description="Negative sentiment",
                    details=f"Found: {word}",
                    action=self.action,
                )
        return None

register_gate_type("sentiment", SentimentGate)
```
