import type { SkillEvidence } from './evidence';
import type { SkillId } from './learner';
import type { QuestionFamily } from './question';
import type { TrainingAction } from './priority';

export const SESSION_MODES = ['EMERGENCY', 'NORMAL', 'INTENSIVE'] as const;
export type SessionMode = (typeof SESSION_MODES)[number];
export const SESSION_BLOCK_TYPES = ['LEXICAL_REVIEW', 'DIAGNOSTIC', 'TARGETED_PRACTICE', 'RETENTION_REVIEW', 'TIMED_BLOCK', 'REFLECTION'] as const;
export type SessionBlockType = (typeof SESSION_BLOCK_TYPES)[number];
export type CognitiveLoad = 'LOW' | 'MEDIUM' | 'HIGH';
export interface SessionCandidate {
  readonly id: string;
  readonly type: SessionBlockType;
  readonly available: boolean;
  readonly expected_minutes: number;
  readonly cognitive_load: CognitiveLoad;
  readonly targets: TrainingAction['targets'];
  readonly question_ids: readonly string[];
  readonly lexical_ids: readonly string[];
  readonly reflection_prompt?: string | undefined;
  readonly timed_enabled: boolean;
}
export interface PlannedSessionBlock {
  readonly id: string;
  readonly type: SessionBlockType;
  readonly target_skills: readonly SkillId[];
  readonly planned_minutes: number;
  readonly candidate_ids: readonly string[];
  readonly question_ids: readonly string[];
  readonly lexical_ids: readonly string[];
  readonly cognitive_load: CognitiveLoad;
  readonly timed_enabled: boolean;
  readonly explanation: string;
}
export interface SessionPlan {
  readonly id: string;
  readonly session_id: string;
  readonly mode: SessionMode;
  readonly created_at: number;
  readonly planned_minutes: number;
  readonly allocated_minutes: number;
  readonly blocks: readonly PlannedSessionBlock[];
  readonly notes: readonly string[];
  readonly config: SessionConfig;
  /** Canonical creation input for exact create retries; absent on manually supplied plans/extensions. */
  readonly creation_signature?: string | undefined;
}
export interface SessionConfig {
  readonly version: 'session-v1';
  readonly mode_minutes: Readonly<Record<SessionMode, number>>;
  readonly lexical_reserve_fraction: number;
  readonly max_single_skill_fraction: number;
  readonly diagnostic_fraction: number;
  readonly cold_start_diagnostic_fraction: number;
  readonly family_coverage_floor: number;
  readonly max_consecutive_high: number;
  readonly question_default_minutes: number;
  readonly lexical_default_minutes: number;
  readonly speed_min_samples: number;
  readonly idle_lease_ms: number;
  readonly inactivity_ms: number;
  readonly ordering: 'MEDIUM_FIRST_LIGHT_FINISH' | 'VALUE_FIRST';
}
export interface SessionBlock extends PlannedSessionBlock {
  readonly status: 'PLANNED' | 'ACTIVE' | 'COMPLETED' | 'SKIPPED';
  readonly started_at: number | null;
  readonly completed_at: number | null;
  readonly actual_duration_ms: number | null;
  readonly completed_question_ids: readonly string[];
  readonly completed_lexical_ids: readonly string[];
  readonly question_attempt_ids: readonly string[];
  readonly lexical_attempt_ids: readonly string[];
}
/** Immutable plan + append-only execution journal are authoritative; this is a derived projection. */
export interface AdaptiveStudySession {
  readonly id: string;
  readonly mode: SessionMode;
  readonly planned_minutes: number;
  readonly total_budget_minutes: number;
  readonly started_at: number | null;
  readonly ended_at: number | null;
  readonly status: 'PLANNED' | 'ACTIVE' | 'COMPLETED' | 'ABANDONED';
  readonly blocks: readonly SessionBlock[];
  readonly actual_active_ms: number;
  readonly pause_ms: number;
  readonly wall_clock_ms: number;
  readonly questions_attempted: number;
  readonly lexical_reviews_completed: number;
  readonly engaged: boolean;
  readonly last_event_at: number;
  readonly revision: number;
}
export type SessionCommand =
  | { readonly type: 'START' | 'PAUSE' | 'RESUME' | 'FINISH' | 'ABANDON' }
  | { readonly type: 'PULSE'; readonly engaged: boolean }
  | { readonly type: 'START_BLOCK' | 'COMPLETE_BLOCK'; readonly block_id: string }
  | { readonly type: 'SKIP_BLOCK'; readonly block_id: string; readonly reason: 'USER' | 'FAILURE' | 'ADAPTATION' }
  | { readonly type: 'QUESTION' | 'LEXICAL'; readonly block_id: string; readonly attempt_id: string; readonly item_id: string; readonly retry_of: string | null }
  | { readonly type: 'EXTEND'; readonly plan: SessionPlan };
export interface SessionEventInput {
  readonly id: string;
  readonly session_id: string;
  readonly at: number;
  readonly command: SessionCommand;
}
export interface SessionEvent extends SessionEventInput {
  readonly sequence: number;
  /** Unique across sessions: an actual attempt cannot earn block credit twice. */
  readonly attempt_ref?: string | undefined;
}
export interface TimedBlockResult {
  readonly block_id: string;
  readonly session_id: string;
  readonly question_count: number;
  readonly completed_count: number;
  readonly correct_count: number;
  readonly assisted_count: number;
  readonly unaided_correct_count: number;
  readonly assisted_correct_count: number;
  readonly attempt_ids: readonly string[];
  readonly total_active_ms: number;
  readonly target_budget_ms: number;
  readonly family_mix: readonly QuestionFamily[];
  readonly started_at: number;
  readonly ended_at: number;
  readonly qualified: boolean;
  readonly disqualification_reasons: readonly string[];
  readonly degradation_signal: { readonly first_accuracy: number; readonly last_accuracy: number; readonly decline: number } | null;
}
/** Compatible reserved source, kept OUTSIDE the frozen Phase 3 event store/validator. */
export interface PacingBlockEvidence extends SkillEvidence {
  readonly source: 'TIMED_PERFORMANCE';
  readonly skill_id: 'PACING_STAMINA';
  readonly block_id: string;
  readonly pacing_version: 'block-v1';
  readonly supporting_attempt_ids: readonly string[];
}
/** Reserved inputs only. No periodic mock scheduling or estimator is implemented. */
export interface FutureMockSignals {
  readonly estimator_uncertainty?: number;
  readonly coverage_gap?: number;
  readonly pacing_risk?: number;
  readonly last_mock_at?: number | null;
  readonly exam_date_proximity?: number;
}
export const SESSION_STATUS_LABELS = Object.freeze({ PLANNED: 'Planlandı', ACTIVE: 'Devam ediyor', COMPLETED: 'Tamamlandı', SKIPPED: 'Atlandı', ABANDONED: 'Yarım bırakıldı' });
