import { describe, it, expect } from 'vitest';
import {
  productionBank,
  validateQuestionBank,
  INTERNAL_FULL_BLUEPRINT_80 as fullBlueprint,
  analyzeFormCapacity,
  buildExamFormSet,
  planMultiFormExpansion,
  QUESTION_FAMILIES
} from '../../../src/index';
import type { QuestionFamily } from '../../../src/types/question';

const AS_OF = 1000;
const inventory = {
  as_of: AS_OF,
  prior_attempts: [],
  exposures: productionBank.map((q) => ({
    question_id: q.id,
    state: 'UNSEEN' as const,
    observed_at: AS_OF,
    method: 'CONTROLLED_INVENTORY' as const,
    reference: `inv:${q.id}`
  }))
};
const unverifiedContext = { as_of: AS_OF, prior_attempts: [], exposures: [] };

describe('Phase 11: Question Bank Expansion & Multi-Form Capacity', () => {
  it('verifies that the expanded production bank contains at least 160 valid, production-eligible questions', () => {
    expect(productionBank.length).toBeGreaterThanOrEqual(160);
    const gate = validateQuestionBank(productionBank);

    expect(gate.total).toBe(160);
    expect(gate.valid).toBe(160);
    expect(gate.productionEligible).toBe(160);
    expect(gate.rejected).toBe(0);
    expect(gate.exactDuplicatesFound).toBe(0);
    expect(gate.results.some((r) => r.errors.length > 0)).toBe(false);

    // Exactly 20 questions in every one of the 8 YÖKDİL families
    for (const family of QUESTION_FAMILIES) {
      expect(gate.families[family]).toBe(20);
    }

    // Answer positions are distributed across A, B, C, D, E
    for (const opt of ['A', 'B', 'C', 'D', 'E']) {
      expect(gate.answerPositionDistribution[opt]).toBeGreaterThanOrEqual(20);
    }
  });

  it('proves that capacity engine analyzes exactly 2 full disjoint forms from the 160-item bank', () => {
    const cap = analyzeFormCapacity({
      blueprint: fullBlueprint,
      questions: productionBank,
      context: inventory
    });

    if (cap.status !== 'ANALYZED') throw new Error('Expected ANALYZED status');

    expect(cap.tiers.RAW.upperBound).toBe(2);
    expect(cap.tiers.RAW.verifiedDisjointFullForms).toBe(2);
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(2);
    expect(cap.tiers.RAW.bottleneckFamilies).toEqual(QUESTION_FAMILIES);

    // Multi-form planning: 2 forms need 0 extra questions; 3 forms need exactly 80 extra questions
    const plan2 = planMultiFormExpansion({
      blueprint: fullBlueprint,
      questions: productionBank,
      context: inventory,
      forms: 2
    });
    if (plan2.status !== 'PLANNED') throw new Error('Expected PLANNED status');
    expect(plan2.currentlyFeasible).toBe(true);
    expect(plan2.additionalQuestionsRequired).toBe(0);

    const plan3 = planMultiFormExpansion({
      blueprint: fullBlueprint,
      questions: productionBank,
      context: inventory,
      forms: 3
    });
    if (plan3.status !== 'PLANNED') throw new Error('Expected PLANNED status');
    expect(plan3.currentlyFeasible).toBe(false);
    expect(plan3.additionalQuestionsRequired).toBe(80);
    for (const family of QUESTION_FAMILIES) {
      expect(plan3.familyShortfalls[family as QuestionFamily]).toBe(10);
    }
  }, 15000);

  it('builds two completely disjoint, independent 80-question mock exams (Form 1 and Form 2)', () => {
    const result = buildExamFormSet({
      id: 'mock-exam-series',
      blueprint: fullBlueprint,
      questions: productionBank,
      context: inventory,
      forms: 2,
      seed: 'yokdil-fen-2026',
      reuse: { kind: 'NO_REUSE' }
    });

    if (result.status !== 'BUILT') throw new Error('Expected BUILT status');

    expect(result.forms).toHaveLength(2);
    expect(result.qualification).toBe('ALL_DISJOINT');
    expect(result.overlap.maxPairwiseShared).toBe(0);
    expect(result.overlap.reuseCount).toBe(0);
    expect(result.overlap.totalUniqueQuestions).toBe(160);
    expect(result.overlap.allPairwiseDisjoint).toBe(true);

    const form1 = result.forms[0]!.form;
    const form2 = result.forms[1]!.form;

    expect(form1.quality).toBe('COMPLETE');
    expect(form2.quality).toBe('COMPLETE');
    expect(form1.questions).toHaveLength(80);
    expect(form2.questions).toHaveLength(80);

    // Form 1 and Form 2 have 0 shared question IDs
    const form1Ids = new Set(form1.question_ids);
    const form2Ids = new Set(form2.question_ids);
    expect(form1Ids.size).toBe(80);
    expect(form2Ids.size).toBe(80);
    const shared = form1.question_ids.filter((id) => form2Ids.has(id));
    expect(shared).toHaveLength(0);

    // Each form satisfies exact blueprint family targets (10 per family)
    for (const family of QUESTION_FAMILIES) {
      expect(form1.questions.filter((q) => q.family === family)).toHaveLength(10);
      expect(form2.questions.filter((q) => q.family === family)).toHaveLength(10);
    }

    // Both forms have unique fingerprints
    expect(form1.fingerprint).not.toBe(form2.fingerprint);
  }, 15000);

  it('maintains exposure safety: unverified context refuses fresh forms fail-closed under UNSEEN_ONLY', () => {
    const cap = analyzeFormCapacity({
      blueprint: fullBlueprint,
      questions: productionBank,
      context: unverifiedContext
    });

    if (cap.status !== 'ANALYZED') throw new Error('Expected ANALYZED status');

    expect(cap.exposure.VERIFIED_FRESH).toBe(0);
    expect(cap.exposure.UNKNOWN_EXPOSURE).toBe(160);
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(0);
    expect(cap.tiers.FRESH_OR_UNKNOWN.verifiedDisjointFullForms).toBe(2);

    // Under default UNSEEN_ONLY policy, build fails because 0 items are verified fresh
    const failBuild = buildExamFormSet({
      id: 'unverified-attempt',
      blueprint: fullBlueprint,
      questions: productionBank,
      context: unverifiedContext,
      forms: 1,
      seed: 'seed-unverified',
      reuse: { kind: 'NO_REUSE' }
    });
    expect(failBuild.status).toBe('INSUFFICIENT_CAPACITY');

    // Under explicit EXCLUDE_SEEN policy, build succeeds with UNKNOWN_EXPOSURE qualification
    const allowUnknown = buildExamFormSet({
      id: 'unknown-allowed',
      blueprint: fullBlueprint,
      questions: productionBank,
      context: unverifiedContext,
      exposurePolicy: 'EXCLUDE_SEEN',
      forms: 2,
      seed: 'seed-unknown',
      reuse: { kind: 'NO_REUSE' }
    });
    if (allowUnknown.status !== 'BUILT') throw new Error('Expected BUILT status');
    expect(allowUnknown.forms[0]!.qualification).toBe('UNKNOWN_EXPOSURE_FULL');
    expect(allowUnknown.forms[0]!.calibrationFresh).toBe(false);
  }, 15000);

  it('preserves Form 2 fresh capacity after Form 1 is fully completed and seen', () => {
    // Generate Form 1
    const form1Result = buildExamFormSet({
      id: 'first-session',
      blueprint: fullBlueprint,
      questions: productionBank,
      context: inventory,
      forms: 1,
      seed: 'session-1',
      reuse: { kind: 'NO_REUSE' }
    });
    if (form1Result.status !== 'BUILT') throw new Error('Expected BUILT status');
    const form1 = form1Result.forms[0]!.form;

    // Simulate completion: all questions in Form 1 are now SEEN
    const updatedContext = {
      as_of: 2000,
      prior_attempts: [],
      exposures: productionBank.map((q) => {
        const isSeenInForm1 = form1.question_ids.includes(q.id);
        return {
          question_id: q.id,
          state: isSeenInForm1 ? ('SEEN' as const) : ('UNSEEN' as const),
          observed_at: 2000,
          method: isSeenInForm1 ? ('RECORDED_EXPOSURE' as const) : ('CONTROLLED_INVENTORY' as const),
          reference: isSeenInForm1 ? `session-1:${q.id}` : `inv:${q.id}`
        };
      })
    };

    const capAfter = analyzeFormCapacity({
      blueprint: fullBlueprint,
      questions: productionBank,
      context: updatedContext
    });
    if (capAfter.status !== 'ANALYZED') throw new Error('Expected ANALYZED status');

    // Exactly 80 questions are SEEN, 80 remain VERIFIED_FRESH
    expect(capAfter.exposure.KNOWN_SEEN).toBe(80);
    expect(capAfter.exposure.VERIFIED_FRESH).toBe(80);
    expect(capAfter.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(1);

    // Form 2 can still be built as FRESH_FULL under strict UNSEEN_ONLY!
    const form2Result = buildExamFormSet({
      id: 'second-session',
      blueprint: fullBlueprint,
      questions: productionBank,
      context: updatedContext,
      forms: 1,
      seed: 'session-2',
      reuse: { kind: 'NO_REUSE' }
    });
    if (form2Result.status !== 'BUILT') throw new Error('Expected BUILT status');
    expect(form2Result.forms[0]!.qualification).toBe('FRESH_FULL');
    expect(form2Result.forms[0]!.calibrationFresh).toBe(true);
    expect(form2Result.forms[0]!.form.question_ids.every((id) => !form1.question_ids.includes(id))).toBe(true);
  }, 15000);
});
