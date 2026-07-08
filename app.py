"""
Intelligent Career Roadmap System — Streamlit Web UI
=====================================================
Run with:   streamlit run app.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Path bootstrap ──────────────────────────────────────────────────────────── #
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import time
import numpy as np
import pandas as pd
import streamlit as st
import config


# ── Page config ─────────────────────────────────────────────────────────────── #
st.set_page_config(
    page_title="ICRS — Career Roadmap",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────── #
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark gradient background */
.stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }

/* Card containers */
.metric-card {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    backdrop-filter: blur(12px);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(0,0,0,0.3); }

/* Gradient headings */
.gradient-text {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}

/* Week cards */
.week-card {
    background: linear-gradient(135deg, rgba(102,126,234,0.15), rgba(118,75,162,0.15));
    border: 1px solid rgba(102,126,234,0.3);
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: all 0.2s ease;
}
.week-card:hover { border-color: rgba(102,126,234,0.7); transform: translateX(4px); }

/* Task pill */
.task-pill {
    display: inline-block;
    background: rgba(102,126,234,0.2);
    border: 1px solid rgba(102,126,234,0.4);
    border-radius: 20px;
    padding: 0.2rem 0.75rem;
    margin: 0.2rem;
    font-size: 0.82rem;
    color: #c7d2fe;
}

/* Tier badges */
.badge-critical  { background:#ff4757; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.badge-moderate  { background:#ffa502; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.badge-marginal  { background:#2ed573; color:#111; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
.badge-met       { background:#57606f; color:#fff; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }

/* Sidebar tweaks */
section[data-testid="stSidebar"] { background: rgba(15,12,41,0.85); border-right: 1px solid rgba(255,255,255,0.08); }

/* Primary button */
.stButton > button {
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 2rem;
    transition: all 0.2s ease;
}
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102,126,234,0.5); }

/* Progress bar */
.stProgress > div > div > div { background: linear-gradient(90deg, #667eea, #f093fb); border-radius: 10px; }

/* Selectbox */
.stSelectbox > label { color: rgba(255,255,255,0.7); font-size: 0.85rem; }

/* Input */
.stTextInput > label { color: rgba(255,255,255,0.7); font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

# ── Domain icons & colours ───────────────────────────────────────────────────── #
DOMAIN_ICONS = {
    "ai": "🤖", "data_science": "📊", "data_analytics": "📈",
    "web_frontend": "🎨", "web_backend": "🖥️", "mobile": "📱", "devops": "⚙️",
    "cybersec": "🔒", "dsa": "🧮", "game_dev": "🎮",
    "genai": "✨", "blockchain": "⛓️", "iot": "📡",
    "quantum_comp": "⚛️", "ux": "🎨", "low_code": "🧩",
    "product": "📋", "business": "💼", "data_eng": "🔧",
    "maths": "📐", "cloud": "☁️", "hardware": "🔩",
    "core_programming": "💻", "tooling": "🛠️", "testing_qa": "🧪",
}
TIER_COLOURS = {"CRITICAL": "#ff4757", "MODERATE": "#ffa502", "MARGINAL": "#2ed573", "MET": "#57606f"}

# ── Data loading (cached) ───────────────────────────────────────────────────── #
@st.cache_resource(show_spinner="⏳ Loading Mulearn data …")
def load_pipeline_data():
    from data_loader import DataLoader
    user_data, task_data, _ = DataLoader().load_all()
    return user_data, task_data

# ── Helper imports (lazy so Streamlit can render the skeleton first) ─────────── #
def get_roadmap(muid: str, name: str, role: str, user_data, task_data):
    from roadmap_app import generate_roadmap
    return generate_roadmap(muid, name, role, user_data, task_data)

# ── Sidebar ─────────────────────────────────────────────────────────────────── #
with st.sidebar:
    st.markdown("<h2 class='gradient-text'>🚀 ICRS</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:rgba(255,255,255,0.5);font-size:0.8rem;margin-top:-0.5rem;'>Intelligent Career Roadmap</p>", unsafe_allow_html=True)
    st.divider()

    ROLES = [
        # ── Core roles (match config.ROLE_REQUIREMENTS exactly) ── #
        "AI/ML Engineer", "Data Scientist", "Data Analyst",
        "Full Stack Developer", "Backend Developer", "Frontend Developer",
        "Mobile Developer", "DevOps Engineer", "Cybersecurity Analyst",
        "Game Developer", "Product Manager", "UI/UX Designer",
        # ── Specialist roles ── #
        "Data Engineer", "Cloud Architect", "Blockchain Developer",
        "IoT Engineer", "Systems Engineer", "Hardware Engineer",
        "Quantum Researcher",
    ]

    st.markdown("### 👤 User Details")
    muid  = st.text_input("MUID", placeholder="user@mulearn.com")
    name  = st.text_input("Name", placeholder="Your name")
    role  = st.selectbox("Dream Role", ROLES, index=2)
    run   = st.button("🗺️ Generate Roadmap", use_container_width=True)

    st.divider()
    st.markdown("<p style='color:rgba(255,255,255,0.3);font-size:0.72rem;text-align:center;'>Powered by Mulearn ICRS</p>", unsafe_allow_html=True)

# ── Hero header ─────────────────────────────────────────────────────────────── #
st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;">
    <h1 class='gradient-text' style='font-size:2.8rem;margin:0;'>Intelligent Career Roadmap</h1>
    <p style='color:rgba(255,255,255,0.55);font-size:1.05rem;margin-top:0.5rem;'>
        Personalised learning paths powered by ML · Built on Mulearn's task ecosystem
    </p>
</div>
""", unsafe_allow_html=True)

