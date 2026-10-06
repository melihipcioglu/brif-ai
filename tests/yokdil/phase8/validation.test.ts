import { describe, expect, it } from 'vitest';
import { validateQuestion, VALIDATION_POLICY_VERSION } from '../../../src/questionBank';
import { initialQuestions } from '../../../src/data/initialQuestions';

describe('Phase 8: Question Validation', () => {
  const validQ = initialQuestions[0]!;

  it('validates a pristine original question as PRODUCTION_ELIGIBLE', () => {
    const result = validateQuestion(validQ);
    expect(result.valid).toBe(true);
    expect(result.productionEligible).toBe(true);
    expect(result.errors).toEqual([]);
    expect(result.status).toBe('PRODUCTION_ELIGIBLE');
    expect(result.policyVersion).toBe(VALIDATION_POLICY_VERSION);
  });

  it('rejects an empty stem as EMPTY_STEM', () => {
    const q = { ...validQ, stem: '   ' };
    const result = validateQuestion(q);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('EMPTY_STEM');
    expect(result.status).toBe('REJECTED');
  });

  it('rejects missing or empty option as EMPTY_OPTION', () => {
    const q = { ...validQ, options: validQ.options.map((o) => (o.id === 'C' ? { ...o, text: '' } : o)) };
    const result = validateQuestion(q);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('EMPTY_OPTION');
  });

  it('rejects duplicate options as DUPLICATE_OPTION', () => {
    const q = { ...validQ, options: validQ.options.map((o) => (o.id === 'D' ? { ...o, text: validQ.options[0]!.text } : o)) };
    const result = validateQuestion(q);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('DUPLICATE_OPTION');
  });

  it('rejects invalid answer key', () => {
    const q = { ...validQ, correct_option: 'X' };
    const result = validateQuestion(q);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('INVALID_ANSWER_KEY');
  });

  it('rejects unsupported family', () => {
    const q = { ...validQ, family: 'UNKNOWN_FAMILY' };
    const result = validateQuestion(q);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('UNSUPPORTED_FAMILY');
  });

  it('rejects unsupported skill', () => {
    const q = { ...validQ, skill_ids: ['UNKNOWN_SKILL'] };
    const result = validateQuestion(q);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('UNSUPPORTED_SKILL');
  });

  it('issues a LEXICAL_LEAKAGE warning if stem directly contains the correct answer text', () => {
    const correctText = validQ.options.find(o => o.id === validQ.correct_option)!.text;
    const q = { ...validQ, stem: `This stem leaks the answer ${correctText}` };
    const result = validateQuestion(q);
    expect(result.warnings).toContain('LEXICAL_LEAKAGE');
    expect(result.valid).toBe(true); // Warning does not invalidate by default unless policy says
  });

  it('issues VERY_LONG_STEM warning for stems over threshold', () => {
    const q = { ...validQ, stem: 'word '.repeat(300) };
    const result = validateQuestion(q);
    expect(result.warnings).toContain('VERY_LONG_STEM');
  });

  it('modifying content changes the fingerprint', () => {
    const res1 = validateQuestion(validQ);
    const q = { ...validQ, stem: validQ.stem + ' modified' };
    const res2 = validateQuestion(q);
    expect(res1.fingerprint).not.toBe(res2.fingerprint);
  });
});
