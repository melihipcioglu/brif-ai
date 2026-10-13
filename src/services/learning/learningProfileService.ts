import type {
  LearnerProfile,
  VocabEncounterContext,
  DailyStudySessionMode,
  ScaffoldLevel
} from '../../types/learning';
import {
  createInitialLearnerProfile,
  generateDailyPlan,
  getTodayDateString
} from './dailyPlanner';
import { recordWordEncounter } from './spacedRepetition';

export const LEARNER_PROFILE_STORAGE_KEY = 'yokdil_learning_profile_v1';

export function loadLearnerProfile(now: number = Date.now()): LearnerProfile {
  if (typeof window === 'undefined' || !window.localStorage) {
    return createInitialLearnerProfile(now);
  }

  try {
    const raw = window.localStorage.getItem(LEARNER_PROFILE_STORAGE_KEY);
    if (!raw) {
      const initial = createInitialLearnerProfile(now);
      saveLearnerProfile(initial);
      return initial;
    }

    const parsed: LearnerProfile = JSON.parse(raw);
    const todayStr = getTodayDateString(now);

    // If day changed, roll over to a fresh daily plan while preserving progress records
    if (parsed.todayPlan.dateString !== todayStr) {
      const lastDate = new Date(parsed.lastActiveDate);
      const currDate = new Date(todayStr);
      const diffDays = Math.round((currDate.getTime() - lastDate.getTime()) / (24 * 60 * 60 * 1000));
      const nextStreak = diffDays === 1 ? parsed.streakDays + 1 : diffDays === 0 ? parsed.streakDays : 1;

      const nextPlan = generateDailyPlan(
        parsed.wordRecords,
        parsed.readingMastery,
        parsed.todayPlan.dayNumber + (diffDays > 0 ? 1 : 0),
        now
      );

      const updated: LearnerProfile = {
        ...parsed,
        lastActiveDate: todayStr,
        streakDays: nextStreak,
        todayPlan: nextPlan
      };
      saveLearnerProfile(updated);
      return updated;
    }

    return parsed;
  } catch {
    const fallback = createInitialLearnerProfile(now);
    saveLearnerProfile(fallback);
    return fallback;
  }
}

export function saveLearnerProfile(profile: LearnerProfile): void {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    window.localStorage.setItem(LEARNER_PROFILE_STORAGE_KEY, JSON.stringify(profile));
  } catch {
    // ignore
  }
}

export function recordWordPracticeResult(
  profile: LearnerProfile,
  wordId: string,
  context: VocabEncounterContext,
  success: boolean,
  now: number = Date.now()
): LearnerProfile {
  const currentRecord = profile.wordRecords[wordId] ?? {
    wordId,
    state: 'NOT_STARTED',
    consecutiveCorrect: 0,
    totalEncounters: 0,
    successEncounters: 0,
    lastReviewedAt: 0,
    nextReviewAt: 0,
    intervalDays: 0,
    difficultyFactor: 2.0,
    encounters: []
  };

  const updatedRecord = recordWordEncounter(currentRecord, { context, success }, now);
  const nextWordRecords = {
    ...profile.wordRecords,
    [wordId]: updatedRecord
  };

  // Re-calculate totals
  let learnedCount = 0;
  let masteredCount = 0;
  let reviewDueCount = 0;

  for (const rec of Object.values(nextWordRecords)) {
    if (rec.state === 'LEARNING' || rec.state === 'RETAINED') learnedCount++;
    if (rec.state === 'MASTERED') masteredCount++;
    if (now >= rec.nextReviewAt && rec.state !== 'NOT_STARTED') reviewDueCount++;
  }

  // Update step count in today plan
  const isNewWord = profile.todayPlan.newWordIds.includes(wordId);
  const nextCompletedSteps = {
    ...profile.todayPlan.completedSteps,
    vocabLearned: isNewWord
      ? Math.min(profile.todayPlan.newWordIds.length, profile.todayPlan.completedSteps.vocabLearned + 1)
      : profile.todayPlan.completedSteps.vocabLearned,
    vocabReviewed: !isNewWord
      ? profile.todayPlan.completedSteps.vocabReviewed + 1
      : profile.todayPlan.completedSteps.vocabReviewed
  };

  const isTodayComplete =
    nextCompletedSteps.vocabLearned >= profile.todayPlan.newWordIds.length &&
    nextCompletedSteps.readingCompleted &&
    nextCompletedSteps.practiceQuestionsCompleted >= profile.todayPlan.practiceQuestionIds.length;

  const updatedProfile: LearnerProfile = {
    ...profile,
    totalWordsLearned: learnedCount,
    totalWordsMastered: masteredCount,
    wordsReviewDueCount: reviewDueCount,
    wordRecords: nextWordRecords,
    todayPlan: {
      ...profile.todayPlan,
      completedSteps: nextCompletedSteps,
      isCompleted: isTodayComplete
    }
  };

  saveLearnerProfile(updatedProfile);
  return updatedProfile;
}

