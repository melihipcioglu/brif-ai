import { z } from 'zod';
import { SKILL_IDS } from '../../types/learner';
import { CHECK_CRITERIA, DISCOURSE_RELATIONS, DISTRACTOR_PATTERNS, ERROR_CATEGORIES, GAP_FILL_SUBCLASSES, OPTION_IDS, QUESTION_FAMILIES, READING_QUESTION_TYPES } from '../../types/question';
import type { ErrorAttribution, Question, QuestionAttempt } from '../../types/question';
import { idSchema, timestampSchema } from '../validation';

const text = z.string().trim().min(1).max(20_000);
const fraction = z.number().min(0).max(1);
const count = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
const option = z.enum(OPTION_IDS);
const unique = <T>(values: readonly T[]): boolean => new Set(values).size === values.length;
const ids = z.array(idSchema).max(10_000).refine(unique, 'Duplicate IDs');
const options = z.array(option).max(5).refine(unique, 'Duplicate options');
const patterns = z.array(z.enum(DISTRACTOR_PATTERNS)).max(10).refine(unique, 'Duplicate patterns');
const roles = z.strictObject({
  agent: text.optional(), action: text, patient: text.optional(), voice: z.enum(['ACTIVE', 'PASSIVE']),
  modality: text.optional(), polarity: text.optional(), time: text.optional(), condition: text.optional(), degree: text.optional(),
  propositions: z.array(text).max(50).refine(unique, 'Duplicate propositions'),
});
const anchor = z.strictObject({ referent: fraction, topic_continuity: fraction, connector: fraction, tense_aspect: fraction, cause_effect: fraction, lexical_chain: fraction });
const temporal = z.strictObject({ temporal_anchor: text, event_order: text, tense_aspect: text, context: text });
const candidateRelations = z.record(option, z.enum(DISCOURSE_RELATIONS).nullable());
const tactical = z.discriminatedUnion('kind', [
  z.strictObject({ kind: z.literal('GAP_FILL'), focus: z.enum(GAP_FILL_SUBCLASSES), temporal: temporal.optional() }),
  z.strictObject({ kind: z.literal('CLOZE_TEST'), previous_sentence: text, target_sentence: text, next_sentence: text, macro_context: text, relation: z.enum(DISCOURSE_RELATIONS), candidate_relations: candidateRelations }),
  z.strictObject({ kind: z.literal('SENTENCE_COMPLETION'), relation: z.enum(DISCOURSE_RELATIONS), candidate_relations: candidateRelations }),
  z.strictObject({ kind: z.literal('TRANSLATION'), direction: z.enum(['ENG_TR', 'TR_ENG']), source: roles, candidates: z.record(option, roles) }),
  z.strictObject({ kind: z.literal('PARAGRAPH_COMPLETION'), relation: z.enum(DISCOURSE_RELATIONS), candidate_relations: candidateRelations, anchors: z.record(option, anchor) }),
  z.strictObject({ kind: z.literal('IRRELEVANT_SENTENCE'), topic: text, discourse_function: text }),
  z.strictObject({ kind: z.literal('READING_COMPREHENSION'), subtype: z.enum(READING_QUESTION_TYPES) }),
]);
export const errorAttributionSchema: z.ZodType<ErrorAttribution> = z.strictObject({
  probabilities: z.partialRecord(z.enum(ERROR_CATEGORIES), fraction), primary_category: z.enum(ERROR_CATEGORIES).nullable(), confidence: fraction,
}).superRefine((value, ctx) => {
  const entries = Object.entries(value.probabilities);
  const sum = entries.reduce((total, [, probability]) => total + probability, 0);
  if (Math.abs(sum - 1) > 0.000001) ctx.addIssue({ code: 'custom', message: 'Probabilities must sum to 1 within 1e-6' });
  if (value.primary_category !== null) {
    const primary = value.probabilities[value.primary_category];
    if (primary === undefined || primary <= 0 || entries.some(([, probability]) => probability > primary)) {
      ctx.addIssue({ code: 'custom', message: 'Primary category must have maximum positive probability' });
    }
  }
});
export const questionSchema: z.ZodType<Question> = z.strictObject({
  id: idSchema, family: z.enum(QUESTION_FAMILIES), subclass: z.enum(GAP_FILL_SUBCLASSES).optional(), science_domain: text.optional(),
  stem: text, passage: text.optional(), options: z.array(z.strictObject({ id: option, text })).length(5), correct_option: option,
  explanation: z.strictObject({
    triage: z.strictObject({ summary: text, cues: z.array(text).min(1), checks: z.array(text).min(1) }),
    option_analysis: z.array(z.strictObject({ option_id: option, verdict: z.enum(['CORRECT', 'ELIMINATE', 'POSSIBLE']), reasons: z.array(text).min(1), patterns })).length(5),
    verification: z.strictObject({ summary: text, evidence: z.array(text).min(1) }), distractor_patterns: patterns,
  }),
  tactical, option_evidence: z.record(option, z.array(z.strictObject({ criterion: z.enum(CHECK_CRITERIA), matches: z.boolean().nullable(), evidence: text })).min(1).refine((checks) => unique(checks.map((c) => c.criterion)), 'Duplicate criteria')),
  difficulty: fraction.optional(), lexical_ids: ids.optional(), skill_ids: z.array(z.enum(SKILL_IDS)).min(1).refine(unique),
  global_benchmark_ms: count.positive().optional(), personal_benchmark_ms: count.positive().optional(), provenance: z.literal('ORIGINAL_PRACTICE'),
}).superRefine((q, ctx) => {
  const issue = (message: string): void => { ctx.addIssue({ code: 'custom', message }); };
  if (!unique(q.options.map((o) => o.id))) issue('Exactly five unique option IDs required');
  if (!q.options.some((o) => o.id === q.correct_option)) issue('Missing correct option');
  if (!unique(q.explanation.option_analysis.map((a) => a.option_id))) issue('Exactly one analysis per option required');
  const correct = q.explanation.option_analysis.filter((a) => a.verdict === 'CORRECT');
  if (correct.length !== 1 || correct[0]?.option_id !== q.correct_option) issue('Analysis and correct option disagree');
  const declared = new Set(q.explanation.distractor_patterns);
  if (q.explanation.option_analysis.some((a) => a.patterns.some((p) => !declared.has(p)))) issue('Missing explanation pattern');
  if (q.family === 'GAP_FILL') {
    if (q.tactical.kind !== 'GAP_FILL' || (q.subclass !== undefined && q.subclass !== q.tactical.focus)) issue('Gap fill subclass mismatch');
  } else if (q.subclass !== undefined) issue('Subclass only applies to GAP_FILL');
  if (q.family.startsWith('TRANSLATION_')) {
    if (q.tactical.kind !== 'TRANSLATION' || q.family !== `TRANSLATION_${q.tactical.direction}`) issue('Translation direction mismatch');
  } else if (q.family !== q.tactical.kind) issue('Family/strategy mismatch');
  if (['CLOZE_TEST', 'PARAGRAPH_COMPLETION', 'IRRELEVANT_SENTENCE', 'READING_COMPREHENSION'].includes(q.family) && q.passage === undefined) issue('Passage required');
  if (q.tactical.kind === 'CLOZE_TEST' && ![q.tactical.previous_sentence, q.tactical.target_sentence, q.tactical.next_sentence].every((s) => q.passage?.includes(s))) issue('Cloze local window must belong to passage');
});
export const questionAttemptSchema: z.ZodType<QuestionAttempt> = z.strictObject({
  id: idSchema, question_id: idSchema, session_id: idSchema.nullable(), family: z.enum(QUESTION_FAMILIES), subclass: z.enum(GAP_FILL_SUBCLASSES).optional(),
  selected_option: option, is_correct: z.boolean(), response_time_ms: count, confidence_level: z.enum(['HIGH', 'MEDIUM', 'LOW']).nullable(),
  eliminated_options: options, distractor_flagged: options, words_clicked: ids, hints_used_count: count, option_change_count: count,
  attempted_at: timestampSchema, error_attribution: errorAttributionSchema.nullable(),
}).superRefine((a, ctx) => {
  if (a.family !== 'GAP_FILL' && a.subclass !== undefined) ctx.addIssue({ code: 'custom', message: 'Subclass only applies to GAP_FILL' });
  if (a.is_correct !== (a.error_attribution === null)) ctx.addIssue({ code: 'custom', message: 'Only incorrect attempts carry error attribution' });
});

export function validateAttemptForQuestion(input: unknown, question: Question): QuestionAttempt {
  const q = questionSchema.parse(question);
  const attempt = questionAttemptSchema.parse(input);
  const subclass = q.tactical.kind === 'GAP_FILL' ? q.tactical.focus : undefined;
  if (attempt.question_id !== q.id || attempt.family !== q.family || attempt.subclass !== subclass ||
      attempt.is_correct !== (attempt.selected_option === q.correct_option) ||
      attempt.words_clicked.some((id) => !q.lexical_ids?.includes(id))) throw new RangeError('Attempt does not match question');
  return attempt;
}
