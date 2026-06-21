"""Tests for CLI interface."""

import subprocess
import sys
import os
import json
import tempfile

CLI = [sys.executable, "cg_cli.py"]


def _run(*args, stdin=None, workdir=None):
    """Run CLI and return (stdout, stderr, exit_code)."""
    cwd = workdir or os.path.dirname(os.path.dirname(__file__))
    result = subprocess.run(
        [sys.executable, os.path.join(cwd, "cg_cli.py")] + list(args),
        capture_output=True,
        text=True,
        input=stdin,
        cwd=cwd,
    )
    return result.stdout, result.stderr, result.returncode


class TestCLI:
    def test_scan_pass(self):
        out, _, code = _run("scan", "clean text", "--config", "examples/config-example.yaml")
        assert "PASS" in out
        assert code == 0

    def test_scan_block(self):
        out, _, code = _run("scan", "好的！有问题。", "--config", "examples/config-example-cjk.yaml")
        assert "BLOCKED" in out
        assert code == 1

    def test_scan_stdin(self):
        out, _, code = _run("scan", "-", "--config", "examples/config-example.yaml", stdin="clean text")
        assert "PASS" in out

    def test_scan_json(self):
        out, _, code = _run("scan", "clean text", "--config", "examples/config-example.yaml", "--format", "json")
        data = json.loads(out)
        assert data["passed"] is True
        assert len(data["violations"]) == 0

    def test_scan_json_blocked(self):
        out, _, code = _run("scan", "好的！有问题。", "--config", "examples/config-example-cjk.yaml", "--format", "json")
        data = json.loads(out)
        assert data["passed"] is False
        assert len(data["violations"]) > 0
        assert code == 1

    def test_scan_quiet(self):
        out, _, code = _run("scan", "clean text", "--config", "examples/config-example.yaml", "--quiet")
        assert out.strip() == "clean text"

    def test_list_gates(self):
        out, _, code = _run("list-gates", "--config", "examples/config-example.yaml")
        assert "Gates loaded:" in out
        assert code == 0

    def test_scan_file(self):
        cwd = os.path.dirname(os.path.dirname(__file__))
        tmp = os.path.join(cwd, "tests", "_test_input.txt")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("clean text")
        try:
            out, _, code = _run("scan", "--file", tmp, "--config", "examples/config-example.yaml")
            assert "PASS" in out
        finally:
            os.remove(tmp)

    def test_missing_config(self):
        _, err, code = _run("scan", "text", "--config", "nonexistent.yaml")
        assert code == 1
        assert "not found" in err.lower()
