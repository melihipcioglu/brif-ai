import { describe, expect, it } from 'vitest';
import { createInitialVocab } from '../../src/data/initialVocab';
import type { LexicalRecord, LexicalReview, RecallGrade } from '../../src/types/lexical';
import { calculateMasteryEvidence, calculateReviewPriority, DAY_MS, recordEncounter, scheduleLexicalReview } from '../../src/services/lexicalScheduler';
import { createLearnerSkillVector } from '../../src/types/learner';
import { lexicalRecordSchema, skillMetricsSchema } from '../../src/services/validation';

function fresh(): LexicalRecord {
  const word = createInitialVocab(0)[0];
  if (word === undefined) throw new Error('Missing vocabulary fixture');
  return word;
}

function recall(word: LexicalRecord, grade: RecallGrade, day: number, context: string, extra: Partial<LexicalReview> = {}): LexicalRecord {
  return scheduleLexicalReview(word, {
    grade, context_id: context, reviewed_at: Math.round(day * DAY_MS),
    response_time_ms: 3_000, assistance_used: false,
    distractor_test: { word: 'inhabit', resisted: grade !== 0 }, ...extra,
  }).record;
}

function familiar(): LexicalRecord {
  let word = fresh();
  for (const [day, context] of [[0, 'a'], [1, 'b'], [4, 'c']] as const) word = recall(word, 3, day, context);
  return word;
}

function mastered(word = fresh(), testDistractor = true): LexicalRecord {
  for (const [day, context] of [[0, 'a'], [3, 'b'], [17, 'c']] as const) {
    word = scheduleLexicalReview(word, {
      grade: 3, context_id: context, reviewed_at: day * DAY_MS, response_time_ms: 3_000, assistance_used: false,
      ...(testDistractor ? { distractor_test: { word: 'inhabit', resisted: true } } : {}),
    }).record;
  }
  return word;
}

describe('MES accuracy evidence calibration audit', () => {
  it.each([
    { name: 'no evidence', grades: [], contribution: 0 },
    { name: 'one unaided success', grades: [3], contribution: 7.8693868057 },
    { name: 'one assisted success', grades: [1], contribution: 3.6253849384 },
    { name: 'only errors', grades: [0, 0], contribution: 0 },
    { name: 'unaided success and one error', grades: [3, 0], contribution: 3.9346934029 },
    { name: 'assisted success and one error', grades: [1, 0], contribution: 1.0358242681 },
    { name: 'mixed success and one error', grades: [3, 1, 0], contribution: 5.8731714558 },
  ] satisfies { name: string; grades: RecallGrade[]; contribution: number }[])(
    '$name has the documented accuracy evidence contribution', ({ grades, contribution }) => {
      let word = fresh();
      for (const grade of grades) word = recall(word, grade, 0, 'same');
      expect(calculateMasteryEvidence(word).unaided_accuracy).toBeCloseTo(contribution, 8);
    },
  );
});

