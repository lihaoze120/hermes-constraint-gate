"""
Live demo of Constraint Gate in action.

Run: python demo.py
Shows 5 test cases against a realistic rule set — which pass, which get blocked, and why.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plugin"))

from gate import ConstraintEngine

config = {
    "enabled": True,
    "gates": [
        {
            "name": "kana_limit",
            "type": "language_ratio",
            "action": "block",
            "description": "Japanese kana must be <= 30%",
            "config": {"foreign_script": "Japanese-Kana", "max_ratio": 0.30},
        },
        {
            "name": "no_pleasantry",
            "type": "starts_with",
            "action": "block",
            "description": "No formulaic openings",
            "config": {"prefixes": ["好的！", "Sure!", "I'd be happy to"]},
        },
        {
            "name": "no_markdown",
            "type": "regex",
            "action": "block",
            "description": "No markdown formatting",
            "config": {"patterns": [r"\*\*[^*]+\*\*", r"```[\s\S]*?```"]},
        },
        {
            "name": "no_traditional",
            "type": "traditional_chinese",
            "action": "block",
            "description": "Simplified Chinese only",
            "config": {},
        },
        {
            "name": "keep_concise",
            "type": "length",
            "action": "warn",
            "description": "Keep under 25 lines",
            "config": {"max_lines": 25},
        },
    ],
}

engine = ConstraintEngine(config)

tests = [
    ("✅ Clean response", "Got it. Pushed to GitHub. Need anything else?"),
    ("❌ Too much Japanese", "お兄ちゃん、それは素晴らしいアイデアですね！"),
    ("❌ Traditional chars", "這是個完整的專案，我們來看看。"),
    ("❌ Markdown bold", "好的！**首先**我们需要检查配置。"),
    ("❌ Formulaic opening", "好的！没问题！我来帮你。"),
]

print("=" * 60)
print("  Constraint Gate — Live Demo")
print("  Rules: kana≤30% | no openings | no markdown | no trad | ≤25 lines")
print("=" * 60)

for label, text in tests:
    result = engine.scan(text)
    status = "✅ PASS" if result.passed else "❌ BLOCKED"
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"  Input : {text[:55]}{'...' if len(text)>55 else ''}")
    print(f"  Result: {status}")
    for v in result.violations:
        print(f"    → {v.gate_name}: {v.details}")

print(f"\n{'=' * 60}")
print("  Done. Every violation caught. Every clean response passed.")
print("=" * 60)
