"""
Live demo of Constraint Gate in action — including transform (auto-fix).

Run: python demo.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plugin"))

from gate import ConstraintEngine

# ── Config with all three actions: warn, block, transform ──
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
            "name": "strip_pleasantry",
            "type": "starts_with",
            "action": "transform",  # ← AUTO-FIX: strips the banned prefix
            "description": "Strip formulaic openings automatically",
            "config": {"prefixes": ["好的！", "Sure!", "I'd be happy to"]},
        },
        {
            "name": "no_markdown",
            "type": "regex",
            "action": "transform",  # ← AUTO-FIX: strips markdown, keeps text
            "description": "Strip markdown formatting, keep content",
            "config": {
                "patterns": [r"\*\*([^*]+)\*\*", r"`([^`]+)`", r"```[\s\S]*?```"],
                "replacement": r"\1",  # keep captured text
            },
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
    ("❌ Too much Japanese (block)", "お兄ちゃん、それは素晴らしいアイデアですね！"),
    ("🔄 Formulaic opening (transform!)", "好的！我来帮你处理这个问题。"),
    ("🔄 Markdown bold (transform!)", "This is **bold** and this is **also bold**."),
    ("❌ Traditional chars (block)", "這是個完整的專案，我們來看看。"),
]

print("=" * 65)
print("  Constraint Gate — Live Demo (warn + block + transform)")
print("=" * 65)

for label, text in tests:
    result = engine.scan(text)
    if result.passed:
        status = "✅ PASS"
    elif result.transformed:
        status = "🔄 TRANSFORMED"
    else:
        status = "❌ BLOCKED"
    
    print(f"\n{'─' * 65}")
    print(f"  {label}")
    print(f"  Input : {text[:55]}{'...' if len(text)>55 else ''}")
    print(f"  Result: {status}")
    
    if result.transformed:
        print(f"  Output: {result.transformed_text[:55]}{'...' if len(result.transformed_text)>55 else ''}")
    
    for v in result.violations:
        print(f"    → {v.gate_name} [{v.action}]: {v.details[:60]}")

print(f"\n{'=' * 65}")
print("  transform = auto-fix, block = refuse, warn = log only")
print("=" * 65)
