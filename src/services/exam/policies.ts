import type { ExamContentSkill } from '../../types/exam';
import type { QuestionFamily } from '../../types/question';
import { deepFreeze } from '../questions/attempts';

export const EXAM_FORM_POLICY = 'exam-form-policy-v1' as const;
export const CALIBRATION_POLICY = 'calibration-policy-v1' as const;
/** Routing mirrors frozen primaryQuestionSkill; it is not an official exam distribution. */
export const PRIMARY_FAMILIES: Readonly<Record<ExamContentSkill, readonly QuestionFamily[]>> = deepFreeze({
  VOCAB_CONTEXT: ['GAP_FILL'], COLLOCATION_PREPOSITION: ['GAP_FILL'], CONNECTOR_DISCOURSE: ['GAP_FILL', 'CLOZE_TEST'],
  TENSE_ASPECT: ['GAP_FILL'], VOICE_REDUCTION: ['GAP_FILL'], SENTENCE_COMPLETION: ['SENTENCE_COMPLETION'],
  TRANSLATION_SEMANTICS: ['TRANSLATION_ENG_TR', 'TRANSLATION_TR_ENG'], PARAGRAPH_COMPLETION: ['PARAGRAPH_COMPLETION'],
  COHESION_COHERENCE: ['IRRELEVANT_SENTENCE', 'READING_COMPREHENSION'], READING_DETAIL: ['READING_COMPREHENSION'],
  READING_INFERENCE: ['READING_COMPREHENSION'], MAIN_IDEA: ['READING_COMPREHENSION'],
});
