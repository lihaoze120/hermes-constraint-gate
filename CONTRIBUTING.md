# Contributing

Thanks for your interest in constraint-gate!

## Setup

```bash
git clone https://github.com/lihaoze120/hermes-constraint-gate.git
cd hermes-constraint-gate
pip install -e ".[test]"
```

## Running Tests

```bash
pytest tests/ -v
```

Tests run automatically on every push via GitHub Actions.

## Adding a Gate Type

1. Subclass `Gate` in `plugin/gate.py`
2. Implement `check(self, response_text) -> Optional[Violation]`
3. Register it in `_GATE_TYPES`
4. Add tests in `tests/test_gate.py`
5. Update `SKILL.md` gate types table

Example:
```python
class MyGate(Gate):
    def check(self, text: str) -> Optional[Violation]:
        if "bad" in text:
            return Violation(
                gate_name=self.name,
                description="Found bad content",
                action=self.action,
            )
        return None

register_gate_type("my_gate", MyGate)
```

## PR Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] New gate types have tests
- [ ] Documentation updated (README, SKILL.md, CHANGELOG)
- [ ] Config examples updated if needed

## License

By contributing, you agree your work will be licensed under MIT.
