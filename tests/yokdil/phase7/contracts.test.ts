import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { analyzeExamPool, buildExamForm, validateExamBlueprint } from '../../../src/exam';
import { blueprint, context } from './fixtures';

describe('Phase 7 initial contracts', () => {
  it('validates an explicitly configured internal blueprint', () => {
    expect(validateExamBlueprint(blueprint()).status).toBe('VALID');
  });
  it('does not manufacture a full form from the real 22-question pool', () => {
    const bp = blueprint({ total_questions: 80, family_targets: { GAP_FILL: 80 }, scope: 'FULL' });
    const result = buildExamForm({ id: 'insufficient', blueprint: bp, questions: initialQuestions, context });
    expect(result.status).toBe('INSUFFICIENT_POOL'); expect(result.form).toBeNull();
    // 80 is test configuration, never an official default.
    if (result.status === 'INSUFFICIENT_POOL') expect(result.report.shortfall).toBe(75);
  });
  it('absence of attempts means UNKNOWN, never UNSEEN', () => {
    const result = analyzeExamPool(blueprint(), initialQuestions, context);
    expect(result.status).toBe('ADEQUATE');
    if (result.status !== 'INVALID_BLUEPRINT') expect(result.report.novelty).toEqual({ UNSEEN: 0, SEEN: 0, UNKNOWN: 5 });
  });
  it('form generation is deterministic across array order', () => {
    const request = { id: 'form', blueprint: blueprint(), questions: initialQuestions, context, seed: 'stable' };
    expect(buildExamForm(request)).toEqual(buildExamForm({ ...request, questions: [...initialQuestions].reverse() }));
  });
  it('insufficient pool can explicitly produce only a partial practice form', () => {
    const result = buildExamForm({ id: 'partial', blueprint: blueprint({ total_questions: 6, family_targets: { GAP_FILL: 6 } }), questions: initialQuestions, context, allow_partial: true });
    expect(result.status).toBe('PARTIAL'); expect(result.form?.question_ids).toHaveLength(5);
  });
});
