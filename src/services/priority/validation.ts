import { z } from 'zod';
import { SKILL_IDS } from '../../types/learner';
import { TRAINING_ACTION_KINDS } from '../../types/priority';
import { idSchema, timestampSchema } from '../validation';

const fraction = z.number().finite().min(0).max(1);
const count = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
export const skillEvidenceCoverageSchema = z.strictObject({
  informative_attempt_count: count, question_count: count, family_count: count.max(8),
  unaided_attempt_count: count, transfer_attempt_count: count, last_informative_at: timestampSchema.nullable(),
}).superRefine((c, ctx) => {
  if (c.question_count > c.informative_attempt_count || c.family_count > c.question_count ||
    c.unaided_attempt_count > c.informative_attempt_count || c.transfer_attempt_count > c.unaided_attempt_count ||
    (c.informative_attempt_count === 0) !== (c.last_informative_at === null) ||
    (c.informative_attempt_count > 0 && (c.question_count === 0 || c.family_count === 0))) {
    ctx.addIssue({ code: 'custom', message: 'Inconsistent evidence coverage' });
  }
});
export const evidenceCoverageMapSchema = z.partialRecord(z.enum(SKILL_IDS), skillEvidenceCoverageSchema);
export const skillTrainingProfileSchema = z.strictObject({
  exam_relevance: fraction, trainability: fraction,
  retention_window_days: z.number().finite().min(1).max(3_650),
  target_question_count: z.number().int().min(1).max(10_000), target_family_count: z.number().int().min(1).max(8),
});
export const priorityModelConfigSchema = z.strictObject({
  version: z.literal('priority-v1'), evidence_saturation_k: z.number().finite().min(1).max(10_000),
  question_breadth_weight: fraction, unsupported_practice_floor: fraction,
  uncertainty_diagnostic_weight: fraction, retention_mastery_floor: fraction,
  minimum_effective_minutes: z.number().finite().min(1).max(1_440),
  weights: z.strictObject({ practice: fraction, diagnostic: fraction, retention: fraction }), default_profile: skillTrainingProfileSchema,
}).refine((c) => Math.abs(c.weights.practice + c.weights.diagnostic + c.weights.retention - 1) < 1e-9, 'Priority weights must sum to 1');
export const priorityContextSchema = z.strictObject({
  as_of: timestampSchema, coverage: evidenceCoverageMapSchema.optional(),
  profiles: z.partialRecord(z.enum(SKILL_IDS), skillTrainingProfileSchema).optional(),
});
export const trainingActionSchema = z.strictObject({
  id: idSchema, title: z.string().trim().min(1).max(300), kind: z.enum(TRAINING_ACTION_KINDS),
  format: z.enum(['SINGLE_QUESTION', 'QUESTION_SET', 'TIMED_BLOCK']), available: z.boolean(),
  expected_minutes: z.number().finite().min(1).max(1_440),
  targets: z.array(z.strictObject({ skill_id: z.enum(SKILL_IDS), weight: fraction.refine((w) => w > 0, 'Target weight must be positive') })).min(1).max(13),
}).superRefine((a, ctx) => {
  if (new Set(a.targets.map((t) => t.skill_id)).size !== a.targets.length) ctx.addIssue({ code: 'custom', message: 'Duplicate target skill' });
  if (Math.abs(a.targets.reduce((sum, t) => sum + t.weight, 0) - 1) >= 1e-9) ctx.addIssue({ code: 'custom', message: 'Target weights must sum to 1' });
});
export const trainingActionsSchema = z.array(trainingActionSchema).max(10_000).refine((actions) => new Set(actions.map((a) => a.id)).size === actions.length, 'Duplicate action IDs');
export const availableMinutesSchema = z.number().finite().min(0).max(1_440);
