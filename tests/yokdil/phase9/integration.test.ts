import { describe, it, expect } from 'vitest';
// Explicitly importing from the public runtime entry point (index)
import { productionBank, validateQuestionBank, planQuestionBankExpansion, analyzeExamPool } from '../../../src/index';
import { blueprintSchema } from '../../../src/services/exam/blueprint';
import { controlled } from '../phase7/fixtures';

describe('Phase 9 Public API Wiring', () => {
  it('exposes the 80-question production bank through the public entry point', () => {
    // 1. actual production question source
    const publicBank = productionBank;
    expect(publicBank).toBeDefined();

    // 2. validation / filter
    const validated = validateQuestionBank(publicBank);
    
    // 3. at least 80 production eligible questions
    expect(validated.productionEligible).toBeGreaterThanOrEqual(80);

    const targetBlueprint = blueprintSchema.parse({
      id: 'test-80', version: '1', scope: 'FULL',
      total_questions: 80, time_limit_ms: 10800000,
      family_targets: { GAP_FILL: 10, CLOZE_TEST: 10, SENTENCE_COMPLETION: 10, TRANSLATION_ENG_TR: 10, TRANSLATION_TR_ENG: 10, PARAGRAPH_COMPLETION: 10, IRRELEVANT_SENTENCE: 10, READING_COMPREHENSION: 10 },
      skill_minimums: {},
      reuse_policy: 'ALLOW_REUSE',
      source: { verification: 'UNVERIFIED', reference: null }
    });

    const ctx = { ...controlled(publicBank), as_of: 2000 };
    
    // 4. FAZ 7 analyzeExamPool
    const analysis = analyzeExamPool(targetBlueprint, publicBank, ctx);
    
    // 5. canBuildOneForm / ADEQUATE
    expect(analysis.status).toMatch(/ADEQUATE|COMPLETE/);
    
    const plan = planQuestionBankExpansion(validated, targetBlueprint, 1);
    expect(plan.canBuildOneForm).toBe(true);
  });
});
