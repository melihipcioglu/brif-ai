import { describe, expect, it } from 'vitest';
import { validateQuestionBank } from '../../../src/questionBank';
import { initialQuestions } from '../../../src/data/initialQuestions';

describe('Phase 8: Bank Validation', () => {
  it('validates the current 22-question production bank', () => {
    const result = validateQuestionBank(initialQuestions);
    expect(result.total).toBe(22);
    expect(result.valid).toBe(22);
    expect(result.productionEligible).toBe(22);
    expect(result.rejected).toBe(0);
    expect(result.exactDuplicatesFound).toBe(0);
    expect(result.families['GAP_FILL']).toBe(5);
  });

  it('detects exact duplicates and marks them as ID_CONFLICT or EXACT_DUPLICATE_CONTENT', () => {
    const q = initialQuestions[0]!;
    // duplicate id
    const dupId = { ...initialQuestions[1]!, id: q.id };
    // duplicate content different id
    const dupContent = { ...q, id: 'some-other-id' };
    
    const result = validateQuestionBank([q, dupId, dupContent]);
    expect(result.total).toBe(3);
    // Only one should be valid/eligible
    expect(result.valid).toBe(1);
    expect(result.exactDuplicatesFound).toBeGreaterThan(0);
    expect(result.rejected).toBe(2);
  });

  it('detects near duplicates', () => {
    const q1 = initialQuestions[0]!;
    // create a near duplicate (change a few words in stem)
    const q2 = { ...q1, id: 'near-dup-id', stem: q1.stem + ' modified' };
    const result = validateQuestionBank([q1, q2]);
    expect(result.nearDuplicatesFound).toBe(1);
    expect(result.warnings).toBeGreaterThan(0);
  });
});
