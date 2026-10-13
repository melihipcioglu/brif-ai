import type { ExamBlueprint } from '../types/exam';
import { deepFreeze } from '../services/questions/attempts';

/**
 * ArcBrief internal 80-question practice blueprint (10 per family).
 * NOT an official ÖSYM/YÖKDİL distribution; source stays UNVERIFIED so it can never qualify as official calibration.
 * reuse_policy is the safest exposure policy; capacity analysis overrides it explicitly per tier.
 */
export const INTERNAL_FULL_BLUEPRINT_80: ExamBlueprint = deepFreeze({
  id: 'arcbrief-internal-full-80', version: '1', scope: 'FULL', total_questions: 80, time_limit_ms: 10_800_000,
  family_targets: { GAP_FILL: 10, CLOZE_TEST: 10, SENTENCE_COMPLETION: 10, TRANSLATION_ENG_TR: 10, TRANSLATION_TR_ENG: 10,
    PARAGRAPH_COMPLETION: 10, IRRELEVANT_SENTENCE: 10, READING_COMPREHENSION: 10 },
  skill_minimums: {}, reuse_policy: 'UNSEEN_ONLY',
  source: { verification: 'UNVERIFIED', reference: 'ArcBrief internal practice distribution, 10 per family; not an official distribution' },
});
