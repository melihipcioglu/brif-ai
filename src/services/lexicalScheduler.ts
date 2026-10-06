import { z } from 'zod';
import type { FrictionLevel, LexicalEntry, LexicalRecord, LexicalReview, LexicalState, RecallGrade } from '../types/lexical';
import {
  DEFAULT_MASTERY_REQUIREMENTS, FAMILIAR_DELAY_DAYS, FAMILIAR_MES_THRESHOLD,
  MASTERED_CONTEXT_COUNT, MASTERED_DELAY_DAYS, MASTERED_MES_THRESHOLD,
} from '../types/lexical';
import { idSchema, lexicalRecordSchema, timestampSchema } from './validation';

export const DAY_MS = 86_400_000;
export const SCHEDULER_VERSION = 'ass-v1' as const;
export const DEFAULT_USER_LEXICAL_FACTOR = 1;
export const RECALL_MULTIPLIERS = Object.freeze({ 0: 0.4, 1: 1, 2: 1.5, 3: 2.2 });
export const MES_WEIGHTS = Object.freeze({ delayed_recall: 30, contexts: 25, unaided_accuracy: 20, speed: 15, distractor_resistance: 10 });
/**
 * MES v1 calibration parameter, in weighted successful-evidence units (not days).
 * At K=5, sufficiency reaches 1-exp(-1), about 63.2%, after 5 assisted or 2 unaided
 * successes. The first unaided/assisted accuracy-score ratio is about 2.17;
 * both approach the same 20-point ceiling. This is an initial tuning choice,
 * not an empirically validated learning threshold.
 */
export const EVIDENCE_SATURATION_K = 5;
/** Numerical guard rails, not calibrated learning thresholds. */
const MIN_STABILITY = 1 / DAY_MS;
const MAX_STABILITY = 365_000;
const FAST_RESPONSE_MS = 4_000;
const STATE_RANK: Readonly<Record<LexicalState, number>> = { NEW: 0, SEEN: 1, LEARNING: 2, FAMILIAR: 3, MASTERED: 4 };

const reviewSchema = z.strictObject({
  grade: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
  context_id: idSchema,
  response_time_ms: z.number().int().positive().max(3_600_000),
  reviewed_at: timestampSchema,
  assistance_used: z.boolean(),
  distractor_test: z.strictObject({ word: idSchema, resisted: z.boolean() }).optional(),
  tested_collocation: idSchema.optional(),
}).refine((review) => review.distractor_test?.resisted !== false || review.grade === 0,
  'Choosing a distractor requires an incorrect grade');

const clamp = (value: number, min: number, max: number): number => Math.min(max, Math.max(min, value));
const roundScore = (value: number): number => Math.round(clamp(value, 0, 100) * 100) / 100;
const unique = (values: readonly string[]): string[] => [...new Set(values)];

export interface MasteryScoreBreakdown {
  readonly delayed_recall: number;
  readonly contexts: number;
  readonly unaided_accuracy: number;
  readonly speed: number;
  readonly distractor_resistance: number;
  readonly total: number;
  readonly eligible_for_familiar: boolean;
  readonly eligible_for_mastered: boolean;
}

/**
 * MES components are normalized before applying the frozen 30/25/20/15/10 weights.
 * Accuracy evidence separates quality (success versus failure) from sufficiency.
 * Successful evidence: unaided=2.5, assisted=1; each failure has weight 2.5.
 * Sufficiency saturates with successful evidence; errors never increase it.
 * Passive encounters alone never award MES. Latency earns credit only with success.
 */
