import type { SkillEvidence } from '../../types/evidence';
import type { SkillId, SkillMetrics } from '../../types/learner';
import { deepFreeze } from '../questions/attempts';
import { timestampSchema } from '../validation';
import { EVIDENCE_DAY_MS, EVIDENCE_V1 as C } from './calibration';
import { uniqueEvidence } from './validation';

export interface SkillAggregate {
  readonly skill_id: SkillId;
  readonly positive_mass: number;
  readonly negative_mass: number;
  readonly family_count: number;
  readonly question_count: number;
  readonly metrics: SkillMetrics;
}
const ratio = (numerator: number, denominator: number): number => denominator === 0 ? 0 : Math.min(1, Math.max(0, numerator / denominator));

/** Full-history calculation with a fixed conservative prior; never accumulate on top of a snapshot. */
export function aggregateEvidence(history: readonly SkillEvidence[], asOf?: number): readonly SkillAggregate[] {
  const rows = uniqueEvidence(history);
  const latest = rows.reduce((time, row) => Math.max(time, row.created_at), 0);
  const now = timestampSchema.parse(asOf ?? latest);
  if (now < latest) throw new RangeError('Aggregation time precedes evidence');
  const bySkill = new Map<SkillId, SkillEvidence[]>();
  for (const row of rows) {
    const group = bySkill.get(row.skill_id) ?? [];
    group.push(row); bySkill.set(row.skill_id, group);
  }
  return deepFreeze([...bySkill].map(([skill_id, evidence]) => {
    const masses = new Map<string, { positive: number; negative: number }>();
    let unaidedTotal = 0, unaidedCorrect = 0, assistedTotal = 0, assistedCorrect = 0, errors = 0, resultTotal = 0;
    const resultAttempts = new Set<string>();
    for (const row of evidence) {
      const recent = C.recency_floor + (1 - C.recency_floor) * Math.exp(-(now - row.created_at) / (C.recency_days * EVIDENCE_DAY_MS));
      const mass = row.strength * row.reliability * recent;
      const entry = masses.get(row.attempt_id) ?? { positive: 0, negative: 0 };
      if (row.direction === 'POSITIVE') entry.positive += mass;
      if (row.direction === 'NEGATIVE') entry.negative += mass;
      masses.set(row.attempt_id, entry);
      if (row.source === 'QUESTION_RESULT' || row.source === 'TRANSFER') {
        if (resultAttempts.has(row.attempt_id)) throw new RangeError('Multiple result rows for one attempt and skill');
        resultAttempts.add(row.attempt_id);
        const weight = row.mapping_weight;
        if (row.assisted) { assistedTotal += weight; if (row.outcome_correct) assistedCorrect += weight; }
        else { unaidedTotal += weight; if (row.outcome_correct) unaidedCorrect += weight; }
        resultTotal += weight;
        if (!row.outcome_correct) errors += weight * (row.attribution_weight ?? 0);
      }
    }
    let positive = 0, negative = 0;
    for (const mass of masses.values()) {
      // One question cannot become multiple full trials through result + tactical evidence.
      const scale = 1 / Math.max(1, mass.positive + mass.negative);
      positive += mass.positive * scale; negative += mass.negative * scale;
    }
    const informative = evidence.filter((e) => e.strength * e.reliability > 0);
    const family_count = new Set(informative.map((e) => e.question_family)).size;
    const question_count = new Set(informative.map((e) => e.question_id)).size;
    const floor = family_count < 2 ? C.single_family_uncertainty_floor : question_count < 3 ? C.low_question_coverage_floor : C.uncertainty_floor;
    return { skill_id, positive_mass: positive, negative_mass: negative, family_count, question_count,
      metrics: { mastery: ratio(positive, C.prior_negative_mass + positive + negative), evidence_count: masses.size,
        unaided_accuracy: ratio(unaidedCorrect, unaidedTotal), assisted_accuracy: ratio(assistedCorrect, assistedTotal),
        recency: evidence.reduce((latestTime, e) => Math.max(latestTime, e.created_at), 0),
        uncertainty: Math.max(floor, 1 / (1 + (positive + negative) / C.uncertainty_scale)), error_rate: ratio(errors, resultTotal) } };
  }));
}
