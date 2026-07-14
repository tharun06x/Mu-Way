/**
 * types.ts — TypeScript interfaces for all ICRS API response shapes.
 *
 * Use these instead of `any` to get compile-time type safety and
 * IDE autocomplete for roadmap data throughout the frontend.
 */

// ── Core Gap & Roadmap ───────────────────────────────────────────────────── //

export interface DomainGap {
  current: number;
  required: number;
  raw_gap: number;
  weighted_gap: number;
  tier: 'CRITICAL' | 'MODERATE' | 'MARGINAL' | 'MET';
  domain_alignment: number;
}

export interface GapData {
  dream_role: string;
  career_gap: number;
  alignment_score: number;
  readiness_pct: number;
  career_gap_tier: 'CRITICAL' | 'MODERATE' | 'MARGINAL' | 'MET';
  domain_gaps: Record<string, DomainGap>;
  domain_gaps_json?: string;
}

export interface TaskResource {
  title: string;
  url: string;
  type: 'video' | 'course' | 'docs' | 'practice';
  platform: string;
  is_free: boolean;
}

export interface RoadmapTask {
  task_name: string;
  domain: string;
  urgency_tier: 'CRITICAL' | 'MODERATE' | 'MARGINAL' | 'MET' | 'BRIDGE' | 'REENGAGEMENT';
  difficulty_level: number;
  difficulty_order?: number;
  score: number;
  is_bridge?: boolean;
  resources?: TaskResource[];  // Enriched learning links
}

export interface RoadmapWeek {
  week: number;
  minutes_used: number;
  tasks: RoadmapTask[];
}

export interface RoadmapSummary {
  total_weeks: number;
  total_tasks: number;
  health_score: number;
  health_ok: boolean;
  first_week_domains: string[];
  next_milestone: {
    description: string;
  };
}

export interface Roadmap {
  user_id: string;
  created_date: string;
  dream_role: string;
  career_gap: number;
  career_gap_tier: 'CRITICAL' | 'MODERATE' | 'MARGINAL' | 'MET';
  readiness_pct: number;
  total_weeks: number;
  roadmap_weeks: RoadmapWeek[];
  roadmap_health: number;
  domain_gaps: Record<string, DomainGap>;
  summary: RoadmapSummary;
}

export interface RecommendedTask {
  rank: number;
  task_name: string;
  domain: string;
  score: number;
  reason: string;
  difficulty_level: number;
  difficulty_label: string;
}

export interface SubmittedTask {
  task_name: string;
  domain: string;
  difficulty_level: number;
  is_approved: number;
  submission_date: string;
}

// ── New: Progress Forecast ───────────────────────────────────────────────── //

export interface AdaptiveGoal {
  recommended_hours: number;
  recommended_tasks: number;
  completion_rate_7d: number;
  burnout_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  motivation: string;
}

export interface ProgressForecast {
  user_id: string;
  dream_role: string;
  current_readiness_pct: number;
  career_gap: number;
  weeks_to_goal: number;
  estimated_completion_date: string;
  weekly_gap_closure_rate: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  message: string;
  adaptive_goal?: AdaptiveGoal;
}

// ── New: Achievements & Gamification ────────────────────────────────────── //

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  earned: boolean;
  earned_date: string | null;
}

export interface AchievementProfile {
  user_id: string;
  xp: number;
  level: number;
  level_title: string;
  xp_to_next_level: number;
  current_streak_days: number;
  longest_streak_days: number;
  total_approved: number;
  total_submitted: number;
  active_days: number;
  badges: Badge[];
  next_milestone: string;
}

// ── New: Skill Decay ─────────────────────────────────────────────────────── //

export interface DomainDecayInfo {
  raw_mastery: number;
  decayed_mastery: number;
  days_inactive: number;
  retention_factor: number;
  is_rusty: boolean;
  rust_severity: 'NONE' | 'MILD' | 'MODERATE' | 'SEVERE';
}

export interface DecayProfile {
  user_id: string;
  overall_retention: number;
  rusty_domains: string[];
  domains: Record<string, DomainDecayInfo>;
}

// ── New: Multi-Role Comparison ───────────────────────────────────────────── //

export interface RoleComparisonResult {
  role_a: string;
  role_b: string;
  gap_a: GapData;
  gap_b: GapData;
  forecast_a: ProgressForecast;
  forecast_b: ProgressForecast;
  recommendation: string;
  shared_domains: string[];
  switching_cost_weeks: number;
}

// ── Full API Response ─────────────────────────────────────────────────────── //

export interface RoadmapApiResponse {
  success: boolean;
  muid: string;
  name: string;
  role: string;
  gap: GapData;
  recs: RecommendedTask[];
  roadmap: Roadmap;
  known_user: boolean;
  submitted_tasks: SubmittedTask[];
  // New fields from upgrade:
  forecast: ProgressForecast | null;
  achievements: AchievementProfile | null;
  decay_profile: DecayProfile | null;
}

export interface CompareRolesApiResponse {
  success: boolean;
  comparison: RoleComparisonResult;
}

export interface InsightsApiResponse {
  success: boolean;
  achievements: AchievementProfile;
}
