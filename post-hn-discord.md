Hacker News / Show HN 终极版

标题：Show HN: Constraint Gate — a linter for LLM output


I kept correcting the same LLM output patterns over and over — markdown in plain-text chat, formulaic openings, forbidden tool suggestions — so I built a YAML-configured scanner that enforces rules at the output level.

Not "please remember to be concise." Code on the pipe. The LLM literally cannot send a violating response.

```
$ gate scan "好的！**bold** text" --config rules.yaml
  Status : ❌ BLOCKED
  Violations: 2
    → no_pleasantry: Response starts with '好的！'
    → no_markdown: Matched pattern
```

7 constraint types (language ratio, regex, forbidden words, length, starts_with, ends_with, traditional Chinese). 3 actions (warn, block, transform — transform auto-fixes: `**bold**` → `bold`).

57 tests, MIT, pip installable. Works as Hermes plugin or standalone CLI — stdin pipe, JSON output, CI-friendly exit codes.

GitHub: https://github.com/lihaoze120/hermes-constraint-gate

Built this for myself. Sharing in case anyone else is tired of reminding their AI the same things 37 times a week. Would love to hear what constraint types you'd add.
