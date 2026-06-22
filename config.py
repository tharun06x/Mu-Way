"""
config.py — Central configuration for the Intelligent Career Roadmap System (ICRS)
"""

import os
import yaml
from pathlib import Path
# File Paths
# ═══════════════════════════════════════════════════════
DATA_DIR = Path(".")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

QUERY_FILE          = DATA_DIR / "query.xlsx"
KARMA_MASTER_FILE   = DATA_DIR / "Karma Master - Software(1).xlsx"

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
BAYESIAN_PRIOR_TASK_WEIGHT = 20  # fake attempts for task empirical difficulty
WARM_UP_THRESHOLD        = 5     # min submissions before full ML pipeline

DOMAINS = [
    'ai', 'genai', 'data_science', 'data_analytics', 'data_eng',
    'web_dev', 'mobile', 'devops', 'cybersec',
    'dsa', 'game_dev', 'quantum_comp', 'blockchain', 'iot',
    'ux', 'low_code', 'product', 'business', 'general'
]

# Load taxonomy from YAML
TAXONOMY_FILE = DATA_DIR / "config" / "taxonomy.yaml"
try:
    with open(TAXONOMY_FILE, 'r') as f:
        _taxonomy = yaml.safe_load(f)
        
        # Invert the mapping: from { 'ml': ['ai', 'ml', ...] } to { 'ml': 'ml', 'ai': 'ml' }
        DOMAIN_TOKEN_MAP = {}
        if 'domain_token_map' in _taxonomy:
            for domain, tokens in _taxonomy['domain_token_map'].items():
                for token in tokens:
                    DOMAIN_TOKEN_MAP[token] = domain
                    
        STRUCTURAL_TOKENS = set(_taxonomy.get('structural_tokens', []))
except Exception as e:
    print(f"Warning: Could not load taxonomy from {TAXONOMY_FILE}: {e}")
    DOMAIN_TOKEN_MAP = {}
    STRUCTURAL_TOKENS = set()

# ═══════════════════════════════════════════════════════
# Problem 2 — Skill Gap Modeling
# ═══════════════════════════════════════════════════════
GAP_TIER_CRITICAL = 0.04
GAP_TIER_MODERATE = 0.01
GAP_TIER_MARGINAL = 0.001

ROLE_REQUIREMENTS = {
    'AI Engineer': {
        'ai':            (0.90, 0.40),
        'genai':         (0.80, 0.25),
        'data_science':  (0.80, 0.15),
        'data_eng':      (0.60, 0.10),
        'devops':        (0.50, 0.10),
    },
    'Data Scientist': {
        'data_science':  (0.95, 0.50),
        'data_analytics':(0.85, 0.20),
        'data_eng':      (0.70, 0.15),
        'ai':            (0.60, 0.10),
        'business':      (0.50, 0.05),
    },
    'Full Stack Developer': {
        'web_dev':       (0.95, 0.50),
        'dsa':           (0.75, 0.20),
        'devops':        (0.60, 0.15),
        'ux':            (0.50, 0.10),
        'general':       (0.80, 0.05),
    },
    'Mobile Developer': {
        'mobile':        (0.95, 0.60),
        'ux':            (0.60, 0.15),
        'web_dev':       (0.50, 0.15),
        'dsa':           (0.60, 0.10),
    },
    'DevOps Engineer': {
        'devops':        (0.95, 0.50),
        'web_dev':       (0.70, 0.20),
        'cybersec':      (0.65, 0.15),
        'data_eng':      (0.50, 0.10),
        'general':       (0.80, 0.05),
    },
    'Security Engineer': {
        'cybersec':      (0.95, 0.60),
        'devops':        (0.75, 0.20),
        'web_dev':       (0.60, 0.15),
        'general':       (0.80, 0.05),
    },
    'Game Developer': {
        'game_dev':      (0.95, 0.60),
        'dsa':           (0.85, 0.25),
        'ux':            (0.50, 0.10),
        'general':       (0.70, 0.05),
    },
    'UI/UX Designer': {
        'ux':            (0.95, 0.60),
        'web_dev':       (0.50, 0.20),
        'product':       (0.60, 0.15),
        'business':      (0.50, 0.05),
    },
    'Blockchain Developer': {
        'blockchain':    (0.95, 0.50),
        'cybersec':      (0.75, 0.20),
        'web_dev':       (0.60, 0.15),
        'dsa':           (0.70, 0.15),
    },
    'IoT Engineer': {
        'iot':           (0.95, 0.50),
        'devops':        (0.60, 0.20),
        'web_dev':       (0.50, 0.15),
        'data_eng':      (0.50, 0.15),
    },
    'Product Manager': {
        'product':       (0.95, 0.40),
        'business':      (0.85, 0.30),
        'ux':            (0.60, 0.15),
        'data_analytics':(0.60, 0.10),
        'general':       (0.70, 0.05),
    },
    'Quantum Researcher': {
        'quantum_comp':  (0.95, 0.50),
        'data_science':  (0.70, 0.20),
        'dsa':           (0.80, 0.20),
        'ai':            (0.60, 0.10),
    }
}

