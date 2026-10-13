import { describe, it, expect } from 'vitest';
import {
  createInitialLearnerProfile,
  generateDailyPlan
} from '../../../src/services/learning/dailyPlanner';
import {
  recordWordPracticeResult,
  recordReadingCompletion,
  recordPracticeQuestionCompletion
} from '../../../src/services/learning/learningProfileService';

describe('Daily Study Planner & Profile Service', () => {
  it('creates clean Day 1 profile with initial daily plan for beginner', () => {
    const t0 = 1791900000000;
    const profile = createInitialLearnerProfile(t0);

    expect(profile.todayPlan.dayNumber).toBe(1);
    expect(profile.todayPlan.newWordIds.length).toBeGreaterThanOrEqual(6);
    expect(profile.todayPlan.reviewWordIds).toHaveLength(0);
    expect(profile.todayPlan.relapsingWordIds).toHaveLength(0);
    expect(profile.todayPlan.practiceQuestionIds.length).toBeGreaterThanOrEqual(3);
    expect(profile.streakDays).toBe(1);
    expect(profile.todayPlan.isCompleted).toBe(false);
  });

  it('updates word progress and today plan steps on word practice', () => {
    const t0 = 1791900000000;
    let profile = createInitialLearnerProfile(t0);
    const targetWord = profile.todayPlan.newWordIds[0]!;

    profile = recordWordPracticeResult(profile, targetWord, 'CARD_INTRO', true, t0);

    expect(profile.wordRecords[targetWord]?.state).toBe('LEARNING');
    expect(profile.todayPlan.completedSteps.vocabLearned).toBe(1);
    expect(profile.totalWordsLearned).toBe(1);
  });

  it('records reading completion and updates scaffold progression', () => {
    const t0 = 1791900000000;
    let profile = createInitialLearnerProfile(t0);

    profile = recordReadingCompletion(profile, 'CLAUSE_DECOMPOSITION', 1.0);

    expect(profile.todayPlan.completedSteps.readingCompleted).toBe(true);
    expect(profile.readingMastery.CLAUSE_DECOMPOSITION.encounters).toBe(1);
    expect(profile.readingMastery.CLAUSE_DECOMPOSITION.accuracy).toBe(1.0);
  });

  it('completes daily plan when all goals are met', () => {
    const t0 = 1791900000000;
    let profile = createInitialLearnerProfile(t0);

    // Complete all new words
    for (const w of profile.todayPlan.newWordIds) {
      profile = recordWordPracticeResult(profile, w, 'CARD_INTRO', true, t0);
    }

    // Complete reading
    profile = recordReadingCompletion(profile, profile.todayPlan.readingSkillTopic, 1.0);

    // Complete practice questions
    for (let i = 0; i < profile.todayPlan.practiceQuestionIds.length; i++) {
      profile = recordPracticeQuestionCompletion(profile);
    }

    expect(profile.todayPlan.isCompleted).toBe(true);
  });

  it('generates day 2 plan incorporating words now due for review', () => {
    const t0 = 1791900000000;
    let profile = createInitialLearnerProfile(t0);
    const word1 = profile.todayPlan.newWordIds[0]!;

    // Practice word1 on day 1
    profile = recordWordPracticeResult(profile, word1, 'CARD_INTRO', true, t0);

    // Advance clock by 2 days (48 hours)
    const tNext = t0 + 2 * 24 * 60 * 60 * 1000;
    const plan2 = generateDailyPlan(profile.wordRecords, profile.readingMastery, 2, tNext);

    expect(plan2.dayNumber).toBe(2);
    // word1 should now appear in reviewWordIds!
    expect(plan2.reviewWordIds).toContain(word1);
  });
});
