import { describe, it, expect } from 'vitest';
import {
  createInitialWordRecord,
  recordWordEncounter,
  isReviewDue,
  isRelapsingOrDifficult,
  categorizeWordPool
} from '../../../src/services/learning/spacedRepetition';

describe('Spaced Repetition Engine', () => {
  it('creates clean initial record in NOT_STARTED state', () => {
    const rec = createInitialWordRecord('catalyst');
    expect(rec.wordId).toBe('catalyst');
    expect(rec.state).toBe('NOT_STARTED');
    expect(rec.consecutiveCorrect).toBe(0);
    expect(rec.encounters).toHaveLength(0);
  });

  it('advances from NOT_STARTED to LEARNING on first correct encounter', () => {
    const t0 = 1000000;
    const initial = createInitialWordRecord('catalyst');
    const step1 = recordWordEncounter(initial, { context: 'CARD_INTRO', success: true }, t0);

    expect(step1.state).toBe('LEARNING');
    expect(step1.consecutiveCorrect).toBe(1);
    expect(step1.intervalDays).toBe(1);
    expect(step1.nextReviewAt).toBe(t0 + 1 * 24 * 60 * 60 * 1000);
  });

  it('promotes to RETAINED on second consecutive success', () => {
    const t0 = 1000000;
    const initial = createInitialWordRecord('catalyst');
    const step1 = recordWordEncounter(initial, { context: 'CARD_INTRO', success: true }, t0);
    const step2 = recordWordEncounter(step1, { context: 'FILL_BLANK', success: true }, t0 + 86400000);

    expect(step2.state).toBe('RETAINED');
    expect(step2.consecutiveCorrect).toBe(2);
    expect(step2.intervalDays).toBeGreaterThanOrEqual(3);
  });

  it('prevents false same-day mastery and promotes to MASTERED across distinct days and 3D dimensions', () => {
    const day1 = 1770000000000; // Day 1
    const day2 = day1 + 24 * 60 * 60 * 1000; // Day 2

    let rec = createInitialWordRecord('catalyst');
    // Day 1: 4 encounters on same day
    rec = recordWordEncounter(rec, { context: 'CARD_INTRO', success: true }, day1);
    rec = recordWordEncounter(rec, { context: 'FILL_BLANK', success: true }, day1 + 1000);
    rec = recordWordEncounter(rec, { context: 'COLLOCATION', success: true }, day1 + 2000);
    rec = recordWordEncounter(rec, { context: 'READING', success: true }, day1 + 3000);

    // On same day, state must NEVER be MASTERED, even with 4 successes!
    expect(rec.state).toBe('RETAINED');
    expect(rec.distinctDaysTested?.length).toBe(1);

    // Day 2: Test Transfer & Application context on subsequent day
    rec = recordWordEncounter(rec, { context: 'PRACTICE_QUESTION', success: true }, day2);

    expect(rec.state).toBe('MASTERED');
    expect(rec.distinctDaysTested?.length).toBe(2);
    expect(rec.recognitionMastered).toBe(true);
    expect(rec.comprehensionMastered).toBe(true);
    expect(rec.transferMastered).toBe(true);
  });

  it('relapses immediately to LEARNING upon a failure and resets interval to 1 day', () => {
    const t0 = 1000000;
    let rec = createInitialWordRecord('catalyst');
    rec = recordWordEncounter(rec, { context: 'CARD_INTRO', success: true }, t0);
    rec = recordWordEncounter(rec, { context: 'FILL_BLANK', success: true }, t0 + 1000);
    expect(rec.state).toBe('RETAINED');

    // Fails on subsequent test
    const failed = recordWordEncounter(rec, { context: 'PRACTICE_QUESTION', success: false }, t0 + 2000);
    expect(failed.state).toBe('LEARNING');
    expect(failed.consecutiveCorrect).toBe(0);
    expect(failed.intervalDays).toBe(1);
    expect(isRelapsingOrDifficult(failed)).toBe(true);
  });

  it('correctly reports review due status according to simulated timestamp', () => {
    const t0 = 1000000;
    let rec = createInitialWordRecord('catalyst');
    rec = recordWordEncounter(rec, { context: 'CARD_INTRO', success: true }, t0);

    // Before due
    expect(isReviewDue(rec, t0 + 1000)).toBe(false);

    // After 1 day
    expect(isReviewDue(rec, t0 + 86400000 + 1000)).toBe(true);
  });

  it('categorizes word pool into notStarted, learning, reviewDue, relapsing', () => {
    const t0 = 10000000;
    const r1 = createInitialWordRecord('w1');
    let r2 = createInitialWordRecord('w2');
    r2 = recordWordEncounter(r2, { context: 'CARD_INTRO', success: true }, t0 - 200000000); // long ago -> review due
    let r3 = createInitialWordRecord('w3');
    r3 = recordWordEncounter(r3, { context: 'CARD_INTRO', success: false }, t0);
    r3 = recordWordEncounter(r3, { context: 'CARD_INTRO', success: false }, t0); // relapsing

    const records = { w1: r1, w2: r2, w3: r3 };
    const pool = categorizeWordPool(records, ['w1', 'w2', 'w3'], t0);

    expect(pool.notStarted).toContain('w1');
    expect(pool.reviewDue).toContain('w2');
    expect(pool.relapsingOrDifficult).toContain('w3');
  });
});