export function calculateMasteryEvidence(record: LexicalRecord): MasteryScoreBreakdown {
  const weightedSuccess = 2.5 * record.unaided_correct_count + record.assisted_correct_count;
  const weightedFailure = 2.5 * record.incorrect_count;
  const quality = weightedSuccess === 0 ? 0 : weightedSuccess / (weightedSuccess + weightedFailure);
  // Equivalent to 1 - exp(-weightedSuccess / K), with stable precision near zero.
  const evidenceSufficiency = -Math.expm1(-weightedSuccess / EVIDENCE_SATURATION_K);
  const accuracyEvidence = quality * evidenceSufficiency;
  const delayed_recall = record.evidence.delayed_unaided_correct_count_14d > 0 &&
    record.evidence.max_unaided_delay_days >= MASTERED_DELAY_DAYS ? MES_WEIGHTS.delayed_recall : 0;
  const successfulContexts = new Set(record.unaided_success_contexts).size;
  const contexts = MES_WEIGHTS.contexts * Math.min(1, successfulContexts / MASTERED_CONTEXT_COUNT);
  const unaided_accuracy = MES_WEIGHTS.unaided_accuracy * accuracyEvidence;
  // Sufficiency applies only to the 20-point accuracy component; speed is unchanged.
  const speed = record.response_time_avg_ms > 0 ?
    MES_WEIGHTS.speed * Math.min(1, FAST_RESPONSE_MS / record.response_time_avg_ms) * quality : 0;
  const distractor_resistance = record.evidence.distractor_attempt_count === 0 ? 0 :
    MES_WEIGHTS.distractor_resistance * record.evidence.distractor_correct_count / record.evidence.distractor_attempt_count;
  const total = roundScore(delayed_recall + contexts + unaided_accuracy + speed + distractor_resistance);
  return {
    delayed_recall, contexts, unaided_accuracy, speed, distractor_resistance, total,
    eligible_for_familiar: total >= FAMILIAR_MES_THRESHOLD &&
      record.evidence.delayed_unaided_correct_count_3d > 0 && record.evidence.max_unaided_delay_days >= FAMILIAR_DELAY_DAYS,
    eligible_for_mastered: total >= MASTERED_MES_THRESHOLD && delayed_recall > 0 && successfulContexts >= MASTERED_CONTEXT_COUNT &&
      (!record.mastery_requirements.collocation_required || record.collocations_mastered.length > 0) &&
      (!record.mastery_requirements.distractor_required || record.evidence.distractor_correct_count > 0),
  };
}

export function calculateMES(record: LexicalRecord): number {
  return calculateMasteryEvidence(record).total;
}

/**
 * Bounded, monotonic overdue priority: 45% exam value, 35% overdue forgetting,
 * 20% evidence gap. Merely reading this value never changes lexical_state or MES.
 * priority_score is the curated exam value; tier alone does not invent frequencies.
 */
export function calculateReviewPriority(record: LexicalRecord, now = Date.now()): number {
  timestampSchema.parse(now);
  const overdueDays = Math.max(0, now - record.next_review_date) / DAY_MS;
  const forgetting = 1 - Math.exp(-overdueDays / Math.max(1, record.stability));
  return roundScore(0.45 * record.priority_score + 35 * forgetting + 0.2 * (100 - record.mastery_score));
}

export function getFrictionLevel(record: Pick<LexicalRecord, 'lexical_state'>): FrictionLevel {
  switch (record.lexical_state) {
    case 'NEW': case 'SEEN': return 1;
    case 'LEARNING': return 2;
    case 'FAMILIAR': return 3;
    case 'MASTERED': return 4;
  }
}

export function createLexicalRecord(entry: LexicalEntry, now = Date.now()): LexicalRecord {
  timestampSchema.parse(now);
  const record: LexicalRecord = {
    ...entry, lexical_state: 'NEW', mastery_score: 0, encounter_count: 0,
    mastery_requirements: entry.mastery_requirements ?? { ...DEFAULT_MASTERY_REQUIREMENTS },
    unaided_correct_count: 0, assisted_correct_count: 0, incorrect_count: 0,
    response_time_avg_ms: 0, stability: 1, last_seen_at: null, last_success_at: null,
    next_review_date: now, review_priority: 0, contexts_seen: [], unaided_success_contexts: [], collocations_mastered: [],
    distractor_errors: {}, evidence: { delayed_unaided_correct_count_3d: 0, delayed_unaided_correct_count_14d: 0,
      max_unaided_delay_days: 0, distractor_correct_count: 0, distractor_attempt_count: 0 },
  };
  return lexicalRecordSchema.parse({ ...record, review_priority: calculateReviewPriority(record, now) });
}

/** Record a reading exposure separately from a test; it cannot count as recall. */
export function recordEncounter(record: LexicalRecord, contextId: string, now = Date.now()): LexicalRecord {
  lexicalRecordSchema.parse(record);
  timestampSchema.parse(now);
  const context = idSchema.parse(contextId);
  if (record.last_seen_at !== null && now < record.last_seen_at) throw new RangeError('Encounter predates last exposure');
  return lexicalRecordSchema.parse({
    ...record, encounter_count: record.encounter_count + 1, last_seen_at: now,
    contexts_seen: unique([...record.contexts_seen, context]),
    lexical_state: record.lexical_state === 'NEW' ? 'SEEN' : record.lexical_state,
    review_priority: calculateReviewPriority(record, now),
  });
}

function promotedState(record: LexicalRecord): LexicalState {
  const mes = calculateMasteryEvidence(record);
  if (mes.eligible_for_mastered) return 'MASTERED';
  if (mes.eligible_for_familiar) return 'FAMILIAR';
  return 'LEARNING';
}

export interface ScheduledReview {
  readonly record: LexicalRecord;
  readonly effective_grade: RecallGrade;
  readonly interval_days: number;
  readonly mes: MasteryScoreBreakdown;
}

