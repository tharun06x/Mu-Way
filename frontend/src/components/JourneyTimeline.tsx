import React, { useState } from 'react';
import {
  Trophy, Star, CheckCircle2, Clock, Code2, Shield,
  BrainCircuit, Database, Smartphone, Activity, Cpu,
  BarChart2, Layers, ChevronDown, ChevronUp, Calendar,
  Zap, Target, BookOpen, GitBranch
} from 'lucide-react';
import './JourneyTimeline.css';

interface Task {
  task_name: string;
  domain: string;
  difficulty_level: number;
  score: number;
  urgency_tier?: string;
  reason?: string;
  complexity?: string;
}

interface SubmittedTask {
  task_name: string;
  domain: string;
  difficulty_level: number;
  is_approved: number;
  submission_date: string;
}

interface Week {
  week: number;
  minutes_used: number;
  tasks: Task[];
}

interface RoadmapData {
  roadmap_weeks: Week[];
}

interface JourneyTimelineProps {
  data: RoadmapData;
  dreamRole: string;
  submittedTasks?: SubmittedTask[];
}

const DOMAIN_META: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  web_frontend: { icon: <Code2 size={14} />, color: '#38bdf8', label: 'Frontend' },
  web_backend:  { icon: <Code2 size={14} />, color: '#34d399', label: 'Backend' },
  ai:           { icon: <BrainCircuit size={14} />, color: '#a78bfa', label: 'AI/ML' },
  genai:        { icon: <BrainCircuit size={14} />, color: '#c084fc', label: 'GenAI' },
  data_science: { icon: <BarChart2 size={14} />, color: '#fb923c', label: 'Data Science' },
  data_analytics:{ icon: <BarChart2 size={14} />, color: '#fbbf24', label: 'Analytics' },
  data_eng:     { icon: <Database size={14} />, color: '#60a5fa', label: 'Data Eng' },
  mobile:       { icon: <Smartphone size={14} />, color: '#4ade80', label: 'Mobile' },
  devops:       { icon: <Layers size={14} />, color: '#f87171', label: 'DevOps' },
  cybersec:     { icon: <Shield size={14} />, color: '#e879f9', label: 'Cybersec' },
  dsa:          { icon: <GitBranch size={14} />, color: '#93c5fd', label: 'DSA' },
  cloud:        { icon: <Cpu size={14} />, color: '#67e8f9', label: 'Cloud' },
};

const getDomainMeta = (domain: string) => {
  const key = domain.toLowerCase().replace(/-/g, '_');
  return DOMAIN_META[key] ?? { icon: <Activity size={14} />, color: '#94a3b8', label: domain };
};

const DIFF_META = [
  { label: 'Beginner',     bg: 'rgba(52,211,153,0.12)', color: '#34d399', border: 'rgba(52,211,153,0.3)' },
  { label: 'Intermediate', bg: 'rgba(96,165,250,0.12)', color: '#60a5fa', border: 'rgba(96,165,250,0.3)' },
  { label: 'Advanced',     bg: 'rgba(251,146,60,0.12)', color: '#fb923c', border: 'rgba(251,146,60,0.3)' },
  { label: 'Expert',       bg: 'rgba(248,113,113,0.12)', color: '#f87171', border: 'rgba(248,113,113,0.3)' },
];

const getDiff = (level: number) => DIFF_META[Math.min(Math.round(level) - 1, 3)] ?? DIFF_META[1];

const formatMinutes = (mins: number) => {
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
};

const scoreToPercent = (score: number) => `${Math.round(score * 100)}%`;

