import type { SkillEvidence } from '../../types/evidence';
import type { LearnerSkillVector } from '../../types/learner';
import { deepFreeze } from '../questions/attempts';
import { learnerSkillVectorSchema } from '../validation';
import { aggregateEvidence } from './aggregateEvidence';

/** `history` MUST contain the full history of each affected skill, not a new-event delta.
 * `current` is a cache for untouched dimensions, never a learned prior. Persistence rebuilds from all events.
 */
export function updateLearnerSkillVector(current: LearnerSkillVector, history: readonly SkillEvidence[], asOf?: number): LearnerSkillVector {
  const next = { ...learnerSkillVectorSchema.parse(current) };
  for (const aggregate of aggregateEvidence(history, asOf)) {
    if (next[aggregate.skill_id].evidence_count > aggregate.metrics.evidence_count) throw new RangeError('Full evidence history is required');
    next[aggregate.skill_id] = aggregate.metrics;
  }
  return deepFreeze(learnerSkillVectorSchema.parse(next));
}
