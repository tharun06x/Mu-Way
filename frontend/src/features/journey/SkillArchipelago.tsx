import React, { useState } from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { CheckCircle2, Lock, Star, ChevronRight, BrainCircuit } from 'lucide-react';
import type { RoadmapWeek, RoadmapTask } from '../../types';
import { TaskDetailDrawer } from './TaskDetailDrawer';

interface SkillArchipelagoProps {
  weeks: RoadmapWeek[];
  dreamRole: string;
}

const container: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.15 },
  },
};

const item: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', damping: 20, stiffness: 100 } },
};

const URGENCY_DOT: Record<string, string> = {
  CRITICAL: 'bg-red-400',
  MODERATE: 'bg-amber-400',
  MARGINAL: 'bg-blue-400',
  MET:      'bg-emerald-400',
  BRIDGE:   'bg-purple-400',
};

export const SkillArchipelago: React.FC<SkillArchipelagoProps> = ({ weeks, dreamRole }) => {
  const [selectedTask, setSelectedTask] = useState<RoadmapTask | null>(null);

  if (!weeks || weeks.length === 0) return null;

  // Group weeks into "Chapters" (every 4 weeks)
  const chapters: RoadmapWeek[][] = [];
  for (let i = 0; i < weeks.length; i += 4) {
    chapters.push(weeks.slice(i, i + 4));
  }

  const chapterTitles = [
    'The Fundamentals',
    'Architectural Core',
    'Advanced Paradigms',
    'The Capstone Expedition',
    'Mastery & Polish',
  ];

  return (
    <>
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="max-w-4xl mx-auto py-12 px-4"
      >
        <div className="mb-16 text-center space-y-4">
          <h2 className="font-serif text-4xl text-slate-100 tracking-tight">
            Your Expedition to {dreamRole}
          </h2>
          <p className="text-slate-400 max-w-lg mx-auto">
            The ML engine has chartered a course through {weeks.length} milestones.{' '}
            <span className="text-slate-500">Click any task to explore its details.</span>
          </p>
        </div>

        <div className="space-y-24">
          {chapters.map((chapterWeeks, cIdx) => (
            <motion.div key={cIdx} variants={item} className="relative">

              {/* Chapter Header */}
              <div className="flex items-center gap-4 mb-8">
                <div className="h-px bg-slate-800 flex-1" />
                <div className="flex items-center gap-3 px-4 py-1.5 rounded-full bg-slate-900 border border-slate-800">
                  <Star size={14} className={cIdx === 0 ? 'text-amber-400' : 'text-slate-500'} />
                  <span className="text-sm font-medium text-slate-300">
                    Chapter {cIdx + 1}: {chapterTitles[Math.min(cIdx, chapterTitles.length - 1)]}
                  </span>
                </div>
                <div className="h-px bg-slate-800 flex-1" />
              </div>

              {/* Chapter Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {chapterWeeks.map((week, wIdx) => {
                  const isCurrent = cIdx === 0 && wIdx === 0;

                  return (
                    <div
                      key={week.week}
                      className={`
                        relative p-6 rounded-2xl border transition-all duration-300
                        ${isCurrent
                          ? 'bg-slate-900/50 border-indigo-500/30 shadow-[0_0_30px_rgba(99,102,241,0.1)]'
                          : 'bg-slate-900/20 border-slate-800/50 hover:bg-slate-900/40'}
                      `}
                    >
                      <div className="flex justify-between items-start mb-6">
                        <div>
                          <div className="text-xs font-semibold tracking-wider text-slate-500 uppercase mb-1">
                            Milestone {week.week}
                          </div>
                          <h3 className="text-lg font-medium text-slate-200">
                            {week.tasks.length} Tasks · {Math.round(week.minutes_used / 60)}h
                          </h3>
                        </div>
                        <div className={`p-2 rounded-xl ${isCurrent ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-500'}`}>
                          {isCurrent ? <BrainCircuit size={20} /> : <Lock size={20} />}
                        </div>
                      </div>

                      <div className="space-y-2">
                        {week.tasks.slice(0, 3).map((task, tIdx) => (
                          <button
                            key={tIdx}
                            onClick={() => setSelectedTask(task)}
                            className="w-full group flex items-start gap-3 p-3 rounded-lg bg-slate-950/50 border border-transparent hover:border-indigo-500/30 hover:bg-slate-900/60 transition-all text-left cursor-pointer"
                          >
                            {/* Urgency dot */}
                            <div className="mt-1.5 flex-shrink-0">
                              <div className={`w-2 h-2 rounded-full ${URGENCY_DOT[task.urgency_tier] ?? 'bg-slate-600'}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-300 group-hover:text-slate-100 line-clamp-1 transition-colors">
                                {task.task_name}
                              </p>
                              {task.reason && (
                                <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                                  {task.reason}
                                </p>
                              )}
                            </div>
                            <CheckCircle2
                              size={15}
                              className="mt-0.5 flex-shrink-0 text-slate-700 group-hover:text-indigo-400 transition-colors"
                            />
                          </button>
                        ))}

                        {week.tasks.length > 3 && (
                          <button
                            onClick={() => setSelectedTask(week.tasks[3])}
                            className="w-full text-xs text-center text-slate-500 hover:text-slate-300 pt-2 font-medium transition-colors"
                          >
                            + {week.tasks.length - 3} more tasks
                          </button>
                        )}
                      </div>

                      {isCurrent && (
                        <button className="mt-6 w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(79,70,229,0.3)]">
                          Enter The Forge <ChevronRight size={16} />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-24 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-500 mb-4 shadow-[0_0_30px_rgba(245,158,11,0.15)]">
            <Star size={28} />
          </div>
          <h3 className="font-serif text-2xl text-slate-200">The Summit</h3>
          <p className="text-slate-400 mt-2">{dreamRole} Achieved</p>
        </div>
      </motion.div>

      {/* Task Detail Drawer — rendered outside the scrollable area */}
      <TaskDetailDrawer task={selectedTask} onClose={() => setSelectedTask(null)} />
    </>
  );
};
