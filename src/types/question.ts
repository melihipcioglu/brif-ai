import type { SkillId } from './learner';

export const OPTION_IDS = ['A', 'B', 'C', 'D', 'E'] as const;
export type OptionId = (typeof OPTION_IDS)[number];
export const QUESTION_FAMILIES = ['GAP_FILL', 'CLOZE_TEST', 'SENTENCE_COMPLETION', 'TRANSLATION_ENG_TR', 'TRANSLATION_TR_ENG', 'PARAGRAPH_COMPLETION', 'IRRELEVANT_SENTENCE', 'READING_COMPREHENSION'] as const;
export type QuestionFamily = (typeof QUESTION_FAMILIES)[number];
export const GAP_FILL_SUBCLASSES = ['VOCAB', 'GRAMMAR', 'PREPOSITION', 'CONNECTOR', 'STRUCTURE'] as const;
export type GapFillSubclass = (typeof GAP_FILL_SUBCLASSES)[number];
export const DISTRACTOR_PATTERNS = ['POLARITY_INVERSION', 'EXTREME_QUALIFIER', 'FALSE_FRIEND', 'SCOPE_DRIFT', 'TEMPORAL_MISMATCH', 'REFERENCE_MISMATCH', 'CAUSE_EFFECT_REVERSAL', 'PARTIAL_TRUTH', 'UNSUPPORTED_DETAIL', 'SEMANTIC_ROLE_SWAP'] as const;
export type DistractorPattern = (typeof DISTRACTOR_PATTERNS)[number];
export const DISCOURSE_RELATIONS = ['CONTRAST', 'CONCESSION', 'CAUSE', 'RESULT', 'CONDITION', 'ADDITION'] as const;
export type DiscourseRelation = (typeof DISCOURSE_RELATIONS)[number];
export const READING_QUESTION_TYPES = ['DETAIL', 'INFERENCE', 'MAIN_IDEA', 'REFERENCE', 'PURPOSE'] as const;
export type ReadingQuestionType = (typeof READING_QUESTION_TYPES)[number];
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';
export const ERROR_CATEGORIES = ['VOCABULARY', 'CONNECTOR', 'GRAMMAR', 'DISTRACTOR', 'READING_INFERENCE', 'TIME_PRESSURE', 'CARELESS', 'UNKNOWN_TERMINOLOGY'] as const;
export type ErrorCategory = (typeof ERROR_CATEGORIES)[number];

