r/Python 终极版

标题：I got so tired of LLMs ignoring my instructions that I made a linter for AI output


You know that feeling when you tell ChatGPT "please be concise, no markdown" — and 3 messages later it's writing `**bold essays** with bullet points`?

I hit this wall so many times I built a thing. It's a CLI that sits between your LLM and the user, and actually *enforces* the rules. Not "please remember" — "you literally cannot send this."

---

Here's what it looks like:

```
$ gate scan "好的！**加粗**的文字" --config rules.yaml

=======================================================
  Constraint Gate — Scan Report
=======================================================
  Status : ❌ BLOCKED
  Violations: 2
    → no_pleasantry [block]
      Response starts with: '好的！'
    → no_markdown [block]
      Matched pattern: \*\*[^*]+\*\*
=======================================================
```

But what I actually wanted was for it to auto-fix the text. So I added a `transform` action:

```yaml
- name: strip_markdown
  type: regex
  action: transform
  config:
    patterns: ["\\*\\*([^*]+)\\*\\*"]
    replacement: "\\1"    # keep the text, ditch the **
```

Now `**加粗**` → `加粗`. Content preserved, formatting stripped. No hand-holding needed.

---

**What it can check (7 types):**
Language ratio · regex patterns · forbidden words · length limits · starts/ends with · traditional Chinese detection

**What it does with violations:**
Warn (log it) · Block (refuse + annotate) · Transform (auto-fix)

---

I built this for Hermes Agent originally, but then realized the engine has zero Hermes dependency. So I wrapped it in a CLI. Now you can:

```bash
pip install git+https://github.com/lihaoze120/hermes-constraint-gate.git
echo "your LLM output" | gate scan - --config rules.yaml --quiet
gate scan --file response.txt --config rules.yaml --format json  # CI-friendly
```

57 tests, Python 3.9+, MIT license. Comes with `python demo.py` that runs 5 test cases in half a second.

---

**Why not just use a system prompt?**

Because prompts are suggestions. LLMs drift. Memory entries get forgotten. I tried both. Then I checked my chat history and found I'd corrected the same drift patterns 37 times in one week.

This doesn't drift. It's code on the output pipe.

---

Still early — no PyPI package yet, some edge cases I'm sure I haven't found. Would genuinely love feedback:

- What constraint types am I missing?
- Should I split the engine into a standalone library + CLI + Hermes plugin as separate packages?
- Anyone else dealing with LLM output drift in production?

GitHub: https://github.com/lihaoze120/hermes-constraint-gate
