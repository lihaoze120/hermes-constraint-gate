# Changelog

All notable changes to the constraint-gate plugin.

## [Unreleased]

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
