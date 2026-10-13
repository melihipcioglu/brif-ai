import { describe, it, expect } from 'vitest';
import {
  productionBank,
  INTERNAL_FULL_BLUEPRINT_80 as fullBlueprint,
  buildExamFormSet,
  auditBankSimilarity,
  auditFormSetSimilarityAndLeakage
} from '../../../src/index';
import type { Question } from '../../../src/types/question';
import type { ExamForm } from '../../../src/types/exam';

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

describe('Phase 11: Similarity, Leakage & Disjointness Audit', () => {
  it('verifies that the 160-item production bank has 0 internal duplicates and 0 shared passages', () => {
    const audit = auditBankSimilarity(productionBank);
    expect(audit.totalQuestions).toBe(160);
    expect(audit.exactDuplicates).toHaveLength(0);
    expect(audit.nearDuplicates).toHaveLength(0);
    expect(audit.sharedPassageGroups).toHaveLength(0);
    expect(audit.pass).toBe(true);
  });

  it('proves that two generated forms have 0 passage leakage, 0 question overlap, and 0 distractor leakage', () => {
    const set = buildExamFormSet({
      id: 'leakage-audit-set',
      blueprint: fullBlueprint,
      questions: productionBank,
      context: inventory,
      forms: 2,
      seed: 'strict-audit-seed',
      reuse: { kind: 'NO_REUSE' }
    });

    if (set.status !== 'BUILT') throw new Error('Expected BUILT status');

    const form1 = set.forms[0]!.form;
    const form2 = set.forms[1]!.form;

    const audit = auditFormSetSimilarityAndLeakage([form1, form2]);
    expect(audit.formCount).toBe(2);
    expect(audit.allPairwiseDisjoint).toBe(true);
    expect(audit.sharedQuestionIds).toHaveLength(0);
    expect(audit.crossFormPassageLeakages).toHaveLength(0);
    expect(audit.crossFormNearDuplicates).toHaveLength(0);
    expect(audit.distractorLeakages).toHaveLength(0);
    expect(audit.pass).toBe(true);
    expect(audit.summary.distinctItems).toBe(160);
    expect(audit.summary.crossFormLeakageCount).toBe(0);
    expect(audit.summary.crossFormNearDuplicateCount).toBe(0);
  });

  const makeMockForm = (id: string, fp: string, questions: readonly Question[]): ExamForm => ({
    id,
    quality: 'COMPLETE',
    blueprint: fullBlueprint,
    created_at: 1000,
    seed: null,
    selection_policy: 'exam-form-policy-v1',
    question_ids: questions.map((q) => q.id),
    questions,
    exposure: {},
    fingerprint: fp
  });

  it('negative test: audit catches cross-form question ID reuse', () => {
    const q0 = productionBank[0]!;
    const mockFormA = makeMockForm('form-a', 'fp-a', [q0]);
    const mockFormB = makeMockForm('form-b', 'fp-b', [q0]);

    const audit = auditFormSetSimilarityAndLeakage([mockFormA, mockFormB]);
    expect(audit.allPairwiseDisjoint).toBe(false);
    expect(audit.sharedQuestionIds).toContain(q0.id);
    expect(audit.pass).toBe(false);
  });

  it('negative test: audit catches cross-form passage leakage', () => {
    const passageText = 'A groundbreaking discovery was made in molecular astrophysics regarding prebiotic chemistry.';
    const qA: Question = {
      ...productionBank[0]!,
      id: 'qa-unique',
      passage: passageText,
      stem: 'What is the main finding in the passage?'
    };
    const qB: Question = {
      ...productionBank[1]!,
      id: 'qb-unique',
      passage: passageText,
      stem: 'Which field made the discovery mentioned above?'
    };

    const mockFormA = makeMockForm('form-a', 'fp-a', [qA]);
    const mockFormB = makeMockForm('form-b', 'fp-b', [qB]);

    const audit = auditFormSetSimilarityAndLeakage([mockFormA, mockFormB]);
    expect(audit.allPairwiseDisjoint).toBe(true); // IDs are different
    expect(audit.crossFormPassageLeakages).toHaveLength(1);
    expect(audit.crossFormPassageLeakages[0]!.overlapScore).toBe(1.0);
    expect(audit.pass).toBe(false);
  });

  it('negative test: audit catches distractor / answer leakage across forms', () => {
    const uniqueAnswer = 'The catalytic conversion of atmospheric nitrogen via engineered molybdenum enzymes';
    const qB: Question = {
      ...productionBank[0]!,
      id: 'qb-target',
      correct_option: 'C',
      options: [
        { id: 'A', text: 'Incorrect option alpha' },
        { id: 'B', text: 'Incorrect option beta' },
        { id: 'C', text: uniqueAnswer },
        { id: 'D', text: 'Incorrect option delta' },
        { id: 'E', text: 'Incorrect option epsilon' }
      ]
    };
    // qA in Form A leaks the exact correct answer of qB in its passage/stem
    const qA: Question = {
      ...productionBank[1]!,
      id: 'qa-leaker',
      stem: `Recent studies show that ${uniqueAnswer} is surprisingly rapid.`
    };

    const mockFormA = makeMockForm('form-a', 'fp-a', [qA]);
    const mockFormB = makeMockForm('form-b', 'fp-b', [qB]);

    const audit = auditFormSetSimilarityAndLeakage([mockFormA, mockFormB]);
    expect(audit.distractorLeakages).toHaveLength(1);
    expect(audit.distractorLeakages[0]!.leakedText).toBe(uniqueAnswer);
    expect(audit.pass).toBe(false);
  });
});
