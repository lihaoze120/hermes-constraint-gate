# Constraint Gate — Pre-Response Constraint Scanner for Hermes Agent

[![Version](https://img.shields.io/badge/version-0.9.3-blue)](https://github.com/lihaoze120/hermes-constraint-gate/releases)
[![CI](https://github.com/lihaoze120/hermes-constraint-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/lihaoze120/hermes-constraint-gate/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Hermes](https://img.shields.io/badge/Hermes-Plugin-orange)](https://github.com/NousResearch/hermes-agent)

A two-layer constraint enforcement system for [Hermes Agent](https://github.com/NousResearch/hermes-agent):
- **Skill** — mental pre-response checklist the assistant self-enforces
- **Plugin** — hooks into `transform_llm_output` for programmatic enforcement

Define your rules once in `config.yaml`. The assistant checks them before every response. The plugin catches what the mental check misses.

> **Status: v0.9.2** — 7 gate types, stable and usable. `transform` action planned for v1.0.

## Quick Start

```bash
# 1. Install plugin
cp -r plugin/ ~/.hermes/plugins/constraint-gate/

# 2. Enable in config.yaml
hermes config set plugins.enabled "['constraint-gate']"

# 3. Add your gates to config.yaml (see examples/)
# 4. Restart Hermes
```

## How It Works

```
Assistant generates response
  → Mental check: skill's pre-send checklist runs
    → Plugin hook: transform_llm_output fires
      → ConstraintEngine scans against configured gates
        → PASS: response delivered unchanged
        → FAIL: violation note injected into conversation history
          → Next turn: assistant reads its own annotated message, self-corrects
```

Two layers, same rules:
- **Skill** = assistant checks itself before sending (proactive)
- **Plugin** = code scans after generation, injects corrections (reactive catch-all)

---

## Gate Types

### `language_ratio` — Control mixed-language output

Counts characters by Unicode script and enforces ratio limits. Two modes:

**Mode 1: Enforce primary script** — "at least 80% Latin"
```yaml
- name: enforce_english
  type: language_ratio
  action: warn
  config:
    primary_script: Latin
    min_ratio: 0.8
```

**Mode 2: Limit foreign script** — "no more than 30% Japanese kana"
```yaml
- name: kana_limit
  type: language_ratio
  action: block
  config:
    foreign_script: Japanese-Kana
    max_ratio: 0.30
```

Supported scripts: `Han`, `Hiragana`, `Katakana`, `Japanese-Kana`, `Hangul`, `Latin`, `Cyrillic`, `Arabic`, `Devanagari`

> **CJK note:** Han characters are shared by Chinese, Japanese, and Korean. Use `foreign_script: Japanese-Kana` (Hiragana+Katakana) to catch Japanese output — `primary_script: Han` won't distinguish them.

---

### `regex` — Block unwanted patterns

Single pattern or multiple. Matches against the entire response with `re.MULTILINE`.

```yaml
- name: no_markdown
  type: regex
  action: block
  config:
    patterns:
      - "\*\*[^*]+\*\*"        # bold
      - "```[\s\S]*?```"       # code blocks
      - "^#{1,6}\s"            # headings
```

Use cases: block markdown in plain-text chat, ban specific URL patterns, catch API key suggestions, prevent code-generated art mentions.

---

### `forbidden_words` — Simple word blacklist

Case-insensitive substring matching. Good for banning terms you never want suggested.

```yaml
- name: no_cloud_suggestions
  type: forbidden_words
  action: block
  config:
    words: ["docker", "kubernetes", "terraform", "AWS"]
```

---

### `length` — Cap response size

Char count, line count, or both.

```yaml
- name: keep_concise
  type: length
  action: warn
  config:
    max_lines: 25
    max_chars: 2000
    min_chars: 10      # prevent empty/lazy responses
```

---

### `starts_with` / `ends_with` — Control openings and closings

Strip formulaic filler from responses. `starts_with` checks after `lstrip()`, `ends_with` checks after `rstrip()`.

```yaml
- name: no_pleasantries
  type: starts_with
  action: block
  config:
    prefixes: ["Sure!", "Of course!", "I'd be happy to"]

- name: no_trailing
  type: ends_with
  action: block
  config:
    suffixes: ["Let me know if", "Would you like me to", "Feel free to ask"]
```

---

### `traditional_chinese` — Simplified Chinese enforcement

Detects traditional Chinese characters using a built-in reference set of 200+ common traditional→simplified pairs. Extend with `extra_chars`.

```yaml
- name: simplified_only
  type: traditional_chinese
  action: block
  config:
    extra_chars: []   # optional: add more traditional chars
```

---

## Actions

| Action | Effect |
|--------|--------|
| `warn` | Log the violation + inject a note the assistant sees next turn (self-correction) |
| `block` | Same as warn + prepend violation report to the user-visible response |
| `transform` | Auto-fix the response *(planned for v1.0)* |

---

## Configuration Files

See `examples/` for complete, ready-to-use config files:
- `config-example.yaml` — universal, English-primary
- `config-example-cjk.yaml` — CJK (Chinese/Japanese) specific with kana limits, traditional char detection

---

## Extending

Register custom gate types without modifying the plugin:

```python
from gate import Gate, Violation, register_gate_type

class SentimentGate(Gate):
    """Block negative-sentiment responses."""
    def check(self, text):
        negative = self.config.get("config", {}).get("words", [])
        for word in negative:
            if word.lower() in text.lower():
                return Violation(
                    gate_name=self.name,
                    description="Negative sentiment detected",
                    details=f"Found: {word}",
                    action=self.action,
                )
        return None

register_gate_type("sentiment", SentimentGate)
```

Then use it in config:
```yaml
- name: no_negativity
  type: sentiment
  action: block
  config:
    words: ["frustrated", "annoying", "terrible"]
```

---

## License

MIT — see [LICENSE](LICENSE)
