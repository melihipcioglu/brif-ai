import { describe, expect, it } from 'vitest';
import { createInitialVocab, initialVocab, initialVocabEntries } from '../../src/data/initialVocab';
import { createLearnerSkillVector, SKILL_IDS } from '../../src/types/learner';
import type { LexicalRecord, LexicalReview, RecallGrade } from '../../src/types/lexical';
import { calculateMES, calculateReviewPriority, DAY_MS, getFrictionLevel, recordEncounter, scheduleLexicalReview } from '../../src/services/lexicalScheduler';
import { lexicalRecordSchema } from '../../src/services/validation';

const fresh = (): LexicalRecord => {
  const word = createInitialVocab(0)[0];
  if (word === undefined) throw new Error('Missing vocabulary fixture');
  return word;
};
const review = (grade: RecallGrade, reviewed_at = 0, context_id = 'biology-1'): LexicalReview => ({
  grade, reviewed_at, context_id, response_time_ms: 3_000, assistance_used: false,
  distractor_test: { word: 'inhabit', resisted: grade !== 0 },
});

function mastered(): LexicalRecord {
  let word = fresh();
  for (const [day, context] of [[0, 'a'], [7, 'b'], [21, 'c']] as const) {
    word = scheduleLexicalReview(word, review(3, day * DAY_MS, context)).record;
  }
  return word;
}

describe('frozen architecture and initial vocabulary', () => {
  it('contains all thirteen exact skill dimensions with independent defaults', () => {
    const vector = createLearnerSkillVector();
    expect(SKILL_IDS).toHaveLength(13);
    expect(Object.keys(vector)).toEqual([...SKILL_IDS]);
    expect(vector.VOCAB_CONTEXT).not.toBe(vector.COLLOCATION_PREPOSITION);
    expect(vector.VOCAB_CONTEXT.uncertainty).toBe(1);
  });
  it('ships unique, valid Tier 1 and Tier 2 entries with families, collocations and distractors', () => {
    expect(initialVocab.length).toBeGreaterThanOrEqual(10);
    expect(new Set(initialVocab.map((word) => word.word_id)).size).toBe(initialVocab.length);
    expect(new Set(initialVocab.map((word) => word.tier))).toEqual(new Set([1, 2]));
    for (const word of initialVocab) {
      expect(lexicalRecordSchema.safeParse(word).success).toBe(true);
      expect(word.word_family.length).toBeGreaterThanOrEqual(3);
      expect(word.critical_collocations.length).toBeGreaterThanOrEqual(3);
      expect(word.typical_distractor.length).toBeGreaterThanOrEqual(3);
    }
    expect(initialVocabEntries.some((entry) => entry.lemma === 'susceptible to')).toBe(true);
  });
});

