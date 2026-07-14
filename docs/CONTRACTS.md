# Module Contracts

This document defines the expected handoff between modules.

## data.py

### Input

- `query.xlsx` with user submissions.
- `Karma Master - Software(1).xlsx` with task metadata.

### Output

- Feature store DataFrame with one row per user.
- Must include `user_id`, global signals, and per-domain mastery, approval,
  count, and interest fields.

## models.py

### Input

- Clean submission DataFrame.
- Task catalog DataFrame.

### Output

- Ranking model object.
- Pairwise recommendation DataFrame with `user_id`, `task_name`, `domain`,
  `rule_score`, `final_score`, and `approval_probability`.

## api.py

### `GET /api/health`

Returns:

```json
{"status": "ok"}
```

### `GET /api/user/<user_id>`

Returns user features and status.

### `POST /api/rank/<user_id>`

Body:

```json
{"role": "AI Engineer", "top_k": 5}
```

Returns ranked tasks and roadmap metadata.

## ui.py

Displays a roadmap for one user by calling the same backend logic used by the
API layer.
