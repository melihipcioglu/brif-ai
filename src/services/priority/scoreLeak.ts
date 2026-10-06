import { SKILL_IDS, type LearnerSkillVector } from '../../types/learner';
import type { PriorityContext, PriorityModelConfig, PriorityReasonCode, ScoreLeakMap, ScoreLeakPriority } from '../../types/priority';
import { deepFreeze } from '../questions/attempts';
import { learnerSkillVectorSchema } from '../validation';
import { PRIORITY_DAY_MS, PRIORITY_V1 } from './calibration';
import { priorityContextSchema, priorityModelConfigSchema } from './validation';

const unit = (value: number): number => Math.min(1, Math.max(0, value));

/** Score Leak is a relative training priority map, never an estimate of lost exam points. */
export function buildScoreLeakMap(learner: LearnerSkillVector, context: PriorityContext, config: PriorityModelConfig = PRIORITY_V1): ScoreLeakMap {
  const vector = learnerSkillVectorSchema.parse(learner);
  const ctx = priorityContextSchema.parse(context);
  const c = priorityModelConfigSchema.parse(config);
  const skills: ScoreLeakPriority[] = SKILL_IDS.map((skill_id) => {
    const metric = vector[skill_id];
    const coverage = ctx.coverage?.[skill_id] ?? null;
    const profile = ctx.profiles?.[skill_id] ?? c.default_profile;
    if (metric.recency !== null && metric.recency > ctx.as_of) throw new RangeError('Learner recency is in the future');
    if (coverage !== null && (coverage.informative_attempt_count > metric.evidence_count ||
      (coverage.last_informative_at !== null && (metric.recency === null || coverage.last_informative_at > metric.recency)))) {
      throw new RangeError('Coverage and learner snapshot are inconsistent');
    }
    // SkillGap is only an evidence-based gap index. No calibrated probability is inferred.
    const skill_gap = 1 - metric.mastery;
    const breadth = coverage === null ? 0 :
      c.question_breadth_weight * Math.min(1, coverage.question_count / profile.target_question_count) +
      (1 - c.question_breadth_weight) * Math.min(1, coverage.family_count / profile.target_family_count);
    const coverage_index = coverage === null ? 0 : unit(-Math.expm1(-coverage.informative_attempt_count / c.evidence_saturation_k) * breadth);
    const evidence_support = (1 - metric.uncertainty) * coverage_index;
    const practice_need = skill_gap * (c.unsupported_practice_floor + (1 - c.unsupported_practice_floor) * evidence_support);
    const diagnostic_need = unit(c.uncertainty_diagnostic_weight * metric.uncertainty + (1 - c.uncertainty_diagnostic_weight) * (1 - coverage_index));
    // Missing/neutral-only history creates no retention claim. Age never rewrites mastery.
    const last = coverage?.last_informative_at ?? null;
    const age_days = last === null ? null : (ctx.as_of - last) / PRIORITY_DAY_MS;
    const retention_need = age_days === null ? 0 : unit(-Math.expm1(-age_days / profile.retention_window_days) *
      evidence_support * (c.retention_mastery_floor + (1 - c.retention_mastery_floor) * metric.mastery));
    const priority_components = {
      practice: 100 * profile.exam_relevance * c.weights.practice * practice_need,
      diagnostic: 100 * profile.exam_relevance * c.weights.diagnostic * diagnostic_need,
      retention: 100 * profile.exam_relevance * c.weights.retention * retention_need,
    };
    const reasons: PriorityReasonCode[] = [];
    if (coverage_index < 0.5) reasons.push('LIMITED_COVERAGE');
    if (metric.uncertainty >= 0.5) reasons.push('UNCERTAIN_EVIDENCE');
    if (skill_gap >= 0.5 && evidence_support >= 0.25) reasons.push('SUPPORTED_SKILL_GAP');
    if (retention_need >= 0.25) reasons.push('RETENTION_NEED');
    if (profile.exam_relevance === 0) reasons.push('NO_EXAM_RELEVANCE');
    return { skill_id, skill_gap, uncertainty: metric.uncertainty, coverage_status: coverage === null ? 'UNKNOWN' : 'KNOWN',
      coverage, coverage_index, evidence_support, age_days, practice_need, diagnostic_need, retention_need,
      profile, priority_components, priority_index: Math.min(100, Math.max(0, Object.values(priority_components).reduce((a, b) => a + b, 0))), reasons };
  });
  skills.sort((a, b) => b.priority_index - a.priority_index || SKILL_IDS.indexOf(a.skill_id) - SKILL_IDS.indexOf(b.skill_id));
  return deepFreeze({ model_version: 'priority-v1', generated_at: ctx.as_of, interpretation: 'RELATIVE_TRAINING_PRIORITY',
    unit: 'INDEX_0_100', config: c, skills });
}
