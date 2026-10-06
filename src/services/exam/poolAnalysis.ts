import { z } from 'zod';
import type { ExamBlueprint, ExamContentSkill, ExamPoolAdequacy, ExamPoolAnalysis, ExamPoolContext, ExamForm, PoolExclusion } from '../../types/exam';
import type { Question, QuestionFamily } from '../../types/question';
import { QUESTION_FAMILIES } from '../../types/question';
import { PERFORMANCE_CONTENT_SKILLS } from '../performance/calibration';
import { questionAttemptSchema, questionSchema } from '../questions/validation';
import { primaryQuestionSkill } from '../evidence/mapping';
import { canonicalEvidence } from '../evidence/validation';
import { timestampSchema } from '../validation';
import { deepFreeze } from '../questions/attempts';
import { validateExamBlueprint } from './blueprint';
import { allocateMinimums, cellKey } from './allocation';
import { compareText, questionContentKey } from './provenance';

const exposureSchema = z.strictObject({ question_id: z.string().min(1).max(200), state: z.enum(['SEEN', 'UNSEEN']), observed_at: timestampSchema,
  method: z.enum(['RECORDED_EXPOSURE', 'CONTROLLED_INVENTORY']), reference: z.string().trim().min(1).max(500) }).refine((e) => e.state !== 'UNSEEN' || e.method === 'CONTROLLED_INVENTORY', 'UNSEEN requires a controlled inventory reference');
