import type { LearnerSkillVector, SkillId } from './learner';
import type { LexicalRecord, RecallGrade, ReviewOutcome } from './lexical';

/** Phase 1 lexical evidence. The question_attempts store name is retained for compatibility. */
export interface LexicalAttempt {
  readonly id: string;
  readonly question_id: string;
  readonly session_id: string | null;
  readonly lexical_ids: readonly string[];
  readonly skill_ids: readonly SkillId[];
  readonly context_id: string;
  readonly outcome: ReviewOutcome;
  readonly response_ms: number;
  readonly attempted_at: number;
  /** Full scheduler evidence makes retry conflicts detectable and reviews auditable. */
  readonly lexical_review: {
    readonly grade: RecallGrade;
    readonly assistance_used: boolean;
    readonly user_lexical_factor: number;
    readonly distractor_test: { readonly word: string; readonly resisted: boolean } | null;
    readonly tested_collocation: string | null;
  } | null;
}

export interface DailySession {
  readonly id: string;
  /** Local calendar date; time_zone records which zone defined that date. */
  readonly date: string;
  readonly time_zone: string;
  readonly started_at: number;
  readonly ended_at: number | null;
  readonly active_ms: number;
  readonly skills: LearnerSkillVector;
}

export interface ProgressBackup {
  readonly format: 'yokdil-fen-progress';
  readonly schema_version: 2;
  readonly scheduler_version: 'ass-v1';
  readonly exported_at: number;
  readonly lexical_store: readonly LexicalRecord[];
  readonly question_attempts: readonly LexicalAttempt[];
  readonly daily_sessions: readonly DailySession[];
}
