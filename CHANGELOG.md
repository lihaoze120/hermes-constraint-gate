# Changelog

All notable changes to the constraint-gate plugin.

## [0.11.1] — 2026-06-21

### Changed
- Optimized cg_cli.py (by Claude Code): fixed sys.path import hack, added --version, improved error handling, load_config now handles empty/broken YAML gracefully

## [0.11.0] — 2026-06-21

### Added
- Standalone CLI (`gate scan`, `gate list-gates`) — no Hermes dependency
- `--format json`, `--quiet`, `--file`, stdin support
- `pyyaml` dependency, `console_scripts` entry point
- 9 CLI tests (57 total)
- CLI usage in README Quick Start

## [0.10.0] — 2026-06-21

### Added
- `transform` action implemented — auto-fix for starts_with, ends_with, regex, forbidden_words
- RegexGate `replacement` config — use `\1` to keep captured text while stripping markers
- GitHub issue templates (bug report, feature request) + PR template
- 7 new tests for transform (48 total)
- Updated demo with transform examples

## [0.9.3] — 2026-06-21

### Added
- 41 unit tests covering all 7 gate types + engine + edge cases
- GitHub Actions CI (Python 3.9–3.12)
- `pyproject.toml` — pip-installable package
- CONTRIBUTING.md — contribution guide
- CI badge on README

## [0.9.2] — 2026-06-21

### Changed
- De-localized documentation: README and SKILL.md now use universal examples
- Split config examples: `config-example.yaml` (universal) + `config-example-cjk.yaml` (CJK)
- Removed localized `config-example-cn.yaml` / `config-example-en.yaml`

## [0.9.1] — 2026-06-21

### Added
- `ends_with` gate type — block trailing pleasantries ("Let me know if...", "需要我继续吗？")
- `traditional_chinese` gate type — detect traditional Chinese characters (200+ char reference set)
- Total gate types: 5 → 7

## [0.9.0] — 2026-06-21

### Added
- Initial release
- 5 gate types: `language_ratio`, `regex`, `forbidden_words`, `length`, `starts_with`
- CJK Unicode disambiguation (Han vs Hiragana vs Katakana)
- Extensible gate registry for custom gate types
- Two-layer enforcement: skill (mental checklist) + plugin (code-level hook)
- Plugin entry point: `transform_llm_output` hook
