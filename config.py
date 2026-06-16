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
WARM_UP_THRESHOLD        = 5     # min submissions before full ML pipeline

DOMAINS = ['ai', 'ds', 'web', 'dsa', 'devops', 'cybersec', 'android', 'general']

# ═══════════════════════════════════════════════════════
# Problem 2 — Skill Gap Modeling
# ═══════════════════════════════════════════════════════
GAP_TIER_CRITICAL = 0.04
GAP_TIER_MODERATE = 0.01
GAP_TIER_MARGINAL = 0.001

# ROLE_REQUIREMENTS = {

#     # Data Scientist — ds and ai are the core, dsa is light foundation
#     'Data Scientist': {
#         'ds':      (0.85, 0.45),   # primary — EDA, stats, modelling
#         'ai':      (0.75, 0.35),   # important — ML algorithms
#         'dsa':     (0.50, 0.10),   # supporting — basic coding efficiency
#         'general': (0.40, 0.10),   # foundation
#     },

#     # AI Engineer — ai dominates, ds is close second, dsa minor
#     'AI Engineer': {
#         'ai':      (0.90, 0.55),   # primary
#         'ds':      (0.70, 0.30),   # secondary
#         'dsa':     (0.45, 0.08),   # light foundation
#         'general': (0.40, 0.07),
#     },

#     # Web Developer — web is everything, dsa is just light background
#     'Web Developer': {
#         'web':     (0.80, 0.70),   # primary
#         'dsa':     (0.35, 0.10),   # light background (basic problem solving)
#         'general': (0.40, 0.20),
#     },

#     # Full Stack Developer — web leads, dsa is supporting
#     'Full Stack Developer': {
#         'web':     (0.80, 0.60),   # primary
#         'dsa':     (0.40, 0.15),   # supporting
#         'general': (0.40, 0.25),
#     },

#     # Frontend Developer — web almost entirely, dsa minimal
#     'Frontend Developer': {
#         'web':     (0.85, 0.75),   # primary
#         'dsa':     (0.30, 0.08),   # very light (basic logic only)
#         'general': (0.40, 0.17),
#     },

#     # Backend Developer — only role where DSA is truly co-equal
#     'Backend Developer': {
#         'web':     (0.70, 0.40),   # backend APIs, DB
#         'dsa':     (0.70, 0.40),   # algorithms genuinely matter here
#         'general': (0.40, 0.20),
#     },

#     # DevOps — no DSA needed, infra and scripting dominate
#     'DevOps Engineer': {
#         'devops':  (0.80, 0.65),   # primary
#         'web':     (0.50, 0.25),   # scripting, APIs
#         'general': (0.40, 0.10),
#     },

#     # Android — android SDK dominates, dsa is light
#     'Android Developer': {
#         'android': (0.80, 0.70),   # primary
#         'dsa':     (0.40, 0.12),   # supporting
#         'general': (0.40, 0.18),
#     },

#     # Security Engineer — cybersec dominates, dsa very light
#     'Security Engineer': {
#         'cybersec': (0.80, 0.72),  # primary
#         'dsa':      (0.35, 0.10),  # light (scripting, basic logic)
#         'general':  (0.40, 0.18),
#     },
# }

