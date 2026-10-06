import { z } from 'zod';
import { SKILL_IDS } from '../types/learner';
import type { LearnerSkillVector, SkillMetrics } from '../types/learner';
import { FAMILIAR_DELAY_DAYS, LEXICAL_STATES, MASTERED_CONTEXT_COUNT, MASTERED_DELAY_DAYS, POS_TYPES } from '../types/lexical';
import type { LexicalRecord } from '../types/lexical';
import type { DailySession, LexicalAttempt, ProgressBackup } from '../types/progress';

export const timestampSchema = z.number().int().min(0).max(8_640_000_000_000_000);
const count = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
const score = z.number().min(0).max(100);
const fraction = z.number().min(0).max(1);
const text = z.string().trim().min(1).max(4_000);
export const idSchema = z.string().trim().min(1).max(200).refine(
  (value) => !['__proto__', 'constructor', 'prototype'].includes(value),
  'Reserved identifier',
);
const uniqueStrings = z.array(idSchema).max(50_000).refine(
  (values) => new Set(values).size === values.length, 'Duplicate values',
);

const lexicalRecordObject = z.strictObject({
  word_id: idSchema,
  lemma: text,
  pos: z.enum(POS_TYPES),
  tier: z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5), z.literal(6)]),
  priority_score: score,
  lexical_state: z.enum(LEXICAL_STATES),
  mastery_score: score,
  encounter_count: count,
  unaided_correct_count: count,
  assisted_correct_count: count,
  incorrect_count: count,
  response_time_avg_ms: z.number().nonnegative().max(Number.MAX_SAFE_INTEGER),
  stability: z.number().positive().max(365_000),
  last_seen_at: timestampSchema.nullable(),
  last_success_at: timestampSchema.nullable(),
  next_review_date: timestampSchema,
  review_priority: score,
  contexts_seen: uniqueStrings,
  unaided_success_contexts: uniqueStrings,
  collocations_mastered: uniqueStrings,
  distractor_errors: z.record(idSchema, count),
  exam_meaning_tr: text,
  critical_collocations: z.array(z.strictObject({ phrase: text, meaning_tr: text })).min(1).max(100),
  synonyms: z.array(text).max(100),
  antonyms: z.array(text).max(100),
  typical_distractor: z.array(z.strictObject({
    word: idSchema, meaning_tr: text, explanation_tr: text,
  })).min(1).max(100),
  exam_sentence: text,
  exam_sentence_tr: text,
  word_family: z.array(z.strictObject({ pos: z.enum(POS_TYPES), form: text, meaning_tr: text })).min(1).max(100),
  polarity_symbol: z.enum(['↑', '↓', '⇄']),
  mastery_requirements: z.strictObject({ collocation_required: z.boolean(), distractor_required: z.boolean() }),
  evidence: z.strictObject({
    delayed_unaided_correct_count_3d: count,
    delayed_unaided_correct_count_14d: count,
    max_unaided_delay_days: z.number().nonnegative().max(100_000_000),
    distractor_correct_count: count,
    distractor_attempt_count: count,
  }),
});

type CommonLexicalRecord = Omit<LexicalRecord, 'unaided_success_contexts' | 'mastery_requirements' | 'evidence'> & {
  readonly evidence: Pick<LexicalRecord['evidence'], 'max_unaided_delay_days' | 'distractor_correct_count' | 'distractor_attempt_count'>;
};

function validateCommonLexicalRecord(record: CommonLexicalRecord, ctx: z.RefinementCtx): void {
  const issue = (message: string): void => { ctx.addIssue({ code: 'custom', message }); };
  const attempts = record.unaided_correct_count + record.assisted_correct_count + record.incorrect_count;
  if (attempts > record.encounter_count) issue('Attempts exceed encounters');
  if (record.last_success_at !== null &&
      (record.last_seen_at === null || record.last_success_at > record.last_seen_at)) {
    issue('Success must not be later than the last encounter');
  }
  if (record.evidence.distractor_correct_count > record.evidence.distractor_attempt_count ||
      record.evidence.distractor_attempt_count > attempts ||
      record.evidence.distractor_correct_count > record.unaided_correct_count) issue('Invalid distractor evidence');
  if (Object.values(record.distractor_errors).reduce((sum, value) => sum + value, 0) > record.incorrect_count) {
    issue('Distractor errors exceed incorrect attempts');
  }
  if (attempts > 0 && record.last_seen_at === null) issue('Attempted records need a last encounter date');
  if (record.unaided_correct_count + record.assisted_correct_count > 0 && record.last_success_at === null) {
    issue('Correct attempts need a success date');
  }
  const knownCollocations = new Set(record.critical_collocations.map((entry) => entry.phrase));
  if (record.collocations_mastered.some((phrase) => !knownCollocations.has(phrase))) issue('Unknown mastered collocation');
  if (record.collocations_mastered.length > record.unaided_correct_count) issue('Mastered collocations exceed unaided recalls');
}

