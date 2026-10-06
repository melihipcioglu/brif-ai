import type { LearnerSkillVector } from '../../types/learner';
import type { ActionExclusionCode, NextBestActionPlan, PriorityContext, PriorityModelConfig, RankedTrainingAction, TrainingAction, TrainingActionKind } from '../../types/priority';
import { deepFreeze } from '../questions/attempts';
import { PRIORITY_V1 } from './calibration';
import { buildScoreLeakMap } from './scoreLeak';
import { availableMinutesSchema, trainingActionsSchema } from './validation';

const EXPLANATIONS: Readonly<Record<TrainingActionKind, string>> = {
  DIAGNOSTIC: 'Kanıt kapsamını genişletmek ve belirsizliği azaltmak için önerilen değerlendirme.',
  TARGETED_PRACTICE: 'Kanıt temelli beceri açığına yönelik çalışma; uygunluk ve süre maliyeti birlikte değerlendirildi.',
  RETENTION_REVIEW: 'Geçmiş kanıtın yaşı ve beceri desteği nedeniyle önerilen tekrar.',
};

/** Pure recommendation. No scheduling, attempt execution, learner mutation, or persistence writes. */
export function planNextBestAction(
  learner: LearnerSkillVector,
  candidates: readonly TrainingAction[],
  context: PriorityContext,
  availableMinutes: number,
  config: PriorityModelConfig = PRIORITY_V1,
): NextBestActionPlan {
  const score_leak_map = buildScoreLeakMap(learner, context, config);
  const actions = trainingActionsSchema.parse(candidates);
  const available_minutes = availableMinutesSchema.parse(availableMinutes);
  const bySkill = new Map(score_leak_map.skills.map((row) => [row.skill_id, row]));
  const ranked: RankedTrainingAction[] = [];
  const excluded: { action_id: string; reasons: ActionExclusionCode[] }[] = [];
  for (const action of actions) {
    const reasons: ActionExclusionCode[] = [];
    if (!action.available) reasons.push('UNAVAILABLE');
    if (action.expected_minutes > available_minutes) reasons.push('OVER_TIME_BUDGET');
    if (action.format !== 'TIMED_BLOCK' && action.targets.some((t) => t.skill_id === 'PACING_STAMINA')) reasons.push('PACING_REQUIRES_TIMED_BLOCK');
    const contributions = action.targets.map((target) => {
      const row = bySkill.get(target.skill_id);
      if (row === undefined) throw new RangeError('Unknown target skill');
      const aligned_need = action.kind === 'DIAGNOSTIC' ? row.diagnostic_need : action.kind === 'RETENTION_REVIEW' ? row.retention_need : row.practice_need;
      if (action.kind === 'RETENTION_REVIEW' && row.retention_need === 0 && !reasons.includes('NO_SUPPORTED_REVIEW')) reasons.push('NO_SUPPORTED_REVIEW');
      return { skill_id: target.skill_id, target_weight: target.weight, aligned_need, exam_relevance: row.profile.exam_relevance,
        trainability: row.profile.trainability, value_index: 100 * target.weight * aligned_need * row.profile.exam_relevance * row.profile.trainability };
    });
    const training_value_index = Math.min(100, contributions.reduce((sum, item) => sum + item.value_index, 0));
    if (training_value_index <= 0) reasons.push('NO_TRAINING_VALUE');
    if (reasons.length > 0) { excluded.push({ action_id: action.id, reasons }); continue; }
    const effective_minutes = Math.max(score_leak_map.config.minimum_effective_minutes, action.expected_minutes);
    ranked.push({ action, contributions, training_value_index, effective_minutes,
      expected_training_value: training_value_index / effective_minutes, value_unit: 'PRIORITY_INDEX_PER_MINUTE', explanation: EXPLANATIONS[action.kind] });
  }
  // Deterministic tie-breaking is independent of caller order and locale.
  ranked.sort((a, b) => b.expected_training_value - a.expected_training_value || b.training_value_index - a.training_value_index ||
    a.action.expected_minutes - b.action.expected_minutes || (a.action.id < b.action.id ? -1 : a.action.id > b.action.id ? 1 : 0));
  excluded.sort((a, b) => a.action_id < b.action_id ? -1 : a.action_id > b.action_id ? 1 : 0);
  return deepFreeze({ score_leak_map, available_minutes, status: ranked.length > 0 ? 'RECOMMENDED' : 'NO_ELIGIBLE_ACTION',
    selected: ranked[0] ?? null, ranked_actions: ranked, excluded_actions: excluded });
}
