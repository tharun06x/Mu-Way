import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Compass, User, Briefcase, ChevronRight, LayoutGrid } from 'lucide-react';
import { api } from './api/client';
import { useAppStore } from './store/useAppStore';
import { SkillArchipelago } from './features/journey/SkillArchipelago';
import { SidebarInsights } from './features/insights/SidebarInsights';

const ROLES = [
  "AI/ML Engineer", "Data Scientist", "Data Analyst",
  "Full Stack Developer", "Backend Developer", "Frontend Developer",
  "Mobile Developer", "DevOps Engineer", "Cybersecurity Analyst",
  "Game Developer", "Product Manager", "UI/UX Designer",
  "Data Engineer", "Cloud Architect", "Blockchain Developer",
  "IoT Engineer", "Systems Engineer"
];

function App() {
  const { activeMuid, activeRole, setSession, clearSession } = useAppStore();
  
  const [formMuid, setFormMuid] = useState(activeMuid || '');
  const [formName, setFormName] = useState('');
  const [formRole, setFormRole] = useState(activeRole || ROLES[3]); // Default to Full Stack

  // Fetch roadmap data using TanStack Query
  const { data, isLoading, error } = useQuery({
    queryKey: ['roadmap', activeMuid, activeRole],
    queryFn: () => api.generateRoadmap(activeMuid!, formName || activeMuid!.split('@')[0], activeRole!),
    enabled: !!activeMuid && !!activeRole, // Only run when we have a session
    staleTime: 1000 * 60 * 5, // Cache for 5 mins
  });

  const handleBeginJourney = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formMuid.trim()) return;
    setSession(formMuid.trim(), formRole);
  };

  // ── View: Setup / Hero ──
  if (!activeMuid) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col items-center justify-center p-4">
        
        {/* Subtle background effects */}
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />
        
        <div className="relative z-10 w-full max-w-lg">
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl mb-6">
              <Compass className="text-indigo-400" size={24} />
            </div>
            <h1 className="text-4xl md:text-5xl font-serif text-white tracking-tight mb-4">
              Welcome to <span className="text-indigo-400 font-medium">muWay</span>
            </h1>
            <p className="text-slate-400 text-lg">
              Your intelligent journey to the career you dream of.
            </p>
          </div>

          <form onSubmit={handleBeginJourney} className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 p-8 rounded-3xl shadow-2xl">
            
            <div className="space-y-6">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">muLearn ID</label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input 
                    type="text" 
                    required
                    value={formMuid}
                    onChange={(e) => setFormMuid(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                    placeholder="e.g. alex@mulearn"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Destination Role</label>
                <div className="relative">
                  <Briefcase className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <select 
                    value={formRole}
                    onChange={(e) => setFormRole(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-slate-200 appearance-none focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all cursor-pointer"
                  >
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
              </div>

              <button type="submit" className="w-full mt-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl py-3.5 font-medium flex items-center justify-center gap-2 transition-colors shadow-lg shadow-indigo-900/20">
                Begin Expedition <ChevronRight size={18} />
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // ── View: Loading ──
  if (isLoading || !data) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-400 space-y-6">
        <div className="w-12 h-12 border-4 border-slate-800 border-t-indigo-500 rounded-full animate-spin" />
        <div className="font-serif text-xl animate-pulse">Charting your course...</div>
      </div>
    );
  }

  // ── View: The Journey (Main Dashboard) ──
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30">
      
      {/* Top Navigation */}
      <nav className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-900/20">
              <Compass size={16} className="text-white" />
            </div>
            <span className="font-serif font-medium text-lg tracking-tight">muWay</span>
          </div>

          <div className="flex items-center gap-6 text-sm font-medium text-slate-400">
            <button className="text-slate-200 flex items-center gap-2"><Compass size={16}/> Journey</button>
            <button className="hover:text-slate-200 flex items-center gap-2 transition-colors"><LayoutGrid size={16}/> Archive</button>
            <button onClick={clearSession} className="px-4 py-1.5 rounded-full bg-slate-900 border border-slate-800 hover:bg-slate-800 transition-colors">
              Exit
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content Layout */}
      <main className="max-w-7xl mx-auto px-4 py-8 flex flex-col lg:flex-row gap-8 items-start">
        
        {/* Left Sidebar (Sticky Context) */}
        <aside className="w-full lg:w-80 flex-shrink-0 lg:sticky lg:top-24 space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900/50 border border-slate-800/50">
            <h2 className="text-xl font-serif text-slate-100 mb-1">{data.name}</h2>
            <div className="text-sm text-slate-400">Targeting: <span className="font-medium text-slate-300">{data.role}</span></div>
          </div>
          
          <SidebarInsights 
            forecast={data.forecast} 
            achievements={data.achievements} 
            decayProfile={data.decay_profile} 
            gapData={data.gap} 
          />
        </aside>

        {/* Right Area (The Journey Map) */}
        <section className="flex-1 w-full pb-32">
          {error ? (
            <div className="p-6 rounded-2xl bg-red-950/20 border border-red-900/30 text-red-400 text-center">
              Failed to load journey. Please try again.
            </div>
          ) : (
            <SkillArchipelago weeks={data.roadmap?.roadmap_weeks || []} dreamRole={data.role} />
          )}
        </section>

      </main>
    </div>
  );
}

export default App;
