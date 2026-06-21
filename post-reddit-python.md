r/Python Showcase 正式版

标题：[Showcase] Constraint Gate — a linter for LLM output that actually enforces rules


**What My Project Does**

Constraint Gate is a YAML-configured scanner that sits between your LLM and the user. Define rules once — language ratio, banned words, regex patterns, response length, opening/closing checks — and it enforces them at the output level. Not "please remember" — "you literally cannot send this."

Quick demo:
```
$ gate scan "好的！**bold** text about Docker" --config rules.yaml
  Status : ❌ BLOCKED
  Violations: 3
    → no_pleasantry [block]  Response starts with: '好的！'
    → no_markdown [block]    Matched pattern: \*\*[^*]+\*\*
    → no_docker [block]      Found forbidden word: 'Docker'
```

Or use `transform` mode and it auto-fixes: strips the opening, strips markdown, removes banned words — all automatic.

```
Input:  "好的！**bold** text about Docker"
Output: "bold text about"
```

---

**Target Audience**

- Anyone using LLMs in production who's tired of output drift
- Developers who pipe LLM responses through CI/CD pipelines
- Hermes Agent users (plugin integration built in)
- Anyone who's said "please be concise" 37 times and is done with it

---

**Comparison**

| Approach | Actually enforced? | Auto-fix? |
|----------|-------------------|-----------|
| System prompt rules | ❌ Drift | ❌ |
| Memory entries | ❌ Forgotten | ❌ |
| Post-processing regex | ✅ | ⚠️ Code-only |
| **Constraint Gate** | ✅ | ✅ YAML, 7 types, 3 actions |

Existing tools (guardrails, output parsers) focus on structural validation. Constraint Gate focuses on *style and behavior* enforcement.

---

7 constraint types (language_ratio, regex, forbidden_words, length, starts_with, ends_with, traditional_chinese). 3 actions (warn, block, transform). 57 tests, MIT, pip-installable.

```bash
pip install git+https://github.com/lihaoze120/hermes-constraint-gate.git
echo "your LLM output" | gate scan - --config rules.yaml
```

GitHub: https://github.com/lihaoze120/hermes-constraint-gate
Demo: `python demo.py`

---

Built for my own Hermes setup, made standalone because the engine has zero framework dependencies. Still early — would love feedback on missing constraint types.
