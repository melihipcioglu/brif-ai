import { z } from 'zod';
import type { ExamBlueprint } from '../../types/exam';
import { QUESTION_FAMILIES } from '../../types/question';
import { PERFORMANCE_CONTENT_SKILLS } from '../performance/calibration';
import { timestampSchema } from '../validation';
import { deepFreeze } from '../questions/attempts';
import { allocateMinimums, cellKey } from './allocation';
import { PRIMARY_FAMILIES } from './policies';

const text = z.string().trim().min(1).max(500), count = z.number().int().min(0).max(1_000);
export const blueprintSchema: z.ZodType<ExamBlueprint> = z.strictObject({
  id: text.max(100), version: text.max(100), scope: z.enum(['MINI', 'FULL']), total_questions: count.positive(),
  time_limit_ms: z.number().int().min(1_000).max(86_400_000),
  family_targets: z.partialRecord(z.enum(QUESTION_FAMILIES), count), skill_minimums: z.partialRecord(z.enum(PERFORMANCE_CONTENT_SKILLS), count),
  reuse_policy: z.enum(['ALLOW_REUSE', 'EXCLUDE_SEEN', 'UNSEEN_ONLY']),
  source: z.discriminatedUnion('verification', [
    z.strictObject({ verification: z.literal('UNVERIFIED'), reference: text.nullable() }),
    z.strictObject({ verification: z.literal('INTERNAL'), reference: text }),
    z.strictObject({ verification: z.literal('OFFICIAL_VERIFIED'), reference: text, verified_at: timestampSchema, verified_by: text }),
  ]),
}).superRefine((b, ctx) => {
  if (Object.values(b.family_targets).reduce((sum, n) => sum + n, 0) !== b.total_questions) ctx.addIssue({ code: 'custom', message: 'Family targets must sum to total_questions' });
  const capacity = new Map<string, number>();
  for (const s of PERFORMANCE_CONTENT_SKILLS) for (const f of PRIMARY_FAMILIES[s]) capacity.set(cellKey(f, s), b.family_targets[f] ?? 0);
  if (allocateMinimums(b, capacity).shortfall > 0) ctx.addIssue({ code: 'custom', message: 'Skill minima are impossible under family targets' });
});
export function validateExamBlueprint(input: unknown): { readonly status: 'VALID'; readonly blueprint: ExamBlueprint } | { readonly status: 'INVALID'; readonly issues: readonly string[] } {
  const parsed = blueprintSchema.safeParse(input);
  return parsed.success ? deepFreeze({ status: 'VALID', blueprint: parsed.data }) : deepFreeze({ status: 'INVALID', issues: parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).sort() });
}
