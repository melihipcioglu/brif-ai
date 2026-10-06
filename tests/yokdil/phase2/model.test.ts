import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { QUESTION_FAMILIES } from '../../../src/types/question';
import type { Question } from '../../../src/types/question';
import { errorAttributionSchema, questionAttemptSchema, questionSchema, validateAttemptForQuestion } from '../../../src/services/questions/validation';
import { createAttemptDraft, submitQuestionAttempt, updateDraft } from '../../../src/services/questions/attempts';
import { attributeQuestionError } from '../../../src/services/questions/attribution';

export function question(id = 'gap-vocab'): Question {
  const q = initialQuestions.find((item) => item.id === id);
  if (q === undefined) throw new Error(`Missing fixture: ${id}`);
  return q;
}
const meta = { id: 'attempt-1', session_id: null, response_time_ms: 2_000, attempted_at: 2_000 };
describe('Phase 2 question contract', () => {
  it('provides at least two original questions for every family and covers all science domains', () => {
    expect(initialQuestions).toHaveLength(22);
    for (const family of QUESTION_FAMILIES) expect(initialQuestions.filter((q) => q.family === family).length).toBeGreaterThanOrEqual(2);
    expect(new Set(initialQuestions.map((q) => q.science_domain)).size).toBe(7);
    expect(new Set(initialQuestions.map((q) => q.id)).size).toBe(initialQuestions.length);
    for (const q of initialQuestions) { expect(questionSchema.safeParse(q).success).toBe(true); expect(q.provenance).toBe('ORIGINAL_PRACTICE'); }
  });
  it.each([0, 4, 6])('rejects %i options', (length) => {
    const q = question();
    expect(questionSchema.safeParse({ ...q, options: Array.from({ length }, () => q.options[0]) }).success).toBe(false);
  });
  it('rejects duplicates, invalid answers and arbitrary distractor strings', () => {
    const q = question();
    expect(questionSchema.safeParse({ ...q, options: [q.options[0], q.options[0], ...q.options.slice(2)] }).success).toBe(false);
    expect(questionSchema.safeParse({ ...q, correct_option: 'F' }).success).toBe(false);
    expect(questionSchema.safeParse({ ...q, explanation: { ...q.explanation, distractor_patterns: ['FAKE_PATTERN'] } }).success).toBe(false);
  });
  it('rejects inconsistent families, subclasses, translation directions and cloze windows', () => {
    const q = question();
    expect(questionSchema.safeParse({ ...q, subclass: 'GRAMMAR' }).success).toBe(false);
    expect(questionSchema.safeParse({ ...q, family: 'READING_COMPREHENSION' }).success).toBe(false);
    const tr = question('translation-eng-tr-sensor');
    expect(questionSchema.safeParse({ ...tr, family: 'TRANSLATION_TR_ENG' }).success).toBe(false);
    const cloze = question('cloze-biology');
    expect(questionSchema.safeParse({ ...cloze, passage: 'Unrelated passage.' }).success).toBe(false);
  });
});
describe('Phase 2 attempt and independent controls', () => {
  it('starts with null confidence and supports reversible strikeout independent of selection', () => {
    let draft = updateDraft(createAttemptDraft(), { type: 'select', option: 'B' });
    expect(draft.confidence_level).toBeNull();
    draft = updateDraft(draft, { type: 'eliminate', option: 'B' });
    expect(draft.eliminated_options).toEqual(['B']);
    expect(draft.selected_option).toBe('B');
    const attempt = submitQuestionAttempt(question(), draft, meta);
    expect(attempt.is_correct).toBe(true);
    expect(attempt.eliminated_options).toEqual(['B']);
    expect(attempt.confidence_level).toBeNull();
    draft = updateDraft(draft, { type: 'eliminate', option: 'B' });
    expect(draft.eliminated_options).toEqual([]);
    expect(draft.selected_option).toBe('B');
  });
  it.each(['HIGH', 'MEDIUM', 'LOW'] as const)('persists explicit %s confidence', (confidence) => {
    const draft = updateDraft(updateDraft(createAttemptDraft(), { type: 'select', option: 'A' }), { type: 'confidence', confidence });
    expect(submitQuestionAttempt(question(), draft, meta).confidence_level).toBe(confidence);
  });
  it('counts actual answer changes only; flags never count as selection', () => {
    let draft = updateDraft(createAttemptDraft(), { type: 'flag', option: 'D' });
    expect(draft.selected_option).toBeNull();
    expect(draft.option_change_count).toBe(0);
    for (const option of ['A', 'A', 'C', 'B', 'B'] as const) draft = updateDraft(draft, { type: 'select', option });
    expect(draft.option_change_count).toBe(2);
    expect(draft.distractor_flagged).toEqual(['D']);
    expect(updateDraft(draft, { type: 'flag', option: 'D' }).distractor_flagged).toEqual([]);
  });
  it('freezes submitted data recursively and creates separate retry records', () => {
    const draft = updateDraft(createAttemptDraft(), { type: 'select', option: 'A' });
    const first = submitQuestionAttempt(question(), draft, meta);
    const second = submitQuestionAttempt(question(), draft, { ...meta, id: 'attempt-2' });
    expect(Object.isFrozen(first)).toBe(true);
    expect(Object.isFrozen(first.words_clicked)).toBe(true);
    expect(Object.isFrozen(first.error_attribution?.probabilities)).toBe(true);
    expect(Reflect.set(first, 'selected_option', 'B')).toBe(false);
    expect(second.id).not.toBe(first.id);
    expect(first.selected_option).toBe('A');
  });
  it('rejects bad telemetry without accepting fake correctness', () => {
    const draft = updateDraft(createAttemptDraft(), { type: 'select', option: 'B' });
    const a = submitQuestionAttempt(question(), draft, meta);
    const invalid = [
      { ...a, selected_option: 'Z' }, { ...a, eliminated_options: ['A', 'A'] }, { ...a, distractor_flagged: ['B', 'B'] },
      { ...a, confidence_level: 'SURE' }, { ...a, confidence_level: undefined }, { ...a, response_time_ms: -1 }, { ...a, family: 'READING_COMPREHENSION' },
    ];
    for (const value of invalid) expect(questionAttemptSchema.safeParse(value).success).toBe(false);
    expect(() => validateAttemptForQuestion({ ...a, selected_option: 'A' }, question())).toThrow();
    expect(() => submitQuestionAttempt(question(), createAttemptDraft(), meta)).toThrow();
  });
});
describe('Probabilistic error attribution', () => {
  it('does not force vocabulary error from a word click, and permits unknown primary cause', () => {
    const q = question();
    const neutral = { ...q, explanation: { ...q.explanation, option_analysis: q.explanation.option_analysis.map((a) => ({ ...a, patterns: [] })) } };
    const attribution = attributeQuestionError(neutral, { is_correct: false, selected_option: 'A', words_clicked: ['inhibit'], response_time_ms: 2_000 });
    expect(attribution?.primary_category).toBeNull();
    expect(attribution?.confidence).toBe(0);
    expect(attribution?.probabilities.VOCABULARY).toBeLessThan(0.2);
    expect(Object.values(attribution?.probabilities ?? {}).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 10);
    expect(attributeQuestionError(q, { is_correct: true, selected_option: 'B', words_clicked: ['inhibit'], response_time_ms: 2_000 })).toBeNull();
  });
  it('rejects invalid probability ranges, sums, categories and primary labels', () => {
    const valid = { probabilities: { VOCABULARY: 0.62, CONNECTOR: 0.23, CARELESS: 0.15 }, primary_category: 'VOCABULARY', confidence: 0.4 };
    expect(errorAttributionSchema.safeParse(valid).success).toBe(true);
    for (const probabilities of [{}, { VOCABULARY: 1.1 }, { VOCABULARY: -0.1, CONNECTOR: 1.1 }, { VOCABULARY: 0.8 }, { INVENTED: 1 }]) {
      expect(errorAttributionSchema.safeParse({ ...valid, probabilities }).success).toBe(false);
    }
    expect(errorAttributionSchema.safeParse({ ...valid, primary_category: 'CARELESS' }).success).toBe(false);
    expect(errorAttributionSchema.safeParse({ ...valid, primary_category: null }).success).toBe(true);
  });
});
