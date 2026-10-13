import type {
  VocabProgressRecord,
  VocabEncounter,
  VocabEncounterContext,
  VocabLearningState
} from '../../types/learning';

const MS_PER_DAY = 24 * 60 * 60 * 1000;

export function createInitialWordRecord(wordId: string): VocabProgressRecord {
  return {
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
}

export interface RecordEncounterInput {
  readonly context: VocabEncounterContext;
  readonly success: boolean;
  readonly responseMs?: number;
}

export function recordWordEncounter(
  record: VocabProgressRecord,
  input: RecordEncounterInput,
  now: number = Date.now()
): VocabProgressRecord {
  const encounter: VocabEncounter = {
    timestamp: now,
    context: input.context,
    success: input.success,
    responseMs: input.responseMs
  };

  const nextEncounters = [...record.encounters, encounter];
  const nextTotal = record.totalEncounters + 1;
  const nextSuccessTotal = record.successEncounters + (input.success ? 1 : 0);

  if (!input.success) {
    // Relapse / Unlearned -> Reset interval and demote state to LEARNING
    const nextDifficulty = Math.max(1.3, Number((record.difficultyFactor - 0.2).toFixed(2)));
    const intervalDays = 1;
    return {
      wordId: record.wordId,
      state: 'LEARNING',
      consecutiveCorrect: 0,
      totalEncounters: nextTotal,
      successEncounters: nextSuccessTotal,
      lastReviewedAt: now,
      nextReviewAt: now + intervalDays * MS_PER_DAY,
      intervalDays,
      difficultyFactor: nextDifficulty,
      encounters: nextEncounters
    };
  }

  // Success
  const nextConsecutive = record.consecutiveCorrect + 1;
  let intervalDays: number;

  if (nextConsecutive === 1) {
    intervalDays = 1;
  } else if (nextConsecutive === 2) {
    intervalDays = Math.round(3 * (record.difficultyFactor / 2.0));
  } else if (nextConsecutive === 3) {
    intervalDays = Math.round(7 * (record.difficultyFactor / 2.0));
  } else {
    intervalDays = Math.min(30, Math.round(14 * (record.difficultyFactor / 2.0)));
  }

  // 3-Dimensional Mastery & Multi-Day Tracking
  const todayDateStr = new Date(now).toISOString().slice(0, 10);
  const prevDays = record.distinctDaysTested || [];
  const distinctDaysTested = prevDays.includes(todayDateStr) ? prevDays : [...prevDays, todayDateStr];

  const recognitionMastered =
    record.recognitionMastered ||
    (input.success && (input.context === 'CARD_INTRO' || input.context === 'PREDICTION' || input.context === 'COLLOCATION'));

  const comprehensionMastered =
    record.comprehensionMastered ||
    (input.success && (input.context === 'READING' || input.context === 'FILL_BLANK'));

  const transferMastered =
    record.transferMastered ||
    (input.success && input.context === 'PRACTICE_QUESTION');

  let nextState: VocabLearningState = record.state;
  // A word can NEVER be MASTERED on the same day! Must be tested across at least 2 distinct days,
  // with all 3 dimensions achieved (Recognition, Sentence Comprehension, Transfer).
  if (
    distinctDaysTested.length >= 2 &&
    recognitionMastered &&
    comprehensionMastered &&
    transferMastered &&
    nextConsecutive >= 3
  ) {
    nextState = 'MASTERED';
  } else if (nextConsecutive >= 2) {
    nextState = 'RETAINED';
  } else {
    nextState = 'LEARNING';
  }

  const nextDifficulty = Math.min(2.5, Number((record.difficultyFactor + 0.05).toFixed(2)));

  return {
    wordId: record.wordId,
    state: nextState,
    consecutiveCorrect: nextConsecutive,
    totalEncounters: nextTotal,
    successEncounters: nextSuccessTotal,
    lastReviewedAt: now,
    nextReviewAt: now + intervalDays * MS_PER_DAY,
    intervalDays,
    difficultyFactor: nextDifficulty,
    encounters: nextEncounters,
    recognitionMastered,
    comprehensionMastered,
    transferMastered,
    distinctDaysTested
  };
}

export function isReviewDue(record: VocabProgressRecord, now: number = Date.now()): boolean {
  if (record.state === 'NOT_STARTED') return false;
  return now >= record.nextReviewAt;
}

export function isRelapsingOrDifficult(record: VocabProgressRecord): boolean {
  if (record.totalEncounters < 2) return false;
  const accuracy = record.successEncounters / record.totalEncounters;
  return accuracy < 0.65 || (record.consecutiveCorrect === 0 && record.totalEncounters >= 2);
}

export function categorizeWordPool(
  allRecords: Record<string, VocabProgressRecord>,
  allWordIds: readonly string[],
  now: number = Date.now()
): {
  readonly notStarted: readonly string[];
  readonly learning: readonly string[];
  readonly reviewDue: readonly string[];
  readonly retained: readonly string[];
  readonly mastered: readonly string[];
  readonly relapsingOrDifficult: readonly string[];
} {
  const notStarted: string[] = [];
  const learning: string[] = [];
  const reviewDue: string[] = [];
  const retained: string[] = [];
  const mastered: string[] = [];
  const relapsingOrDifficult: string[] = [];

  for (const wordId of allWordIds) {
    const rec = allRecords[wordId] ?? createInitialWordRecord(wordId);
    if (rec.state === 'NOT_STARTED') {
      notStarted.push(wordId);
    } else if (isReviewDue(rec, now)) {
      reviewDue.push(wordId);
      if (isRelapsingOrDifficult(rec)) {
        relapsingOrDifficult.push(wordId);
      }
    } else if (isRelapsingOrDifficult(rec)) {
      relapsingOrDifficult.push(wordId);
      learning.push(wordId);
    } else if (rec.state === 'MASTERED') {
      mastered.push(wordId);
    } else if (rec.state === 'RETAINED') {
      retained.push(wordId);
    } else {
      learning.push(wordId);
    }
  }

  return {
    notStarted,
    learning,
    reviewDue,
    retained,
    mastered,
    relapsingOrDifficult
  };
}
