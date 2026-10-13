import type {
  DailyStudyPlan,
  LearnerProfile,
  ReadingStrategyTopic
} from '../../types/learning';
import { academicVocabBank } from '../../data/learning/academicVocabBank';
import { academicReadingBank } from '../../data/learning/academicReadingBank';
import { learningQuestionsBank } from '../../data/learning/learningQuestionsBank';
import { categorizeWordPool, createInitialWordRecord } from './spacedRepetition';

const READING_TOPICS_ROTATION: readonly ReadingStrategyTopic[] = [
  'CLAUSE_DECOMPOSITION',
  'SUBJECT_VERB_IDENTIFICATION',
  'CONNECTOR_DISCOURSE',
  'RELATIVE_CLAUSE_UNPACKING',
  'PASSIVE_VOICE_ANALYSIS',
  'NOUN_PHRASE_DECOMPOSITION',
  'CONTEXTUAL_VOCABULARY',
  'MAIN_IDEA_EXTRACTION',
  'INFERENCE_EXTRACTION',
  'DISTRACTOR_ELIMINATION'
];

export function getTodayDateString(now: number = Date.now()): string {
  const d = new Date(now);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function generateDailyPlan(
  wordRecords: LearnerProfile['wordRecords'],
  readingMastery: LearnerProfile['readingMastery'],
  dayNumber: number,
  now: number = Date.now()
): DailyStudyPlan {
  const allWordIds = academicVocabBank.map((w) => w.word_id);
  const pool = categorizeWordPool(wordRecords, allWordIds, now);

  // Spaced Repetition Allocation
  // Standard target: 12 new words, 15 reviews, 8 relapsing/difficult
  const relapsingWordIds = pool.relapsingOrDifficult.slice(0, 8);
  const reviewWordIds = pool.reviewDue.filter((id) => !relapsingWordIds.includes(id)).slice(0, 15);

  // If beginner has few/no reviews, adjust new words cleanly (10-12 words)
  const remainingSlots = Math.max(8, 35 - reviewWordIds.length - relapsingWordIds.length);
  const newWordsQuota = Math.min(12, Math.max(6, remainingSlots));
  const newWordIds = pool.notStarted.slice(0, newWordsQuota);

  // Pick reading topic
  let selectedTopic: ReadingStrategyTopic = 'CLAUSE_DECOMPOSITION';
  for (const topic of READING_TOPICS_ROTATION) {
    const stat = readingMastery[topic];
    if (!stat || stat.encounters === 0) {
      selectedTopic = topic;
      break;
    }
  }

  // Find passage matching topic
  const passage =
    academicReadingBank.find((p) => p.sentences.some((s) => s.pedagogical_focus === selectedTopic)) ??
    academicReadingBank[0]!;

  // Select 3 practice questions
  const activeWordIds = [...newWordIds, ...reviewWordIds, ...relapsingWordIds];
  const matchingQuestions = learningQuestionsBank.filter((q) =>
    q.target_word_ids.some((id) => activeWordIds.includes(id))
  );
  const finalQuestions =
    matchingQuestions.length >= 3
      ? matchingQuestions.slice(0, 3)
      : learningQuestionsBank.slice(0, 3);

  return {
    dayNumber,
    dateString: getTodayDateString(now),
    newWordIds,
    reviewWordIds,
    relapsingWordIds,
    readingSkillTopic: selectedTopic,
    readingPassageId: passage.id,
    practiceQuestionIds: finalQuestions.map((q) => q.id),
    completedSteps: {
      vocabLearned: 0,
      vocabReviewed: 0,
      readingCompleted: false,
      practiceQuestionsCompleted: 0
    },
    isCompleted: false
  };
}

export function createInitialLearnerProfile(now: number = Date.now()): LearnerProfile {
  const dateStr = getTodayDateString(now);
  const wordRecords: LearnerProfile['wordRecords'] = {};
  for (const entry of academicVocabBank) {
    wordRecords[entry.word_id] = createInitialWordRecord(entry.word_id);
  }

  const readingMastery: LearnerProfile['readingMastery'] = {} as LearnerProfile['readingMastery'];
  for (const topic of READING_TOPICS_ROTATION) {
    readingMastery[topic] = {
      encounters: 0,
      accuracy: 0,
      scaffoldLevel: 'SYSTEM_MODEL'
    };
  }

  const todayPlan = generateDailyPlan(wordRecords, readingMastery, 1, now);

  return {
    createdAt: now,
    lastActiveDate: dateStr,
    streakDays: 1,
    totalWordsLearned: 0,
    totalWordsMastered: 0,
    wordsReviewDueCount: 0,
    readingMastery,
    wordRecords,
    completedSessionsCount: 0,
    todayPlan
  };
}
