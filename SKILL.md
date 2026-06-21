---
name: constraint-gate
description: Use BEFORE EVERY response. A universal pre-response constraint scanner — configurable gates enforce language ratio, banned patterns, interaction style, and technical vetos. Backed by the constraint-gate plugin for code-level enforcement.
version: 0.9.1
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [constraints, self-check, quality-gate, pre-send, universal]
    related_skills: [agent-operations, self-quality-gate]
---

# Constraint Gate — Universal Pre-Response Scanner

**Load at session start. Execute before every response.**

This skill is a mental pre-flight checklist. It works together with the `constraint-gate`
plugin (hooks into `transform_llm_output`) for two-layer enforcement:
- **Skill** = mental self-check before sending
- **Plugin** = code-level scan, injects violation notes into conversation history

---

## How to Configure

Define your gates in `config.yaml` under `constraint_gate:`. The plugin reads this
section and enforces it programmatically. This skill mirrors the gates for mental
self-check.

**Example — Chinese-primary user who wants to limit Japanese:**
```yaml
constraint_gate:
  enabled: true
  gates:
    - name: foreign_script_limit
      type: language_ratio
      action: block
      config:
        foreign_script: Japanese-Kana   # Hiragana + Katakana
        max_ratio: 0.35
```

**Example — English-primary user who wants concise responses:**
```yaml
constraint_gate:
  enabled: true
  gates:
    - name: concise_only
      type: length
      action: warn
      config:
        max_lines: 25
    - name: no_formal_openings
      type: starts_with
      action: block
      config:
        prefixes: ["Dear", "Hello", "Greetings", "I hope this"]
```

**Example — Developer who bans certain suggestions:**
```yaml
constraint_gate:
  enabled: true
  gates:
    - name: no_api_key_suggestions
      type: regex
      action: block
      config:
        patterns:
          - "(?:sign up|create an account|get an API key)"
    - name: no_docker_suggestions
      type: forbidden_words
      action: warn
      config:
        words: ["docker", "containerize", "kubernetes"]
```

---

## Available Gate Types

| Type | What it checks | Config keys |
|------|---------------|------------|
| `language_ratio` | Script ratio in text | `primary_script`+`min_ratio` OR `foreign_script`+`max_ratio` |
| `regex` | Regex pattern match | `pattern` (single) or `patterns` (list) |
| `forbidden_words` | Case-insensitive word match | `words` (list) |
| `length` | Char/line count limits | `max_chars`, `min_chars`, `max_lines` |
| `starts_with` | Response prefix check | `prefixes` (list) |
| `ends_with` | Response suffix check | `suffixes` (list) |
| `traditional_chinese` | Detect traditional Chinese characters | `extra_chars` (list, optional) |

### Script names for `language_ratio`

Atomic: `Han`, `Hiragana`, `Katakana`, `Hangul`, `Latin`, `Cyrillic`, `Arabic`, `Devanagari`

Composite: `Japanese-Kana` (Hiragana + Katakana)

**Important for CJK users:** Use `foreign_script` mode, not `primary_script`. Han characters
are shared between Chinese, Japanese, and Korean — a Japanese sentence with kanji will pass
a `primary_script: Han` check. Use `foreign_script: Japanese-Kana` with `max_ratio` to catch
Japanese-heavy responses.

### Action types

| Action | Effect |
|--------|--------|
| `warn` | Log violation, inject note into history for next-turn self-correction |
| `block` | Same as warn + prepend violation report to user-visible response |
| `transform` | Auto-fix (planned for v1.0 — not yet implemented) |

---

## Pre-Response Checklist

Before sending, run through YOUR configured gates:

1. **Language ratio** — is the foreign script under your threshold?
2. **Banned patterns** — any regex matches?
3. **Forbidden words** — any blacklisted terms?
4. **Length** — within line/char limits?
5. **Opening** — not starting with a banned prefix?
6. **Closing** — not ending with a banned suffix?

If any gate triggers: fix the response, then re-check, then send.

---

## Plugin Integration

The `constraint-gate` plugin (install at `~/.hermes/plugins/constraint-gate/`) hooks into
Hermes's `transform_llm_output` and runs the same gates programmatically.

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

1. **Configuring `primary_script: Han` for Chinese** — Han is shared with Japanese. Use `foreign_script: Japanese-Kana` instead.
2. **Setting thresholds too tight** — 30% kana allows natural flavor particles; 10% would block every ね.
3. **Regex patterns too broad** — `.*` or unanchored patterns will match everything. Anchor with `^` or use specific strings.
4. **Forgetting to restart** — plugins load at Hermes startup. Config changes need restart.
5. **Trusting memory over enforcement** — constraints in memory ≠ constraints enforced. Use the plugin.
6. **Self-check only, no plugin** — mental check is fallible. The plugin catches what you miss.

---

## Extending

Register custom gate types in your own code:

```python
from gate import Gate, Violation, register_gate_type
from typing import Optional

class SentimentGate(Gate):
    """Block negative-sentiment responses."""
    def check(self, response_text: str) -> Optional[Violation]:
        negative_words = self.config.get("config", {}).get("words", [])
        for word in negative_words:
            if word.lower() in response_text.lower():
                return Violation(
                    gate_name=self.name,
                    description="Negative sentiment detected",
                    details=f"Found: {word}",
                    action=self.action,
                )
        return None

register_gate_type("sentiment", SentimentGate)
```