export interface PreparedPool { readonly questions: readonly Question[]; readonly exposure: ExamForm['exposure']; readonly report: ExamPoolAdequacy }
export function preparePool(blueprint: ExamBlueprint, pool: readonly unknown[], context: ExamPoolContext): PreparedPool {
  timestampSchema.parse(context.as_of);
  if (blueprint.source.verification === 'OFFICIAL_VERIFIED' && blueprint.source.verified_at > context.as_of) throw new RangeError('Blueprint verification is in the future');
  const history = context.prior_attempts.map((a) => questionAttemptSchema.parse(a));
  const observations = context.exposures.map((e) => exposureSchema.parse(e));
  if (history.some((a) => a.attempted_at > context.as_of) || observations.some((e) => e.observed_at > context.as_of)) throw new RangeError('Future exposure history');
  const groups = new Map<string, Question[]>(), excluded: PoolExclusion[] = [];
  for (const raw of pool) {
    const parsed = questionSchema.safeParse(raw);
    if (!parsed.success) { const id = z.object({ id: z.string() }).safeParse(raw); excluded.push({ question_id: id.success ? id.data.id : 'unidentified', reason: 'INVALID_QUESTION' }); continue; }
    const q = parsed.data, group = groups.get(q.id) ?? []; group.push(q); groups.set(q.id, group);
  }
  const valid: Question[] = [];
  for (const [id, group] of [...groups].sort(([a], [b]) => compareText(a, b))) {
    if (new Set(group.map(canonicalEvidence)).size > 1) { excluded.push({ question_id: id, reason: 'CONFLICTING_ID' }); continue; }
    valid.push(group[0]!); if (group.length > 1) excluded.push({ question_id: id, reason: 'DUPLICATE_ID' });
  }
  const seenIds = new Set(history.map((a) => a.question_id));
  for (const e of observations) if (e.state === 'SEEN') seenIds.add(e.question_id);
  const seenContent = new Set(valid.filter((q) => seenIds.has(q.id)).map(questionContentKey));
  const unique: Question[] = [], content = new Set<string>(), exposure: Record<string, ExamForm['exposure'][string]> = {};
  for (const q of valid) {
    const key = questionContentKey(q);
    if (content.has(key)) { excluded.push({ question_id: q.id, reason: 'DUPLICATE_CONTENT' }); continue; }
    content.add(key); unique.push(q);
  }
  const novelty = { UNSEEN: 0, SEEN: 0, UNKNOWN: 0 }, eligible: Question[] = [];
  for (const q of unique) {
    if (!(blueprint.family_targets[q.family] ?? 0)) { excluded.push({ question_id: q.id, reason: 'FAMILY_NOT_REQUESTED' }); continue; }
    const refs = observations.filter((e) => e.question_id === q.id);
    const seen = seenIds.has(q.id) || seenContent.has(questionContentKey(q));
    // An old clean inventory does not prove novelty at form construction time.
    const state = seen ? 'SEEN' : refs.some((e) => e.state === 'UNSEEN' && e.observed_at === context.as_of) ? 'UNSEEN' : 'UNKNOWN';
    exposure[q.id] = { state, references: [...new Set([...refs.map((e) => e.reference), ...history.filter((a) => a.question_id === q.id).map((a) => `attempt:${a.id}`),
      ...valid.filter((other) => other.id !== q.id && seenIds.has(other.id) && questionContentKey(other) === questionContentKey(q)).map((other) => `seen-content-alias:${other.id}`)])].sort(compareText) };
    novelty[state] += 1;
    if (state === 'SEEN' && blueprint.reuse_policy !== 'ALLOW_REUSE') { excluded.push({ question_id: q.id, reason: 'SEEN' }); continue; }
    if (state === 'UNKNOWN' && blueprint.reuse_policy === 'UNSEEN_ONLY') { excluded.push({ question_id: q.id, reason: 'UNKNOWN_EXPOSURE' }); continue; }
    eligible.push(q);
  }
  const families = Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, 0])) as Record<QuestionFamily, number>;
  const skills = Object.fromEntries(PERFORMANCE_CONTENT_SKILLS.map((s) => [s, 0])) as Record<ExamContentSkill, number>;
  const capacities = new Map<string, number>();
  for (const q of eligible) { const s = primaryQuestionSkill(q); if (s === 'PACING_STAMINA') throw new RangeError('Invalid content skill');
    families[q.family]++; skills[s]++; const key = cellKey(q.family, s); capacities.set(key, (capacities.get(key) ?? 0) + 1); }
  const family_shortfalls = Object.fromEntries(QUESTION_FAMILIES.filter((f) => (blueprint.family_targets[f] ?? 0) > families[f]).map((f) => [f, blueprint.family_targets[f]! - families[f]]));
  const skill_shortfalls = Object.fromEntries(PERFORMANCE_CONTENT_SKILLS.filter((s) => (blueprint.skill_minimums[s] ?? 0) > skills[s]).map((s) => [s, blueprint.skill_minimums[s]! - skills[s]]));
  const allocation = allocateMinimums(blueprint, capacities);
  return deepFreeze({ questions: eligible, exposure, report: { required: blueprint.total_questions, available: unique.length, eligible: eligible.length,
    shortfall: Math.max(0, blueprint.total_questions - eligible.length), family_available: families, family_shortfalls, skill_available: skills, skill_shortfalls,
    novelty, novelty_shortfall: Math.max(0, blueprint.total_questions - novelty.UNSEEN), constraint_shortfall: allocation.shortfall,
    exclusions: excluded.sort((a, b) => compareText(a.question_id, b.question_id) || compareText(a.reason, b.reason)) } });
}
export function adequate(report: ExamPoolAdequacy): boolean {
  return report.shortfall === 0 && report.constraint_shortfall === 0 && Object.keys(report.family_shortfalls).length === 0 && Object.keys(report.skill_shortfalls).length === 0;
}
export function analyzeExamPool(blueprint: unknown, questions: readonly unknown[], context: ExamPoolContext): ExamPoolAnalysis {
  const parsed = validateExamBlueprint(blueprint);
  if (parsed.status === 'INVALID') return deepFreeze({ status: 'INVALID_BLUEPRINT', issues: parsed.issues });
  const prepared = preparePool(parsed.blueprint, questions, context);
  return deepFreeze({ status: adequate(prepared.report) ? 'ADEQUATE' : 'INSUFFICIENT_POOL', blueprint: parsed.blueprint, report: prepared.report });
}