export interface SemanticRoleMap {
  /** Canonical meaning IDs, independent of surface word order and language. */
  readonly agent?: string | undefined;
  readonly action: string;
  readonly patient?: string | undefined;
  readonly voice: 'ACTIVE' | 'PASSIVE';
  readonly modality?: string | undefined;
  readonly polarity?: string | undefined;
  readonly time?: string | undefined;
  readonly condition?: string | undefined;
  readonly degree?: string | undefined;
  /** Canonical additional propositions; compare as sets, never as word sequences. */
  readonly propositions: readonly string[];
}
export interface AnchorChain {
  readonly referent: number;
  readonly topic_continuity: number;
  readonly connector: number;
  readonly tense_aspect: number;
  readonly cause_effect: number;
  readonly lexical_chain: number;
}
export const CHECK_CRITERIA = ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB', 'TENSE_ASPECT', 'VOICE', 'REDUCTION', 'MODALITY', 'CLAUSE_RELATION', 'TEMPORAL_CONTEXT', 'DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'SCOPE', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'TOPIC', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'] as const;
export type CheckCriterion = (typeof CHECK_CRITERIA)[number];
export interface TacticalCheck {
  readonly criterion: CheckCriterion;
  readonly matches: boolean | null;
  /** Human-authored contextual evidence, shown only after submission. */
  readonly evidence: string;
}
export interface TriageExplanation {
  readonly summary: string;
  readonly cues: readonly string[];
  readonly checks: readonly string[];
}
export interface OptionAnalysis {
  readonly option_id: OptionId;
  readonly verdict: 'CORRECT' | 'ELIMINATE' | 'POSSIBLE';
  readonly reasons: readonly string[];
  readonly patterns: readonly DistractorPattern[];
}
export interface VerificationExplanation {
  readonly summary: string;
  readonly evidence: readonly string[];
}
export interface QuestionExplanation {
  readonly triage: TriageExplanation;
  readonly option_analysis: readonly OptionAnalysis[];
  readonly verification: VerificationExplanation;
  readonly distractor_patterns: readonly DistractorPattern[];
}
export interface TemporalContext {
  readonly temporal_anchor: string;
  readonly event_order: string;
  readonly tense_aspect: string;
  readonly context: string;
}
export type TacticalMetadata =
  | { readonly kind: 'GAP_FILL'; readonly focus: GapFillSubclass; readonly temporal?: TemporalContext | undefined }
  | { readonly kind: 'CLOZE_TEST'; readonly previous_sentence: string; readonly target_sentence: string; readonly next_sentence: string; readonly macro_context: string; readonly relation: DiscourseRelation; readonly candidate_relations: Readonly<Record<OptionId, DiscourseRelation | null>> }
  | { readonly kind: 'SENTENCE_COMPLETION'; readonly relation: DiscourseRelation; readonly candidate_relations: Readonly<Record<OptionId, DiscourseRelation | null>> }
  | { readonly kind: 'TRANSLATION'; readonly direction: 'ENG_TR' | 'TR_ENG'; readonly source: SemanticRoleMap; readonly candidates: Readonly<Record<OptionId, SemanticRoleMap>> }
  | { readonly kind: 'PARAGRAPH_COMPLETION'; readonly relation: DiscourseRelation; readonly candidate_relations: Readonly<Record<OptionId, DiscourseRelation | null>>; readonly anchors: Readonly<Record<OptionId, AnchorChain>> }
  | { readonly kind: 'IRRELEVANT_SENTENCE'; readonly topic: string; readonly discourse_function: string }
  | { readonly kind: 'READING_COMPREHENSION'; readonly subtype: ReadingQuestionType };

export interface Question {
  readonly id: string;
  readonly family: QuestionFamily;
  readonly subclass?: GapFillSubclass | undefined;
  readonly science_domain?: string | undefined;
  readonly stem: string;
  readonly passage?: string | undefined;
  readonly options: readonly { readonly id: OptionId; readonly text: string }[];
  readonly correct_option: OptionId;
  readonly explanation: QuestionExplanation;
  readonly tactical: TacticalMetadata;
  readonly option_evidence: Readonly<Record<OptionId, readonly TacticalCheck[]>>;
  readonly difficulty?: number | undefined;
  readonly lexical_ids?: readonly string[] | undefined;
  readonly skill_ids: readonly SkillId[];
  readonly global_benchmark_ms?: number | undefined;
  readonly personal_benchmark_ms?: number | undefined;
  readonly provenance: 'ORIGINAL_PRACTICE';
}
export interface ErrorAttribution {
  readonly probabilities: Readonly<Partial<Record<ErrorCategory, number>>>;
  readonly primary_category: ErrorCategory | null;
  readonly confidence: number;
}
/** Separate from Phase 1 LexicalAttempt, including its historical table name. */
export interface QuestionAttempt {
  readonly id: string;
  readonly question_id: string;
  readonly session_id: string | null;
  readonly family: QuestionFamily;
  readonly subclass?: GapFillSubclass | undefined;
  readonly selected_option: OptionId;
  readonly is_correct: boolean;
  readonly response_time_ms: number;
  readonly confidence_level: ConfidenceLevel | null;
  readonly eliminated_options: readonly OptionId[];
  readonly distractor_flagged: readonly OptionId[];
  readonly words_clicked: readonly string[];
  readonly hints_used_count: number;
  readonly option_change_count: number;
  readonly attempted_at: number;
  /** Null for correct answers. Uncertain errors may have a null primary category. */
  readonly error_attribution: ErrorAttribution | null;
}
