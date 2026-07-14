/**
 * types.ts — TypeScript interfaces for all ICRS API response shapes.
 *
 * Use these instead of `any` to get compile-time type safety and
 * IDE autocomplete for roadmap data throughout the frontend.
 */

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

export interface RoadmapTask {
  task_name: string;
  domain: string;
  urgency_tier: 'CRITICAL' | 'MODERATE' | 'MARGINAL' | 'MET' | 'BRIDGE' | 'REENGAGEMENT';
  difficulty_level: number;
  difficulty_order?: number;
  score: number;
  is_bridge?: boolean;
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
}
