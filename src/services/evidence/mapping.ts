import type { SkillId } from '../../types/learner';
import type { CheckCriterion, ErrorCategory, Question } from '../../types/question';
import { tacticalSolvers } from '../questions/strategies';

export interface SkillMapping { readonly skill_id: SkillId; readonly weight: number }
export function primaryQuestionSkill(q: Question): SkillId {
  switch (q.tactical.kind) {
    case 'GAP_FILL': return ({ VOCAB: 'VOCAB_CONTEXT', GRAMMAR: 'TENSE_ASPECT', PREPOSITION: 'COLLOCATION_PREPOSITION', CONNECTOR: 'CONNECTOR_DISCOURSE', STRUCTURE: 'VOICE_REDUCTION' } as const)[q.tactical.focus];
    case 'CLOZE_TEST': return 'CONNECTOR_DISCOURSE';
    case 'SENTENCE_COMPLETION': return 'SENTENCE_COMPLETION';
    case 'TRANSLATION': return 'TRANSLATION_SEMANTICS';
    case 'PARAGRAPH_COMPLETION': return 'PARAGRAPH_COMPLETION';
    case 'IRRELEVANT_SENTENCE': return 'COHESION_COHERENCE';
    case 'READING_COMPREHENSION': return ({ DETAIL: 'READING_DETAIL', INFERENCE: 'READING_INFERENCE', MAIN_IDEA: 'MAIN_IDEA', REFERENCE: 'COHESION_COHERENCE', PURPOSE: 'READING_INFERENCE' } as const)[q.tactical.subtype];
  }
}
const criterionSkill: Partial<Record<CheckCriterion, SkillId>> = {
  SEMANTIC_FIT: 'VOCAB_CONTEXT', COLLOCATION: 'COLLOCATION_PREPOSITION',
  TENSE_ASPECT: 'TENSE_ASPECT', TEMPORAL_CONTEXT: 'TENSE_ASPECT',
  VOICE: 'VOICE_REDUCTION', REDUCTION: 'VOICE_REDUCTION',
  DISCOURSE_RELATION: 'CONNECTOR_DISCOURSE', REFERENT: 'COHESION_COHERENCE',
  CONTINUATION: 'COHESION_COHERENCE', LEXICAL_CONTINUITY: 'COHESION_COHERENCE',
};
/** Relative editorial weights: primary 1, declared secondary .6, observed tactical focus .3. */
export function mapQuestionSkills(q: Question): readonly SkillMapping[] {
  const weights = new Map<SkillId, number>();
  for (const skill of q.skill_ids) if (skill !== 'PACING_STAMINA') weights.set(skill, 0.6);
  weights.set(primaryQuestionSkill(q), 1);
  const checks = tacticalSolvers[q.family].verify(q, q.correct_option, { eliminated_options: [] }).checks;
  for (const check of checks) {
    const skill = criterionSkill[check.criterion];
    if (skill !== undefined && check.matches !== null) weights.set(skill, Math.max(weights.get(skill) ?? 0, 0.3));
  }
  const total = [...weights.values()].reduce((sum, w) => sum + w, 0);
  return [...weights].map(([skill_id, weight]) => ({ skill_id, weight: weight / total }));
}

/** Unallocated CARELESS/TIME_PRESSURE and unrelated signals remain unallocated, never renormalized. */
export function allocateAttribution(q: Question, mapping: readonly SkillMapping[], signals: Readonly<Partial<Record<ErrorCategory, number>>>): ReadonlyMap<SkillId, number> {
  const result = new Map<SkillId, number>();
  const routes: Readonly<Partial<Record<ErrorCategory, readonly SkillId[]>>> = {
    VOCABULARY: ['VOCAB_CONTEXT'], UNKNOWN_TERMINOLOGY: ['VOCAB_CONTEXT'], CONNECTOR: ['CONNECTOR_DISCOURSE'],
    GRAMMAR: ['TENSE_ASPECT', 'VOICE_REDUCTION'], READING_INFERENCE: ['READING_INFERENCE'], DISTRACTOR: [primaryQuestionSkill(q)],
  };
  for (const [category, targets] of Object.entries(routes)) {
    const candidates = mapping.filter((m) => targets.includes(m.skill_id));
    const total = candidates.reduce((sum, m) => sum + m.weight, 0);
    if (total === 0) continue;
    const signal = signals[category as ErrorCategory] ?? 0;
    for (const m of candidates) result.set(m.skill_id, Math.min(1, (result.get(m.skill_id) ?? 0) + signal * (m.weight / total)));
  }
  return result;
}