// ── Collapsed Past Submissions row ──────────────────────────────────────────
const PastSubmissionsNode: React.FC<{ tasks: SubmittedTask[] }> = ({ tasks }) => {
  const [expanded, setExpanded] = useState(false);
  const approved = tasks.filter(t => t.is_approved === 1).length;
  const pending  = tasks.length - approved;

  return (
    <div className="tl-node past-node">
      <div className="tl-spine-dot done"><CheckCircle2 size={16} /></div>
      <div className="tl-card past-card">
        {/* Header — always visible */}
        <div className="past-header" onClick={() => setExpanded(e => !e)}>
          <div className="past-header-left">
            <span className="past-title">Completed Submissions</span>
            <div className="past-stats">
              <span className="past-stat approved"><CheckCircle2 size={12} /> {approved} approved</span>
              {pending > 0 && <span className="past-stat pending"><Clock size={12} /> {pending} pending</span>}
              <span className="past-stat total"><BookOpen size={12} /> {tasks.length} total</span>
            </div>
          </div>
          <button className="expand-toggle">{expanded ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}</button>
        </div>

        {/* Expandable task list */}
        {expanded && (
          <div className="past-task-list">
            {tasks.map((task, i) => {
              const dm = getDomainMeta(task.domain);
              const diff = getDiff(task.difficulty_level);
              const dateStr = task.submission_date && task.submission_date !== 'NaT'
                ? new Date(task.submission_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
                : null;
              return (
                <div key={i} className="past-task-row">
                  <div className="past-task-status">
                    {task.is_approved === 1
                      ? <CheckCircle2 size={14} color="#34d399" />
                      : <Clock size={14} color="#fbbf24" />}
                  </div>
                  <div className="past-task-body">
                    <span className="past-task-name">{task.task_name}</span>
                    <div className="past-task-meta">
                      <span className="domain-chip" style={{ color: dm.color, borderColor: `${dm.color}40`, background: `${dm.color}12` }}>
                        {dm.icon} {dm.label}
                      </span>
                      <span className="diff-chip" style={{ color: diff.color, borderColor: diff.border, background: diff.bg }}>
                        {diff.label}
                      </span>
                      {dateStr && <span className="date-chip"><Calendar size={11}/> {dateStr}</span>}
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

// ── Main component ───────────────────────────────────────────────────────────
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
        <div className="tl-summary-item"><Layers size={14}/> {weeks.length} weeks</div>
        <div className="tl-summary-item"><Target size={14}/> {totalTasks} tasks</div>
        <div className="tl-summary-item"><Clock size={14}/> {formatMinutes(totalMins)} total</div>
        <div className="tl-summary-item"><Zap size={14}/> {dreamRole}</div>
      </div>

      {/* Vertical spine */}
      <div className="tl-spine" />

      {/* Journey start */}
      <div className="tl-start-label">
        <Star size={13} /> Journey Begins
      </div>

      {/* Past submissions node */}
      {submittedTasks && submittedTasks.length > 0 && (
        <PastSubmissionsNode tasks={submittedTasks} />
      )}

      {/* Week nodes */}
      {weeks.map((week, wIdx) => {
        const isFirst = wIdx === 0;
        return (
          <div key={week.week} className={`tl-node week-node ${isFirst ? 'first-week' : ''}`}>
            <div className={`tl-spine-dot ${isFirst ? 'active' : 'idle'}`}>
              {isFirst ? <Star size={14} /> : <span className="dot-num">{week.week}</span>}
            </div>
            <div className="tl-card week-card">
              {/* Week header */}
              <div className="week-header">
                <div className="week-header-left">
                  <span className="week-label">Week {week.week}</span>
                  {isFirst && <span className="week-badge-now">▶ Up Next</span>}
                </div>
                <div className="week-meta-row">
                  <span className="week-meta-item"><Clock size={12}/> {formatMinutes(week.minutes_used)}</span>
                  <span className="week-meta-item"><Target size={12}/> {week.tasks.length} task{week.tasks.length !== 1 ? 's' : ''}</span>
                </div>
              </div>

              {/* Tasks */}
              <div className="week-task-list">
                {week.tasks.map((task, tIdx) => {
                  const dm   = getDomainMeta(task.domain);
                  const diff = getDiff(task.difficulty_level);
                  const score = task.score ?? 0;

                  return (
                    <div key={tIdx} className="week-task-row">
                      {/* Left accent bar coloured by domain */}
                      <div className="task-accent" style={{ background: dm.color }} />

                      <div className="task-body">
                        {/* Task name row */}
                        <div className="task-name-row">
                          <span className="task-icon-wrap" style={{ color: dm.color }}>{dm.icon}</span>
                          <span className="task-name-text">{task.task_name}</span>
                        </div>

                        {/* Meta chips */}
                        <div className="task-chips">
                          <span className="domain-chip" style={{ color: dm.color, borderColor: `${dm.color}40`, background: `${dm.color}12` }}>
                            {dm.label}
                          </span>
                          <span className="diff-chip" style={{ color: diff.color, borderColor: diff.border, background: diff.bg }}>
                            {diff.label}
                          </span>
                          {task.urgency_tier && (
                            <span className="urgency-chip">{task.urgency_tier}</span>
                          )}
                          {task.complexity && (
                            <span className="complexity-chip">Complexity: {task.complexity}</span>
                          )}
                        </div>

                        {/* Score bar + reason */}
                        <div className="task-score-row">
                          <div className="score-bar-wrap">
                            <div className="score-bar-track">
                              <div
                                className="score-bar-fill"
                                style={{ width: scoreToPercent(score), background: dm.color }}
                              />
                            </div>
                            <span className="score-label">ML Score {scoreToPercent(score)}</span>
                          </div>
                          {task.reason && (
                            <span className="task-reason">{task.reason}</span>
                          )}
                        </div>
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
        <div className="tl-end-icon"><Trophy size={28} color="#fbbf24" /></div>
        <div className="tl-end-body">
          <span className="tl-end-label">Dream Role Achieved</span>
          <span className="tl-end-role">{dreamRole}</span>
        </div>
      </div>
    </div>
  );
};