export function recordReadingCompletion(
  profile: LearnerProfile,
  topic: LearnerProfile['todayPlan']['readingSkillTopic'],
  accuracy: number
): LearnerProfile {
  const currentStat = profile.readingMastery[topic] ?? {
    encounters: 0,
    accuracy: 0,
    scaffoldLevel: 'SYSTEM_MODEL'
  };

  const nextEncounters = currentStat.encounters + 1;
  const nextAccuracy = Number(
    ((currentStat.accuracy * currentStat.encounters + accuracy) / nextEncounters).toFixed(2)
  );

  let nextScaffold: ScaffoldLevel = 'SYSTEM_MODEL';
  if (nextAccuracy >= 0.8 && nextEncounters >= 4) {
    nextScaffold = 'INDEPENDENT';
  } else if (nextEncounters >= 2 && nextAccuracy >= 0.6) {
    nextScaffold = 'GUIDED_PROMPT';
  }

  const nextReadingMastery = {
    ...profile.readingMastery,
    [topic]: {
      encounters: nextEncounters,
      accuracy: nextAccuracy,
      scaffoldLevel: nextScaffold
    }
  };

  const nextCompletedSteps = {
    ...profile.todayPlan.completedSteps,
    readingCompleted: true
  };

  const isTodayComplete =
    nextCompletedSteps.vocabLearned >= profile.todayPlan.newWordIds.length &&
    nextCompletedSteps.readingCompleted &&
    nextCompletedSteps.practiceQuestionsCompleted >= profile.todayPlan.practiceQuestionIds.length;

  const updatedProfile: LearnerProfile = {
    ...profile,
    readingMastery: nextReadingMastery,
    todayPlan: {
      ...profile.todayPlan,
      completedSteps: nextCompletedSteps,
      isCompleted: isTodayComplete
    }
  };

  saveLearnerProfile(updatedProfile);
  return updatedProfile;
}

export function recordPracticeQuestionCompletion(
  profile: LearnerProfile
): LearnerProfile {
  const nextCompletedSteps = {
    ...profile.todayPlan.completedSteps,
    practiceQuestionsCompleted: profile.todayPlan.completedSteps.practiceQuestionsCompleted + 1
  };

  const isTodayComplete =
    nextCompletedSteps.vocabLearned >= profile.todayPlan.newWordIds.length &&
    nextCompletedSteps.readingCompleted &&
    nextCompletedSteps.practiceQuestionsCompleted >= profile.todayPlan.practiceQuestionIds.length;

  const updatedProfile: LearnerProfile = {
    ...profile,
    todayPlan: {
      ...profile.todayPlan,
      completedSteps: nextCompletedSteps,
      isCompleted: isTodayComplete
    }
  };

  saveLearnerProfile(updatedProfile);
  return updatedProfile;
}

export const SESSION_MODE_CONFIGS: Record<
  DailyStudySessionMode,
  {
    readonly title: string;
    readonly durationMinutes: number;
    readonly description: string;
    readonly badge: string;
  }
> = {
  EMERGENCY_10: {
    title: 'Acil Çalışma (10 Dk)',
    durationMinutes: 10,
    description: 'Hızlı kelime tekrarı, 1 temel cümle çözümleme ve 2 pekiştirme sorusuyla sınav öncesi zihinsel ısınma.',
    badge: '10 Dk Hızlı'
  },
  SHORT_15: {
    title: 'Kısa Çalışma (15 Dk)',
    durationMinutes: 15,
    description: 'Hedef kelime öğretimi, kısa bir akademik cümle çözümleme ve odaklı alıştırma seansı.',
    badge: '15 Dk Odak'
  },
  NORMAL_25: {
    title: 'Standart Çalışma (25 Dk)',
    durationMinutes: 25,
    description: 'Günün kelime paketi, adım adım akademik okuma stratejisi ve yönlendirmeli soru çözümü.',
    badge: '25 Dk Önerilen'
  },
  INTENSIVE_50: {
    title: 'Yoğun Çalışma (50 Dk)',
    durationMinutes: 50,
    description: 'Kapsamlı kelime tekrarı, çoklu okuma parçaları, bağımsız soru çözümü ve derin hata analizi.',
    badge: '50 Dk Kapsamlı'
  }
};
