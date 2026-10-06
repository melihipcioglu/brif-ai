import { ERROR_CATEGORIES } from '../../types/question';
import type { ErrorAttribution, ErrorCategory, Question, QuestionAttempt } from '../../types/question';
import { errorAttributionSchema } from './validation';

/** Explainable, uncalibrated evidence mixture. Never presented as a causal diagnosis. */
export function attributeQuestionError(question: Question, attempt: Pick<QuestionAttempt, 'is_correct' | 'selected_option' | 'words_clicked' | 'response_time_ms'>): ErrorAttribution | null {
  if (attempt.is_correct) return null;
  const weights: Record<ErrorCategory, number> = { VOCABULARY: 1, CONNECTOR: 1, GRAMMAR: 1, DISTRACTOR: 1, READING_INFERENCE: 1, TIME_PRESSURE: 1, CARELESS: 1, UNKNOWN_TERMINOLOGY: 1 };
  const patterns = question.explanation.option_analysis.find((a) => a.option_id === attempt.selected_option)?.patterns ?? [];
  for (const pattern of patterns) {
    const category: ErrorCategory = pattern === 'FALSE_FRIEND' ? 'VOCABULARY' : pattern === 'TEMPORAL_MISMATCH' ? 'GRAMMAR' :
      pattern === 'CAUSE_EFFECT_REVERSAL' ? 'CONNECTOR' : pattern === 'UNSUPPORTED_DETAIL' ? 'READING_INFERENCE' : 'DISTRACTOR';
    weights[category] += 2;
  }
  // A help request is weak evidence; it cannot establish why an answer was wrong.
  if (attempt.words_clicked.length > 0) { weights.VOCABULARY += 0.25; weights.UNKNOWN_TERMINOLOGY += 0.25; }
  const benchmark = question.personal_benchmark_ms ?? question.global_benchmark_ms;
  if (benchmark !== undefined && attempt.response_time_ms > benchmark * 1.5) weights.TIME_PRESSURE += 0.25;
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  const probabilities = Object.fromEntries(ERROR_CATEGORIES.map((category) => [category, weights[category] / total])) as Record<ErrorCategory, number>;
  const ranked = [...ERROR_CATEGORIES].sort((a, b) => probabilities[b] - probabilities[a]);
  const first = ranked[0];
  const second = ranked[1];
  const primary = first !== undefined && second !== undefined && patterns.length > 0 && probabilities[first] > probabilities[second] ? first : null;
  return errorAttributionSchema.parse({ probabilities, primary_category: primary, confidence: primary === null ? 0 : Math.min(0.6, probabilities[primary]) });
}
