import React, { useState } from 'react';
import axios from 'axios';
import { Rocket, User, Briefcase, ChevronRight } from 'lucide-react';
import { JourneyTimeline } from './components/JourneyTimeline';
import type { RoadmapApiResponse } from './types';
import './App.css';

// Use dynamic hostname for backend in development (e.g. 192.168.x.x or localhost)
// In production, use relative paths.
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : `http://${window.location.hostname}:8000`);

const ROLES = [
  "AI/ML Engineer", "Data Scientist", "Data Analyst",
  "Full Stack Developer", "Backend Developer", "Frontend Developer",
  "Mobile Developer", "DevOps Engineer", "Cybersecurity Analyst",
  "Game Developer", "Product Manager", "UI/UX Designer",
  "Data Engineer", "Cloud Architect", "Blockchain Developer",
  "IoT Engineer", "Systems Engineer", "Hardware Engineer",
  "Quantum Researcher",
];

function App() {
  const [muid, setMuid] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState(ROLES[2]);
  
  const [loading, setLoading] = useState(false);
  const [roadmapData, setRoadmapData] = useState<RoadmapApiResponse | null>(null);
  const [error, setError] = useState('');

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!muid.trim()) {
      setError("Please enter your MUID");
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await axios.post(`${API_BASE_URL}/generate_roadmap`, {
        muid: muid.trim(),
        name: name.trim() || muid.split('@')[0],
        role: role
      });
      
      if (response.data && response.data.success) {
        setRoadmapData(response.data);
      } else {
        const errorMsg = response.data 
          ? `Failed to generate roadmap. Backend returned: ${JSON.stringify(response.data).substring(0, 100)}` 
          : "Failed to generate roadmap. No data returned.";
        setError(errorMsg);
      }
    } catch (err: any) {
      console.error(err);
      if (err.message === "Network Error") {
        setError("Network error: Could not connect to the backend server. If you are on a different device, ensure the backend is running and accessible on the network.");
      } else {
        setError(err.response?.data?.detail || `Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-container">
          <div className="logo-icon-bg">
            <Rocket size={24} color="white" />
          </div>
          <div className="logo-text">
            <h1>ICRS</h1>
            <p>Intelligent Career Roadmap</p>
          </div>
        </div>
      </header>

      <main className="main-content">
        
        {/* Hero Section */}
        {!roadmapData && (
          <div className="hero-section animate-float">
            <div className="badge-powered-by">
              <span className="pulse-dot"></span>
              <span>Powered by Mulearn</span>
            </div>
            
            <h1 className="hero-title">
              Your personalised <span className="gradient-text">journey awaits</span>
            </h1>
            
            <p className="hero-subtitle">
              Enter your MUID and dream role to generate an ML-powered, week-by-week learning roadmap tailored exactly to your current skill level.
            </p>

            {/* Input Form */}
            <form onSubmit={handleGenerate} className="glass-card form-layout hero-form">
              <div className="form-bg-glow"></div>
              
              {error && (
                <div className="error-message">
                  {error}
                </div>
              )}

              <div className="form-group">
                <label>Mulearn ID (MUID)</label>
                <div className="input-icon-wrapper">
                  <div className="input-icon">
                    <User size={18} />
                  </div>
                  <input 
                    type="text" 
                    value={muid}
                    onChange={(e) => setMuid(e.target.value)}
                    className="input-field has-icon" 
                    placeholder="user@mulearn" 
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Display Name (Optional)</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-field" 
                  placeholder="Your Name" 
                />
              </div>

              <div className="form-group">
                <label>Dream Role</label>
                <div className="input-icon-wrapper">
                  <div className="input-icon">
                    <Briefcase size={18} />
                  </div>
                  <select 
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="input-field has-icon select-field"
                  >
                    {ROLES.map(r => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button 
                type="submit" 
                disabled={loading}
                className="btn-primary submit-btn"
              >
                {loading ? (
                  <div className="spinner"></div>
                ) : (
                  <>
                    Generate Roadmap
                    <ChevronRight size={18} className="btn-icon" />
                  </>
                )}
              </button>
            </form>
          </div>
        )}

        {/* Results Section */}
        {roadmapData && (
          <div className="results-section">
            
            <div className="results-header">
              <div className="results-title-group">
                <h2>
                  Roadmap for <span>{roadmapData.name}</span>
                </h2>
                <p>Targeting: <strong>{roadmapData.role}</strong></p>
              </div>
              
              <button 
                onClick={() => setRoadmapData(null)}
                className="btn-outline"
              >
                New Search
              </button>
            </div>

            {/* KPIs */}
            <div className="kpi-grid">
              <div className="stat-card">
                <div className="stat-value">{roadmapData.gap?.readiness_pct?.toFixed(0) || 0}%</div>
                <div className="stat-label">Readiness</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{roadmapData.roadmap?.roadmap_weeks?.length || 0}</div>
                <div className="stat-label">Weeks Planned</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">
                  {roadmapData.roadmap?.roadmap_weeks?.reduce((acc: number, w: any) => acc + w.tasks.length, 0) || 0}
                </div>
                <div className="stat-label">Total Tasks</div>
              </div>
              <div className="stat-card">
                <div className="tier-badge-container">
                  <span className={`badge ${roadmapData.gap?.career_gap_tier === 'CRITICAL' ? 'badge-red' : 'badge-orange'} tier-badge`}>
                    {roadmapData.gap?.career_gap_tier || 'UNKNOWN'}
                  </span>
                </div>
                <div className="stat-label">Gap Tier</div>
              </div>
            </div>

            {/* Journey Timeline */}
            <div className="timeline-wrapper">
              <div className="timeline-header">
                <h3>
                  Your Learning Journey
                  <div className="title-underline"></div>
                </h3>
              </div>
              
              <JourneyTimeline 
                data={roadmapData.roadmap} 
                dreamRole={roadmapData.role} 
                submittedTasks={roadmapData.submitted_tasks} 
              />
            </div>
            
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
