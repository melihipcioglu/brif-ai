import { SKILL_IDS } from '../../types/learner';
import { QUESTION_FAMILIES } from '../../types/question';
import { deepFreeze } from '../questions/attempts';

export const DEFAULT_CONFIDENCE_LEVEL = 0.95 as const;
export const WILSON_Z_95 = 1.959963984540054;
export const PERFORMANCE_CONTENT_SKILLS = Object.freeze(SKILL_IDS.filter((s) => s !== 'PACING_STAMINA'));
/** Editorial release gates, NOT empirical calibration. Rationale and sensitivity are in the audit. */
export const PERFORMANCE_V1 = deepFreeze({
  version: 'performance-range-v1' as const,
  required_families: QUESTION_FAMILIES,
  required_skills: PERFORMANCE_CONTENT_SKILLS,
  min_questions: PERFORMANCE_CONTENT_SKILLS.length * 5, // 60; not an assumed exam length
  min_questions_per_family: 5,
  min_questions_per_skill: 3,
  min_blocks: 4,
  min_sessions: 2,
  max_family_fraction: 0.35,
  max_block_fraction: 0.35,
  max_session_fraction: 0.65,
  max_interval_width: 0.25,
  max_age_ms: 30 * 86_400_000,
});
