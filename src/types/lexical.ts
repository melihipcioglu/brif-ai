export const LEXICAL_STATES = ['NEW', 'SEEN', 'LEARNING', 'FAMILIAR', 'MASTERED'] as const;
export type LexicalState = (typeof LEXICAL_STATES)[number];
export const POS_TYPES = ['noun', 'verb', 'adjective', 'adverb', 'conjunction', 'preposition', 'phrase'] as const;
export type PosType = (typeof POS_TYPES)[number];
export type Tier = 1 | 2 | 3 | 4 | 5 | 6;
export type PolaritySymbol = '↑' | '↓' | '⇄';
export type RecallGrade = 0 | 1 | 2 | 3;
export type ReviewOutcome = 'unassisted' | 'assisted' | 'incorrect';
export type FrictionLevel = 1 | 2 | 3 | 4;

export const FAMILIAR_MES_THRESHOLD = 60;
export const MASTERED_MES_THRESHOLD = 85;
export const FAMILIAR_DELAY_DAYS = 3;
export const MASTERED_DELAY_DAYS = 14;
export const MASTERED_CONTEXT_COUNT = 3;

export interface MasteryRequirements {
  readonly collocation_required: boolean;
  readonly distractor_required: boolean;
}

/** Do not invent a preposition test for every word; require genuine distractor evidence. */
export const DEFAULT_MASTERY_REQUIREMENTS: Readonly<MasteryRequirements> = Object.freeze({
  collocation_required: false,
  distractor_required: true,
});

export interface WordFamilyMember {
  readonly pos: PosType;
  readonly form: string;
  readonly meaning_tr: string;
}

export interface CriticalCollocation {
  readonly phrase: string;
  readonly meaning_tr: string;
}

export interface TypicalDistractor {
  readonly word: string;
  readonly meaning_tr: string;
  readonly explanation_tr: string;
}

/** Extra persisted evidence required to reproduce MES without inventing delayed recall. */
export interface MasteryEvidence {
  readonly delayed_unaided_correct_count_3d: number;
  readonly delayed_unaided_correct_count_14d: number;
  readonly max_unaided_delay_days: number;
  readonly distractor_correct_count: number;
  readonly distractor_attempt_count: number;
}

/** Dates are UTC epoch milliseconds; stability is in days; scores are 0–100. */
export interface LexicalRecord {
  readonly word_id: string;
  readonly lemma: string;
  readonly pos: PosType;
  readonly tier: Tier;
  readonly priority_score: number;
  readonly lexical_state: LexicalState;
  readonly mastery_score: number;
  readonly encounter_count: number;
  readonly unaided_correct_count: number;
  readonly assisted_correct_count: number;
  readonly incorrect_count: number;
  readonly response_time_avg_ms: number;
  readonly stability: number;
  readonly last_seen_at: number | null;
  readonly last_success_at: number | null;
  readonly next_review_date: number;
  /** Cached at the last update; recalculate with calculateReviewPriority for a live queue. */
  readonly review_priority: number;
  /** Exposure telemetry only; never used as mastery evidence. */
  readonly contexts_seen: readonly string[];
  /** Unique contexts with a correct effective grade >= 2; subset of contexts_seen. */
  readonly unaided_success_contexts: readonly string[];
  readonly collocations_mastered: readonly string[];
  /** Keys are distractor words, values are error counts. */
  readonly distractor_errors: Readonly<Record<string, number>>;
  readonly exam_meaning_tr: string;
  readonly critical_collocations: readonly CriticalCollocation[];
  readonly synonyms: readonly string[];
  readonly antonyms: readonly string[];
  readonly typical_distractor: readonly TypicalDistractor[];
  readonly exam_sentence: string;
  readonly exam_sentence_tr: string;
  readonly word_family: readonly WordFamilyMember[];
  readonly polarity_symbol: PolaritySymbol;
  readonly mastery_requirements: MasteryRequirements;
  readonly evidence: MasteryEvidence;
}

export type LexicalEntry = Pick<LexicalRecord,
  'word_id' | 'lemma' | 'pos' | 'tier' | 'priority_score' | 'exam_meaning_tr' |
  'critical_collocations' | 'synonyms' | 'antonyms' | 'typical_distractor' |
  'exam_sentence' | 'exam_sentence_tr' | 'word_family' | 'polarity_symbol'
> & { readonly mastery_requirements?: MasteryRequirements };

export interface LexicalReview {
  readonly grade: RecallGrade;
  readonly context_id: string;
  readonly response_time_ms: number;
  readonly reviewed_at: number;
  /** True whenever any translation, polarity or other hint was exposed. */
  readonly assistance_used: boolean;
  /** Only set for a question that actually tested a distractor. */
  readonly distractor_test?: {
    readonly word: string;
    readonly resisted: boolean;
  };
  /** Only set when the named collocation was directly tested. */
  readonly tested_collocation?: string;
}
