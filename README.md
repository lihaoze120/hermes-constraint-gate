# Constraint Gate — Pre-Response Constraint Scanner for Hermes Agent

A two-layer constraint enforcement system for [Hermes Agent](https://github.com/NousResearch/hermes-agent):
- **Skill** — mental pre-response checklist the assistant self-enforces
- **Plugin** — hooks into `transform_llm_output` for programmatic enforcement

Define your rules once in `config.yaml`. The assistant checks them before every response. The plugin catches what the mental check misses.

## Quick Start

> **Status: v0.9.1** — 7 gate types, stable and usable. `transform` action planned for v1.0.

```bash
# 1. Install plugin
cp -r plugin/ ~/.hermes/plugins/constraint-gate/

# 2. Enable in config.yaml
hermes config set plugins.enabled "['constraint-gate']"  # add to existing list

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

## Gate Types

| Type | What it checks | Example |
|------|---------------|---------|
| `language_ratio` | Script ratio in text | Limit Japanese kana to 30% |
| `regex` | Regex pattern match | Block markdown formatting |
| `forbidden_words` | Case-insensitive word match | Ban "docker", "browser" |
| `length` | Char / line count | Max 30 lines per response |
| `starts_with` | Response prefix | No "好的！" openings |
| `ends_with` | Response suffix | No "需要我继续吗？" endings |
| `traditional_chinese` | Character check | Block traditional Chinese chars |

### Language Ratio — CJK Special Handling

Han (CJK ideographs) are shared across Chinese, Japanese, and Korean. Use `foreign_script` mode:

```yaml
# WRONG — Japanese text with kanji passes
primary_script: Han
min_ratio: 0.7

# RIGHT — kana is uniquely Japanese
foreign_script: Japanese-Kana
max_ratio: 0.35
```

## Configuration

See `examples/` for complete config files:
- `config-example-cn.yaml` — Chinese-primary user
- `config-example-en.yaml` — English-primary user

## Extending

Register custom gate types:

```python
from gate import Gate, Violation, register_gate_type

class MyGate(Gate):
    def check(self, response_text):
        if "badword" in response_text:
            return Violation(
                gate_name=self.name,
                description="Found bad word",
                details="...",
                action="block",
            )
        return None

register_gate_type("my_custom_type", MyGate)
```

## License

MIT — see [LICENSE](LICENSE)
