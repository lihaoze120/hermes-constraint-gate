# Constraint Gate

*Never let your AI assistant forget the rules again.*

[![Version](https://img.shields.io/badge/version-0.9.3-blue)](https://github.com/lihaoze120/hermes-constraint-gate/releases)
[![CI](https://github.com/lihaoze120/hermes-constraint-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/lihaoze120/hermes-constraint-gate/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Hermes](https://img.shields.io/badge/Hermes-Plugin-orange)](https://github.com/NousResearch/hermes-agent)

---

## What It Does

You tell your AI assistant "no markdown." Five messages later, it's writing `**bold**` again.

Constraint Gate **enforces** your rules at the code level — not just "please remember," but "you literally cannot send this."

```
Without Constraint Gate:
  Assistant: "好的！我来帮你解决这个问题。**首先**..."
              ↑ formulaic opening    ↑ markdown

With Constraint Gate:
  Assistant: "直接看代码。首先..."
              ↑ clean, got to the point
```

Two layers, same rules:
- **Skill** — assistant self-checks before sending (proactive)
- **Plugin** — code scans after generation (reactive catch-all)

---

## Table of Contents

- [Quick Start](#quick-start)
- [Why Constraint Gate?](#why-constraint-gate)
- [Gate Types](#gate-types)
  - [language_ratio](#language_ratio)
  - [regex](#regex)
  - [forbidden_words](#forbidden_words)
  - [length](#length)
  - [starts_with / ends_with](#starts_with--ends_with)
  - [traditional_chinese](#traditional_chinese)
- [Actions](#actions)
- [Configuration Examples](#configuration-examples)
- [Extending](#extending)
- [Development](#development)
- [License](#license)

---

## Quick Start

**30 seconds to your first gate:**

```bash
# 1. Install
cp -r plugin/ ~/.hermes/plugins/constraint-gate/

# 2. Enable
hermes config set plugins.enabled "['constraint-gate']"

# 3. Add a rule to config.yaml
#    (copy from examples/config-example.yaml)

# 4. Restart
hermes restart
```

That's it. The plugin now scans every assistant response before delivery.

---

## Why Constraint Gate?

**The problem:** Memory and system prompts are suggestions. LLMs drift. You tell them "be concise" and three messages later they're writing paragraphs.

**The solution:** Code-level enforcement. The plugin hooks into Hermes's `transform_llm_output` — it sees every response BEFORE the user does. If a gate triggers, the response gets annotated with a violation note. Next turn, the assistant reads its own annotated message and self-corrects.

**What it's NOT:**
- ❌ A prompt wrapper (those can be ignored)
- ❌ A content filter (doesn't block topics, just enforces style/format)
- ❌ Another "please remember to..." checklist

**What it IS:**
- ✅ A programmable response scanner with 7 pluggable check types
- ✅ Extensible — add your own gate types without touching plugin code
- ✅ Self-healing — violations feed back into the next conversation turn

**vs alternatives:**

| Approach | Enforced? | Self-corrects? | Customizable? |
|----------|-----------|----------------|---------------|
| System prompt rules | ❌ Drift | ❌ | ✅ |
| Memory entries | ❌ Forgotten | ❌ | ✅ |
| Post-processing regex | ✅ | ❌ | ⚠️ Code only |
| **Constraint Gate** | ✅ | ✅ | ✅ YAML config |

---

## Gate Types

### `language_ratio`

Count characters by Unicode script and enforce ratios. Two modes:

**Enforce primary language:**
```yaml
- name: enforce_english
  type: language_ratio
  action: warn
  config:
    primary_script: Latin
    min_ratio: 0.8
```

**Limit foreign script:**
```yaml
- name: kana_limit
  type: language_ratio
  action: block
  config:
    foreign_script: Japanese-Kana
    max_ratio: 0.30
```

Supported scripts: `Han`, `Hiragana`, `Katakana`, `Japanese-Kana`, `Hangul`, `Latin`, `Cyrillic`, `Arabic`, `Devanagari`

> ⚠️ **CJK users:** Han characters are shared by Chinese, Japanese, and Korean. Use `foreign_script: Japanese-Kana` (Hiragana+Katakana) to catch Japanese drift — `primary_script: Han` won't distinguish them.

### `regex`

Match (or block) patterns in responses. Single pattern or multiple:

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

Invalid regex is safely skipped (logged, not crashed).

### `forbidden_words`

Case-insensitive substring matching. Blacklist terms you never want suggested:

```yaml
- name: no_cloud
  type: forbidden_words
  action: block
  config:
    words: ["docker", "kubernetes", "terraform"]
```

### `length`

Cap response size by chars or lines:

```yaml
- name: keep_concise
  type: length
  action: warn
  config:
    max_lines: 25
    max_chars: 2000
    min_chars: 10      # prevent lazy one-word replies
```

### `starts_with` / `ends_with`

Strip formulaic filler. `starts_with` checks after stripping leading whitespace, `ends_with` after trailing:

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
    suffixes: ["Let me know if", "Would you like me to"]
```

### `traditional_chinese`

Detect traditional Chinese characters (200+ reference pairs). For simplified-only output:

```yaml
- name: simplified_only
  type: traditional_chinese
  action: block
  config:
    extra_chars: []   # optional: extend the default set
```

---

## Actions

What happens when a gate triggers:

| Action | Effect |
|--------|--------|
| `warn` | Log + inject note for assistant's next-turn self-correction |
| `block` | Same as warn + violation report prepended to user-visible response |
| `transform` | Auto-fix the response *(planned for v1.0)* |

---

## Configuration Examples

Full working configs in `examples/`:

| File | For |
|------|-----|
| `config-example.yaml` | Universal (English, developers) |
| `config-example-cjk.yaml` | Chinese/Japanese with kana limits + trad detection |

Paste into your `config.yaml` under `constraint_gate:` and restart Hermes.

---

## Extending

Add custom gate types without forking:

```python
from gate import Gate, Violation, register_gate_type

class SentimentGate(Gate):
    """Block negative-sentiment responses."""
    def check(self, text):
        bad = self.config.get("config", {}).get("words", [])
        for word in bad:
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

Then use it in config:
```yaml
- name: no_negativity
  type: sentiment
  action: block
  config:
    words: ["frustrated", "annoying"]
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Development

```bash
git clone https://github.com/lihaoze120/hermes-constraint-gate.git
cd hermes-constraint-gate
pip install -e ".[test]"
pytest tests/ -v    # 41 tests, all 7 gates
```

CI runs on Python 3.9–3.12 via GitHub Actions.

---

## License

MIT — do whatever you want, just keep the notice.
