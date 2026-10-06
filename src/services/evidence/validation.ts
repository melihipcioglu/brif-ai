import { z } from 'zod';
import { SKILL_IDS } from '../../types/learner';
import { DISCOURSE_RELATIONS, QUESTION_FAMILIES } from '../../types/question';
import type { SkillEvidence } from '../../types/evidence';
import { EVIDENCE_DIRECTIONS, EVIDENCE_SOURCES } from '../../types/evidence';
import { idSchema, timestampSchema } from '../validation';
import { EVIDENCE_DAY_MS, EVIDENCE_V1 } from './calibration';

const fraction = z.number().finite().min(0).max(1);
export const transferContextSchema = z.strictObject({ unseen: z.boolean(), exam_like: z.boolean(), prior_practice_at: timestampSchema });
export const evidenceContextSchema = z.strictObject({
  transfer: transferContextSchema.optional(),
  identified_relation: z.strictObject({ relation: z.enum(DISCOURSE_RELATIONS), recorded_at: timestampSchema }).optional(),
});
export function evidenceId(attemptId: string, skillId: SkillEvidence['skill_id'], source: SkillEvidence['source']): string {
  return JSON.stringify(['skill-evidence-v1', attemptId, skillId, source]);
}
export const skillEvidenceSchema = z.strictObject({
  id: z.string().min(1).max(2_000), extractor_version: z.literal('v1'),
  attempt_id: idSchema, question_id: idSchema, session_id: idSchema.nullable(), skill_id: z.enum(SKILL_IDS),
  question_family: z.enum(QUESTION_FAMILIES), direction: z.enum(EVIDENCE_DIRECTIONS), source: z.enum(EVIDENCE_SOURCES),
  evidence_kind: z.enum(['PRACTICE', 'TRANSFER']), strength: fraction, reliability: fraction, transfer_level: fraction,
  assisted: z.boolean(), difficulty: fraction.optional(), attribution_weight: fraction.optional(),
  mapping_weight: fraction, outcome_correct: z.boolean(), transfer_context: transferContextSchema.optional(), created_at: timestampSchema,
}).superRefine((e, ctx) => {
  const fail = (message: string): void => { ctx.addIssue({ code: 'custom', message }); };
  if (e.id !== evidenceId(e.attempt_id, e.skill_id, e.source)) fail('Non-deterministic evidence ID');
  if ((e.direction === 'NEUTRAL') !== (e.strength === 0)) fail('Neutral evidence must have zero strength');
  if (e.evidence_kind === 'TRANSFER') {
    const t = e.transfer_context;
    if (e.assisted || t === undefined || !t.unseen || !t.exam_like ||
      e.created_at - t.prior_practice_at < EVIDENCE_V1.transfer_delay_days * EVIDENCE_DAY_MS || e.transfer_level !== 1) fail('Invalid transfer contract');
  } else if (e.transfer_level !== 0 || e.transfer_context !== undefined || e.source === 'TRANSFER') fail('Invalid practice contract');
  if (e.source === 'QUESTION_RESULT' || e.source === 'TRANSFER') {
    if (e.outcome_correct && e.direction !== 'POSITIVE') fail('A correct result must remain positive');
    if (!e.outcome_correct && e.direction === 'POSITIVE') fail('A wrong result cannot be positive');
    if (e.attribution_weight === undefined) fail('Result requires attribution weight');
    if (e.outcome_correct && e.attribution_weight !== 0) fail('Correct result cannot be an attributed error');
  }
  // No qualified block telemetry exists in v1. Reserve the contract without inventing pacing evidence.
  if (e.skill_id === 'PACING_STAMINA' || e.source === 'TIMED_PERFORMANCE') fail('Qualified block context is not implemented in evidence v1');
});
export const confidenceCalibrationSchema = z.strictObject({ attempt_id: idSchema, confidence: z.enum(['HIGH', 'MEDIUM', 'LOW']), correct: z.boolean() });
export const evidenceRunSchema = z.strictObject({
  attempt_id: idSchema, question_id: idSchema, extractor_version: z.literal('v1'), context: evidenceContextSchema,
  evidence_ids: z.array(z.string().min(1).max(2_000)).max(100), created_at: timestampSchema,
}).refine((r) => new Set(r.evidence_ids).size === r.evidence_ids.length, 'Duplicate evidence IDs');

/** Stable comparison is independent of object insertion order; array order remains meaningful. */
export function canonicalEvidence(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalEvidence).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.entries(value).filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${JSON.stringify(k)}:${canonicalEvidence(v)}`).join(',')}}`;
  return JSON.stringify(value) ?? 'null';
}
export function uniqueEvidence(history: readonly SkillEvidence[]): readonly SkillEvidence[] {
  const rows = new Map<string, SkillEvidence>();
  for (const input of history) {
    const e = skillEvidenceSchema.parse(input);
    const previous = rows.get(e.id);
    if (previous !== undefined && canonicalEvidence(previous) !== canonicalEvidence(e)) throw new RangeError('Conflicting deterministic evidence ID');
    rows.set(e.id, e);
  }
  return [...rows.values()].sort((a, b) => a.created_at - b.created_at || a.id.localeCompare(b.id));
}
