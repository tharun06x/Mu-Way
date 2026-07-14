"""
core/services/enrichment_service.py — Smart Task Enrichment
=============================================================
Automatically augments each recommended task with curated external
learning resources (YouTube searches, Coursera topics, documentation links).

This is a pure, deterministic, offline enrichment service — it uses
pre-configured URL templates and keyword extraction rather than live
API calls. This means:
  ✓ Zero API costs / keys required
  ✓ Works offline / on Hugging Face Spaces
  ✓ Instant (<1ms per task)

For production, swap _build_resource_links() with real API integrations
(YouTube Data API, Coursera Partner API) without changing the interface.
"""

import logging
import urllib.parse
from dataclasses import dataclass

from core.config import settings as config

logger = logging.getLogger(__name__)


# ── Resource Templates ────────────────────────────────────────────────────── #

@dataclass
class TaskResource:
    title: str
    url: str
    type: str           # 'video' | 'course' | 'docs' | 'practice'
    platform: str       # 'YouTube' | 'Coursera' | 'MDN' | 'LeetCode' | ...
    is_free: bool

    def to_dict(self) -> dict:
        return {
            'title':    self.title,
            'url':      self.url,
            'type':     self.type,
            'platform': self.platform,
            'is_free':  self.is_free,
        }


# Domain → primary documentation / reference site
DOMAIN_DOCS: dict[str, tuple[str, str]] = {
    'ai':             ('PyTorch Docs',          'https://pytorch.org/docs/stable/'),
    'genai':          ('LangChain Docs',         'https://python.langchain.com/'),
    'data_science':   ('Scikit-learn Docs',      'https://scikit-learn.org/stable/'),
    'data_analytics': ('Pandas Docs',            'https://pandas.pydata.org/docs/'),
    'data_eng':       ('Apache Spark Docs',      'https://spark.apache.org/docs/latest/'),
    'web_frontend':   ('MDN Web Docs',           'https://developer.mozilla.org/'),
    'web_backend':    ('Django Docs',            'https://docs.djangoproject.com/'),
    'mobile':         ('Flutter Docs',           'https://docs.flutter.dev/'),
    'devops':         ('Docker Docs',            'https://docs.docker.com/'),
    'cybersec':       ('OWASP Top 10',           'https://owasp.org/www-project-top-ten/'),
    'dsa':            ('LeetCode',               'https://leetcode.com/'),
    'game_dev':       ('Unity Learn',            'https://learn.unity.com/'),
    'quantum_comp':   ('Qiskit Learn',           'https://learning.quantum.ibm.com/'),
    'blockchain':     ('Ethereum Docs',          'https://ethereum.org/en/developers/docs/'),
    'iot':            ('Arduino Docs',           'https://docs.arduino.cc/'),
    'ux':             ('Figma Learn',            'https://www.figma.com/resource-library/'),
    'cloud':          ('AWS Docs',               'https://docs.aws.amazon.com/'),
    'core_programming':('Python Docs',           'https://docs.python.org/3/'),
    'tooling':        ('Git Docs',               'https://git-scm.com/doc'),
    'testing_qa':     ('Pytest Docs',            'https://docs.pytest.org/'),
    'maths':          ('Khan Academy — Math',    'https://www.khanacademy.org/math'),
    'product':        ('Atlassian Agile Guide',  'https://www.atlassian.com/agile'),
    'business':       ('HBR Essentials',         'https://hbr.org/'),
    'hardware':       ('Raspberry Pi Docs',      'https://www.raspberrypi.com/documentation/'),
    'low_code':       ('Zapier Learn',           'https://learn.zapier.com/'),
    'data_analytics': ('Google Analytics Docs',  'https://support.google.com/analytics'),
}

# Domain → Coursera search anchor keyword
DOMAIN_COURSERA: dict[str, str] = {
    'ai':             'machine+learning',
    'genai':          'generative+AI+LLM',
    'data_science':   'data+science+python',
    'data_analytics': 'data+analytics',
    'data_eng':       'data+engineering',
    'web_frontend':   'web+development+react',
    'web_backend':    'backend+development',
    'mobile':         'flutter+mobile+development',
    'devops':         'devops+kubernetes',
    'cybersec':       'cybersecurity',
    'dsa':            'algorithms+data+structures',
    'cloud':          'aws+cloud',
    'game_dev':       'game+development+unity',
    'blockchain':     'blockchain+ethereum',
    'iot':            'internet+of+things',
    'ux':             'ui+ux+design+figma',
    'maths':          'linear+algebra+statistics',
    'product':        'product+management',
    'quantum_comp':   'quantum+computing',
    'testing_qa':     'software+testing+automation',
    'core_programming': 'python+programming',
    'tooling':        'git+github+version+control',
    'hardware':       'embedded+systems',
}


def _build_resource_links(task_name: str, domain: str) -> list[TaskResource]:
    """
    Build 2-4 resource links for a given task name and domain.
    Uses deterministic URL templates (no API calls).
    """
    resources: list[TaskResource] = []
    query = urllib.parse.quote_plus(task_name)
    domain_query = urllib.parse.quote_plus(f"{task_name} tutorial")

    # 1. YouTube search
    resources.append(TaskResource(
        title=f'YouTube: {task_name}',
        url=f'https://www.youtube.com/results?search_query={domain_query}',
        type='video',
        platform='YouTube',
        is_free=True,
    ))

    # 2. Coursera domain course
    coursera_kw = DOMAIN_COURSERA.get(domain, urllib.parse.quote_plus(task_name))
    resources.append(TaskResource(
        title=f'Coursera: {config.DOMAIN_DISPLAY_NAMES.get(domain, domain)} Course',
        url=f'https://www.coursera.org/search?query={coursera_kw}',
        type='course',
        platform='Coursera',
        is_free=False,
    ))

    # 3. Official docs (domain-specific)
    if domain in DOMAIN_DOCS:
        doc_name, doc_url = DOMAIN_DOCS[domain]
        resources.append(TaskResource(
            title=doc_name,
            url=doc_url,
            type='docs',
            platform='Official Docs',
            is_free=True,
        ))

    # 4. LeetCode / practice (for DSA tasks specifically)
    if domain == 'dsa':
        resources.append(TaskResource(
            title=f'LeetCode Practice: {task_name}',
            url=f'https://leetcode.com/search/?q={query}',
            type='practice',
            platform='LeetCode',
            is_free=True,
        ))

    return resources


def enrich_tasks(tasks: list[dict]) -> list[dict]:
    """
    Add resource links to a flat list of task dicts.
    Each task dict is expected to have 'task_name' and 'domain' keys.

    Returns the same list with a new 'resources' key per task.
    Completely safe — never raises; on failure, resources=[].
    """
    enriched = []
    for task in tasks:
        task = dict(task)
        try:
            task_name = task.get('task_name', '')
            domain = task.get('domain', 'general')
            if task_name and domain not in ('general', 'ignored'):
                task['resources'] = [
                    r.to_dict() for r in _build_resource_links(task_name, domain)
                ]
            else:
                task['resources'] = []
        except Exception as exc:
            logger.debug(f"Enrichment failed for task {task.get('task_name')!r}: {exc}")
            task['resources'] = []
        enriched.append(task)
    return enriched


def enrich_roadmap_weeks(roadmap_weeks: list[dict]) -> list[dict]:
    """
    Enrich all tasks inside a week-by-week roadmap structure.
    Operates in-place on task dicts but returns a new list for safety.
    """
    result = []
    for week in roadmap_weeks:
        week = dict(week)
        week['tasks'] = enrich_tasks(week.get('tasks', []))
        result.append(week)
    return result
