import { z } from 'zod';
import type { LearnerSkillVector } from '../../types/learner';
import type { QuestionAttempt } from '../../types/question';
import type { PacingBlockEvidence, SessionBlock, SessionEvent, TimedBlockResult } from '../../types/session';
import { deepFreeze } from '../questions/attempts';
import { questionAttemptSchema } from '../questions/validation';
import { evidenceId, skillEvidenceSchema } from '../evidence/validation';
import { learnerSkillVectorSchema, timestampSchema } from '../validation';
import { EVIDENCE_DAY_MS, EVIDENCE_V1 } from '../evidence/calibration';
import { PACING_V1 } from './calibration';
import { longId } from './validation';

/** Separate extension: reuse bounded fields, explicitly replace the v1 reserved-source rejection. */
export const pacingBlockEvidenceSchema = z.strictObject({
  ...skillEvidenceSchema.shape, source: z.literal('TIMED_PERFORMANCE'), skill_id: z.literal('PACING_STAMINA'),
  evidence_kind: z.literal('PRACTICE'), transfer_level: z.literal(0), mapping_weight: z.literal(1),
  block_id: longId, pacing_version: z.literal('block-v1'), supporting_attempt_ids: z.array(z.string().min(1).max(200)).min(PACING_V1.min_questions),
}).superRefine((e, ctx) => {
  if (e.id !== evidenceId(e.attempt_id, 'PACING_STAMINA', 'TIMED_PERFORMANCE') ||
    (e.direction === 'NEUTRAL') !== (e.strength === 0) || e.transfer_context !== undefined || e.session_id === null ||
    new Set(e.supporting_attempt_ids).size !== e.supporting_attempt_ids.length || !e.supporting_attempt_ids.includes(e.attempt_id)) {
    ctx.addIssue({ code: 'custom', message: 'Invalid block evidence provenance' });
  }
});

