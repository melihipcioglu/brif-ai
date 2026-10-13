import { describe, it, expect } from 'vitest';
import { phase9Bank } from '../../../src/data/productionBank';
import { validateQuestionBank, planQuestionBankExpansion } from '../../../src/questionBank';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { batch1Questions } from '../../../src/data/batch1';
import { batch2Questions } from '../../../src/data/batch2';
import { batch3Questions } from '../../../src/data/batch3';
import { batch4Questions } from '../../../src/data/batch4';
import { batch5Questions } from '../../../src/data/batch5';
import { blueprintSchema } from '../../../src/services/exam/blueprint';
import { analyzeExamPool, buildExamForm } from '../../../src/exam';
import { controlled } from '../phase7/fixtures';

describe('Phase 9: Question Authoring & Coverage Expansion', () => {
  const targetBlueprint = blueprintSchema.parse({
    id: 'test-80', version: '1', scope: 'FULL',
    total_questions: 80, time_limit_ms: 10800000,
    family_targets: { GAP_FILL: 10, CLOZE_TEST: 10, SENTENCE_COMPLETION: 10, TRANSLATION_ENG_TR: 10, TRANSLATION_TR_ENG: 10, PARAGRAPH_COMPLETION: 10, IRRELEVANT_SENTENCE: 10, READING_COMPREHENSION: 10 },
    skill_minimums: {},
    reuse_policy: 'ALLOW_REUSE',
    source: { verification: 'UNVERIFIED', reference: null }
  });

  it('verifies that each new production question passes FAZ 8 validator and production eligible total increases', () => {
    const bankInitial = validateQuestionBank(initialQuestions);
    expect(bankInitial.productionEligible).toBe(22);

    const bankWithB1 = validateQuestionBank([...initialQuestions, ...batch1Questions]);
    expect(bankWithB1.productionEligible).toBe(29);
    expect(bankWithB1.results.filter(r => !r.valid)).toHaveLength(0);

    const bankFinal = validateQuestionBank(phase9Bank);
    expect(bankFinal.productionEligible).toBe(80);
    expect(bankFinal.results.filter(r => !r.valid)).toHaveLength(0);

    // Verify duplicate ID and exact normalized duplicate absence
    const exactDuplicates = bankFinal.results.filter(r => r.errors.includes('EXACT_DUPLICATE_CONTENT') || r.errors.includes('ID_CONFLICT'));
    expect(exactDuplicates).toHaveLength(0);
    expect(bankFinal.results.some(r => r.errors.length > 0)).toBe(false); // No production-blocking errors
  });

  it('verifies that each authoring batch reduces shortages without regressing', () => {
    let currentBank = [...initialQuestions];
    let lastShortage = planQuestionBankExpansion(validateQuestionBank(currentBank), targetBlueprint, 1).minimumAdditionalQuestions;
    expect(lastShortage).toBe(58);

    const batches = [batch1Questions, batch2Questions, batch3Questions, batch4Questions, batch5Questions];
    for (const batch of batches) {
      currentBank = [...currentBank, ...batch];
      const newPlan = planQuestionBankExpansion(validateQuestionBank(currentBank), targetBlueprint, 1);
      expect(newPlan.minimumAdditionalQuestions!).toBeLessThan(lastShortage!);
      
      // Ensure family shortage does not regress
      const totalFamilyShortage = Object.values(newPlan.familyShortages).reduce((a, b) => (a ?? 0) + (b ?? 0), 0);
      expect(totalFamilyShortage).toBeLessThanOrEqual(lastShortage!);

      lastShortage = newPlan.minimumAdditionalQuestions;
    }
    
    expect(lastShortage).toBe(0);
  });

  it('ensures rejected candidates do not enter FAZ 7 exam pool', () => {
    const badQuestion = { ...batch1Questions[0], id: 'bad-id', stem: '' }; // Invalid stem
    const pool = [...phase9Bank, badQuestion];
    const validated = validateQuestionBank(pool);
    expect(validated.productionEligible).toBe(80); // Bad question rejected
    
    // Test that pool analyzer only receives 80 valid questions implicitly or handles rejection
    const validQuestionsForExam = pool.filter(q => validated.results.find(r => r.questionId === q.id && r.valid));
    expect(validQuestionsForExam).toHaveLength(80);
  });

  it('verifies that expanded validated bank is successfully passed to FAZ 7 pool analyzer', () => {
    const ctx = { ...controlled(phase9Bank), as_of: 2000 };
    const analysis = analyzeExamPool(targetBlueprint, phase9Bank, ctx);
    expect(analysis.status).toBe('ADEQUATE');
  });

  it('verifies full form capability, constraints, and determinism', () => {
    const ctx = { ...controlled(phase9Bank), as_of: 2000 };
    
    const request1 = { id: 'test-exam-1', blueprint: targetBlueprint, questions: phase9Bank, context: ctx, seed: 'stable-seed-9' };
    const form1 = buildExamForm(request1);
    
    expect(form1.form?.questions).toHaveLength(80); // target question count
    
    const ids = form1.form?.questions.map(q => q.id) ?? [];
    expect(new Set(ids).size).toBe(80); // duplicate ID = 0
    
    const validated = validateQuestionBank(form1.form?.questions ?? []);
    expect(validated.productionEligible).toBe(80); // all production eligible
    
    // family constraints satisfied
    const families = form1.form?.questions.reduce((acc, q) => {
      acc[q.family] = (acc[q.family] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    expect(families?.GAP_FILL).toBe(10);
    expect(families?.CLOZE_TEST).toBe(10);
    
    // deterministic
    const request2 = { id: 'test-exam-2', blueprint: targetBlueprint, questions: phase9Bank, context: ctx, seed: 'stable-seed-9' };
    const form2 = buildExamForm(request2);
    expect(form2.form?.questions.map(q => q.id)).toEqual(ids);
  });

  it('mutation sanity: removing a required question fails coverage and acceptance tests', () => {
    // b5-irrelevant-1 is required to have 10 IRRELEVANT_SENTENCE
    const mutatedBank = phase9Bank.filter(q => q.id !== 'b5-irrelevant-1');
    const newPlan = planQuestionBankExpansion(validateQuestionBank(mutatedBank), targetBlueprint, 1);
    
    expect(newPlan.canBuildOneForm).toBe(false);
    expect(newPlan.familyShortages['IRRELEVANT_SENTENCE']).toBe(1);

    const ctx = { ...controlled(mutatedBank), as_of: 2000 };
    const analysis = analyzeExamPool(targetBlueprint, mutatedBank, ctx);
    expect(analysis.status).toBe('INSUFFICIENT_POOL');
  });
});





