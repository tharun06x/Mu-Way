import React, { useState } from 'react';
import {
  Trophy, Star, CheckCircle2, Clock, Code2, Shield,
  BrainCircuit, Database, Smartphone, Activity, Cpu,
  BarChart2, Layers, ChevronDown, ChevronUp, Calendar,
  Zap, Target, BookOpen, GitBranch, Youtube, MonitorPlay, 
  FileText, ExternalLink
} from 'lucide-react';
import './JourneyTimeline.css';
import type { RoadmapTask, RoadmapWeek, SubmittedTask, TaskResource } from '../types';

interface RoadmapData {
  roadmap_weeks: RoadmapWeek[];
}

interface JourneyTimelineProps {
  data: RoadmapData;
  dreamRole: string;
  submittedTasks?: SubmittedTask[];
}

const DOMAIN_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  web_frontend: { icon: <Code2 size={16} />, color: '#3b82f6', label: 'Frontend' },
  web_backend:  { icon: <Code2 size={16} />, color: '#059669', label: 'Backend' },
  ai:           { icon: <BrainCircuit size={16} />, color: '#7c3aed', label: 'AI/ML' },
  genai:        { icon: <BrainCircuit size={16} />, color: '#9333ea', label: 'GenAI' },
  data_science: { icon: <BarChart2 size={16} />, color: '#ea580c', label: 'Data Science' },
  data_analytics:{ icon: <BarChart2 size={16} />, color: '#d97706', label: 'Analytics' },
  data_eng:     { icon: <Database size={16} />, color: '#2563eb', label: 'Data Eng' },
  mobile:       { icon: <Smartphone size={16} />, color: '#16a34a', label: 'Mobile' },
  devops:       { icon: <Layers size={16} />, color: '#dc2626', label: 'DevOps' },
  cybersec:     { icon: <Shield size={16} />, color: '#c026d3', label: 'Cybersec' },
  dsa:          { icon: <GitBranch size={16} />, color: '#0284c7', label: 'DSA' },
  cloud:        { icon: <Cpu size={16} />, color: '#0891b2', label: 'Cloud' },
};

const getDomainMeta = (domain: string) => {
  const key = domain.toLowerCase().replace(/-/g, '_');
  return DOMAIN_META[key] ?? { icon: <Activity size={16} />, color: '#64748b', label: domain };
};

const DIFF_META = [
  { label: 'Beginner',     bg: 'rgba(5, 150, 105, 0.1)', color: '#059669' },
  { label: 'Intermediate', bg: 'rgba(37, 99, 235, 0.1)', color: '#2563eb' },
  { label: 'Advanced',     bg: 'rgba(234, 88, 12, 0.1)', color: '#ea580c' },
  { label: 'Expert',       bg: 'rgba(220, 38, 38, 0.1)',  color: '#dc2626' },
];

const getDiff = (level: number) => DIFF_META[Math.min(Math.max(Math.round(level) - 1, 0), 3)] ?? DIFF_META[1];

const formatMinutes = (mins: number) => {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
};

// ── Resource Link Component ──
const ResourceButton: React.FC<{ resource: TaskResource }> = ({ resource }) => {
  let Icon = ExternalLink;
  let typeClass = '';
  
  if (resource.platform.toLowerCase().includes('youtube')) {
    Icon = Youtube;
    typeClass = 'platform-youtube';
  } else if (resource.platform.toLowerCase().includes('coursera')) {
    Icon = MonitorPlay;
    typeClass = 'platform-coursera';
  } else if (resource.type === 'docs') {
    Icon = FileText;
    typeClass = 'platform-docs';
  }

  return (
    <a 
      href={resource.url} 
      target="_blank" 
      rel="noopener noreferrer" 
      className={`resource-btn ${typeClass}`}
    >
      <Icon size={12} />
      {resource.platform}
    </a>
  );
};

