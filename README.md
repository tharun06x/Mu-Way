# Mulearn Career Roadmap Generator

## Project Blueprint

An AI-powered learning recommendation system that creates personalized skill
development paths for community members. It uses community submission history,
task metadata, approval outcomes, and dream-role requirements to produce
personalized week-by-week roadmaps.

---

## Project Structure

### Root Files

* **`.env.example`** -> Template for environment variables.
* **`.gitignore`** -> Ignore raw data, generated models, cache, and secrets.
* **`requirements.txt`** -> Python dependencies.
* **`pytest.ini`** -> Test configuration.
* **`setup.py`** -> Package installation configuration.
* **`main.py`** -> Full pipeline runner for all five problems.
* **`roadmap_app.py`** -> Interactive roadmap generator for one user.
* **`README.md`** -> This file.
* **`CONTRACTS.md`** -> Output specifications for each module.
* **`CONTRIBUTING.md`** -> Team workflow, branching, and PR guidance.

### The Source (`src/`)

```text
src/
└── career_roadmap/
    ├── __init__.py
    ├── core.py              <- Shared: UserFeatures, Roadmap, constants
    ├── data.py              <- Data loading, cleaning, feature engineering
    ├── models.py            <- Ranking model training and prediction wrappers
    ├── api.py               <- REST API endpoints
    ├── ui.py                <- Console UI entry points
    └── utils.py             <- Helper functions
```

### Tests (`tests/`)

```text
tests/
├── test_data.py
├── test_models.py
├── test_api.py
├── test_ui.py
├── integration/
│   ├── test_data_to_models.py
│   ├── test_models_to_api.py
│   └── test_api_to_ui.py
├── fixtures.py
└── conftest.py
```

### Data & Configuration

```text
data/
├── raw/                     <- Input data from community (not committed)
└── processed/               <- Cleaned feature outputs

models/
└── ranker.pkl               <- Trained model artifact

config/
└── constants.json           <- System configuration snapshot

.github/workflows/
├── tests.yml
└── lint.yml
```

---

## Current Status: Active Development

### Core Modules

- ✅ **core.py** - Shared data structures and constants
- ✅ **data.py** - Wrappers around the feature pipeline
- ✅ **models.py** - Ranking pipeline wrappers with rule-based fallback
- ✅ **api.py** - Flask app factory for recommendation endpoints
- ✅ **ui.py** - Console roadmap entry point
- ✅ **Tests** - Starter unit and integration test suite

---

## Quick Start

### Prerequisites

- Python 3.10+
- `pip` or `uv`
- Git

### Installation

#### Using `uv`

```bash
uv venv
uv pip install -r requirements.txt
```

#### Using `pip`

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Verify Installation

```bash
pytest tests/ -v
```

---

## How to Use This Project

### Run the Full Backend Pipeline

Use this when you want to rebuild outputs for every user.

```bash
python main.py
```

### Generate a Roadmap for One User

Use this for normal usage.

```bash
python roadmap_app.py
```

Or pass values directly:

```bash
python roadmap_app.py --muid aravinds@mulearn --name Aravind --role "AI Engineer"
```

### Start the API

```bash
python -m career_roadmap.api --port 5000
```

Then call:

- `GET /api/health`
- `GET /api/user/<user_id>`
- `POST /api/rank/<user_id>`

---

## Understanding the Modules

### `core.py`

Defines shared structures used across the system:

- `UserFeatures`
- `ScheduledTask`
- `Roadmap`
- `CANONICAL_DOMAINS`
- `ROLE_REQUIREMENTS`

Treat this module as stable. Changes should be discussed by the team first.

### `data.py`

Loads community data, cleans it, and builds the feature store.

Key functions:

- `load_data()`
- `clean_data(df)`
- `compute_features(user_data, task_data)`

### `models.py`

Trains or loads the ranking model and produces top task recommendations.

Key functions:

- `train_ranker(user_data, task_data)`
- `predict(user_id, top_k=5)`

If `scikit-learn` is unavailable, the existing rule-based ranker still runs.

### `api.py`

Serves roadmap data over HTTP.

Key endpoints:

- `GET /api/health`
- `GET /api/user/<user_id>`
- `POST /api/rank/<user_id>`

### `ui.py`

Delegates to the existing console roadmap app.

---

## Next Steps

### Phase 1: Core Implementation

- [x] Implement feature engineering
- [x] Implement skill gap modeling
- [x] Implement task ranking fallback
- [x] Implement roadmap sequencing
- [x] Implement drift monitoring

### Phase 2: Package Cleanup

- [ ] Move legacy modules fully into `src/career_roadmap/`
- [ ] Replace wrappers with direct package imports
- [ ] Add stronger unit tests for formulas
- [ ] Add API response contract tests

### Phase 3: Frontend & Launch

- [ ] Build dashboard UI
- [ ] Add authentication if required
- [ ] Deploy API and UI to staging
- [ ] Collect user feedback

### Phase 4: Monitoring & Iteration

- [x] Add drift monitoring logic
- [ ] Store monitoring history
- [ ] Automate retraining decision alerts
- [ ] Improve recommendation quality metrics

---

## License

MIT License. See `LICENSE` when added.
