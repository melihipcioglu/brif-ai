import type { Question, QuestionAttempt, QuestionFamily } from './question';
import type { SkillId } from './learner';
import type { PerformanceCoverage, PerformanceEvidence, PerformanceEvidenceSet, PerformanceRange, PerformanceSource } from './performance';
import type { AdaptiveStudySession, SessionEvent, SessionPlan } from './session';

export type ExamContentSkill = Exclude<SkillId, 'PACING_STAMINA'>;
export type BlueprintSource =
  | { readonly verification: 'UNVERIFIED'; readonly reference: string | null }
  | { readonly verification: 'INTERNAL'; readonly reference: string }
  | { readonly verification: 'OFFICIAL_VERIFIED'; readonly reference: string; readonly verified_at: number; readonly verified_by: string };
export interface ExamBlueprint {
  readonly id: string;
  readonly version: string;
  readonly scope: 'MINI' | 'FULL';
  readonly total_questions: number;
  readonly time_limit_ms: number;
  /** Exact counts, summing to total_questions. No implicit official distribution. */
  readonly family_targets: Readonly<Partial<Record<QuestionFamily, number>>>;
  readonly skill_minimums: Readonly<Partial<Record<ExamContentSkill, number>>>;
  readonly reuse_policy: 'ALLOW_REUSE' | 'EXCLUDE_SEEN' | 'UNSEEN_ONLY';
  readonly source: BlueprintSource;
}
export type ExposureState = 'UNSEEN' | 'SEEN' | 'UNKNOWN';
/** A trusted integration may supply a controlled inventory observation; absent evidence means UNKNOWN. */
export interface ExposureObservation {
  readonly question_id: string;
  readonly state: Exclude<ExposureState, 'UNKNOWN'>;
  readonly observed_at: number;
  readonly method: 'RECORDED_EXPOSURE' | 'CONTROLLED_INVENTORY';
  readonly reference: string;
}
export interface ExamPoolContext {
  readonly as_of: number;
  readonly prior_attempts: readonly unknown[];
  readonly exposures: readonly ExposureObservation[];
}
export interface PoolExclusion {
  readonly question_id: string;
  readonly reason: 'INVALID_QUESTION' | 'CONFLICTING_ID' | 'DUPLICATE_ID' | 'DUPLICATE_CONTENT' | 'FAMILY_NOT_REQUESTED' | 'SEEN' | 'UNKNOWN_EXPOSURE';
}
export interface ExamPoolAdequacy {
  readonly required: number;
  readonly available: number;
  readonly eligible: number;
  readonly shortfall: number;
  readonly family_available: Readonly<Record<QuestionFamily, number>>;
  readonly family_shortfalls: Readonly<Partial<Record<QuestionFamily, number>>>;
  readonly skill_available: Readonly<Record<ExamContentSkill, number>>;
  readonly skill_shortfalls: Readonly<Partial<Record<ExamContentSkill, number>>>;
  readonly novelty: Readonly<Record<ExposureState, number>>;
  readonly novelty_shortfall: number;
  readonly constraint_shortfall: number;
  readonly exclusions: readonly PoolExclusion[];
}
export type ExamPoolAnalysis = { readonly status: 'INVALID_BLUEPRINT'; readonly issues: readonly string[] }
  | { readonly status: 'ADEQUATE' | 'INSUFFICIENT_POOL'; readonly blueprint: ExamBlueprint; readonly report: ExamPoolAdequacy };
export interface ExamForm {
  readonly id: string;
  readonly quality: 'COMPLETE' | 'PARTIAL';
  readonly blueprint: ExamBlueprint;
  readonly created_at: number;
  readonly seed: string | null;
  readonly selection_policy: 'exam-form-policy-v1';
  readonly question_ids: readonly string[];
  /** Validated immutable item snapshots bind the answer key to this form. No official items are inferred. */
  readonly questions: readonly Question[];
  readonly exposure: Readonly<Record<string, { readonly state: ExposureState; readonly references: readonly string[] }>>;
  readonly fingerprint: string;
}
export interface BuildExamFormRequest {
  readonly id: string;
  readonly blueprint: unknown;
  readonly questions: readonly unknown[];
  readonly context: ExamPoolContext;
  readonly seed?: string;
  readonly allow_partial?: boolean;
}
export type ExamFormBuildResult = { readonly status: 'INVALID_BLUEPRINT'; readonly form: null; readonly issues: readonly string[] }
  | { readonly status: 'INSUFFICIENT_POOL'; readonly form: null; readonly report: ExamPoolAdequacy }
  | { readonly status: 'COMPLETE' | 'PARTIAL'; readonly form: ExamForm; readonly report: ExamPoolAdequacy };