// ── Collapsed Past Submissions row ──
const PastSubmissionsNode: React.FC<{ tasks: SubmittedTask[] }> = ({ tasks }) => {
  const [expanded, setExpanded] = useState(false);
  const approved = tasks.filter(t => t.is_approved === 1).length;
  const pending  = tasks.length - approved;

  return (
    <div className="tl-node">
      <div className="tl-spine-dot done"><CheckCircle2 size={16} /></div>
      <div className="tl-card">
        <div className="past-header" onClick={() => setExpanded(e => !e)}>
          <div>
            <span className="past-title">Completed Foundation</span>
            <div className="past-stats">
              <span className="past-stat"><CheckCircle2 size={12} className="text-green-600"/> {approved} approved</span>
              {pending > 0 && <span className="past-stat"><Clock size={12} className="text-orange-500"/> {pending} pending</span>}
            </div>
          </div>
          <button className="expand-toggle">{expanded ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}</button>
        </div>

        {expanded && (
          <div className="past-task-list">
            {tasks.map((task, i) => {
              const dm = getDomainMeta(task.domain);
              const diff = getDiff(task.difficulty_level);
              return (
                <div key={i} className="past-task-row">
                  {task.is_approved === 1 ? <CheckCircle2 size={16} color="#059669" /> : <Clock size={16} color="#ea580c" />}
                  <div>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500 }}>{task.task_name}</div>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                      <span className="badge" style={{ color: dm.color, background: `${dm.color}15` }}>{dm.label}</span>
                      <span className="badge" style={{ color: diff.color, background: diff.bg }}>{diff.label}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

// ── Main component ──
export const JourneyTimeline: React.FC<JourneyTimelineProps> = ({ data, dreamRole, submittedTasks }) => {
  if (!data || !data.roadmap_weeks || data.roadmap_weeks.length === 0) {
    return <div className="no-data">No roadmap tasks available to display.</div>;
  }

  const weeks = data.roadmap_weeks;
  const totalTasks = weeks.reduce((sum, w) => sum + w.tasks.length, 0);
  const totalMins  = weeks.reduce((sum, w) => sum + w.minutes_used, 0);

  return (
    <div className="tl-root">
      
      {/* Summary bar */}
      <div className="tl-summary">
        <div className="tl-summary-item"><Layers size={16}/> {weeks.length} Weeks</div>
        <div className="tl-summary-item"><Target size={16}/> {totalTasks} Tasks</div>
        <div className="tl-summary-item"><Clock size={16}/> {formatMinutes(totalMins)}</div>
      </div>

      {/* Past submissions node */}
      {submittedTasks && submittedTasks.length > 0 && (
        <PastSubmissionsNode tasks={submittedTasks} />
      )}

      {/* Week nodes */}
      {weeks.map((week, wIdx) => {
        const isFirst = wIdx === 0;
        return (
          <div key={week.week} className="tl-node">
            <div className={`tl-spine-dot ${isFirst ? 'active' : 'idle'}`}>
              {isFirst ? <Star size={14} /> : week.week}
            </div>
            
            <div className="tl-card">
              <div className="week-header">
                <div>
                  <span className="week-label">Week {week.week}</span>
                  {isFirst && <span className="week-badge-now">▶ Up Next</span>}
                </div>
                <div className="week-meta-row">
                  <span><Clock size={14}/> {formatMinutes(week.minutes_used)}</span>
                  <span><Target size={14}/> {week.tasks.length} tasks</span>
                </div>
              </div>

              <div className="week-task-list">
                {week.tasks.map((task, tIdx) => {
                  const dm = getDomainMeta(task.domain);
                  const diff = getDiff(task.difficulty_level);

                  return (
                    <div key={tIdx} className="task-card">
                      <div className="task-header">
                        <div className="task-title-group">
                          <div className="task-icon" style={{ background: `${dm.color}15`, color: dm.color }}>
                            {dm.icon}
                          </div>
                          <h4 className="task-name">{task.task_name}</h4>
                        </div>
                        <div className="task-meta-chips">
                          <span className="badge" style={{ color: diff.color, background: diff.bg }}>
                            {diff.label}
                          </span>
                          {task.urgency_tier === 'CRITICAL' && (
                            <span className="badge badge-red">Critical Focus</span>
                          )}
                        </div>
                      </div>
                      
                      <div className="task-body">
                        {task.reason && (
                          <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                            {task.reason}
                          </div>
                        )}

                        {/* Enrichment Resources */}
                        {task.resources && task.resources.length > 0 && (
                          <div className="task-resources">
                            {task.resources.map((res, i) => (
                              <ResourceButton key={i} resource={res} />
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );
      })}

      {/* Dream role end node */}
      <div className="tl-end">
        <div className="tl-end-icon"><Trophy size={28} color="#ea580c" /></div>
        <div className="tl-end-label">Goal Achieved</div>
        <div className="tl-end-role">{dreamRole}</div>
      </div>
      
    </div>
  );
};
