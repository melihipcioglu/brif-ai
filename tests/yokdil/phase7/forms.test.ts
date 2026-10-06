import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { QUESTION_FAMILIES } from '../../../src/types/question';
import { analyzeExamPool, buildExamForm, validateExamBlueprint } from '../../../src/exam';
import { primaryQuestionSkill } from '../../../src/services/evidence/mapping';
import { actual } from '../phase5/fixtures';
import { blueprint, context, controlled, syntheticPool } from './fixtures';

describe('Blueprint and pool safety', () => {
  it.each([
    { total_questions: 0 }, { total_questions: -1 }, { time_limit_ms: NaN }, { time_limit_ms: 0 },
    { version: '' }, { family_targets: { GAP_FILL: 4 } }, { skill_minimums: { MAIN_IDEA: 1 } },
    { total_questions: 10, family_targets: { GAP_FILL: 5, READING_COMPREHENSION: 5 }, skill_minimums: { VOCAB_CONTEXT: 3, TENSE_ASPECT: 3 } },
    { source: { verification: 'OFFICIAL_VERIFIED', reference: '' } },
  ])('rejects invalid/impossible blueprint %j', (change) => {
    expect(validateExamBlueprint({ ...blueprint(), ...change }).status).toBe('INVALID');
  });
  it('unverified blueprint supports practice form creation while retaining verification provenance', () => {
    const result = buildExamForm({ id: 'form', blueprint: blueprint({ source: { verification: 'UNVERIFIED', reference: null } }), questions: initialQuestions, context });
    expect(result.status).toBe('COMPLETE'); expect(result.form?.blueprint.source.verification).toBe('UNVERIFIED');
  });
  it('empty pool returns typed insufficiency and cannot produce an empty partial form', () => {
    const result = buildExamForm({ id: 'empty', blueprint: blueprint(), questions: [], context, allow_partial: true });
    expect(result.status).toBe('INSUFFICIENT_POOL'); expect(result.form).toBeNull();
  });
  it('the real pool has 22 questions, with actual family and skill coverage', () => {
    const all = blueprint({ total_questions: 22, family_targets: { GAP_FILL: 5, CLOZE_TEST: 2, SENTENCE_COMPLETION: 2, TRANSLATION_ENG_TR: 2,
      TRANSLATION_TR_ENG: 2, PARAGRAPH_COMPLETION: 2, IRRELEVANT_SENTENCE: 2, READING_COMPREHENSION: 5 } });
    const result = analyzeExamPool(all, initialQuestions, context);
    expect(result.status).toBe('ADEQUATE'); if (result.status === 'INVALID_BLUEPRINT') return;
    expect(result.report.available).toBe(22); expect(result.report.eligible).toBe(22);
    expect(Object.values(result.report.family_available)).toEqual([5, 2, 2, 2, 2, 2, 2, 5]);
    expect(Object.values(result.report.skill_available).filter((n) => n > 0)).toHaveLength(12);
    expect(result.report.novelty.UNKNOWN).toBe(22);
  });
  it('quantity alone does not satisfy missing families', () => {
    const gaps = initialQuestions.filter((q) => q.family === 'GAP_FILL');
    const result = analyzeExamPool(blueprint({ family_targets: { GAP_FILL: 3, CLOZE_TEST: 2 } }), gaps, context);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status === 'INVALID_BLUEPRINT') return;
    expect(result.report.shortfall).toBe(0); expect(result.report.family_shortfalls.CLOZE_TEST).toBe(2);
  });
  it('exact duplicate IDs are counted once and conflicting duplicates are excluded', () => {
    const q = initialQuestions[0]!;
    const same = analyzeExamPool(blueprint(), [...initialQuestions, q], context);
    expect(same.status).toBe('ADEQUATE'); if (same.status !== 'INVALID_BLUEPRINT') expect(same.report.eligible).toBe(5);
    const different = analyzeExamPool(blueprint(), [...initialQuestions, { ...q, stem: 'conflict' }], context);
    expect(different.status).toBe('INSUFFICIENT_POOL');
  });
  it('same content under another ID cannot fill a shortage', () => {
    const q = initialQuestions[0]!;
    const result = analyzeExamPool(blueprint({ total_questions: 6, family_targets: { GAP_FILL: 6 } }), [...initialQuestions, { ...q, id: 'alias' }], context);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status !== 'INVALID_BLUEPRINT') expect(result.report.eligible).toBe(5);
  });
  it.each([{ family: 'UNSUPPORTED' }, { correct_option: 'Z' }, { provenance: 'UNKNOWN' }, { explanation: null }])('excludes invalid question %j', (changes) => {
    const result = analyzeExamPool(blueprint(), [{ ...initialQuestions[0], ...changes }], context);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status !== 'INVALID_BLUEPRINT') expect(result.report.exclusions[0]?.reason).toBe('INVALID_QUESTION');
  });
  it('known prior attempt overrides an unseen assertion, including content aliases', () => {
    const q = initialQuestions[0]!, ctx = { ...controlled(), prior_attempts: [actual(q, 'prior', 500)] };
    const result = analyzeExamPool(blueprint({ reuse_policy: 'UNSEEN_ONLY' }), initialQuestions, ctx);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status !== 'INVALID_BLUEPRINT') expect(result.report.novelty.SEEN).toBe(1);
    const alias = analyzeExamPool(blueprint({ reuse_policy: 'EXCLUDE_SEEN' }), [...initialQuestions, { ...q, id: 'alias' }], ctx);
    if (alias.status !== 'INVALID_BLUEPRINT') expect(alias.report.eligible).toBe(4);
  });
  it('unknown exposure cannot meet unseen-only selection', () => {
    const result = analyzeExamPool(blueprint({ reuse_policy: 'UNSEEN_ONLY' }), initialQuestions, context);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status !== 'INVALID_BLUEPRINT') expect(result.report.eligible).toBe(0);
  });
  it('rejects future exposure and uncontrolled unseen labels', () => {
    expect(() => analyzeExamPool(blueprint(), initialQuestions, { ...controlled(), as_of: 0 })).toThrow();
    expect(() => analyzeExamPool(blueprint(), initialQuestions, { ...context, exposures: [{ question_id: 'gap-vocab', state: 'UNSEEN', observed_at: 0, method: 'RECORDED_EXPOSURE', reference: 'claim' }] })).toThrow();
  });
});

