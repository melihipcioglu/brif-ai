import type { PerformanceCoverage, PerformanceEvidence } from '../../types/performance';
import type { QuestionFamily } from '../../types/question';
import type { SkillId } from '../../types/learner';
import { deepFreeze } from '../questions/attempts';
import { PERFORMANCE_V1 as C } from './calibration';

export function analyzePerformanceCoverage(records: readonly PerformanceEvidence[]): PerformanceCoverage {
  const family_counts = Object.fromEntries(C.required_families.map((f) => [f, 0])) as Record<QuestionFamily, number>;
  const skill_counts = Object.fromEntries(C.required_skills.map((s) => [s, 0])) as Record<Exclude<SkillId, 'PACING_STAMINA'>, number>;
  const blocks = new Map<string, number>(), sessions = new Map<string, number>();
  const seen = new Set<string>(), questions = new Set<string>();
  for (const e of records) {
    if (seen.has(e.attempt_id) || questions.has(e.question_id) || !C.required_families.includes(e.family) || !C.required_skills.includes(e.primary_skill)) throw new RangeError('Coverage requires unique, validated evidence');
    seen.add(e.attempt_id); questions.add(e.question_id); family_counts[e.family] += 1; skill_counts[e.primary_skill] += 1;
    blocks.set(e.block_id, (blocks.get(e.block_id) ?? 0) + 1); sessions.set(e.session_id, (sessions.get(e.session_id) ?? 0) + 1);
  }
  const concentration = (counts: readonly number[]): number => records.length === 0 ? 0 : Math.max(0, ...counts) / records.length;
  return deepFreeze({ family_counts, skill_counts,
    covered_families: C.required_families.filter((f) => family_counts[f] > 0),
    missing_families: C.required_families.filter((f) => family_counts[f] === 0),
    underrepresented_families: C.required_families.filter((f) => family_counts[f] > 0 && family_counts[f] < C.min_questions_per_family),
    covered_skills: C.required_skills.filter((s) => skill_counts[s] > 0),
    missing_skills: C.required_skills.filter((s) => skill_counts[s] === 0),
    underrepresented_skills: C.required_skills.filter((s) => skill_counts[s] > 0 && skill_counts[s] < C.min_questions_per_skill),
    block_count: blocks.size, session_count: sessions.size, family_concentration: concentration(Object.values(family_counts)),
    block_concentration: concentration([...blocks.values()]), session_concentration: concentration([...sessions.values()]) });
}
