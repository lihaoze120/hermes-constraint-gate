"""CLI for constraint-gate — scan text without Hermes.

Usage:
  gate scan "text to check" --config rules.yaml
  echo "text" | gate scan -
  gate scan --file response.txt --config rules.yaml
  gate scan "text" --config rules.yaml --format json
"""

import argparse
import json
import sys
import os
from pathlib import Path

import yaml

# pyyaml may be installed without __init__.py (broken partial install);
# fall back to the Loader class directly.
try:
    _has_safe_load = hasattr(yaml, "safe_load")
except Exception:
    _has_safe_load = False


def _yaml_load(stream):
    """Load YAML, working around broken PyYAML installs."""
    if _has_safe_load:
        return yaml.safe_load(stream)
    else:
        from yaml.loader import SafeLoader
        loader = SafeLoader(stream)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plugin"))
from gate import ConstraintEngine


def load_config(path: str) -> dict:
    """Load constraint_gate config from a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = _yaml_load(f)
    # Support both top-level constraint_gate key and flat gate list
    if isinstance(data, dict) and "constraint_gate" in data:
        return data["constraint_gate"]
    if isinstance(data, list):
        return {"gates": data}
    return data


def main():
    parser = argparse.ArgumentParser(
        prog="gate",
        description="Scan text against constraint rules.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan text against constraint rules")
    scan.add_argument(
        "text", nargs="?", default=None,
        help="Text to scan. Use '-' to read from stdin."
    )
    scan.add_argument(
        "--file", "-f", default=None,
        help="Read text from a file instead of argument."
    )
    scan.add_argument(
        "--config", "-c", default="constraint_gate.yaml",
        help="Path to YAML config file (default: constraint_gate.yaml)."
    )
    scan.add_argument(
        "--format", "-F", choices=["text", "json"], default="text",
        help="Output format (default: text)."
    )
    scan.add_argument(
        "--quiet", "-q", action="store_true",
        help="Only output transformed text, no scan report."
    )

    list_cmd = sub.add_parser("list-gates", help="List gates from config")
    list_cmd.add_argument(
        "--config", "-c", default="constraint_gate.yaml",
        help="Path to YAML config file."
    )

    args = parser.parse_args()

    if args.command == "list-gates":
        if not os.path.exists(args.config):
            print(f"Config not found: {args.config}")
            sys.exit(1)
        config = load_config(args.config)
        engine = ConstraintEngine(config)
        print(f"Config: {args.config}")
        print(f"Enabled: {engine.enabled}")
        print(f"Gates loaded: {len(engine.gates)}")
        for g in engine.gates:
            enabled = "✓" if engine.enabled else "✗"
            print(f"  [{enabled}] {g.name} (type={g.__class__.__name__.replace('Gate','').lower()}, action={g.action})")
        return

    if args.command == "scan":
        # Get text
        if args.text == "-":
            text = sys.stdin.read()
        elif args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                text = f.read()
        elif args.text:
            text = args.text
        else:
            print("Error: no text provided. Use 'gate scan \"text\"' or 'gate scan -' for stdin.", file=sys.stderr)
            sys.exit(1)

        # Load config
        if not os.path.exists(args.config):
            print(f"Error: config file not found: {args.config}", file=sys.stderr)
            print("Create one with: gate init", file=sys.stderr)
            sys.exit(1)

        config = load_config(args.config)
        engine = ConstraintEngine(config)

        # Scan
        result = engine.scan(text)

        if args.format == "json":
            output = {
                "passed": result.passed,
                "transformed": result.transformed,
                "violations": [
                    {
                        "gate": v.gate_name,
                        "action": v.action,
                        "details": v.details,
                    }
                    for v in result.violations
                ],
                "transformed_text": result.transformed_text if result.transformed else None,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            if args.quiet:
                if result.transformed:
                    print(result.transformed_text)
                else:
                    print(text)
            else:
                print(f"{'=' * 55}")
                print(f"  Constraint Gate — Scan Report")
                print(f"{'=' * 55}")
                if result.transformed:
                    print(f"  Status : 🔄 TRANSFORMED")
                    print(f"  Input  : {text[:60]}{'...' if len(text)>60 else ''}")
                    print(f"  Output : {result.transformed_text[:60]}{'...' if len(result.transformed_text)>60 else ''}")
                elif result.passed:
                    print(f"  Status : ✅ PASS")
                else:
                    print(f"  Status : ❌ BLOCKED")
                print(f"  Violations: {len(result.violations)}")
                for v in result.violations:
                    print(f"    → {v.gate_name} [{v.action}]")
                    print(f"      {v.details}")
                print(f"{'=' * 55}")

        sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
