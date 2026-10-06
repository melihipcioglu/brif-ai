import type { PriorityModelConfig } from '../../types/priority';
import { deepFreeze } from '../questions/attempts';

/** Editorial v1 planning parameters. Not fitted to the 22 seed questions or calibrated exam data. */
export const PRIORITY_V1: PriorityModelConfig = deepFreeze({
  version: 'priority-v1',
  evidence_saturation_k: 8,
  question_breadth_weight: 0.6,
  unsupported_practice_floor: 0.25,
  uncertainty_diagnostic_weight: 0.6,
  retention_mastery_floor: 0.25,
  minimum_effective_minutes: 5,
  weights: { practice: 0.45, diagnostic: 0.35, retention: 0.2 },
  default_profile: {
    // Equal defaults avoid inventing exam frequencies or empirical trainability differences.
    exam_relevance: 1, trainability: 1, retention_window_days: 30,
    target_question_count: 5, target_family_count: 2,
  },
});
export const PRIORITY_DAY_MS = 86_400_000;