DOMAIN_TO_ROLE = {
    'ai':            'AI Engineer',
    'genai':         'AI Engineer',
    'data_science':  'Data Scientist',
    'data_analytics':'Data Scientist',
    'data_eng':      'Data Scientist',
    'web_dev':       'Full Stack Developer',
    'mobile':        'Mobile Developer',
    'devops':        'DevOps Engineer',
    'cybersec':      'Security Engineer',
    'game_dev':      'Game Developer',
    'quantum_comp':  'Quantum Researcher',
    'blockchain':    'Blockchain Developer',
    'iot':           'IoT Engineer',
    'ux':            'UI/UX Designer',
    'product':       'Product Manager',
    'business':      'Product Manager',
    'dsa':           'Full Stack Developer',
    'low_code':      'Product Manager',
    'general':       'Full Stack Developer',
}

DOMAIN_DISPLAY_NAMES = {
    'ai':            'Artificial Intelligence',
    'genai':         'Generative AI',
    'data_science':  'Data Science',
    'data_analytics':'Data Analytics',
    'data_eng':      'Data Engineering',
    'web_dev':       'Web Development',
    'mobile':        'Mobile Development',
    'devops':        'Cloud & DevOps',
    'cybersec':      'Cyber Security',
    'dsa':           'Data Structures & Algorithms',
    'game_dev':      'Game Development',
    'quantum_comp':  'Quantum Computing',
    'blockchain':    'Blockchain & Web3',
    'iot':           'Internet of Things (IoT)',
    'ux':            'UI/UX Design',
    'low_code':      'No/Low Code',
    'product':       'Product Management',
    'business':      'Business & Entrepreneurship',
    'general':       'General Foundation'
}

DOMAIN_PREREQUISITES = {
    'general': [],
    'dsa': ['general'],
    'web_dev': ['general', 'dsa'],
    'mobile': ['web_dev'],
    'devops': ['web_dev', 'general'],
    'cybersec': ['devops', 'web_dev'],
    'data_analytics': ['general'],
    'data_eng': ['data_analytics', 'general'],
    'data_science': ['data_analytics', 'dsa'],
    'ai': ['data_science', 'data_eng'],
    'genai': ['ai'],
    'game_dev': ['dsa', 'general'],
    'quantum_comp': ['data_science', 'dsa'],
    'blockchain': ['web_dev', 'cybersec'],
    'iot': ['general', 'web_dev'],
    'ux': ['general'],
    'business': ['general'],
    'product': ['business', 'ux'],
    'low_code': ['general']
}

# ═══════════════════════════════════════════════════════
# Problem 3 — Task Ranking
# ═══════════════════════════════════════════════════════
TOP_K_RECOMMENDATIONS       = 5
WEIGHT_CAREER_GAP           = 0.30 ## 40 to 30
WEIGHT_INTEREST             = 0.20
WEIGHT_COMMUNITY_APPROVAL   = 0.20
WEIGHT_DIFFICULTY_SUITABILITY = 0.30 ## 10 to 30

# Backward-compatible aliases for older code paths.
WEIGHT_SUBMISSION_COUNT     = WEIGHT_COMMUNITY_APPROVAL
WEIGHT_RECENCY              = WEIGHT_DIFFICULTY_SUITABILITY

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
MINUTES_PER_WEEK = HOURS_PER_WEEK * 60  # Easier to calculate smaller tasks
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
