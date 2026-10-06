import type { SkillId } from './learner';
import type { ConfidenceLevel, DiscourseRelation, QuestionFamily } from './question';

export const EVIDENCE_DIRECTIONS = ['POSITIVE', 'NEGATIVE', 'NEUTRAL'] as const;
export const EVIDENCE_SOURCES = ['QUESTION_RESULT', 'TACTICAL_DECISION', 'TRANSFER', 'TIMED_PERFORMANCE'] as const;
export type EvidenceDirection = (typeof EVIDENCE_DIRECTIONS)[number];
export type EvidenceSource = (typeof EVIDENCE_SOURCES)[number];
export type EvidenceKind = 'PRACTICE' | 'TRANSFER';

/** Caller-observed metadata; an unseen question can test a previously practised skill. */
export interface TransferContext {
  readonly unseen: boolean;
  readonly exam_like: boolean;
  readonly prior_practice_at: number;
}
export interface EvidenceContext {
  readonly transfer?: TransferContext | undefined;
  /** Explicit learner response, recorded before submission; never inferred from the answer key. */
  readonly identified_relation?: {
    readonly relation: DiscourseRelation;
    readonly recorded_at: number;
  } | undefined;
}

/** Immutable event. Optional metadata is copied, never a reference into a mutable attempt. */
export interface SkillEvidence {
  readonly id: string;
  readonly extractor_version: 'v1';
  readonly attempt_id: string;
  readonly question_id: string;
  readonly session_id: string | null;
  readonly skill_id: SkillId;
  readonly question_family: QuestionFamily;
  readonly direction: EvidenceDirection;
  readonly source: EvidenceSource;
  readonly evidence_kind: EvidenceKind;
  readonly strength: number;
  readonly reliability: number;
  readonly transfer_level: number;
  readonly assisted: boolean;
  readonly difficulty?: number | undefined;
  readonly attribution_weight?: number | undefined;
  readonly mapping_weight: number;
  /** Attempt linkage for historical accuracy; tactical success is not an answered question. */
  readonly outcome_correct: boolean;
  readonly transfer_context?: TransferContext | undefined;
  readonly created_at: number;
}
export interface ConfidenceCalibrationRecord {
  readonly attempt_id: string;
  readonly confidence: ConfidenceLevel;
  readonly correct: boolean;
}
/** Processing receipt also makes an empty extraction idempotent and detects changed context. */
export interface EvidenceRun {
  readonly attempt_id: string;
  readonly question_id: string;
  readonly extractor_version: 'v1';
  readonly context: EvidenceContext;
  readonly evidence_ids: readonly string[];
  readonly created_at: number;
}