describe('context and familiar gate audit', () => {
  it('three passive contexts with no recall give zero context MES and zero mastery contexts', () => {
    let word = fresh();
    for (const context of ['a', 'b', 'c']) word = recordEncounter(word, context, 0);
    expect(word.contexts_seen).toHaveLength(3);
    expect(word.unaided_success_contexts).toEqual([]);
    expect(calculateMasteryEvidence(word).contexts).toBe(0);
  });
  it.each([0, 1] as const)('three grade %i reviews in three contexts give no transfer credit', (grade) => {
    let word = fresh();
    for (const context of ['a', 'b', 'c']) word = recall(word, grade, 0, context);
    expect(word.contexts_seen).toHaveLength(3);
    expect(word.unaided_success_contexts).toEqual([]);
    expect(calculateMasteryEvidence(word).contexts).toBe(0);
  });
  it('three successful unaided contexts earn all 25 transfer points without duplicates', () => {
    let word = fresh();
    for (const context of ['a', 'b', 'c', 'a']) word = recall(word, 3, 0, context);
    expect(word.unaided_success_contexts).toEqual(['a', 'b', 'c']);
    expect(calculateMasteryEvidence(word).contexts).toBe(25);
  });
  it('hints cap the effective grade and cannot add a successful context or delayed recall', () => {
    let word = recall(fresh(), 3, 0, 'unaided');
    word = recall(word, 3, 21, 'hinted', { assistance_used: true });
    expect(word.contexts_seen).toContain('hinted');
    expect(word.unaided_success_contexts).toEqual(['unaided']);
    expect(word.evidence.delayed_unaided_correct_count_3d).toBe(0);
    expect(word.evidence.delayed_unaided_correct_count_14d).toBe(0);
  });
  it('three passive contexts followed by assisted recall still earn zero context MES', () => {
    let word = fresh();
    for (const context of ['a', 'b', 'c']) word = recordEncounter(word, context, 0);
    word = recall(word, 1, 0, 'a');
    expect(calculateMasteryEvidence(word).contexts).toBe(0);
  });
  it('ten correct same-day recalls can exceed MES 60 but cannot become FAMILIAR', () => {
    let word = fresh();
    for (let index = 0; index < 10; index += 1) word = recall(word, 3, 0, `c-${index}`);
    expect(word.mastery_score).toBeGreaterThan(60);
    expect(word.lexical_state).toBe('LEARNING');
  });
  it('MES >= 60 and an exact three-day unaided recall permit FAMILIAR', () => {
    const word = familiar();
    expect(word.mastery_score).toBe(65.54);
    expect(word.evidence.delayed_unaided_correct_count_3d).toBe(1);
    expect(word.evidence.delayed_unaided_correct_count_14d).toBe(0);
    expect(calculateMasteryEvidence(word).eligible_for_familiar).toBe(true);
    expect(word.lexical_state).toBe('FAMILIAR');
  });
  it('2.999 days or an intervening exposure cannot satisfy the familiar delay gate', () => {
    let early = recall(recall(fresh(), 3, 0, 'a'), 3, 0, 'b');
    early = recall(early, 3, 2.999, 'c');
    expect(early.mastery_score).toBe(65.54);
    expect(early.lexical_state).toBe('LEARNING');
    let exposed = recall(recall(fresh(), 3, 0, 'a'), 3, 0, 'b');
    exposed = recordEncounter(exposed, 'reading', 2 * DAY_MS);
    exposed = recall(exposed, 3, 3, 'c');
    expect(exposed.evidence.delayed_unaided_correct_count_3d).toBe(0);
    expect(exposed.lexical_state).toBe('LEARNING');
  });
  it('validates the success-context subset, duplicates and delayed counter hierarchy', () => {
    const word = recall(fresh(), 3, 0, 'a');
    expect(lexicalRecordSchema.safeParse({ ...word, unaided_success_contexts: ['unseen'] }).success).toBe(false);
    expect(lexicalRecordSchema.safeParse({ ...word, unaided_success_contexts: ['a', 'a'] }).success).toBe(false);
    expect(lexicalRecordSchema.safeParse({ ...word, lexical_state: 'FAMILIAR' }).success).toBe(false);
    expect(lexicalRecordSchema.safeParse({ ...word, evidence: {
      ...word.evidence, delayed_unaided_correct_count_14d: 1, max_unaided_delay_days: 14,
    } }).success).toBe(false);
  });
});

