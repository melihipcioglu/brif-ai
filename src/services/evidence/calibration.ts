import type { ConfidenceCalibrationRecord } from '../../types/evidence';
import type { QuestionAttempt } from '../../types/question';
import { deepFreeze } from '../questions/attempts';
import { questionAttemptSchema } from '../questions/validation';

/** Editorial v1 calibration parameters, NOT fitted probabilities or empirical skill priors. */
export const EVIDENCE_V1 = Object.freeze({
  correct_base: 0.8,
  incorrect_base: 0.8,
  assisted_factor: 0.55,
  hint_penalty: 0.15,
  word_penalty: 0.1,
  change_penalty: 0.1,
  difficulty_floor: 0.75,
  difficulty_range: 0.25,
  default_difficulty: 0.5,
  slow_floor: 0.7,
  elimination_floor: 0.9,
  practice_reliability: 0.7,
  transfer_reliability: 0.9,
  attribution_reliability_floor: 0.35,
  attribution_reliability_range: 0.25,
  relation_strength: 0.3,
  elimination_strength: 0.2,
  tactical_reliability: 0.4,
  transfer_delay_days: 14,
  prior_negative_mass: 8,
  recency_floor: 0.75,
  recency_days: 180,
  uncertainty_scale: 4,
  single_family_uncertainty_floor: 0.35,
  low_question_coverage_floor: 0.15,
  uncertainty_floor: 0.05,
});
export const CONFIDENCE_QUALITY_V1 = Object.freeze({ HIGH: 1, MEDIUM: 0.9, LOW: 0.7, UNSET: 0.9 });
export const EVIDENCE_DAY_MS = 86_400_000;

/** Kept separately for later calibration; does not assign a learner mastery value. */
export function extractConfidenceCalibration(attempt: QuestionAttempt): ConfidenceCalibrationRecord | null {
  const a = questionAttemptSchema.parse(attempt);
  return a.confidence_level === null ? null : deepFreeze({ attempt_id: a.id, confidence: a.confidence_level, correct: a.is_correct });
}