# ── Load data once ───────────────────────────────────────────────────────────── #
try:
    user_data, task_data = load_pipeline_data()
    data_ok = True
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    data_ok = False

# ── Main roadmap section ─────────────────────────────────────────────────────── #
if run and data_ok:
    if not muid.strip():
        st.warning("⚠️ Please enter a MUID.")
        st.stop()

    name_clean = name.strip() or muid.split("@")[0].capitalize()

    with st.spinner(f"🧠 Building roadmap for **{name_clean}** …"):
        t0 = time.time()
        try:
            result = get_roadmap(muid.strip(), name_clean, role, user_data, task_data)
            elapsed = time.time() - t0
        except Exception as e:
            st.error(f"❌ Pipeline error: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()

    gap       = result["gap"]
    recs      = result["recs"]
    roadmap   = result.get("roadmap", {})
    known     = result.get("known_user", False)
    weeks     = roadmap.get("roadmap_weeks", [])

    st.success(f"✅ Roadmap ready in {elapsed:.1f}s!")

    # ── KPI row ─────────────────────────────────────────────────────────────── #
    col1, col2, col3, col4 = st.columns(4)

    readiness = gap.get("readiness_pct", 0)
    career_gap = gap.get("career_gap", 1)
    tier = gap.get("career_gap_tier", "CRITICAL")

    with col1:
        st.markdown(f"""
        <div class='metric-card' style='text-align:center;'>
            <div style='font-size:2rem;font-weight:800;color:#667eea;'>{readiness:.0f}%</div>
            <div style='color:rgba(255,255,255,0.6);font-size:0.82rem;margin-top:0.2rem;'>Readiness</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='metric-card' style='text-align:center;'>
            <div style='font-size:2rem;font-weight:800;color:#f093fb;'>{len(weeks)}</div>
            <div style='color:rgba(255,255,255,0.6);font-size:0.82rem;margin-top:0.2rem;'>Weeks Planned</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        n_tasks = sum(len(w.get("tasks", [])) for w in weeks)
        st.markdown(f"""
        <div class='metric-card' style='text-align:center;'>
            <div style='font-size:2rem;font-weight:800;color:#2ed573;'>{n_tasks}</div>
            <div style='color:rgba(255,255,255,0.6);font-size:0.82rem;margin-top:0.2rem;'>Tasks Assigned</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        badge_cls = f"badge-{tier.lower()}"
        st.markdown(f"""
        <div class='metric-card' style='text-align:center;'>
            <div style='font-size:1.5rem;margin-bottom:0.3rem;'>🎯</div>
            <span class='{badge_cls}'>{tier}</span>
            <div style='color:rgba(255,255,255,0.6);font-size:0.82rem;margin-top:0.4rem;'>Gap Tier</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Readiness progress bar ──────────────────────────────────────────────── #
    st.markdown(f"<p style='color:rgba(255,255,255,0.6);font-size:0.85rem;margin-bottom:0.2rem;'>Readiness towards <strong style='color:#c7d2fe;'>{role}</strong></p>", unsafe_allow_html=True)
    st.progress(min(1.0, readiness / 100))

    st.markdown("---")

    # ── Two-column layout ───────────────────────────────────────────────────── #
    left, right = st.columns([1.4, 1], gap="large")

    # ── LEFT: Week-by-week roadmap ──────────────────────────────────────────── #
    with left:
        st.markdown("<h3 style='color:white;'>📅 Weekly Learning Plan</h3>", unsafe_allow_html=True)

        if not weeks:
            st.info("No roadmap weeks generated. Try a different role or user.")
        else:
            for w in weeks:
                week_num   = w.get("week", "?")
                mins_used  = w.get("minutes_used", 0)
                tasks_list = w.get("tasks", [])
                domain_set = set(t.get("domain", "general") for t in tasks_list)
                icons      = " ".join(DOMAIN_ICONS.get(d, "📚") for d in domain_set)

                with st.expander(f"Week {week_num} — {len(tasks_list)} tasks · {mins_used} min  {icons}", expanded=(week_num == 1)):
                    for t in tasks_list:
                        tname    = t.get("task_name", "—")
                        tdomain  = t.get("domain", "general")
                        tscore   = t.get("score", 0)
                        ttier    = t.get("urgency_tier", "MODERATE")
                        tdiff    = int(float(t.get("difficulty_level", 2)))
                        diff_map = {1: "🟢 Beginner", 2: "🔵 Intermediate", 3: "🔴 Advanced", 4: "⚫ Expert"}
                        tier_col = TIER_COLOURS.get(ttier, "#57606f")

                        st.markdown(f"""
                        <div class='week-card'>
                            <div style='display:flex;justify-content:space-between;align-items:center;'>
                                <div>
                                    <span style='color:white;font-weight:600;'>{DOMAIN_ICONS.get(tdomain,'📚')} {tname}</span>
                                    <div style='margin-top:0.3rem;'>
                                        <span style='color:rgba(255,255,255,0.45);font-size:0.78rem;'>{tdomain} &nbsp;·&nbsp; {diff_map.get(tdiff,'—')}</span>
                                    </div>
                                </div>
                                <div style='text-align:right;'>
                                    <span style='background:{tier_col};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.72rem;font-weight:600;'>{ttier}</span>
                                    <div style='color:rgba(255,255,255,0.4);font-size:0.72rem;margin-top:0.3rem;'>score {tscore:.3f}</div>
                                </div>
                            </div>
                        </div>""", unsafe_allow_html=True)

    # ── RIGHT: Skill gap breakdown ──────────────────────────────────────────── #
    with right:
        st.markdown("<h3 style='color:white;'>🎯 Skill Gap Analysis</h3>", unsafe_allow_html=True)

        domain_gaps_raw = gap.get("domain_gaps") or {}
        if isinstance(domain_gaps_raw, str):
            try:
                domain_gaps_raw = json.loads(domain_gaps_raw)
            except Exception:
                domain_gaps_raw = {}

        if domain_gaps_raw:
            gap_data = []
            for dom, info in domain_gaps_raw.items():
                if isinstance(info, dict):
                    gap_data.append({
                        "Domain": f"{DOMAIN_ICONS.get(dom,'📚')} {config.DOMAIN_DISPLAY_NAMES.get(dom, dom.replace('_',' ').title())}",
                        "Current": info.get("current", 0),
                        "Required": info.get("required", 0),
                        "Gap": info.get("raw_gap", 0),
                        "Tier": info.get("tier", "MET"),
                    })

            if gap_data:
                gap_df = pd.DataFrame(gap_data).sort_values("Gap", ascending=False)

                for _, row in gap_df.iterrows():
                    curr    = row["Current"]
                    req     = row["Required"]
                    t       = row["Tier"]
                    badge   = f"badge-{t.lower()}"
                    fill    = min(1.0, curr / req) if req > 0 else 1.0

                    st.markdown(f"""
                    <div style='margin-bottom:0.6rem;'>
                        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;'>
                            <span style='color:white;font-size:0.85rem;font-weight:500;'>{row['Domain']}</span>
                            <span class='{badge}'>{t}</span>
                        </div>
                        <div style='background:rgba(255,255,255,0.08);border-radius:8px;height:8px;overflow:hidden;'>
                            <div style='width:{fill*100:.1f}%;height:100%;background:linear-gradient(90deg,#667eea,#f093fb);border-radius:8px;transition:width 0.4s ease;'></div>
                        </div>
                        <div style='display:flex;justify-content:space-between;margin-top:0.15rem;'>
                            <span style='color:rgba(255,255,255,0.35);font-size:0.72rem;'>Mastery {curr:.2f}</span>
                            <span style='color:rgba(255,255,255,0.35);font-size:0.72rem;'>Required {req:.2f}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
        else:
            st.info("Skill gap breakdown not available.")

        st.markdown("---")

        # ── Top task recommendations ──────────────────────────────────────── #
        st.markdown("<h3 style='color:white;'>⭐ Top Recommendations</h3>", unsafe_allow_html=True)

        if recs is not None and len(recs) > 0:
            top_recs = recs.head(8)
            for _, rec in top_recs.iterrows():
                tname  = rec.get("task_name", "—")
                tdom   = rec.get("domain", "general")
                tscore = rec.get("final_score", rec.get("rule_score", rec.get("score", 0)))
                tdiff  = int(float(rec.get("difficulty_level", 2)))
                diff_label = {1: "Beginner", 2: "Intermediate", 3: "Advanced", 4: "Expert"}.get(tdiff, "—")

                st.markdown(f"""
                <div class='week-card' style='padding:0.7rem 1rem;'>
                    <span style='color:white;font-size:0.88rem;font-weight:500;'>
                        {DOMAIN_ICONS.get(tdom,'📚')} {tname}
                    </span>
                    <div style='color:rgba(255,255,255,0.4);font-size:0.75rem;margin-top:0.2rem;'>
                        {tdom} &nbsp;·&nbsp; {diff_label} &nbsp;·&nbsp; score <strong style='color:#c7d2fe;'>{float(tscore):.3f}</strong>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No recommendations generated.")

    st.markdown("---")

    # ── JSON export ──────────────────────────────────────────────────────────── #
    export_data = {
        "muid":       muid,
        "name":       name_clean,
        "role":       role,
        "gap":        {k: v for k, v in gap.items() if k != "domain_gaps"},
        "roadmap":    roadmap,
    }
    st.download_button(
        label="⬇️ Download Roadmap (JSON)",
        data=json.dumps(export_data, indent=2, default=str),
        file_name=f"roadmap_{muid.split('@')[0]}.json",
        mime="application/json",
    )

# ── Default landing ──────────────────────────────────────────────────────────── #
else:
    if data_ok:
        st.markdown("""
        <div style="text-align:center;padding:3rem 2rem;max-width:700px;margin:0 auto;">
            <div style="font-size:4rem;margin-bottom:1rem;">🎯</div>
            <h2 style="color:white;font-weight:700;">Your personalised roadmap awaits</h2>
            <p style="color:rgba(255,255,255,0.55);font-size:1rem;line-height:1.7;">
                Enter your <strong style='color:#c7d2fe;'>MUID</strong>, choose your
                <strong style='color:#c7d2fe;'>dream role</strong>, and ICRS will analyse your
                Mulearn activity to generate a week-by-week learning plan tailored to your
                current skill level and career gaps.
            </p>
            <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-top:2rem;">
                <div class='metric-card' style='width:160px;text-align:center;'>
                    <div style='font-size:2rem;'>🤖</div>
                    <div style='color:rgba(255,255,255,0.7);font-size:0.8rem;margin-top:0.3rem;'>ML-Powered Ranking</div>
                </div>
                <div class='metric-card' style='width:160px;text-align:center;'>
                    <div style='font-size:2rem;'>📅</div>
                    <div style='color:rgba(255,255,255,0.7);font-size:0.8rem;margin-top:0.3rem;'>Week-by-Week Plans</div>
                </div>
                <div class='metric-card' style='width:160px;text-align:center;'>
                    <div style='font-size:2rem;'>🎯</div>
                    <div style='color:rgba(255,255,255,0.7);font-size:0.8rem;margin-top:0.3rem;'>Skill Gap Analysis</div>
                </div>
                <div class='metric-card' style='width:160px;text-align:center;'>
                    <div style='font-size:2rem;'>⬇️</div>
                    <div style='color:rgba(255,255,255,0.7);font-size:0.8rem;margin-top:0.3rem;'>JSON Export</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