describe('Adaptive Stability Scheduler v1', () => {
  it.each([
    [0, 0.4, 1], [1, 1, 2], [2, 1.5, 1.5], [3, 2.2, 2.2],
  ] as const)('applies grade %i with exact stability %f and interval %f', (grade, stability, interval) => {
    const result = scheduleLexicalReview(fresh(), review(grade));
    expect(result.record.stability).toBeCloseTo(stability);
    expect(result.interval_days).toBeCloseTo(interval);
    expect(result.record.next_review_date).toBe(Math.round(interval * DAY_MS));
  });
  it('uses the personal factor only for strong unaided recall and enforces its range', () => {
    expect(scheduleLexicalReview(fresh(), review(3), 1.25).record.stability).toBeCloseTo(2.75);
    expect(scheduleLexicalReview(fresh(), review(2), 1.25).record.stability).toBe(1.5);
    expect(() => scheduleLexicalReview(fresh(), review(3), 1.26)).toThrow();
    expect(() => scheduleLexicalReview(fresh(), review(3), Number.NaN)).toThrow();
  });
  it('caps a hinted correct answer at assisted even if caller supplies grade 3', () => {
    const result = scheduleLexicalReview(fresh(), { ...review(3), assistance_used: true });
    expect(result.effective_grade).toBe(1);
    expect(result.record.unaided_correct_count).toBe(0);
    expect(result.record.assisted_correct_count).toBe(1);
    expect(result.record.stability).toBe(1);
  });
  it('never mutates the caller record', () => {
    const word = fresh();
    const before = structuredClone(word);
    scheduleLexicalReview(word, review(0));
    expect(word).toEqual(before);
  });
  it('elapsed time raises review priority without altering state or evidence', () => {
    const word = mastered();
    const before = structuredClone(word);
    expect(calculateReviewPriority(word, word.next_review_date + 21 * DAY_MS))
      .toBeGreaterThan(calculateReviewPriority(word, word.next_review_date));
    expect(calculateReviewPriority(word, word.next_review_date + 365 * DAY_MS)).toBeLessThanOrEqual(100);
    expect(word).toEqual(before);
    expect(word.lexical_state).toBe('MASTERED');
  });
  it('demotes on a test error, but not on assisted success', () => {
    let word = mastered();
    for (let index = 1; index <= 20; index += 1) {
      word = scheduleLexicalReview(word, { ...review(1, (21 + index) * DAY_MS, 'same'), response_time_ms: 60_000 }).record;
    }
    expect(word.mastery_score).toBeLessThan(85);
    expect(word.lexical_state).toBe('MASTERED');
    expect(scheduleLexicalReview(word, review(0, 50 * DAY_MS)).record.lexical_state).toBe('FAMILIAR');
  });
  it('counts a distractor error and requires unaided evidence to master a collocation', () => {
    let word = scheduleLexicalReview(fresh(), review(0)).record;
    expect(word.distractor_errors.inhabit).toBe(1);
    word = scheduleLexicalReview(word, { ...review(1, DAY_MS), tested_collocation: 'inhibit growth' }).record;
    expect(word.collocations_mastered).toEqual([]);
    word = scheduleLexicalReview(word, { ...review(3, 2 * DAY_MS), tested_collocation: 'inhibit growth' }).record;
    expect(word.collocations_mastered).toEqual(['inhibit growth']);
  });
  it('rejects invalid timestamps, latency, distractors, collocations and contradictory evidence', () => {
    const word = scheduleLexicalReview(fresh(), review(3, DAY_MS)).record;
    expect(() => scheduleLexicalReview(word, review(3, 0))).toThrow();
    expect(() => scheduleLexicalReview(fresh(), { ...review(3), response_time_ms: 0 })).toThrow();
    expect(() => scheduleLexicalReview(fresh(), { ...review(3), tested_collocation: 'invented' })).toThrow();
    expect(() => scheduleLexicalReview(fresh(), { ...review(3), distractor_test: { word: 'inhabit', resisted: false } })).toThrow();
    expect(() => calculateReviewPriority(word, Number.NaN)).toThrow();
  });
});

describe('Mastery Evidence Score', () => {
  it('starts at zero and awards no mastery for passive exposures', () => {
    let word = fresh();
    for (const context of ['a', 'b', 'c']) word = recordEncounter(word, context, 0);
    expect(word.lexical_state).toBe('SEEN');
    expect(calculateMES(word)).toBe(0);
    expect(word.unaided_correct_count).toBe(0);
  });
  it('requires 14-day delayed unaided recall and three contexts to master', () => {
    const word = mastered();
    expect(word.mastery_score).toBe(95.54);
    expect(word.lexical_state).toBe('MASTERED');
    expect(word.evidence.max_unaided_delay_days).toBe(14);
    let early = fresh();
    for (const [day, context] of [[0, 'a'], [1, 'b'], [14.999, 'c']] as const) {
      early = scheduleLexicalReview(early, review(3, Math.round(day * DAY_MS), context)).record;
    }
    expect(early.mastery_score).toBe(65.54);
    expect(early.lexical_state).not.toBe('MASTERED');
  });
  it('does not infer a delay before the first encounter or from repeated context IDs', () => {
    let word = scheduleLexicalReview(fresh(), review(3, 100 * DAY_MS)).record;
    expect(word.evidence.delayed_unaided_correct_count_14d).toBe(0);
    for (const day of [114, 128, 142]) word = scheduleLexicalReview(word, review(3, day * DAY_MS)).record;
    expect(word.contexts_seen).toHaveLength(1);
    expect(word.lexical_state).not.toBe('MASTERED');
  });
  it('resets the measured delay after a reading exposure', () => {
    let word = scheduleLexicalReview(fresh(), review(3, 0)).record;
    word = recordEncounter(word, 'reading', 20 * DAY_MS);
    word = scheduleLexicalReview(word, review(3, 21 * DAY_MS, 'exam')).record;
    expect(word.evidence.delayed_unaided_correct_count_14d).toBe(0);
  });
  it('maps states to the four required friction levels', () => {
    expect(['NEW', 'SEEN', 'LEARNING', 'FAMILIAR', 'MASTERED'].map((state) =>
      getFrictionLevel({ lexical_state: state as LexicalRecord['lexical_state'] }))).toEqual([1, 1, 2, 3, 4]);
  });
});
