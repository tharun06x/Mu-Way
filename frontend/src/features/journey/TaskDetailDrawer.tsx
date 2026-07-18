import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { X, BrainCircuit, AlertTriangle, TrendingUp, Minus, Star } from 'lucide-react';
import type { RoadmapTask } from '../../types';

interface TaskDetailDrawerProps {
  task: RoadmapTask | null;
  onClose: () => void;
}

const URGENCY_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  CRITICAL:     { label: 'Critical Gap',  color: 'text-red-400 bg-red-400/10 border-red-400/20',    icon: <AlertTriangle size={13} /> },
  MODERATE:     { label: 'Moderate Gap',  color: 'text-amber-400 bg-amber-400/10 border-amber-400/20', icon: <TrendingUp size={13} /> },
  MARGINAL:     { label: 'Marginal Gap',  color: 'text-blue-400 bg-blue-400/10 border-blue-400/20',  icon: <Minus size={13} /> },
  MET:          { label: 'Gap Met',       color: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20', icon: <Star size={13} /> },
  BRIDGE:       { label: 'Bridge Task',   color: 'text-purple-400 bg-purple-400/10 border-purple-400/20', icon: <BrainCircuit size={13} /> },
  REENGAGEMENT: { label: 'Re-engagement', color: 'text-slate-400 bg-slate-400/10 border-slate-400/20', icon: <Minus size={13} /> },
};

const DIFF_LABEL: Record<number, string> = {
  1: 'Beginner', 2: 'Intermediate', 3: 'Advanced', 4: 'Expert',
};

function getDiffColor(level: number): string {
  if (level <= 1) return 'text-emerald-400';
  if (level <= 2) return 'text-blue-400';
  if (level <= 3) return 'text-amber-400';
  return 'text-red-400';
}

export const TaskDetailDrawer: React.FC<TaskDetailDrawerProps> = ({ task, onClose }) => {
  // Close on ESC key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [onClose]);

  const urgency = task ? (URGENCY_CONFIG[task.urgency_tier] ?? URGENCY_CONFIG['MARGINAL']) : null;
  const diffLabel = task ? (DIFF_LABEL[Math.round(task.difficulty_level)] ?? 'Intermediate') : '';

  return (
    <AnimatePresence>
      {task && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.aside
            key="drawer"
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 220 }}
            className="fixed right-0 top-0 h-full z-50 w-full max-w-lg bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-start justify-between p-6 border-b border-slate-800 flex-shrink-0">
              <div className="flex-1 pr-4">
                <div className="flex items-center gap-2 mb-2">
                  {urgency && (
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${urgency.color}`}>
                      {urgency.icon}
                      {urgency.label}
                    </span>
                  )}
                  <span className={`text-xs font-medium ${getDiffColor(task.difficulty_level)}`}>
                    {diffLabel}
                  </span>
                </div>
                <h2 className="text-xl font-semibold text-slate-100 leading-snug">
                  {task.task_name}
                </h2>
                <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                  <span className="capitalize">{task.domain.replace(/_/g, ' ')}</span>
                  <span>·</span>
                  <span>Score {task.score.toFixed(3)}</span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="flex-shrink-0 p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                aria-label="Close panel"
              >
                <X size={20} />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-6">

              {/* ML Reason */}
              {task.reason && (
                <div className="mb-6 p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/15">
                  <p className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-1.5">
                    Why this task?
                  </p>
                  <p className="text-sm text-slate-300 leading-relaxed">{task.reason}</p>
                </div>
              )}

              {/* Markdown Detail */}
              {task.markdown_detail ? (
                <div className="prose prose-invert prose-sm max-w-none
                  prose-headings:text-slate-200 prose-headings:font-semibold
                  prose-p:text-slate-300 prose-p:leading-relaxed
                  prose-strong:text-slate-200
                  prose-code:text-indigo-300 prose-code:bg-indigo-500/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono
                  prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800 prose-pre:rounded-xl
                  prose-ul:text-slate-300 prose-ol:text-slate-300
                  prose-li:marker:text-indigo-400
                  prose-a:text-indigo-400 prose-a:no-underline hover:prose-a:underline
                  prose-blockquote:border-indigo-500/30 prose-blockquote:text-slate-400
                  prose-hr:border-slate-800">
                  <ReactMarkdown>{task.markdown_detail}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <BrainCircuit size={36} className="text-slate-700 mb-4" />
                  <p className="text-slate-500 text-sm">
                    No detailed description available for this task yet.
                  </p>
                  <p className="text-slate-600 text-xs mt-1">
                    Populate the <code className="text-indigo-500">markdown_detail</code> field in the TaskCatalog to add one.
                  </p>
                </div>
              )}

              {/* Learning Resources */}
              {task.resources && task.resources.length > 0 && (
                <div className="mt-8">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                    Learning Resources
                  </h3>
                  <div className="flex flex-col gap-2">
                    {task.resources.map((r, i) => (
                      <a
                        key={i}
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50 hover:border-indigo-500/30 hover:bg-slate-800 transition-all group"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-200 group-hover:text-indigo-300 transition-colors truncate">
                            {r.title}
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {r.platform} · {r.is_free ? 'Free' : 'Paid'}
                          </p>
                        </div>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400 capitalize">
                          {r.type}
                        </span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};
