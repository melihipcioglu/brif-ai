import { z } from 'zod';
import type { BuildExamFormRequest, ExamForm, ExamFormBuildResult } from '../../types/exam';
import { QUESTION_FAMILIES } from '../../types/question';
import { questionSchema } from '../questions/validation';
import { deepFreeze } from '../questions/attempts';
import { timestampSchema } from '../validation';
import { primaryQuestionSkill } from '../evidence/mapping';
import { PERFORMANCE_CONTENT_SKILLS } from '../performance/calibration';
import { blueprintSchema, validateExamBlueprint } from './blueprint';
import { adequate, preparePool } from './poolAnalysis';
import { allocateMinimums, cellKey } from './allocation';
import { compareText, fingerprint, questionContentKey } from './provenance';
import { EXAM_FORM_POLICY } from './policies';

const formSchema: z.ZodType<ExamForm> = z.strictObject({
  id: z.string().min(1).max(100), quality: z.enum(['COMPLETE', 'PARTIAL']), blueprint: blueprintSchema, created_at: timestampSchema,
  seed: z.string().max(200).nullable(), selection_policy: z.literal(EXAM_FORM_POLICY), question_ids: z.array(z.string().min(1).max(200)).min(1).max(1_000),
  questions: z.array(questionSchema).min(1).max(1_000),
  exposure: z.record(z.string(), z.strictObject({ state: z.enum(['SEEN', 'UNSEEN', 'UNKNOWN']), references: z.array(z.string().min(1).max(500)).max(10_000) })),
  fingerprint: z.string().regex(/^[a-f0-9]{16}$/),
});
/** Validates a portable form without treating its stored quality flag as proof. */
export function parseExamForm(raw: unknown): ExamForm {
  const form = formSchema.parse(raw), { fingerprint: stored, ...body } = form;
  if (stored !== fingerprint(body) || new Set(form.question_ids).size !== form.question_ids.length ||
    form.questions.length !== form.question_ids.length || form.questions.some((q, i) => q.id !== form.question_ids[i]) ||
    new Set(form.questions.map(questionContentKey)).size !== form.questions.length ||
    Object.keys(form.exposure).length !== form.questions.length || form.questions.some((q) => form.exposure[q.id] === undefined) ||
    Object.values(form.exposure).some((e) => e.state === 'UNSEEN' && e.references.length === 0)) throw new RangeError('Invalid form identity/content/novelty');
  const b = form.blueprint;
  if (b.source.verification === 'OFFICIAL_VERIFIED' && b.source.verified_at > form.created_at) throw new RangeError('Future blueprint verification');
  for (const f of QUESTION_FAMILIES) {
    const n = form.questions.filter((q) => q.family === f).length;
    if (n > (b.family_targets[f] ?? 0) || form.quality === 'COMPLETE' && n !== (b.family_targets[f] ?? 0)) throw new RangeError('Form violates family targets');
  }
  if (form.questions.length > b.total_questions || form.quality === 'COMPLETE' && form.questions.length !== b.total_questions) throw new RangeError('Form violates question count');
  if (form.quality === 'COMPLETE') for (const s of PERFORMANCE_CONTENT_SKILLS) {
    if (form.questions.filter((q) => primaryQuestionSkill(q) === s).length < (b.skill_minimums[s] ?? 0)) throw new RangeError('Form violates skill minimum');
  }
  if (Object.values(form.exposure).some((e) => b.reuse_policy === 'UNSEEN_ONLY' && e.state !== 'UNSEEN' || b.reuse_policy === 'EXCLUDE_SEEN' && e.state === 'SEEN')) throw new RangeError('Form violates reuse policy');
  return deepFreeze(form);
}
export function buildExamForm(request: BuildExamFormRequest): ExamFormBuildResult {
  const parsed = validateExamBlueprint(request.blueprint);
  if (parsed.status === 'INVALID') return deepFreeze({ status: 'INVALID_BLUEPRINT', form: null, issues: parsed.issues });
  const blueprint = parsed.blueprint, prepared = preparePool(blueprint, request.questions, request.context), complete = adequate(prepared.report);
  if (!complete && !request.allow_partial || prepared.questions.length === 0) return deepFreeze({ status: 'INSUFFICIENT_POOL', form: null, report: prepared.report });
  const seed = request.seed ?? null;
  const ranked = [...prepared.questions].sort((a, b) => seed === null ? compareText(a.id, b.id) : compareText(fingerprint([seed, a.id]), fingerprint([seed, b.id])) || compareText(a.id, b.id));
  const capacities = new Map<string, number>();
  for (const q of ranked) { const key = cellKey(q.family, primaryQuestionSkill(q)); capacities.set(key, (capacities.get(key) ?? 0) + 1); }
  const allocation = allocateMinimums(blueprint, capacities), chosen = new Set<string>();
  for (const [key, count] of allocation.cells) for (const q of ranked.filter((q) => cellKey(q.family, primaryQuestionSkill(q)) === key).slice(0, count)) chosen.add(q.id);
  for (const family of QUESTION_FAMILIES) {
    const already = ranked.filter((q) => chosen.has(q.id) && q.family === family).length;
    for (const q of ranked.filter((q) => q.family === family && !chosen.has(q.id)).slice(0, Math.max(0, (blueprint.family_targets[family] ?? 0) - already))) chosen.add(q.id);
  }
  const questions = ranked.filter((q) => chosen.has(q.id));
  if (questions.length === 0) return deepFreeze({ status: 'INSUFFICIENT_POOL', form: null, report: prepared.report });
  const quality = complete ? 'COMPLETE' : 'PARTIAL';
  const body = { id: request.id, quality, blueprint, created_at: request.context.as_of, seed, selection_policy: EXAM_FORM_POLICY,
    question_ids: questions.map((q) => q.id), questions, exposure: Object.fromEntries(questions.map((q) => [q.id, prepared.exposure[q.id]!])) };
  const form = parseExamForm({ ...body, fingerprint: fingerprint(body) });
  return deepFreeze({ status: quality, form, report: prepared.report });
}