export type SimulationMode = 'PRACTICE_SIMULATION' | 'STRICT_SIMULATION';
export interface ExamSimulationDefinition {
  readonly id: string;
  readonly session_kind: 'EXAM_SIMULATION';
  readonly mode: SimulationMode;
  readonly form: ExamForm;
  readonly created_at: number;
  readonly source: PerformanceSource;
  readonly monitoring: { readonly assistance: 'COMPLETE' | 'UNKNOWN'; readonly interruptions: 'COMPLETE' | 'UNKNOWN'; readonly reference: string | null };
  readonly policy_version: 'calibration-policy-v1';
}
export type ExamSimulationCommand =
  | { readonly type: 'START' | 'PAUSE' | 'RESUME' | 'INTERRUPT' | 'COMPLETE' | 'ABANDON' | 'TIMEOUT' }
  | { readonly type: 'PULSE'; readonly engaged: boolean }
  | { readonly type: 'SUBMIT'; readonly attempt: QuestionAttempt; readonly replaces_attempt_id: string | null }
  | { readonly type: 'HELP'; readonly kind: 'HINT' | 'WORD_POPOVER' | 'VOCABULARY_REVEAL' | 'ANSWER_REVEAL' | 'EXPLANATION_REVEAL' }
  | { readonly type: 'ANSWER_EDIT'; readonly question_id: string }
  | { readonly type: 'EXTEND_TIME'; readonly additional_ms: number };
export interface ExamSimulationEventInput {
  readonly id: string;
  readonly simulation_id: string;
  readonly form_id: string;
  readonly form_fingerprint: string;
  readonly at: number;
  readonly command: ExamSimulationCommand;
}
export interface ExamSimulationEvent extends ExamSimulationEventInput { readonly sequence: number }
export interface ExamSimulationTranscript { readonly definition: ExamSimulationDefinition; readonly events: readonly ExamSimulationEvent[] }
export type CalibrationReason = 'INVALID_EXECUTION' | 'PRACTICE_MODE' | 'PARTIAL_FORM' | 'UNVERIFIED_BLUEPRINT' | 'UNTRUSTED_SOURCE'
  | 'MONITORING_UNKNOWN' | 'INCOMPLETE' | 'TIME_LIMIT' | 'PAUSED' | 'INTERRUPTED' | 'TIME_EXTENDED'
  | 'ASSISTANCE' | 'ANSWER_REVISION' | 'SEEN_QUESTIONS' | 'UNKNOWN_EXPOSURE' | 'INSUFFICIENT_TIMING_EVIDENCE' | 'NOT_QUALIFIED_BLOCK';
export interface ExamSimulationState {
  readonly simulation_id: string;
  readonly form_id: string;
  readonly mode: SimulationMode;
  readonly status: 'PLANNED' | 'ACTIVE' | 'COMPLETED' | 'ABANDONED' | 'TIMED_OUT';
  readonly started_at: number | null;
  readonly ended_at: number | null;
  readonly time_limit_ms: number;
  readonly actual_elapsed_ms: number;
  readonly active_elapsed_ms: number;
  readonly paused: boolean;
  readonly answers: readonly QuestionAttempt[];
  readonly submitted_attempt_ids: readonly string[];
  readonly conditions: readonly CalibrationReason[];
  readonly duplicate_event_ids: readonly string[];
  /** Reused pure Phase 5 projection only; never persisted as a study session or fed into mastery. */
  readonly execution: { readonly plan: SessionPlan; readonly events: readonly SessionEvent[]; readonly projection: AdaptiveStudySession };
}
export interface CalibrationEvidence {
  readonly id: string;
  readonly kind: 'CALIBRATION_MOCK';
  readonly tier: 'PARTIAL_CALIBRATION' | 'FULL_CALIBRATION';
  readonly policy_version: 'calibration-policy-v1';
  readonly simulation_id: string;
  readonly form_id: string;
  readonly form_fingerprint: string;
  readonly blueprint_id: string;
  readonly blueprint_version: string;
  readonly blueprint_source: BlueprintSource;
  readonly source: PerformanceSource;
  readonly seed: string | null;
  readonly execution_event_ids: readonly string[];
  readonly novelty_references: readonly string[];
  readonly records: readonly PerformanceEvidence[];
  readonly question_content_keys: Readonly<Record<string, string>>;
  readonly official_exam: false;
  readonly official_score_mapping: null;
}
interface CalibrationResultBase {
  readonly simulation_id: string;
  readonly form_id: string;
  readonly blueprint_id: string;
  readonly reasons: readonly CalibrationReason[];
  readonly question_count: number;
  readonly coverage: PerformanceCoverage;
  readonly observed_accuracy: number | null;
  readonly interval: PerformanceRange | null;
  readonly timing_valid: boolean;
  readonly assistance_valid: boolean;
  readonly completion_valid: boolean;
  readonly novelty: Readonly<Record<ExposureState, number>>;
}
export type CalibrationQualificationResult = CalibrationResultBase & (
  | { readonly qualified: false; readonly tier: 'NOT_ELIGIBLE' | 'PRACTICE_ONLY'; readonly evidence: null }
  | { readonly qualified: true; readonly tier: 'PARTIAL_CALIBRATION' | 'FULL_CALIBRATION'; readonly evidence: CalibrationEvidence }
);
export interface CalibrationPerformanceSelection {
  readonly evidence: PerformanceEvidenceSet;
  readonly calibration_references: readonly { readonly id: string; readonly tier: CalibrationEvidence['tier']; readonly form_id: string }[];
  readonly rejected: readonly { readonly simulation_id: string; readonly reasons: readonly string[] }[];
  readonly coverage: PerformanceCoverage;
  readonly interval: PerformanceRange | null;
  readonly observed_accuracy: number | null;
  /** This additive adapter does not change Phase 6 readiness or fabricate transfer receipts. */
  readonly exam_range: null;
  readonly scope: 'CALIBRATION_OBSERVATION';
}