export const lexicalRecordSchema: z.ZodType<LexicalRecord> = lexicalRecordObject.superRefine((record, ctx) => {
  validateCommonLexicalRecord(record, ctx);
  const issue = (message: string): void => { ctx.addIssue({ code: 'custom', message }); };
  const evidence = record.evidence;
  if (evidence.delayed_unaided_correct_count_14d > evidence.delayed_unaided_correct_count_3d ||
      evidence.delayed_unaided_correct_count_3d > record.unaided_correct_count) issue('Invalid delayed recall counts');
  if (evidence.delayed_unaided_correct_count_3d > 0 && evidence.max_unaided_delay_days < FAMILIAR_DELAY_DAYS) {
    issue('Familiar recall evidence requires at least 3 days');
  }
  if (evidence.delayed_unaided_correct_count_14d > 0 && evidence.max_unaided_delay_days < MASTERED_DELAY_DAYS) {
    issue('Mastered recall evidence requires at least 14 days');
  }
  const exposureContexts = new Set(record.contexts_seen);
  if (record.unaided_success_contexts.some((context) => !exposureContexts.has(context))) issue('Unaided contexts must be a subset of exposures');
  if (record.unaided_success_contexts.length > record.unaided_correct_count) issue('Successful contexts exceed unaided recalls');
  // Scores may later fall below promotion thresholds. Earned levels retain their historical gates.
  if ((record.lexical_state === 'FAMILIAR' || record.lexical_state === 'MASTERED') &&
      evidence.delayed_unaided_correct_count_3d < 1) issue('FAMILIAR requires a delayed unaided recall of at least 3 days');
  if (record.lexical_state === 'MASTERED' && (
    evidence.delayed_unaided_correct_count_14d < 1 || record.unaided_success_contexts.length < MASTERED_CONTEXT_COUNT ||
    (record.mastery_requirements.collocation_required && record.collocations_mastered.length === 0) ||
    (record.mastery_requirements.distractor_required && evidence.distractor_correct_count === 0)
  )) issue('MASTERED requires delayed recall, three successful contexts and required evidence');
});

/** Isolated legacy contract: exposure contexts are parsed, never interpreted as mastery. */
export const legacyLexicalRecordV1Schema = lexicalRecordObject.omit({ unaided_success_contexts: true, mastery_requirements: true }).extend({
  evidence: z.strictObject({
    delayed_unaided_correct_count: count,
    max_unaided_delay_days: z.number().nonnegative().max(100_000_000),
    distractor_correct_count: count,
    distractor_attempt_count: count,
  }),
}).superRefine((record, ctx) => {
  validateCommonLexicalRecord(record, ctx);
  if (record.evidence.delayed_unaided_correct_count > record.unaided_correct_count ||
      (record.evidence.delayed_unaided_correct_count > 0 && record.evidence.max_unaided_delay_days < MASTERED_DELAY_DAYS)) {
    ctx.addIssue({ code: 'custom', message: 'Invalid legacy delayed recall evidence' });
  }
});

const skillMetricsObject = z.strictObject({
  mastery: fraction, evidence_count: count, unaided_accuracy: fraction,
  assisted_accuracy: fraction, recency: timestampSchema.nullable(),
  uncertainty: fraction, error_rate: fraction,
});
export const skillMetricsSchema: z.ZodType<SkillMetrics> = skillMetricsObject;
export const learnerSkillVectorSchema: z.ZodType<LearnerSkillVector> = z.record(z.enum(SKILL_IDS), skillMetricsSchema);

