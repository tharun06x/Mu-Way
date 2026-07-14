import React, { useState } from 'react';
import axios from 'axios';
import { Rocket, User, Briefcase, ChevronRight, Compass } from 'lucide-react';
import { JourneyTimeline } from './components/JourneyTimeline';
import { ProgressInsights } from './components/ProgressInsights';
import type { RoadmapApiResponse } from './types';
import './App.css';

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
        setError("Network error: Could not connect to the backend server.");
      } else {
        setError(err.response?.data?.detail || `Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* ── Global Header ── */}
      <header className="app-header">
        <div className="logo-container">
          <div className="logo-icon-bg">
            <Rocket size={16} color="white" />
          </div>
          <div className="logo-text">
            <h1>ICRS</h1>
            <p>Intelligent Career Roadmap</p>
          </div>
        </div>
      </header>

      <main className="main-content">
        
        {/* ── Setup / Hero State ── */}
        {!roadmapData && (
          <div className="hero-section animate-fade-in">
            <div className="badge-powered-by">
              <span className="pulse-dot"></span>
              <span>Powered by Mulearn ML</span>
            </div>
            
            <h1 className="hero-title">
              Your personalised <br />
              <em className="editorial">learning journey</em>
            </h1>
            
            <p className="hero-subtitle">
              Enter your MUID and dream role. We'll analyze your past tasks, predict your learning velocity, and generate a tailored roadmap to get you there.
            </p>

            <form onSubmit={handleGenerate} className="setup-form">
              {error && (
                <div className="error-message">
                  {error}
                </div>
              )}

              <div className="form-group">
                <label>Mulearn ID (MUID)</label>
                <div className="input-icon-wrapper">
                  <div className="input-icon"><User size={16} /></div>
                  <input 
                    type="text" 
                    value={muid}
                    onChange={(e) => setMuid(e.target.value)}
                    className="input-field has-icon" 
                    placeholder="e.g. user@mulearn" 
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
                  <div className="input-icon"><Briefcase size={16} /></div>
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

              <button type="submit" disabled={loading} className="btn-primary submit-btn">
                {loading ? (
                  <div className="spinner"></div>
                ) : (
                  <>Begin Journey <ChevronRight size={16} /></>
                )}
              </button>
            </form>
          </div>
        )}

        {/* ── Dashboard Layout ── */}
        {roadmapData && (
          <div className="dashboard-layout animate-fade-in">
            
            {/* Left Sidebar (Context) */}
            <aside className="sidebar">
              <div className="card profile-card">
                <h2>{roadmapData.name}</h2>
                <div className="role-target">Target: <strong>{roadmapData.role}</strong></div>
                <div className="action-row">
                  <button onClick={() => setRoadmapData(null)} className="btn-secondary w-full">
                    Change Role
                  </button>
                </div>
              </div>

              {/* Progress Insights Component */}
              <ProgressInsights 
                forecast={roadmapData.forecast} 
                achievements={roadmapData.achievements} 
                decayProfile={roadmapData.decay_profile} 
                gapData={roadmapData.gap} 
              />
            </aside>

            {/* Right Main Area (Journey) */}
            <section className="journey-view">
              <div className="journey-header">
                <Compass size={24} className="text-brand mx-auto mb-2" />
                <h3 className="editorial">Your Learning Map</h3>
                <p>Follow the milestones to reach your goal.</p>
              </div>

              <JourneyTimeline 
                data={roadmapData.roadmap} 
                dreamRole={roadmapData.role} 
                submittedTasks={roadmapData.submitted_tasks} 
              />
            </section>
            
          </div>
        )}

      </main>
    </div>
  );
}

export default App;
