import type { SkillId } from './learner';

/** Phase 4 is a planning index model. No field denotes an exam outcome probability or score gain. */
export interface SkillEvidenceCoverage {
  readonly informative_attempt_count: number;
  readonly question_count: number;
  readonly family_count: number;
  readonly unaided_attempt_count: number;
  readonly transfer_attempt_count: number;
  readonly last_informative_at: number | null;
}
export type EvidenceCoverageMap = Readonly<Partial<Record<SkillId, SkillEvidenceCoverage>>>;
export interface SkillTrainingProfile {
  /** Relative editorial relevance, not an exam item frequency or number of exam points. */
  readonly exam_relevance: number;
  /** Relative editorial suitability for training, not predicted improvement. */
  readonly trainability: number;
  readonly retention_window_days: number;
  readonly target_question_count: number;
  readonly target_family_count: number;
}
export interface PriorityModelConfig {
  readonly version: 'priority-v1';
  readonly evidence_saturation_k: number;
  readonly question_breadth_weight: number;
  readonly unsupported_practice_floor: number;
  readonly uncertainty_diagnostic_weight: number;
  readonly retention_mastery_floor: number;
  readonly minimum_effective_minutes: number;
  readonly weights: {
    readonly practice: number;
    readonly diagnostic: number;
    readonly retention: number;
  };
  readonly default_profile: SkillTrainingProfile;
}
export interface PriorityContext {
  /** Explicit clock input keeps planning deterministic and independently testable. */
  readonly as_of: number;
  /** Missing coverage means UNKNOWN, not an assertion that no historical evidence exists. */
  readonly coverage?: EvidenceCoverageMap | undefined;
  readonly profiles?: Readonly<Partial<Record<SkillId, SkillTrainingProfile>>> | undefined;
}
export const PRIORITY_REASON_CODES = ['LIMITED_COVERAGE', 'UNCERTAIN_EVIDENCE', 'SUPPORTED_SKILL_GAP', 'RETENTION_NEED', 'NO_EXAM_RELEVANCE'] as const;
export type PriorityReasonCode = (typeof PRIORITY_REASON_CODES)[number];
export interface ScoreLeakPriority {
  readonly skill_id: SkillId;
  /** Exactly 1 - mastery. Evidence-based skill gap index only. */
  readonly skill_gap: number;
  readonly uncertainty: number;
  readonly coverage_status: 'KNOWN' | 'UNKNOWN';
  readonly coverage: SkillEvidenceCoverage | null;
  readonly coverage_index: number;
  readonly evidence_support: number;
  readonly age_days: number | null;
  readonly practice_need: number;
  readonly diagnostic_need: number;
  readonly retention_need: number;
  readonly profile: SkillTrainingProfile;
  readonly priority_components: {
    readonly practice: number;
    readonly diagnostic: number;
    readonly retention: number;
  };
  /** 0..100 planning index. Neither a percentage nor lost exam points. */
  readonly priority_index: number;
  readonly reasons: readonly PriorityReasonCode[];
}
export interface ScoreLeakMap {
  readonly model_version: 'priority-v1';
  readonly generated_at: number;
  readonly interpretation: 'RELATIVE_TRAINING_PRIORITY';
  readonly unit: 'INDEX_0_100';
  readonly config: PriorityModelConfig;
  readonly skills: readonly ScoreLeakPriority[];
}

export const TRAINING_ACTION_KINDS = ['DIAGNOSTIC', 'TARGETED_PRACTICE', 'RETENTION_REVIEW'] as const;
export type TrainingActionKind = (typeof TRAINING_ACTION_KINDS)[number];
export interface TrainingAction {
  readonly id: string;
  readonly title: string;
  readonly kind: TrainingActionKind;
  readonly format: 'SINGLE_QUESTION' | 'QUESTION_SET' | 'TIMED_BLOCK';
  /** The caller confirms that actual content/resources exist and are currently usable. */
  readonly available: boolean;
  readonly expected_minutes: number;
  /** Nonempty, unique skills, positive weights summing to 1. */
  readonly targets: readonly { readonly skill_id: SkillId; readonly weight: number }[];
}
export interface ActionContribution {
  readonly skill_id: SkillId;
  readonly target_weight: number;
  readonly aligned_need: number;
  readonly exam_relevance: number;
  readonly trainability: number;
  readonly value_index: number;
}
export interface RankedTrainingAction {
  readonly action: TrainingAction;
  readonly contributions: readonly ActionContribution[];
  readonly training_value_index: number;
  readonly effective_minutes: number;
  /** Heuristic value index / minute; not expected exam points or a predicted learning gain. */
  readonly expected_training_value: number;
  readonly value_unit: 'PRIORITY_INDEX_PER_MINUTE';
  readonly explanation: string;
}
export const ACTION_EXCLUSION_CODES = ['UNAVAILABLE', 'OVER_TIME_BUDGET', 'PACING_REQUIRES_TIMED_BLOCK', 'NO_SUPPORTED_REVIEW', 'NO_TRAINING_VALUE'] as const;
export type ActionExclusionCode = (typeof ACTION_EXCLUSION_CODES)[number];
export interface NextBestActionPlan {
  readonly score_leak_map: ScoreLeakMap;
  readonly available_minutes: number;
  readonly status: 'RECOMMENDED' | 'NO_ELIGIBLE_ACTION';
  readonly selected: RankedTrainingAction | null;
  readonly ranked_actions: readonly RankedTrainingAction[];
  readonly excluded_actions: readonly { readonly action_id: string; readonly reasons: readonly ActionExclusionCode[] }[];
}
