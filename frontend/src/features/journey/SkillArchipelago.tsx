import React from 'react';
import { motion } from 'framer-motion';
import type { Variants } from 'framer-motion';
import { CheckCircle2, Lock, Star, ChevronRight, BrainCircuit } from 'lucide-react';
import type { RoadmapWeek } from '../../types';

interface SkillArchipelagoProps {
  weeks: RoadmapWeek[];
  dreamRole: string;
}

const container: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  }
};

const item: Variants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', damping: 20, stiffness: 100 } }
};

export const SkillArchipelago: React.FC<SkillArchipelagoProps> = ({ weeks, dreamRole }) => {
  if (!weeks || weeks.length === 0) return null;

  // Group weeks into "Chapters" (every 4 weeks is a new chapter/region)
  const chapters = [];
  for (let i = 0; i < weeks.length; i += 4) {
    chapters.push(weeks.slice(i, i + 4));
  }

  const chapterTitles = [
    "The Fundamentals",
    "Architectural Core",
    "Advanced Paradigms",
    "The Capstone Expedition",
    "Mastery & Polish"
  ];

  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="max-w-4xl mx-auto py-12 px-4"
    >
      <div className="mb-16 text-center space-y-4">
        <h2 className="font-serif text-4xl text-slate-100 tracking-tight">Your Expedition to {dreamRole}</h2>
        <p className="text-slate-400 max-w-lg mx-auto">
          The ML engine has chartered a course through {weeks.length} milestones. Complete tasks to clear the fog and unlock new regions.
        </p>
      </div>

      <div className="space-y-24">
        {chapters.map((chapterWeeks, cIdx) => (
          <motion.div key={cIdx} variants={item} className="relative">
            
            {/* Chapter Header */}
            <div className="flex items-center gap-4 mb-8">
              <div className="h-px bg-slate-800 flex-1" />
              <div className="flex items-center gap-3 px-4 py-1.5 rounded-full bg-slate-900 border border-slate-800">
                <Star size={14} className={cIdx === 0 ? "text-amber-400" : "text-slate-500"} />
                <span className="text-sm font-medium text-slate-300">
                  Chapter {cIdx + 1}: {chapterTitles[Math.min(cIdx, chapterTitles.length - 1)]}
                </span>
              </div>
              <div className="h-px bg-slate-800 flex-1" />
            </div>

            {/* Chapter Grid (The Islands) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {chapterWeeks.map((week, wIdx) => {
                // First week is always unlocked. Others might be "locked" visually if we were tracking live completion state.
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
                          {week.tasks.length} Tasks • {Math.round(week.minutes_used / 60)}h
                        </h3>
                      </div>
                      
                      <div className={`p-2 rounded-xl ${isCurrent ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-500'}`}>
                        {isCurrent ? <BrainCircuit size={20} /> : <Lock size={20} />}
                      </div>
                    </div>

                    <div className="space-y-3">
                      {week.tasks.slice(0, 3).map((task, tIdx) => (
                        <div key={tIdx} className="group flex items-start gap-3 p-3 rounded-lg bg-slate-950/50 border border-transparent hover:border-slate-800 transition-colors">
                          <div className="mt-0.5 text-slate-600 group-hover:text-slate-400">
                            <CheckCircle2 size={16} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-slate-300 group-hover:text-slate-200 line-clamp-1">
                              {task.task_name}
                            </p>
                            {task.reason && (
                              <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                                {task.reason}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                      {week.tasks.length > 3 && (
                        <div className="text-xs text-center text-slate-500 pt-2 font-medium">
                          + {week.tasks.length - 3} more tasks
                        </div>
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
  );
};
