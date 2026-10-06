import type { SessionConfig } from '../../types/session';
import { deepFreeze } from '../questions/attempts';

/** Editorial v1 heuristics, not measured pedagogical or physiological constants. */
export const SESSION_V1: SessionConfig = deepFreeze({
  version: 'session-v1', mode_minutes: { EMERGENCY: 10, NORMAL: 25, INTENSIVE: 50 },
  lexical_reserve_fraction: 0.25, max_single_skill_fraction: 0.45,
  diagnostic_fraction: 0.25, cold_start_diagnostic_fraction: 0.6,
  family_coverage_floor: 2, max_consecutive_high: 1,
  question_default_minutes: 2, lexical_default_minutes: 1 / 3, speed_min_samples: 3,
  idle_lease_ms: 30_000, inactivity_ms: 120_000, ordering: 'MEDIUM_FIRST_LIGHT_FINISH',
});
export const PACING_V1 = Object.freeze({
  min_questions: 5, min_active_ms: 180_000, min_completion: 0.8, max_assisted_fraction: 0.2,
  min_accuracy_for_timing: 0.7, on_time_ratio: 1.1, overrun_ratio: 1.5,
  strength: 0.3, reliability: 0.5, degradation_min_questions: 8,
});