describe('mastered evidence gates', () => {
  it('does not trust a cached MES >=85 or three passive exposures as mastery evidence', () => {
    const word: LexicalRecord = { ...mastered(), lexical_state: 'LEARNING', mastery_score: 99, unaided_success_contexts: [] };
    expect(word.contexts_seen).toHaveLength(3);
    expect(calculateMasteryEvidence(word).contexts).toBe(0);
    expect(calculateMasteryEvidence(word).eligible_for_mastered).toBe(false);
    expect(lexicalRecordSchema.safeParse({ ...word, lexical_state: 'MASTERED' }).success).toBe(false);
  });
  it('requires fourteen days, three successful contexts, sufficient MES and required evidence', () => {
    const word = mastered();
    expect(word.mastery_score).toBe(95.54);
    expect(word.unaided_success_contexts).toHaveLength(3);
    expect(word.evidence.delayed_unaided_correct_count_3d).toBe(2);
    expect(word.evidence.delayed_unaided_correct_count_14d).toBe(1);
    expect(calculateMasteryEvidence(word).eligible_for_mastered).toBe(true);
    expect(word.lexical_state).toBe('MASTERED');
  });
  it('does not invent a mandatory collocation gate for ordinary words', () => {
    const word = mastered();
    expect(word.mastery_requirements.collocation_required).toBe(false);
    expect(word.collocations_mastered).toEqual([]);
    expect(word.lexical_state).toBe('MASTERED');
  });
  it('enforces an explicit collocation requirement even above MES 85', () => {
    let word = mastered({ ...fresh(), mastery_requirements: { collocation_required: true, distractor_required: true } });
    expect(word.mastery_score).toBe(95.54);
    expect(word.lexical_state).toBe('FAMILIAR');
    expect(lexicalRecordSchema.safeParse({ ...word, lexical_state: 'MASTERED' }).success).toBe(false);
    word = recall(word, 1, 18, 'assisted-collocation', { tested_collocation: 'inhibit growth' });
    expect(word.lexical_state).toBe('FAMILIAR');
    word = recall(word, 3, 19, 'tested-collocation', { tested_collocation: 'inhibit growth' });
    expect(word.collocations_mastered).toContain('inhibit growth');
    expect(word.lexical_state).toBe('MASTERED');
  });
  it('enforces required resistance independently of MES and honors an explicit opt-out', () => {
    let required = mastered(fresh(), false);
    expect(required.mastery_score).toBe(85.54);
    expect(required.lexical_state).toBe('FAMILIAR');
    expect(lexicalRecordSchema.safeParse({ ...required, lexical_state: 'MASTERED' }).success).toBe(false);
    required = recall(required, 3, 18, 'resistance');
    expect(required.lexical_state).toBe('MASTERED');
    const optional = mastered({ ...fresh(), mastery_requirements: { collocation_required: false, distractor_required: false } }, false);
    expect(optional.mastery_score).toBe(85.54);
    expect(optional.lexical_state).toBe('MASTERED');
  });
  it('marks the preposition-bearing susceptible to entry as requiring collocation evidence', () => {
    const word = createInitialVocab(0).find((entry) => entry.word_id === 'susceptible-to');
    expect(word?.mastery_requirements).toEqual({ collocation_required: true, distractor_required: true });
  });
});

describe('deterministic demotion and time decay', () => {
  it('one confirmed lexical error demotes MASTERED to FAMILIAR', () => {
    expect(recall(mastered(), 0, 18, 'error').lexical_state).toBe('FAMILIAR');
  });
  it('one confirmed lexical error demotes FAMILIAR to LEARNING', () => {
    expect(recall(familiar(), 0, 5, 'error').lexical_state).toBe('LEARNING');
  });
  it('an ordinary error leaves LEARNING at LEARNING', () => {
    const learning = recall(fresh(), 3, 0, 'a');
    expect(recall(learning, 0, 1, 'error').lexical_state).toBe('LEARNING');
  });
  it('thirty inactive days preserve FAMILIAR while increasing review priority', () => {
    const word = familiar();
    const before = structuredClone(word);
    expect(calculateReviewPriority(word, 34 * DAY_MS)).toBeGreaterThan(calculateReviewPriority(word, 4 * DAY_MS));
    expect(word.lexical_state).toBe('FAMILIAR');
    expect(word).toEqual(before);
  });
});

describe('SkillMetrics mastery is a fraction', () => {
  it('accepts 0.8 and supports ErrorProbability = 1 - mastery', () => {
    const metrics = skillMetricsSchema.parse({ ...createLearnerSkillVector().VOCAB_CONTEXT, mastery: 0.8 });
    expect(1 - metrics.mastery).toBeCloseTo(0.2);
  });
  it.each([80, -0.01, 1.01, Number.NaN, Number.POSITIVE_INFINITY])('rejects %s as domain skill mastery', (mastery) => {
    expect(skillMetricsSchema.safeParse({ ...createLearnerSkillVector().VOCAB_CONTEXT, mastery }).success).toBe(false);
  });
});
