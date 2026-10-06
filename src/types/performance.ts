import type { Question, QuestionFamily } from './question';
import type { SkillId } from './learner';

/** Integration provenance, not a learner's report of correctness. Unknown origins fail closed. */
export interface PerformanceSource {
  readonly kind: 'USER_EXECUTION' | 'IMPORTED_USER_EXECUTION' | 'DEMO' | 'SYNTHETIC' | 'UNKNOWN';
  readonly reference: string;
}
/** Complete history is required for repeat detection; do not prefilter attempts to successful blocks. */
export interface PerformanceSnapshot {
  readonly source: PerformanceSource;
  readonly as_of: number;
  readonly questions: readonly Question[];
  readonly plans: readonly unknown[];
  readonly events: readonly unknown[];
  readonly attempts: readonly unknown[];
  readonly timed_results: readonly unknown[];
  readonly pacing_evidence: readonly unknown[];
  readonly evidence_runs: readonly unknown[];
  readonly skill_evidence: readonly unknown[];
  readonly lexical_attempt_ids: readonly string[];
}
export type PerformanceExclusionReason = 'UNTRUSTED_SOURCE' | 'INVALID_RECORD' | 'DUPLICATE' | 'LEXICAL_ATTEMPT'
  | 'INCOMPLETE' | 'NOT_QUALIFIED' | 'INSUFFICIENT_TIME' | 'NOT_TIMED' | 'NO_QUALIFIED_BLOCK'
  | 'ASSISTED' | 'REPEATED_QUESTION' | 'OUTSIDE_WINDOW' | 'NOT_EXAM_LIKE_TRANSFER';
export interface PerformanceExclusion {
  readonly kind: 'SOURCE' | 'SESSION' | 'BLOCK' | 'ATTEMPT' | 'RECORD';
  readonly id: string;
  readonly reason: PerformanceExclusionReason;
}
export interface PerformanceEvidence {
  readonly attempt_id: string;
  readonly question_id: string;
  readonly block_id: string;
  readonly session_id: string;
  readonly family: QuestionFamily;
  /** Primary task classification; secondary annotations cannot inflate coverage. */
  readonly primary_skill: Exclude<SkillId, 'PACING_STAMINA'>;
  readonly correct: boolean;
  readonly attempted_at: number;
  readonly exam_like_transfer: boolean;
}
export interface PerformanceEvidenceSet {
  readonly records: readonly PerformanceEvidence[];
  readonly exclusions: readonly PerformanceExclusion[];
  readonly integrity: 'VALID' | 'INVALID';
}
export interface PerformanceRange {
  readonly lower_bound: number;
  readonly upper_bound: number;
  readonly confidence_level: 0.95;
  readonly sample_size: number;
  readonly method: 'WILSON';
  readonly unit: 'CORRECT_RESPONSE_PROPORTION';
}
export interface ExamPerformanceRange extends PerformanceRange {
  readonly scope: 'EXAM_LIKE_PRACTICE_PROXY';
  readonly calibrated: false;
  /** Repository contains no verified exam blueprint/point scale. No points are inferred. */
  readonly point_scale: null;
}
export interface PerformanceCoverage {
  readonly family_counts: Readonly<Record<QuestionFamily, number>>;
  readonly skill_counts: Readonly<Record<Exclude<SkillId, 'PACING_STAMINA'>, number>>;
  readonly covered_families: readonly QuestionFamily[];
  readonly missing_families: readonly QuestionFamily[];
  readonly underrepresented_families: readonly QuestionFamily[];
  readonly covered_skills: readonly Exclude<SkillId, 'PACING_STAMINA'>[];
  readonly missing_skills: readonly Exclude<SkillId, 'PACING_STAMINA'>[];
  readonly underrepresented_skills: readonly Exclude<SkillId, 'PACING_STAMINA'>[];
  readonly block_count: number;
  readonly session_count: number;
  readonly family_concentration: number;
  readonly block_concentration: number;
  readonly session_concentration: number;
}
export type PerformanceEstimateBlocker = 'SOURCE_NOT_VERIFIED' | 'INVALID_SOURCE_RECORDS' | 'NO_ELIGIBLE_EVIDENCE'
  | 'INSUFFICIENT_SAMPLE' | 'EXAM_LIKE_CONTEXT' | 'FAMILY_COVERAGE' | 'SKILL_COVERAGE'
  | 'BLOCK_DIVERSITY' | 'SESSION_DIVERSITY' | 'CONCENTRATED_EVIDENCE' | 'WIDE_INTERVAL';
export type PerformanceReadiness = 'INSUFFICIENT' | 'OBSERVED_ONLY' | 'PROVISIONAL' | 'READY';
export interface PerformanceObservation {
  readonly eligible_question_count: number;
  readonly correct_count: number;
  readonly incorrect_count: number;
  readonly accuracy: number | null;
  readonly qualified_block_count: number;
  readonly interval: PerformanceRange | null;
}
export interface PerformanceEstimateProvenance {
  readonly version: 'performance-range-v1';
  readonly source: PerformanceSource;
  readonly as_of: number;
  readonly confidence_level: 0.95;
  readonly attempt_ids: readonly string[];
  readonly block_ids: readonly string[];
  readonly generalization_attempt_ids: readonly string[];
  readonly exclusions: readonly PerformanceExclusion[];
  readonly assumptions: readonly string[];
}
interface PerformanceEstimateBase {
  readonly observed: PerformanceObservation;
  /** Coverage here is for generalization-eligible records, not all practice results. */
  readonly coverage: PerformanceCoverage;
  readonly observed_coverage: PerformanceCoverage;
  readonly generalization: { readonly sample_size: number; readonly interval: PerformanceRange | null };
  readonly provenance: PerformanceEstimateProvenance;
  readonly uncertainty: { readonly sampling_width: number | null; readonly calibrated_exam_prediction: false; readonly scope: 'EXAM_LIKE_PRACTICE_PROXY' };
}
/** READY is conditional comparability, never a calibrated ÖSYM score or probability of success. */
export type PerformanceEstimateResult = PerformanceEstimateBase & (
  | { readonly status: 'READY'; readonly exam_range: ExamPerformanceRange; readonly blockers: readonly [] }
  | { readonly status: Exclude<PerformanceReadiness, 'READY'>; readonly exam_range: null; readonly blockers: readonly PerformanceEstimateBlocker[] }
);