export const lexicalAttemptSchema: z.ZodType<LexicalAttempt> = z.strictObject({
  id: idSchema, question_id: idSchema, session_id: idSchema.nullable(),
  lexical_ids: uniqueStrings,
  skill_ids: z.array(z.enum(SKILL_IDS)).min(1).max(13).refine((ids) => new Set(ids).size === ids.length),
  context_id: idSchema,
  outcome: z.enum(['unassisted', 'assisted', 'incorrect']),
  response_ms: count,
  attempted_at: timestampSchema,
  lexical_review: z.strictObject({
    grade: z.union([z.literal(0), z.literal(1), z.literal(2), z.literal(3)]),
    assistance_used: z.boolean(),
    user_lexical_factor: z.number().min(0.75).max(1.25),
    distractor_test: z.strictObject({ word: idSchema, resisted: z.boolean() }).nullable(),
    tested_collocation: idSchema.nullable(),
  }).nullable(),
}).superRefine((attempt, ctx) => {
  const review = attempt.lexical_review;
  if (review === null) return;
  const expected = review.grade === 0 ? 'incorrect' :
    review.assistance_used || review.grade === 1 ? 'assisted' : 'unassisted';
  if (attempt.lexical_ids.length !== 1 || attempt.outcome !== expected ||
      (review.distractor_test?.resisted === false && review.grade !== 0)) {
    ctx.addIssue({ code: 'custom', message: 'Inconsistent lexical review evidence' });
  }
});

const calendarDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((value) => {
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}, 'Invalid calendar date');

const dailySessionObject = z.strictObject({
  id: idSchema,
  date: calendarDate,
  time_zone: text.refine((zone) => {
    try { new Intl.DateTimeFormat('en', { timeZone: zone }); return true; } catch { return false; }
  }, 'Invalid time zone'),
  started_at: timestampSchema,
  ended_at: timestampSchema.nullable(),
  active_ms: count,
  skills: learnerSkillVectorSchema,
});
const validSessionOrder = (session: Pick<DailySession, 'started_at' | 'ended_at'>): boolean =>
  session.ended_at === null || session.ended_at >= session.started_at;
export const dailySessionSchema: z.ZodType<DailySession> = dailySessionObject.refine(validSessionOrder,
  'Session end precedes start');

/** Only schema v1 permits percent mastery. Never reused by a v2 domain validator. */
export const legacyDailySessionV1Schema = dailySessionObject.extend({
  skills: z.record(z.enum(SKILL_IDS), skillMetricsObject.extend({ mastery: score })),
}).refine(validSessionOrder, 'Session end precedes start');

export const progressBackupSchema: z.ZodType<ProgressBackup> = z.strictObject({
  format: z.literal('yokdil-fen-progress'),
  schema_version: z.literal(2),
  scheduler_version: z.literal('ass-v1'),
  exported_at: timestampSchema,
  lexical_store: z.array(lexicalRecordSchema).max(100_000),
  question_attempts: z.array(lexicalAttemptSchema).max(100_000),
  daily_sessions: z.array(dailySessionSchema).max(100_000),
}).superRefine(validateBackupKeys);

export const legacyProgressBackupV1Schema = z.strictObject({
  format: z.literal('yokdil-fen-progress'), schema_version: z.literal(1), scheduler_version: z.literal('ass-v1'),
  exported_at: timestampSchema,
  lexical_store: z.array(legacyLexicalRecordV1Schema).max(100_000),
  question_attempts: z.array(lexicalAttemptSchema).max(100_000),
  daily_sessions: z.array(legacyDailySessionV1Schema).max(100_000),
}).superRefine(validateBackupKeys);

function validateBackupKeys(backup: {
  readonly lexical_store: readonly { readonly word_id: string }[];
  readonly question_attempts: readonly { readonly id: string }[];
  readonly daily_sessions: readonly { readonly id: string }[];
}, ctx: z.RefinementCtx): void {
  const unique = (ids: readonly string[], table: string): void => {
    if (new Set(ids).size !== ids.length) ctx.addIssue({ code: 'custom', message: `Duplicate keys in ${table}` });
  };
  unique(backup.lexical_store.map((row) => row.word_id), 'lexical_store');
  unique(backup.question_attempts.map((row) => row.id), 'question_attempts');
  unique(backup.daily_sessions.map((row) => row.id), 'daily_sessions');
}
