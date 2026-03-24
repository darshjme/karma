# Contributing to agent-workflow

Thank you for your interest in contributing!

## Getting Started

```bash
git clone https://github.com/your-org/agent-workflow
cd agent-workflow
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Guidelines

- Keep zero runtime dependencies.
- All new features must include tests.
- Follow PEP 8 and add type hints.
- Open an issue before large changes.

## Pull Request Process

1. Fork and create a feature branch.
2. Write tests for your changes.
3. Ensure all tests pass.
4. Submit a PR with a clear description.