/** Pure scheduler: persistence, clock acquisition and review deduplication belong to the caller. */
export function scheduleLexicalReview(
  record: LexicalRecord,
  input: LexicalReview,
  userLexicalFactor = DEFAULT_USER_LEXICAL_FACTOR,
): ScheduledReview {
  lexicalRecordSchema.parse(record);
  const review = reviewSchema.parse(input);
  z.number().min(0.75).max(1.25).parse(userLexicalFactor);
  if (record.last_seen_at !== null && review.reviewed_at < record.last_seen_at) throw new RangeError('Review predates last exposure');
  if (review.tested_collocation !== undefined && !record.critical_collocations.some((item) => item.phrase === review.tested_collocation)) {
    throw new RangeError('Unknown tested collocation');
  }
  if (review.distractor_test !== undefined && !record.typical_distractor.some((item) => item.word === review.distractor_test?.word)) {
    throw new RangeError('Unknown tested distractor');
  }
  // Hints always cap successful recall at grade 1, including a correct micro-test.
  const grade: RecallGrade = review.assistance_used && review.grade > 1 ? 1 : review.grade;
  const unaided = grade >= 2;
  const correct = grade > 0;
  const delayDays = record.last_seen_at === null ? 0 : (review.reviewed_at - record.last_seen_at) / DAY_MS;
  const multiplier = RECALL_MULTIPLIERS[grade] * (grade === 3 ? userLexicalFactor : 1);
  const stability = clamp(record.stability * multiplier, MIN_STABILITY, MAX_STABILITY);
  const intervalDays = grade === 0 ? 1 : grade === 1 ? Math.max(2, stability) : stability;
  const nextReviewDate = review.reviewed_at + Math.round(intervalDays * DAY_MS);
  timestampSchema.parse(nextReviewDate);
  const oldAttempts = record.unaided_correct_count + record.assisted_correct_count + record.incorrect_count;
  const distractor = review.distractor_test;
  const draft: LexicalRecord = {
    ...record, stability,
    encounter_count: record.encounter_count + 1,
    unaided_correct_count: record.unaided_correct_count + Number(unaided),
    assisted_correct_count: record.assisted_correct_count + Number(grade === 1),
    incorrect_count: record.incorrect_count + Number(!correct),
    response_time_avg_ms: (record.response_time_avg_ms * oldAttempts + review.response_time_ms) / (oldAttempts + 1),
    last_seen_at: review.reviewed_at,
    last_success_at: correct ? review.reviewed_at : record.last_success_at,
    next_review_date: nextReviewDate,
    contexts_seen: unique([...record.contexts_seen, review.context_id]),
    unaided_success_contexts: unaided ? unique([...record.unaided_success_contexts, review.context_id]) : record.unaided_success_contexts,
    collocations_mastered: unaided && review.tested_collocation !== undefined ?
      unique([...record.collocations_mastered, review.tested_collocation]) : record.collocations_mastered,
    distractor_errors: distractor !== undefined && !distractor.resisted ? {
      ...record.distractor_errors, [distractor.word]: (record.distractor_errors[distractor.word] ?? 0) + 1,
    } : { ...record.distractor_errors },
    evidence: {
      delayed_unaided_correct_count_3d: record.evidence.delayed_unaided_correct_count_3d + Number(unaided && delayDays >= FAMILIAR_DELAY_DAYS),
      delayed_unaided_correct_count_14d: record.evidence.delayed_unaided_correct_count_14d + Number(unaided && delayDays >= MASTERED_DELAY_DAYS),
      max_unaided_delay_days: unaided ? Math.max(record.evidence.max_unaided_delay_days, delayDays) : record.evidence.max_unaided_delay_days,
      distractor_correct_count: record.evidence.distractor_correct_count + Number(unaided && distractor?.resisted === true),
      distractor_attempt_count: record.evidence.distractor_attempt_count + Number(distractor !== undefined),
    },
  };
  const mes = calculateMasteryEvidence(draft);
  const candidate = promotedState(draft);
  // A test error may demote; an assisted or slow success never demotes an earned state.
  // Phase 1 has no misconception attribution: an ordinary error never drops LEARNING to SEEN.
  const demotedState: LexicalState = record.lexical_state === 'MASTERED' ? 'FAMILIAR' : 'LEARNING';
  const lexicalState: LexicalState = grade === 0 ? demotedState :
    STATE_RANK[candidate] > STATE_RANK[record.lexical_state] ? candidate : record.lexical_state;
  const scored: LexicalRecord = { ...draft, mastery_score: mes.total, lexical_state: lexicalState };
  return {
    record: lexicalRecordSchema.parse({ ...scored, review_priority: calculateReviewPriority(scored, review.reviewed_at) }),
    effective_grade: grade, interval_days: intervalDays, mes,
  };
}
