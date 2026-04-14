"""
config.py — Central configuration for the Intelligent Career Roadmap System (ICRS)
"""

from pathlib import Path

# ═══════════════════════════════════════════════════════
# File Paths
# ═══════════════════════════════════════════════════════
DATA_DIR = Path(".")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

QUERY_FILE          = DATA_DIR / "query.xlsx"
KARMA_MASTER_FILE   = DATA_DIR / "Karma_Master_-_Software_1_.xlsx"

FEATURE_STORE_FILE  = OUTPUT_DIR / "feature_store.pkl"
CAREER_GAP_FILE     = OUTPUT_DIR / "career_gaps.csv"
RANKING_MODEL_FILE  = OUTPUT_DIR / "ranking_model.pkl"
MODEL_METADATA_FILE = OUTPUT_DIR / "model_metadata.json"
ROADMAP_FILE        = OUTPUT_DIR / "roadmaps.json"
HEALTH_REPORT_FILE  = OUTPUT_DIR / "health_report.json"

# ═══════════════════════════════════════════════════════
# Problem 1 — Feature Engineering
# ═══════════════════════════════════════════════════════
DECAY_LAMBDA            = 0.95   # time decay per day
BAYESIAN_PRIOR_APPROVALS = 2     # pseudo-approvals
BAYESIAN_PRIOR_TOTAL     = 4     # pseudo-total attempts
WARM_UP_THRESHOLD        = 5     # min submissions before full ML pipeline

DOMAINS = ['ai', 'ds', 'web', 'dsa', 'devops', 'cybersec', 'android', 'general']

# ═══════════════════════════════════════════════════════
# Problem 2 — Skill Gap Modeling
# ═══════════════════════════════════════════════════════
GAP_TIER_CRITICAL = 0.04
GAP_TIER_MODERATE = 0.01
GAP_TIER_MARGINAL = 0.001

ROLE_REQUIREMENTS = {
    'Data Scientist': {
        'ds':      (0.85, 0.35),
        'ai':      (0.75, 0.30),
        'dsa':     (0.65, 0.20),
        'general': (0.50, 0.15),
    },
    'AI Engineer': {
        'ai':      (0.90, 0.40),
        'ds':      (0.75, 0.25),
        'dsa':     (0.70, 0.25),
        'general': (0.50, 0.10),
    },
    'Web Developer': {
        'web':     (0.80, 0.50),
        'dsa':     (0.60, 0.30),
        'general': (0.40, 0.20),
    },
    'Full Stack Developer': {
        'web':     (0.80, 0.40),
        'dsa':     (0.65, 0.35),
        'general': (0.40, 0.25),
    },
    'Frontend Developer': {
        'web':     (0.85, 0.55),
        'dsa':     (0.50, 0.25),
        'general': (0.40, 0.20),
    },
    'Backend Developer': {
        'web':     (0.75, 0.35),
        'dsa':     (0.75, 0.45),
        'general': (0.40, 0.20),
    },
    'DevOps Engineer': {
        'devops':  (0.80, 0.50),
        'web':     (0.60, 0.30),
        'general': (0.40, 0.20),
    },
    'Android Developer': {
        'android': (0.80, 0.55),
        'dsa':     (0.65, 0.30),
        'general': (0.40, 0.15),
    },
    'Security Engineer': {
        'cybersec': (0.80, 0.55),
        'dsa':      (0.60, 0.30),
        'general':  (0.40, 0.15),
    },
}

DOMAIN_TO_ROLE = {
    'ai':      'AI Engineer',
    'ds':      'Data Scientist',
    'web':     'Full Stack Developer',
    'android': 'Android Developer',
    'devops':  'DevOps Engineer',
    'cybersec':'Security Engineer',
    'dsa':     'Backend Developer',
    'general': 'Full Stack Developer',
}

# ═══════════════════════════════════════════════════════
# Problem 3 — Task Ranking
# ═══════════════════════════════════════════════════════
TOP_K_RECOMMENDATIONS       = 5
WEIGHT_CAREER_GAP           = 0.40
WEIGHT_INTEREST             = 0.30
WEIGHT_SUBMISSION_COUNT     = 0.20
WEIGHT_RECENCY              = 0.10

GBREGRESSOR_N_ESTIMATORS    = 100
GBREGRESSOR_LEARNING_RATE   = 0.1
GBREGRESSOR_MAX_DEPTH       = 4
GBREGRESSOR_MIN_SAMPLES_SPLIT = 10
GBREGRESSOR_RANDOM_STATE    = 42
TRAIN_RANDOM_STATE          = 42

# ═══════════════════════════════════════════════════════
# Problem 4 — Roadmap Sequencing
# ═══════════════════════════════════════════════════════
HOURS_PER_WEEK      = 3
MAX_ROADMAP_WEEKS   = 16
NUM_MILESTONES      = 5

# ═══════════════════════════════════════════════════════
# Problem 5 — Drift Monitoring
# ═══════════════════════════════════════════════════════
PSI_THRESHOLD_WARNING = 0.10
PSI_THRESHOLD_ALERT   = 0.20

HEALTH_WEIGHTS = {
    "feature_drift": 0.25,
    "label_drift":   0.20,
    "approval_rate": 0.25,
    "ndcg":          0.15,
    "churn_risk":    0.15,
}

HEALTH_SCORE_THRESHOLDS = {
    "EXCELLENT": (0.85, 1.00),
    "GOOD":      (0.70, 0.85),
    "WARNING":   (0.50, 0.70),
    "CRITICAL":  (0.00, 0.50),
}

RETRAIN_DECISION = {
    "min_retraining_interval_days": 7
}
