# Contributing

## Branching

Use short feature branches:

```bash
git checkout -b feature/your-feature-name
```

## Development Flow

1. Make changes in `src/career_roadmap/` or the legacy runner modules.
2. Add or update tests under `tests/`.
3. Run:

```bash
pytest tests/ -v
```

4. Commit with a clear message.
5. Open a pull request for review.

## Code Expectations

- Keep module contracts stable.
- Do not commit raw data, generated models, cache files, or secrets.
- Prefer deterministic formulas for feature and roadmap logic.
- Add tests when changing shared behavior.
