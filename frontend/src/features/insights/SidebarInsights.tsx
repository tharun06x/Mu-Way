import React from 'react';
import { Target, Trophy, TrendingUp, ShieldAlert, Zap } from 'lucide-react';
import type { ProgressForecast, AchievementProfile, DecayProfile } from '../../types';

interface SidebarInsightsProps {
  forecast: ProgressForecast | null;
  achievements: AchievementProfile | null;
  decayProfile: DecayProfile | null;
}

export const SidebarInsights: React.FC<SidebarInsightsProps> = ({ 
  forecast, achievements, decayProfile
}) => {
  return (
    <div className="flex flex-col gap-6">
      
      {/* Forecast Card */}
      {forecast && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm relative overflow-hidden">
          {/* subtle background glow */}
          <div className="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl" />
          
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={16} className="text-indigo-400" />
            <h3 className="font-serif text-lg text-slate-100">The Path Ahead</h3>
          </div>
          
          <div className="flex items-baseline gap-2 mb-4">
            <span className="text-5xl font-light font-serif tracking-tighter text-white">
              {forecast.weeks_to_goal}
            </span>
            <span className="text-sm font-medium text-slate-400">weeks to {forecast.dream_role}</span>
          </div>
          
          <div className="p-3 rounded-xl bg-slate-800/50 border-l-2 border-indigo-500 text-sm text-slate-300 leading-relaxed mb-4">
            {forecast.message}
          </div>

          {forecast.adaptive_goal && (
            <div className="pt-4 border-t border-slate-800/80">
              <div className="flex items-start gap-2 text-xs text-slate-400 mb-2">
                <Target size={14} className="mt-0.5 text-slate-500" />
                <span>Target: <strong className="text-slate-200">{forecast.adaptive_goal.recommended_tasks} tasks</strong> ({forecast.adaptive_goal.recommended_hours}h)</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-slate-400">
                <Zap size={14} className="mt-0.5 text-amber-500" />
                <span>{forecast.adaptive_goal.motivation}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Mastery & Ranks */}
      {achievements && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <Trophy size={16} className="text-amber-500" />
            <h3 className="font-serif text-lg text-slate-100">Career Rank</h3>
          </div>

          <div className="flex items-center gap-4 mb-6">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-400 to-orange-600 flex flex-col items-center justify-center text-white shadow-lg shadow-orange-900/20">
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-80">Rank</span>
              <span className="text-lg font-bold leading-none">{achievements.level}</span>
            </div>
            <div>
              <div className="text-lg font-semibold text-slate-100">{achievements.level_title}</div>
              <div className="text-sm text-slate-400 font-medium">{achievements.xp} XP</div>
            </div>
          </div>

          {/* XP Progress Bar */}
          <div className="space-y-1.5 mb-6">
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-1000" 
                style={{ width: `${Math.min(100, (achievements.xp / (achievements.xp + achievements.xp_to_next_level)) * 100)}%` }} 
              />
            </div>
            <div className="text-xs text-right font-medium text-slate-500">
              {achievements.xp_to_next_level} XP to next rank
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-6">
            <div className="p-3 rounded-xl bg-slate-800/50 text-center border border-slate-800">
              <div className="text-xl font-bold text-slate-200 mb-0.5">{achievements.current_streak_days} 🔥</div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Day Streak</div>
            </div>
            <div className="p-3 rounded-xl bg-slate-800/50 text-center border border-slate-800">
              <div className="text-xl font-bold text-slate-200 mb-0.5">{achievements.total_approved} ✅</div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Tasks Done</div>
            </div>
          </div>

          {achievements.badges.filter(b => b.earned).length > 0 && (
            <div className="pt-4 border-t border-slate-800/80">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Earned Badges</div>
              <div className="flex flex-wrap gap-2">
                {achievements.badges.filter(b => b.earned).slice(0, 5).map(b => (
                  <div key={b.id} className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-lg hover:scale-110 hover:bg-slate-700 transition-all cursor-help" title={`${b.name}: ${b.description}`}>
                    {b.icon}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Rust Alerts (Decay) */}
      {decayProfile && decayProfile.rusty_domains.length > 0 && (
        <div className="p-5 rounded-2xl bg-red-950/20 border border-red-900/30">
          <div className="flex items-center gap-2 text-red-500 mb-2">
            <ShieldAlert size={16} />
            <h4 className="text-sm font-semibold">Skills Fading</h4>
          </div>
          <p className="text-xs text-slate-400 mb-3 leading-relaxed">
            The ML detected inactivity in these domains. Review recommended:
          </p>
          <div className="flex flex-wrap gap-2">
            {decayProfile.rusty_domains.map(domain => (
              <span key={domain} className="px-2 py-1 rounded-md bg-red-900/40 text-red-400 text-[11px] font-medium uppercase tracking-wider">
                {domain.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
