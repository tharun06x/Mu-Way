---
title: muWay — Intelligent Career Operating System
emoji: 🚀
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
license: mit
short_description: Personalised career roadmaps powered by ML on Mulearn data
---

# 🚀 muWay — Intelligent Career Operating System

**muWay** is an intelligent platform designed to analyze your past "karma" submissions through a Machine Learning pipeline and generate personalized, week-by-week learning roadmaps. It helps you navigate the "Skill Archipelago" to reach your dream role.

## ✨ Key Features

- **Personalized Career Roadmaps**: AI-driven task recommendations tailored to your skill gaps and career goals.
- **Roadmap Persistence**: Roadmaps are generated, cached in the database, and instantly retrieved. Users can bypass the cache and force a fresh ML pipeline run anytime.
- **Task Exploration Drawer**: Click any task to view detailed Markdown descriptions, ML reasoning ("Why this task?"), difficulty levels, urgency, and curated learning resources.
- **Progress Forecasting**: Adaptive goals predicting your completion date and burnout risk based on your learning velocity.
- **Skill Decay Simulation**: Analyzes inactivity to determine your "rust severity" and dynamically schedules bridge tasks to recover forgotten skills.
- **Role Comparison**: Compare your readiness across two different dream roles side-by-side.
- **Gamification & Insights**: Earn XP, badges, and track your activity streaks.

## 🛠️ Technology Stack

**Frontend**
- React 18 (Vite + TypeScript)
- Tailwind CSS v4 + Framer Motion (for dynamic, premium UI aesthetics)
- React Query (TanStack) & Zustand (State Management)
- React Markdown

**Backend**
- Python 3 / Django
- Pandas & Scikit-learn (ML Pipeline, TF-IDF, Bayesian Difficulty Ranking)
- SQLite (Development Database)

## 📦 Local Setup & Development

### 1. Backend (Django + ML Pipeline)
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (assuming you have a requirements.txt)
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start the development server (runs on port 8000)
python manage.py runserver
```

### 2. Frontend (React + Vite)
```bash
cd frontend

# Install dependencies
npm install

# Start the frontend development server (runs on port 5173)
npm run dev
```

## 🗺️ How It Works (The ML Pipeline)
1. **Data Loading**: Fetches User Submissions and Task Catalogs from the database.
2. **Feature Engineering**: Calculates user mastery across domains and TF-IDF scores for tasks.
3. **Gap Analysis**: Measures the distance between the user's current mastery and the dream role's requirements.
4. **Sequencing**: A heuristic algorithm schedules the recommended tasks week-by-week (max 3 hours per week), enforcing a gradual difficulty progression.

## 📄 License
This project is licensed under the MIT License.
