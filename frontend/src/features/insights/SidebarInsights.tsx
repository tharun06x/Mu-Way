import React from 'react';
import { Target, TrendingUp, ShieldAlert, Zap } from 'lucide-react';
import type { ProgressForecast, DecayProfile } from '../../types';

interface SidebarInsightsProps {
  forecast: ProgressForecast | null;
  decayProfile: DecayProfile | null;
}

export const SidebarInsights: React.FC<SidebarInsightsProps> = ({
  forecast, decayProfile
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
