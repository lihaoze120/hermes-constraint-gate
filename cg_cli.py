"""CLI for constraint-gate — scan text without Hermes.

Usage:
  cg scan "text to check" --config rules.yaml
  echo "text" | cg scan -
  cg scan --file response.txt --config rules.yaml
  cg scan "text" --config rules.yaml --format json
"""

import argparse
import json
import sys
import os
from pathlib import Path

import yaml

# ── Version ───────────────────────────────────────────────────────────

__version__ = "0.11.0"


# ── YAML loading (robust against broken PyYAML installs) ─────────────

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


# ── Import ConstraintEngine from the plugin directory ─────────────────

_plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin")
if _plugin_dir not in sys.path:
    sys.path.insert(0, _plugin_dir)

try:
    from gate import ConstraintEngine
except ImportError as e:
    sys.exit(
        f"Fatal: cannot import ConstraintEngine from '{_plugin_dir}'.\n"
        f"  Ensure plugin/gate.py exists and is readable.\n"
        f"  Import error: {e}"
    )


# ── Config loading ────────────────────────────────────────────────────


def load_config(path: str) -> dict:
    """Load constraint_gate config from a YAML file.

    Returns a dict suitable for passing to ConstraintEngine().
    Handles missing files, empty files, invalid YAML, and
    permission errors gracefully.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except PermissionError:
        raise PermissionError(f"Cannot read config file (permission denied): {path}")
    except (UnicodeDecodeError, OSError) as e:
        raise OSError(f"Cannot read config file '{path}': {e}")

    # Empty or whitespace-only config — treat as no gates
    if not raw.strip():
        return {"gates": []}

    try:
        data = _yaml_load(raw)
    except Exception as e:
        raise ValueError(f"Invalid YAML in config '{path}': {e}")

    # None means an empty YAML document
    if data is None:
        return {"gates": []}

    # Support both top-level constraint_gate key and flat gate list
    if isinstance(data, dict) and "constraint_gate" in data:
        return data["constraint_gate"]
    if isinstance(data, list):
        return {"gates": data}
    if isinstance(data, dict):
        return data

    raise ValueError(
        f"Unexpected config structure in '{path}': "
        f"expected a dict or list, got {type(data).__name__}"
    )


# ── CLI ───────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="cg",
        description="Scan text against constraint rules.",
    )
    parser.add_argument(
        "--version", "-V", action="version",
        version=f"cg {__version__}",
        help="Show version and exit.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan text against constraint rules")
    scan.add_argument(
        "text", nargs="?", default=None,
        help="Text to scan. Use '-' to read from stdin.",
    )
    scan.add_argument(
        "--file", "-f", default=None,
        help="Read text from a file instead of argument.",
    )
    scan.add_argument(
        "--config", "-c", default="constraint_gate.yaml",
        help="Path to YAML config file (default: constraint_gate.yaml).",
    )
    scan.add_argument(
        "--format", "-F", choices=["text", "json"], default="text",
        help="Output format (default: text).",
    )
    scan.add_argument(
        "--quiet", "-q", action="store_true",
        help="Only output transformed text, no scan report.",
    )

    list_cmd = sub.add_parser("list-gates", help="List gates from config")
    list_cmd.add_argument(
        "--config", "-c", default="constraint_gate.yaml",
        help="Path to YAML config file.",
    )

    args = parser.parse_args()

    if args.command == "list-gates":
        try:
            config = load_config(args.config)
        except (FileNotFoundError, PermissionError, OSError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

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
            try:
                with open(args.file, "r", encoding="utf-8") as f:
                    text = f.read()
            except FileNotFoundError:
                print(f"Error: input file not found: {args.file}", file=sys.stderr)
                sys.exit(1)
            except PermissionError:
                print(f"Error: cannot read input file (permission denied): {args.file}", file=sys.stderr)
                sys.exit(1)
            except (UnicodeDecodeError, OSError) as e:
                print(f"Error: cannot read input file '{args.file}': {e}", file=sys.stderr)
                sys.exit(1)
        elif args.text:
            text = args.text
        else:
            print(
                "Error: no text provided. Use 'cg scan \"text\"', "
                "'cg scan --file <path>', or 'cg scan -' for stdin.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Load config
        try:
            config = load_config(args.config)
        except FileNotFoundError:
            print(f"Error: config file not found: {args.config}", file=sys.stderr)
            print("  Create one manually or use an example from the examples/ directory.", file=sys.stderr)
            sys.exit(1)
        except PermissionError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except (OSError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

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