export function deriveTimedBlockResult(sessionId: string, block: SessionBlock, events: readonly SessionEvent[], attemptsInput: readonly QuestionAttempt[]): TimedBlockResult {
  if (block.type !== 'TIMED_BLOCK' || !block.timed_enabled || block.status !== 'COMPLETED' || block.started_at === null || block.completed_at === null) throw new RangeError('A completed explicit timed block is required');
  const attempts = new Map(attemptsInput.map((a) => { const parsed = questionAttemptSchema.parse(a); return [parsed.id, parsed] as const; }));
  const linked = events.filter((e) => e.session_id === sessionId && e.command.type === 'QUESTION' && e.command.block_id === block.id).sort((a, b) => a.sequence - b.sequence);
  const seen = new Set<string>(); let retried = false;
  const completed: QuestionAttempt[] = [];
  for (const event of linked) {
    const cmd = event.command; if (cmd.type !== 'QUESTION') continue;
    const a = attempts.get(cmd.attempt_id);
    if (!a || a.question_id !== cmd.item_id || a.attempted_at !== event.at || a.attempted_at < block.started_at || a.attempted_at > block.completed_at || !block.question_ids.includes(a.question_id)) throw new RangeError('Invalid timed attempt reference');
    if (cmd.retry_of !== null || seen.has(a.question_id)) { retried = true; continue; }
    seen.add(a.question_id); completed.push(a);
  }
  const assisted = (a: QuestionAttempt): boolean => a.hints_used_count > 0 || a.words_clicked.length > 0;
  const total_active_ms = block.actual_duration_ms ?? 0;
  const reasons: string[] = [];
  if (block.question_ids.length < PACING_V1.min_questions || completed.length < PACING_V1.min_questions) reasons.push('TOO_FEW_QUESTIONS');
  if (total_active_ms < PACING_V1.min_active_ms) reasons.push('INSUFFICIENT_ACTIVE_DURATION');
  if (completed.length / block.question_ids.length < PACING_V1.min_completion) reasons.push('LOW_COMPLETION');
  if (completed.filter(assisted).length / Math.max(1, completed.length) > PACING_V1.max_assisted_fraction) reasons.push('HEAVILY_ASSISTED');
  if (retried) reasons.push('RETRY_IN_BLOCK');
  if (completed.reduce((sum, a) => sum + a.response_time_ms, 0) > total_active_ms || completed.some((a) => a.response_time_ms <= 0)) reasons.push('INCONSISTENT_ACTIVE_TIME');
  const half = Math.floor(completed.length / 2);
  const accuracy = (rows: readonly QuestionAttempt[]): number => rows.filter((a) => a.is_correct).length / rows.length;
  const first = completed.length >= PACING_V1.degradation_min_questions ? accuracy(completed.slice(0, half)) : null;
  const last = first === null ? null : accuracy(completed.slice(-half));
  return deepFreeze({ block_id: block.id, session_id: sessionId, question_count: block.question_ids.length, completed_count: completed.length,
    correct_count: completed.filter((a) => a.is_correct).length, assisted_count: completed.filter(assisted).length,
    unaided_correct_count: completed.filter((a) => a.is_correct && !assisted(a)).length,
    assisted_correct_count: completed.filter((a) => a.is_correct && assisted(a)).length,
    attempt_ids: completed.map((a) => a.id), total_active_ms, target_budget_ms: block.planned_minutes * 60_000,
    family_mix: [...new Set(completed.map((a) => a.family))], started_at: block.started_at, ended_at: block.completed_at,
    qualified: reasons.length === 0, disqualification_reasons: reasons,
    degradation_signal: first === null || last === null ? null : { first_accuracy: first, last_accuracy: last, decline: Math.max(0, first - last) } });
}
/** Call after deriving a result from authoritative session events/attempts. Persistence regenerates it. */
export function extractPacingBlockEvidence(result: TimedBlockResult, attempts: readonly QuestionAttempt[]): PacingBlockEvidence | null {
  if (!result.qualified) return null;
  const supporting = result.attempt_ids.map((id) => questionAttemptSchema.parse(attempts.find((a) => a.id === id)));
  const assistedCount = supporting.filter((a) => a.hints_used_count > 0 || a.words_clicked.length > 0).length;
  if (!Number.isSafeInteger(result.question_count) || result.question_count < PACING_V1.min_questions ||
    supporting.length < PACING_V1.min_questions || new Set(supporting.map((a) => a.question_id)).size !== supporting.length ||
    supporting.length !== result.completed_count || supporting.length > result.question_count ||
    result.correct_count !== supporting.filter((a) => a.is_correct).length || result.assisted_count !== assistedCount ||
    !Number.isSafeInteger(result.total_active_ms) || result.total_active_ms < PACING_V1.min_active_ms ||
    result.total_active_ms > result.ended_at - result.started_at || !Number.isFinite(result.target_budget_ms) || result.target_budget_ms <= 0 ||
    supporting.length / result.question_count < PACING_V1.min_completion || assistedCount / supporting.length > PACING_V1.max_assisted_fraction ||
    supporting.some((a) => a.response_time_ms <= 0 || a.attempted_at < result.started_at || a.attempted_at > result.ended_at) ||
    supporting.reduce((sum, a) => sum + a.response_time_ms, 0) > result.total_active_ms || result.disqualification_reasons.length !== 0) {
    throw new RangeError('Qualified result contradicts actual supporting attempts');
  }
  const anchor = supporting[supporting.length - 1];
  if (!anchor) throw new RangeError('Missing terminal attempt');
  const accuracy = result.correct_count / result.completed_count;
  const ratio = result.total_active_ms / result.target_budget_ms;
  const direction = accuracy < PACING_V1.min_accuracy_for_timing ? 'NEUTRAL' : ratio <= PACING_V1.on_time_ratio ? 'POSITIVE' : ratio >= PACING_V1.overrun_ratio ? 'NEGATIVE' : 'NEUTRAL';
  return deepFreeze(pacingBlockEvidenceSchema.parse({ id: evidenceId(anchor.id, 'PACING_STAMINA', 'TIMED_PERFORMANCE'), extractor_version: 'v1',
    attempt_id: anchor.id, question_id: anchor.question_id, session_id: result.session_id, question_family: anchor.family,
    skill_id: 'PACING_STAMINA', source: 'TIMED_PERFORMANCE', evidence_kind: 'PRACTICE', transfer_level: 0,
    direction, strength: direction === 'NEUTRAL' ? 0 : PACING_V1.strength * (result.completed_count / result.question_count),
    reliability: PACING_V1.reliability, assisted: result.assisted_count > 0, mapping_weight: 1, outcome_correct: anchor.is_correct,
    attribution_weight: direction === 'NEGATIVE' ? PACING_V1.strength : 0, created_at: result.ended_at,
    block_id: result.block_id, pacing_version: 'block-v1', supporting_attempt_ids: result.attempt_ids }));
}
/** Only the reserved dimension is overlaid. All twelve frozen content metrics pass through unchanged. */
export function overlayPacingModel(current: LearnerSkillVector, records: readonly { readonly result: TimedBlockResult; readonly evidence: PacingBlockEvidence }[], asOf: number): LearnerSkillVector {
  const vector = learnerSkillVectorSchema.parse(current); timestampSchema.parse(asOf);
  let positive = 0, negative = 0, ua = 0, ac = 0, uaCorrect = 0, assistedCorrect = 0, errors = 0, latest: number | null = null;
  const blocks = new Set<string>();
  for (const { result, evidence: input } of records) {
    const e = pacingBlockEvidenceSchema.parse(input);
    if (blocks.has(e.block_id)) throw new RangeError('Duplicate pacing block'); blocks.add(e.block_id);
    if (asOf < e.created_at || !result.qualified || result.block_id !== e.block_id) throw new RangeError('Invalid pacing result');
    const mass = e.strength * e.reliability * (EVIDENCE_V1.recency_floor + (1 - EVIDENCE_V1.recency_floor) * Math.exp(-(asOf - e.created_at) / (EVIDENCE_V1.recency_days * EVIDENCE_DAY_MS)));
    if (e.direction === 'POSITIVE') positive += mass;
    if (e.direction === 'NEGATIVE') { negative += mass; errors += e.attribution_weight ?? 0; }
    ua += result.completed_count - result.assisted_count; ac += result.assisted_count;
    uaCorrect += result.unaided_correct_count; assistedCorrect += result.assisted_correct_count;
    latest = Math.max(latest ?? 0, e.created_at);
  }
  if (blocks.size === 0) return deepFreeze(vector);
  return deepFreeze(learnerSkillVectorSchema.parse({ ...vector, PACING_STAMINA: {
    mastery: positive / (EVIDENCE_V1.prior_negative_mass + positive + negative), evidence_count: blocks.size,
    unaided_accuracy: ua === 0 ? 0 : uaCorrect / ua, assisted_accuracy: ac === 0 ? 0 : assistedCorrect / ac,
    uncertainty: Math.max(0.35, 1 / (1 + (positive + negative) / EVIDENCE_V1.uncertainty_scale)),
    error_rate: errors / blocks.size, recency: latest,
  } }));
}
