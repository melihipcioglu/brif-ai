export const SKILL_IDS = [
  'VOCAB_CONTEXT',
  'COLLOCATION_PREPOSITION',
  'CONNECTOR_DISCOURSE',
  'TENSE_ASPECT',
  'VOICE_REDUCTION',
  'SENTENCE_COMPLETION',
  'TRANSLATION_SEMANTICS',
  'PARAGRAPH_COMPLETION',
  'COHESION_COHERENCE',
  'READING_DETAIL',
  'READING_INFERENCE',
  'MAIN_IDEA',
  'PACING_STAMINA',
] as const;
export type SkillId = (typeof SKILL_IDS)[number];

export interface SkillMetrics {
  /** Proficiency in [0, 1]. ErrorProbability = 1 - mastery; multiply by 100 only for display. */
  readonly mastery: number;
  readonly evidence_count: number;
  /** Accuracy, uncertainty and error_rate are fractions in [0, 1]. */
  readonly unaided_accuracy: number;
  readonly assisted_accuracy: number;
  /** UTC epoch milliseconds of latest evidence, null if there is none. */
  readonly recency: number | null;
  readonly uncertainty: number;
  readonly error_rate: number;
}

/** All thirteen named dimensions are required; arbitrary keys are rejected. */
export type LearnerSkillVector = { readonly [K in SkillId]: SkillMetrics };

export function createLearnerSkillVector(): LearnerSkillVector {
  const metric = (): SkillMetrics => ({
    mastery: 0, evidence_count: 0, unaided_accuracy: 0, assisted_accuracy: 0,
    recency: null, uncertainty: 1, error_rate: 0,
  });
  return {
    VOCAB_CONTEXT: metric(), COLLOCATION_PREPOSITION: metric(),
    CONNECTOR_DISCOURSE: metric(), TENSE_ASPECT: metric(), VOICE_REDUCTION: metric(),
    SENTENCE_COMPLETION: metric(), TRANSLATION_SEMANTICS: metric(),
    PARAGRAPH_COMPLETION: metric(), COHESION_COHERENCE: metric(),
    READING_DETAIL: metric(), READING_INFERENCE: metric(), MAIN_IDEA: metric(),
    PACING_STAMINA: metric(),
  };
}