ROLE_REQUIREMENTS = {

    # Data Scientist
    'Data Scientist': {
        'ds':      (0.90, 0.50),   # primary — EDA, stats, predictive modelling
        'ai':      (0.65, 0.25),   # secondary — basic ML algorithms
        'web':     (0.40, 0.15),   # Building data dashboards (Streamlit, Gradio)
        'devops':  (0.35, 0.10),   # Basic Docker/Airflow for data pipelines
        'dsa':     (0.40, 0.10),   # supporting — pandas/numpy optimization
        'general': (0.40, 0.10),
    },

    # AI Engineer
    'AI Engineer': {
        'ai':      (0.90, 0.55),   # primary — deep learning, NLP, CV
        'ds':      (0.65, 0.25),   # secondary — data prep
        'dsa':     (0.60, 0.20),   # secondary — pipeline efficiency
        'devops':  (0.40, 0.15),   # MLOps, Docker, Cloud model deployment
        'web':     (0.30, 0.10),   # Building FastAPI/Flask endpoints for the models
        'general': (0.40, 0.07),
    },

    # Web Developer
    'Web Developer': {
        'web':      (0.85, 0.65),  # primary
        'dsa':      (0.40, 0.10),  # basic logic
        'cybersec': (0.30, 0.10),  # Basic OWASP, XSS prevention
        'devops':   (0.30, 0.10),  # Basic hosting concepts (Vercel/Netlify/DNS)
        'android':  (0.25, 0.05),  # ADDED: Mobile web testing & Progressive Web Apps (PWAs)
        'general':  (0.40, 0.15),
    },

    # Full Stack Developer
    'Full Stack Developer': {
        'web':      (0.85, 0.60),  # primary
        'dsa':      (0.50, 0.20),  # supporting
        'devops':   (0.45, 0.15),  # Docker, CI/CD, Server management
        'cybersec': (0.40, 0.15),  # Auth (JWT/OAuth), Data protection
        'android':  (0.25, 0.05),  # ADDED: Cross-platform context (React Native/Ionic)
        'general':  (0.40, 0.15),
    },

    # Frontend Developer
    'Frontend Developer': {
        'web':      (0.90, 0.70),  # primary
        'dsa':      (0.35, 0.10),  # DOM manipulation logic
        'cybersec': (0.25, 0.05),  # CORS, CSRF, Client-side auth security
        'android':  (0.20, 0.05),  # ADDED: Mobile UI/UX constraints
        'general':  (0.40, 0.15),
    },

    # Backend Developer
    'Backend Developer': {
        'web':      (0.75, 0.45),  # APIs, DB design
        'dsa':      (0.75, 0.40),  # Algorithms genuinely matter here
        'devops':   (0.45, 0.15),  # Containerization, Server configs
        'cybersec': (0.40, 0.15),  # Encryption, API security (Rate limiting)
        'general':  (0.40, 0.10),
    },

    # DevOps Engineer
    'DevOps Engineer': {
        'devops':   (0.90, 0.65),  # primary
        'cybersec': (0.50, 0.20),  # Infrastructure security (IAM, VPCs, Firewalls)
        'web':      (0.45, 0.15),  # Automation scripts, server monitoring UIs
        'dsa':      (0.30, 0.05),  # Scripting efficiency
        'general':  (0.40, 0.10),
    },

    # Android Developer
    'Android Developer': {
        'android':  (0.85, 0.65),  # primary
        'web':      (0.40, 0.15),  # REST APIs, Firebase integrations
        'dsa':      (0.45, 0.15),  # Memory management, async processing
        'cybersec': (0.35, 0.10),  # Secure local storage, OAuth, Code obfuscation
        'devops':   (0.25, 0.05),  # CI/CD (Fastlane, Play Store deployment pipelines)
        'general':  (0.40, 0.10),
    },

    # Security Engineer
    'Security Engineer': {
        'cybersec': (0.90, 0.65),  # primary
        'web':      (0.55, 0.25),  # Web App PenTesting (SQLi, XSS)
        'devops':   (0.50, 0.20),  # Cloud/Network Security, misconfigurations
        'dsa':      (0.40, 0.15),  # Scripting, Malware Analysis
        'android':  (0.35, 0.10),  # ADDED: Mobile App Penetration Testing (APK reversing)
        'general':  (0.40, 0.10),
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

DOMAIN_DISPLAY_NAMES = {
    'ai': 'Artificial Intelligence',
    'ds': 'Data Science',
    'web': 'Web Development',
    'dsa': 'Data Structures & Algorithms',
    'devops': 'DevOps Engineering',
    'cybersec': 'Cybersecurity',
    'android': 'Android Development',
    'general': 'General Foundation'
}

# DOMAIN_PREREQUISITES = {
#     'ai': ['general', 'ds'],    
#     'ds': ['general'],          
#     'web': ['general'],
#     'android': ['general', 'dsa'],
#     'devops': ['general', 'web'],
#     'cybersec': ['general', 'web'],
#     'dsa': ['general'],
#     'general': [],              # Base level, no prerequisites
# }

DOMAIN_PREREQUISITES = {
    # Tier 0: Absolute Basics
    'general': [],              
    
    # Tier 1: Core Programming
    'web': ['general'],         
    'dsa': ['general'],         
    
    # Tier 2: Intermediate Applications
    'ds': ['general', 'dsa'],     # Needs DSA logic for Pandas/Numpy
    'android': ['web', 'dsa'],    # Needs Web for APIs and DSA for logic
    'devops': ['web'],            # Needs Web to understand what to deploy
    
    # Tier 3: Advanced Specializations
    'ai': ['ds', 'dsa'],          # Needs Data Science math and DSA efficiency
    'cybersec': ['web', 'devops'] # Needs to know how to build apps AND deploy them to secure them
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
