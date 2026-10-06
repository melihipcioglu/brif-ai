import { describe, expect, it } from 'vitest';
import { createInitialVocab } from '../../src/data/initialVocab';
import { calculateMasteryEvidence, DAY_MS, MES_WEIGHTS } from '../../src/services/lexicalScheduler';
import { lexicalRecordSchema } from '../../src/services/validation';
import type { LexicalRecord } from '../../src/types/lexical';

/** Valid aggregate evidence without generating millions of review events. */
function evidence(unaided: number, assisted: number, incorrect = 0): LexicalRecord {
  const word = createInitialVocab(0)[0];
  if (word === undefined) throw new Error('Missing vocabulary fixture');
  const attempts = unaided + assisted + incorrect;
  const successfulContexts = ['biology', 'chemistry', 'physics'].slice(0, Math.min(3, unaided));
  return lexicalRecordSchema.parse({
    ...word,
    lexical_state: attempts === 0 ? 'NEW' : 'LEARNING',
    encounter_count: attempts,
    unaided_correct_count: unaided,
    assisted_correct_count: assisted,
    incorrect_count: incorrect,
    response_time_avg_ms: attempts === 0 ? 0 : 3_000,
    last_seen_at: attempts === 0 ? null : 14 * DAY_MS,
    last_success_at: unaided + assisted === 0 ? null : 14 * DAY_MS,
    contexts_seen: attempts === 0 ? [] : [...new Set(['biology', ...successfulContexts])],
    unaided_success_contexts: successfulContexts,
    evidence: {
      delayed_unaided_correct_count_3d: unaided >= 2 ? 1 : 0,
      delayed_unaided_correct_count_14d: unaided >= 2 ? 1 : 0,
      max_unaided_delay_days: unaided >= 2 ? 14 : 0,
      distractor_correct_count: unaided,
      distractor_attempt_count: attempts,
    },
  });
}

const accuracyScore = (unaided: number, assisted: number, incorrect = 0): number =>
  calculateMasteryEvidence(evidence(unaided, assisted, incorrect)).unaided_accuracy;

describe('MES evidence quality and sufficiency', () => {
  it('awards more accuracy evidence for one unaided success than one assisted success', () => {
    const assisted = accuracyScore(0, 1);
    const unaided = accuracyScore(1, 0);
    expect(assisted).toBeGreaterThan(0);
    expect(unaided).toBeGreaterThan(assisted);
    expect(assisted).toBeLessThan(20);
    expect(unaided).toBeLessThan(20);
  });

  it('gives unaided evidence 2–2.5 times the accuracy contribution at the first success', () => {
    const ratio = accuracyScore(1, 0) / accuracyScore(0, 1);
    expect(ratio).toBeGreaterThanOrEqual(2);
    expect(ratio).toBeLessThanOrEqual(2.5);
    expect(ratio).toBeCloseTo(2.1706348262, 8);
  });

  it('still distinguishes ten assisted successes from ten unaided successes', () => {
    const assisted = accuracyScore(0, 10);
    const unaided = accuracyScore(10, 0);
    expect(assisted).toBeCloseTo(17.2932943353, 8);
    expect(unaided).toBeCloseTo(19.8652410600, 8);
    expect(assisted).toBeLessThan(unaided);
  });

  it.each(['assisted', 'unaided'] as const)('%s evidence saturates monotonically with diminishing gains', (kind) => {
    const scoreAt = (count: number): number => kind === 'assisted' ? accuracyScore(0, count) : accuracyScore(count, 0);
    const firstGain = scoreAt(1) - scoreAt(0);
    const secondGain = scoreAt(2) - scoreAt(1);
    const thirdGain = scoreAt(3) - scoreAt(2);
    expect(thirdGain).toBeGreaterThan(0);
    expect(thirdGain).toBeLessThan(secondGain);
    expect(secondGain).toBeLessThan(firstGain);
    for (const count of [10, 100, 1_000, 1_000_000, Number.MAX_SAFE_INTEGER]) {
      expect(scoreAt(count)).toBeLessThanOrEqual(20);
      expect(scoreAt(count)).toBeGreaterThanOrEqual(scoreAt(3));
    }
    expect(scoreAt(1_000)).toBeCloseTo(20, 10);
  });

  it.each(['assisted', 'unaided'] as const)('incorrect evidence reduces the %s score, including after saturation', (kind) => {
    for (const count of [1, 10, 1_000]) {
      const scoreWith = (incorrect: number): number => kind === 'assisted' ?
        accuracyScore(0, count, incorrect) : accuracyScore(count, 0, incorrect);
      expect(scoreWith(1)).toBeLessThan(scoreWith(0));
      expect(scoreWith(10)).toBeLessThan(scoreWith(1));
    }
  });

  it('assigns zero accuracy evidence to no successes or to errors alone', () => {
    for (const incorrect of [0, 1, 10, 1_000_000, Number.MAX_SAFE_INTEGER]) {
      expect(accuracyScore(0, 0, incorrect)).toBe(0);
    }
  });

  it('bounds every component and total MES across empty, mixed and abundant evidence', () => {
    expect(MES_WEIGHTS).toEqual({ delayed_recall: 30, contexts: 25, unaided_accuracy: 20, speed: 15, distractor_resistance: 10 });
    const counts = [0, 1, 3, 10, 100, 1_000_000];
    for (const unaided of counts) for (const assisted of counts) for (const incorrect of counts) {
      const mes = calculateMasteryEvidence(evidence(unaided, assisted, incorrect));
      for (const component of Object.keys(MES_WEIGHTS) as (keyof typeof MES_WEIGHTS)[]) {
        expect(Number.isFinite(mes[component])).toBe(true);
        expect(mes[component]).toBeGreaterThanOrEqual(0);
        expect(mes[component]).toBeLessThanOrEqual(MES_WEIGHTS[component]);
      }
      expect(Number.isFinite(mes.total)).toBe(true);
      expect(mes.total).toBeGreaterThanOrEqual(0);
      expect(mes.total).toBeLessThanOrEqual(100);
    }
    expect(calculateMasteryEvidence(evidence(1_000, 0)).total).toBe(100);
  });

  it('leaves the speed contribution on quality alone without applying evidence sufficiency', () => {
    expect(calculateMasteryEvidence(evidence(0, 1)).speed).toBe(15);
    expect(calculateMasteryEvidence(evidence(1, 0)).speed).toBe(15);
    expect(calculateMasteryEvidence(evidence(0, 1, 1)).speed).toBeCloseTo(4.2857142857, 8);
    expect(calculateMasteryEvidence(evidence(1, 0, 1)).speed).toBe(7.5);
  });
});
