import { describe, expect, it } from 'vitest';
import { planQuestionBankExpansion, validateQuestionBank } from '../../../src/questionBank';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { blueprintSchema } from '../../../src/services/exam/blueprint';

describe('Phase 8: Expansion Planner', () => {
  const bank = validateQuestionBank(initialQuestions);
  
  const testBlueprint = blueprintSchema.parse({
    id: 'test', version: '1', scope: 'FULL',
    total_questions: 80, time_limit_ms: 10800000,
    family_targets: { GAP_FILL: 10, CLOZE_TEST: 10, SENTENCE_COMPLETION: 10, TRANSLATION_ENG_TR: 10, TRANSLATION_TR_ENG: 10, PARAGRAPH_COMPLETION: 10, IRRELEVANT_SENTENCE: 10, READING_COMPREHENSION: 10 },
    skill_minimums: {},
    reuse_policy: 'ALLOW_REUSE',
    source: { verification: 'UNVERIFIED', reference: null }
  });

  it('calculates shortages for a single form', () => {
    const plan = planQuestionBankExpansion(bank, testBlueprint, 1);
    expect(plan.canBuildOneForm).toBe(false);
    expect(plan.canBuildMultipleDistinctForms).toBe(false);
    
    // Total needed 80, current 22 -> minimum 58
    expect(plan.minimumAdditionalQuestions).toBeGreaterThanOrEqual(58);
    // e.g. GAP_FILL target 10, current 5 -> shortage 5
    expect(plan.familyShortages['GAP_FILL']).toBe(5);
  });

  it('calculates shortages for multiple forms', () => {
    const plan = planQuestionBankExpansion(bank, testBlueprint, 3);
    expect(plan.canBuildOneForm).toBe(false);
    // for 3 forms, we need 3 * 10 = 30 GAP_FILL. We have 5. Shortage = 25.
    expect(plan.familyShortages['GAP_FILL']).toBe(25);
    expect(plan.minimumAdditionalQuestions).toBeGreaterThanOrEqual(80 * 3 - 22);
  });
});
