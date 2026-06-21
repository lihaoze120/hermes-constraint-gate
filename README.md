# Constraint Gate — Pre-Response Constraint Scanner for Hermes Agent

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

## Gate Types (7)

| Type | What it checks | Example |
|------|---------------|---------|
| `language_ratio` | Script ratio in text | Limit non-English scripts, enforce primary language |
| `regex` | Regex pattern match | Block markdown, code blocks, specific patterns |
| `forbidden_words` | Case-insensitive word match | Ban "docker", "browser", "sign up" |
| `length` | Char / line count | Max 30 lines, min 10 chars |
| `starts_with` | Response prefix | No "Sure!" / "Let me" openings |
| `ends_with` | Response suffix | No "Let me know if..." endings |
| `traditional_chinese` | Traditional Chinese chars | Block traditional characters in simplified output |

### Gate Config Reference

```yaml
# language_ratio — enforce primary script or limit foreign script
- name: enforce_english
  type: language_ratio
  action: warn
  config:
    primary_script: Latin
    min_ratio: 0.8

# regex — single or multiple patterns
- name: no_markdown
  type: regex
  action: block
  config:
    patterns:
      - "\*\*[^*]+\*\*"
      - "```[\s\S]*?```"

# forbidden_words — case-insensitive
- name: no_docker
  type: forbidden_words
  action: warn
  config:
    words: ["docker", "kubernetes", "containerize"]

# length — char or line limits
- name: keep_concise
  type: length
  action: warn
  config:
    max_lines: 25
    max_chars: 2000

# starts_with / ends_with — opening/closing patterns
- name: no_formal_opening
  type: starts_with
  action: block
  config:
    prefixes: ["Dear", "Hello", "Greetings"]

- name: no_trailing_questions
  type: ends_with
  action: block
  config:
    suffixes: ["Let me know if", "Would you like me to"]
```

## Configuration

See `examples/` for complete config files:
- `config-example.yaml` — universal, English-primary
- `config-example-cjk.yaml` — CJK (Chinese/Japanese) specific

## Extending

Register custom gate types:

```python
from gate import Gate, Violation, register_gate_type

class SentimentGate(Gate):
    def check(self, text):
        if "frustrated" in text.lower():
            return Violation(
                gate_name=self.name,
                description="Negative sentiment detected",
                action="warn",
            )
        return None

register_gate_type("sentiment", SentimentGate)
```

## License

MIT — see [LICENSE](LICENSE)
