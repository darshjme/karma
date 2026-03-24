# Contributing to agent-workflow

Thank you for your interest in contributing! Please follow these guidelines.

## Development Setup

```bash
git clone https://github.com/your-org/agent-workflow.git
cd agent-workflow
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v --cov=agent_workflow
```

All tests must pass before opening a pull request.

## Code Style

- Follow PEP 8.
- Type-annotate all public functions.
- Docstrings on all public classes and methods.

## Pull Request Process

1. Fork the repository.
2. Create a feature branch: `git checkout -b feat/my-feature`.
3. Add tests for new behaviour.
4. Run the full test suite — zero failures allowed.
5. Open a PR against `main` with a clear description.

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.
