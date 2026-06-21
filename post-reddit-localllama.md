r/LocalLLaMA 终极版

标题：37 times in one week I had to remind my LLM "no markdown, keep it short." So I built an output linter.


Running local models is great. Running local models that slowly forget every instruction you gave them is... less great.

I went through my chat logs and counted: in one week, I corrected the same drift patterns 37 times. "Stop using markdown." "Don't suggest Docker." "No formulaic openings." Over and over.

So I built a YAML-configured output gate that sits between the model and the user. Define your rules once, it enforces them every time.

```
$ echo "好的！**bold** text about Docker" | gate scan - --config rules.yaml

  Status : ❌ BLOCKED
  Violations: 2
    → no_pleasantry: Response starts with '好的！'
    → no_docker: Found forbidden word 'Docker'
```

Or use `transform` mode and it auto-fixes:

```
Input:  "好的！**bold** text about Docker"
Output: "bold text about Docker"
```

(Strips the opening pleasantry, strips markdown, strips the forbidden word — all automatic.)

---

Setup:
```bash
pip install git+https://github.com/lihaoze120/hermes-constraint-gate.git

cat > rules.yaml << 'EOF'
constraint_gate:
  enabled: true
  gates:
    - name: no_markdown
      type: regex
      action: transform
      config:
        patterns: ["\\*\\*([^*]+)\\*\\*"]
        replacement: "\\1"
    - name: keep_short
      type: length
      action: warn
      config:
        max_lines: 20
EOF

# Pipe your model output through it
curl ... | jq '.choices[0].message.content' | gate scan - --config rules.yaml
```

Works with any LLM — local or API. stdin in, scanned text out. JSON mode for scripting. Exit code 0/1 for CI.

---

7 constraint types, 57 tests, MIT. Built for my own Hermes setup, made it standalone because why not.

Curious if anyone else here deals with model output drift and how you handle it. Pure prompt engineering? Post-processing scripts? Something else?

GitHub: https://github.com/lihaoze120/hermes-constraint-gate