describe('Deterministic constrained form selection', () => {
  it('exact-sized synthetic pool can meet an explicit test blueprint without altering production', () => {
    const pool = syntheticPool(), bp = blueprint({ scope: 'FULL', total_questions: 80, family_targets: Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, 10])) });
    const result = buildExamForm({ id: 'synthetic-full', blueprint: bp, questions: pool, context: controlled(pool), seed: 'full' });
    expect(result.status).toBe('COMPLETE'); expect(result.form?.questions).toHaveLength(80); expect(initialQuestions).toHaveLength(22);
  });
  it('same seed is stable across input order; different seeds produce different valid forms', () => {
    const pool = syntheticPool(), bp = blueprint({ total_questions: 8, family_targets: Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, 1])) });
    const request = { id: 'seeded', blueprint: bp, questions: pool, context: controlled(pool), seed: 'a' };
    const a = buildExamForm(request), b = buildExamForm({ ...request, seed: 'b' });
    expect(a).toEqual(buildExamForm({ ...request, questions: [...pool].reverse() }));
    expect(a.form?.question_ids).not.toEqual(b.form?.question_ids);
    expect(new Set(a.form?.question_ids).size).toBe(8); expect(a.status).toBe('COMPLETE'); expect(b.status).toBe('COMPLETE');
  });
  it('joint family/skill constraints require allocation, not naive first-fit', () => {
    const bp = blueprint({ total_questions: 4, family_targets: { GAP_FILL: 1, CLOZE_TEST: 1, READING_COMPREHENSION: 1, IRRELEVANT_SENTENCE: 1 },
      skill_minimums: { VOCAB_CONTEXT: 1, CONNECTOR_DISCOURSE: 1, MAIN_IDEA: 1, COHESION_COHERENCE: 1 } });
    const result = buildExamForm({ id: 'constraints', blueprint: bp, questions: initialQuestions, context });
    expect(result.status).toBe('COMPLETE');
    expect(new Set(result.form?.questions.map(primaryQuestionSkill))).toEqual(new Set(['VOCAB_CONTEXT', 'CONNECTOR_DISCOURSE', 'MAIN_IDEA', 'COHESION_COHERENCE']));
  });
  it('reports concrete skill shortage even when the abstract blueprint is feasible', () => {
    const bp = blueprint({ skill_minimums: { VOCAB_CONTEXT: 2 } });
    const result = analyzeExamPool(bp, initialQuestions, context);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status !== 'INVALID_BLUEPRINT') expect(result.report.skill_shortfalls.VOCAB_CONTEXT).toBe(1);
  });
  it('one-item internal mini form is valid but is not silently expanded', () => {
    const result = buildExamForm({ id: 'single', blueprint: blueprint({ total_questions: 1, family_targets: { GAP_FILL: 1 } }), questions: initialQuestions, context });
    expect(result.status).toBe('COMPLETE'); expect(result.form?.question_ids).toHaveLength(1);
  });
  it('forms and source inputs remain immutable', () => {
    const before = JSON.stringify(initialQuestions);
    const result = buildExamForm({ id: 'immutable', blueprint: blueprint(), questions: initialQuestions, context });
    expect(JSON.stringify(initialQuestions)).toBe(before); expect(Object.isFrozen(result.form?.questions)).toBe(true);
  });
});
