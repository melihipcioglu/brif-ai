import { describe, expect, it } from 'vitest';
// Public runtime entry point only: no direct data-file imports.
import { productionBank, validateQuestionBank, INTERNAL_FULL_BLUEPRINT_80, analyzeFormCapacity, buildExamFormSet, planMultiFormExpansion, analyzeExamPool } from '../../../src/index';

describe('FAZ 10 public production integration', () => {
  it('public productionBank -> FAZ 8 gate -> FAZ 10 capacity -> FAZ 7 forms', () => {
    const gate = validateQuestionBank(productionBank);
    expect(gate.productionEligible).toBe(productionBank.length);
    const context = { as_of: 1_000, prior_attempts: [], exposures: productionBank.map((q) => ({ question_id: q.id, state: 'UNSEEN' as const, observed_at: 1_000,
      method: 'CONTROLLED_INVENTORY' as const, reference: `inventory:${q.id}` })) };
    const pool = analyzeExamPool(INTERNAL_FULL_BLUEPRINT_80, productionBank, context);
    expect(pool.status).toBe('ADEQUATE');

    const cap = analyzeFormCapacity({ blueprint: INTERNAL_FULL_BLUEPRINT_80, questions: productionBank, context });
    if (cap.status !== 'ANALYZED') throw new Error('capacity');
    expect(cap.qualityGate.productionEligible).toBe(gate.productionEligible);
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBeGreaterThanOrEqual(1);

    const one = buildExamFormSet({ id: 'public', blueprint: INTERNAL_FULL_BLUEPRINT_80, questions: productionBank, context, forms: 1, seed: 'public', reuse: { kind: 'NO_REUSE' } });
    if (one.status !== 'BUILT') throw new Error('form');
    const form = one.forms[0]!.form;
    expect(form.quality).toBe('COMPLETE');
    expect(form.question_ids).toHaveLength(INTERNAL_FULL_BLUEPRINT_80.total_questions);
    for (const [family, target] of Object.entries(INTERNAL_FULL_BLUEPRINT_80.family_targets)) expect(form.questions.filter((q) => q.family === family).length).toBe(target);
    expect(one.forms[0]!.qualification).toBe('FRESH_FULL');

    const two = planMultiFormExpansion({ blueprint: INTERNAL_FULL_BLUEPRINT_80, questions: productionBank, context, forms: 2 });
    if (two.status !== 'PLANNED') throw new Error('plan');
    expect(two.currentlyFeasible).toBe(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms >= 2);
  });
});
