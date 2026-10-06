import { z } from 'zod';
import { SKILL_IDS } from '../../types/learner';
import { SESSION_BLOCK_TYPES, SESSION_MODES } from '../../types/session';
import type { SessionPlan } from '../../types/session';
import { idSchema, timestampSchema } from '../validation';
import { trainingActionSchema } from '../priority/validation';

export const longId = z.string().min(1).max(2_000);
const fraction = z.number().finite().min(0).max(1);
const minutes = z.number().finite().positive().max(180);
const ids = z.array(idSchema).max(1_000).refine((a) => new Set(a).size === a.length, 'Duplicate item IDs');
export const sessionConfigSchema = z.strictObject({
  version: z.literal('session-v1'), mode_minutes: z.record(z.enum(SESSION_MODES), minutes),
  lexical_reserve_fraction: fraction.max(0.5), max_single_skill_fraction: fraction.positive(),
  diagnostic_fraction: fraction, cold_start_diagnostic_fraction: fraction,
  family_coverage_floor: z.number().int().min(1).max(8), max_consecutive_high: z.number().int().min(1).max(10),
  question_default_minutes: minutes.min(1), lexical_default_minutes: minutes.min(1 / 60),
  speed_min_samples: z.number().int().min(1).max(100), idle_lease_ms: z.number().int().min(1_000).max(60_000),
  inactivity_ms: z.number().int().min(15_000).max(600_000),
  ordering: z.enum(['MEDIUM_FIRST_LIGHT_FINISH', 'VALUE_FIRST']),
});
export const sessionCandidateSchema = z.strictObject({
  id: idSchema, type: z.enum(SESSION_BLOCK_TYPES), available: z.boolean(), expected_minutes: minutes,
  cognitive_load: z.enum(['LOW', 'MEDIUM', 'HIGH']), targets: trainingActionSchema.shape.targets,
  question_ids: ids, lexical_ids: ids, reflection_prompt: z.string().trim().min(1).max(2_000).optional(), timed_enabled: z.boolean(),
}).superRefine((c, ctx) => {
  const fail = (message: string): void => { ctx.addIssue({ code: 'custom', message }); };
  if (new Set(c.targets.map((t) => t.skill_id)).size !== c.targets.length || Math.abs(c.targets.reduce((s, t) => s + t.weight, 0) - 1) > 1e-9) fail('Invalid target weights');
  if (c.type === 'LEXICAL_REVIEW' ? c.lexical_ids.length === 0 || c.question_ids.length > 0 : c.lexical_ids.length > 0) fail('Invalid lexical content');
  if (c.type === 'REFLECTION' ? c.reflection_prompt === undefined || c.question_ids.length > 0 : c.type !== 'LEXICAL_REVIEW' && c.question_ids.length === 0) fail('Missing real content');
  if (c.type !== 'TIMED_BLOCK' && (c.timed_enabled || c.targets.some((t) => t.skill_id === 'PACING_STAMINA'))) fail('Pacing requires timed context');
  if (c.type === 'TIMED_BLOCK' && !c.timed_enabled) fail('Explicit timed context required');
  if (c.type !== 'LEXICAL_REVIEW' && c.type !== 'REFLECTION' && c.expected_minutes < 1) fail('Question estimate must be at least one minute');
});
export const plannedBlockSchema = z.strictObject({
  id: longId, type: z.enum(SESSION_BLOCK_TYPES), target_skills: z.array(z.enum(SKILL_IDS)).min(1).max(13),
  planned_minutes: minutes, candidate_ids: ids.min(1), question_ids: ids, lexical_ids: ids,
  cognitive_load: z.enum(['LOW', 'MEDIUM', 'HIGH']), timed_enabled: z.boolean(), explanation: z.string().min(1).max(4_000),
});
export const sessionPlanSchema: z.ZodType<SessionPlan> = z.strictObject({
  id: idSchema, session_id: idSchema, mode: z.enum(SESSION_MODES), created_at: timestampSchema,
  planned_minutes: minutes, allocated_minutes: z.number().finite().min(0).max(180),
  blocks: z.array(plannedBlockSchema).max(1_000), notes: z.array(z.string().max(1_000)).max(100), config: sessionConfigSchema,
  creation_signature: z.string().max(100_000).optional(),
}).superRefine((p, ctx) => {
  const total = p.blocks.reduce((sum, b) => sum + b.planned_minutes, 0);
  if (Math.abs(total - p.allocated_minutes) > 1e-8 || total > p.planned_minutes + 1e-8) ctx.addIssue({ code: 'custom', message: 'Plan exceeds time budget or has an inconsistent total' });
  for (const keys of [p.blocks.map((b) => b.id), p.blocks.flatMap((b) => b.candidate_ids), p.blocks.flatMap((b) => b.question_ids), p.blocks.flatMap((b) => b.lexical_ids)]) {
    if (new Set(keys).size !== keys.length) ctx.addIssue({ code: 'custom', message: 'Repeated plan content' });
  }
  for (const b of p.blocks) {
    if (new Set(b.target_skills).size !== b.target_skills.length || b.timed_enabled !== (b.type === 'TIMED_BLOCK') ||
      (b.type === 'LEXICAL_REVIEW' ? b.lexical_ids.length === 0 || b.question_ids.length > 0 : b.lexical_ids.length > 0) ||
      (!['LEXICAL_REVIEW', 'REFLECTION'].includes(b.type) && b.question_ids.length === 0) ||
      (b.type === 'REFLECTION' && b.question_ids.length > 0)) ctx.addIssue({ code: 'custom', message: 'Invalid block content' });
  }
});
const simple = z.strictObject({ type: z.enum(['START', 'PAUSE', 'RESUME', 'FINISH', 'ABANDON']) });
export const sessionCommandSchema = z.union([
  simple, z.strictObject({ type: z.literal('PULSE'), engaged: z.boolean() }),
  z.strictObject({ type: z.enum(['START_BLOCK', 'COMPLETE_BLOCK']), block_id: longId }),
  z.strictObject({ type: z.literal('SKIP_BLOCK'), block_id: longId, reason: z.enum(['USER', 'FAILURE', 'ADAPTATION']) }),
  z.strictObject({ type: z.enum(['QUESTION', 'LEXICAL']), block_id: longId, attempt_id: idSchema, item_id: idSchema, retry_of: idSchema.nullable() }),
  z.strictObject({ type: z.literal('EXTEND'), plan: sessionPlanSchema }),
]);
export const sessionEventInputSchema = z.strictObject({ id: idSchema, session_id: idSchema, at: timestampSchema, command: sessionCommandSchema });
export const sessionEventSchema = sessionEventInputSchema.extend({ sequence: z.number().int().positive().max(1_000_000), attempt_ref: z.string().max(500).optional() });
