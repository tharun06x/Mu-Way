import React from 'react';
import { Target, Clock, Trophy, Zap, AlertCircle, TrendingUp, Star, ShieldAlert } from 'lucide-react';
import type { ProgressForecast, AchievementProfile, DecayProfile, GapData } from '../types';
import './ProgressInsights.css';

interface ProgressInsightsProps {
  forecast: ProgressForecast | null;
  achievements: AchievementProfile | null;
  decayProfile: DecayProfile | null;
  gapData: GapData | null;
}

export const ProgressInsights: React.FC<ProgressInsightsProps> = ({ 
  forecast, achievements, decayProfile, gapData 
}) => {
  return (
    <div className="insights-container">
      
      {/* ── Progress Forecaster ── */}
      {forecast && (
        <div className="card insight-card">
          <div className="insight-header">
            <TrendingUp size={18} className="text-brand" />
            <h3 className="editorial">The Path Ahead</h3>
          </div>
          
          <div className="eta-display">
            <span className="eta-number">{forecast.weeks_to_goal}</span>
            <span className="eta-label">weeks to {forecast.dream_role}</span>
          </div>
          
          <div className="insight-message">
            {forecast.message}
          </div>

          {forecast.adaptive_goal && (
            <div className="adaptive-goal-box">
              <div className="goal-row">
                <Target size={14} className="text-tertiary" />
                <span>Target: <strong>{forecast.adaptive_goal.recommended_tasks} tasks</strong> ({forecast.adaptive_goal.recommended_hours}h)</span>
              </div>
              <div className="goal-row mt-1">
                <Zap size={14} className="text-tertiary" />
                <span>{forecast.adaptive_goal.motivation}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Mastery & Achievements ── */}
      {achievements && (
        <div className="card insight-card">
          <div className="insight-header">
            <Trophy size={18} className="text-brand" />
            <h3 className="editorial">Mastery</h3>
          </div>

          <div className="level-display">
            <div className="level-badge">
              <Star size={16} fill="currentColor" />
              <span>Lv. {achievements.level}</span>
            </div>
            <div className="level-details">
              <div className="level-title">{achievements.level_title}</div>
              <div className="xp-text">{achievements.xp} XP</div>
            </div>
          </div>

          {/* XP Progress Bar */}
          <div className="xp-progress">
            <div className="xp-bar-bg">
              <div 
                className="xp-bar-fill" 
                style={{ width: `${Math.min(100, (achievements.xp / (achievements.xp + achievements.xp_to_next_level)) * 100)}%` }} 
              />
            </div>
            <div className="xp-hint">{achievements.xp_to_next_level} XP to next level</div>
          </div>

          <div className="stats-grid">
            <div className="stat-mini">
              <div className="stat-mini-val">{achievements.current_streak_days} 🔥</div>
              <div className="stat-mini-lbl">Day Streak</div>
            </div>
            <div className="stat-mini">
              <div className="stat-mini-val">{achievements.total_approved} ✅</div>
              <div className="stat-mini-lbl">Tasks Done</div>
            </div>
          </div>

          {/* Badges Preview */}
          {achievements.badges.filter(b => b.earned).length > 0 && (
            <div className="badges-preview">
              <div className="badges-title">Earned Badges</div>
              <div className="badges-list">
                {achievements.badges.filter(b => b.earned).slice(0, 5).map(b => (
                  <div key={b.id} className="badge-icon" title={`${b.name}: ${b.description}`}>
                    {b.icon}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Skill Decay Alerts ── */}
      {decayProfile && decayProfile.rusty_domains.length > 0 && (
        <div className="card rust-alert-card">
          <div className="rust-header">
            <ShieldAlert size={16} className="text-red" />
            <h4>Skills fading</h4>
          </div>
          <p className="rust-desc">You haven't practiced these recently:</p>
          <div className="rust-tags">
            {decayProfile.rusty_domains.map(domain => (
              <span key={domain} className="badge badge-red">{domain.replace(/_/g, ' ')}</span>
            ))}
          </div>
        </div>
      )}
      
    </div>
  );
};
