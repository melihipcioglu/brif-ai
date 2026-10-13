import type { OptionId, Question, QuestionFamily, QuestionAttempt } from '../../types/question';
import { QUESTION_FAMILIES } from '../../types/question';
import type { ExamBlueprint, ExamForm, ExamPoolContext, ExposureObservation } from '../../types/exam';
import { buildExamForm } from './formBuilder';
import { INTERNAL_FULL_BLUEPRINT_80 } from '../../data/internalBlueprint';
import { productionBank } from '../../data/productionBank';
import { primaryQuestionSkill } from '../evidence/mapping';
import { PERFORMANCE_CONTENT_SKILLS } from '../performance/calibration';
import { questionDb, persistSolverAttempts } from '../questions/db';
import type {
  ActiveExamSession,
  ExamHistoryEntry,
  ExamModeInfo,
  ExamResultReport,
  ExamReviewItem,
  ExamSessionMode,
  FamilyStat,
  SkillStat
} from '../../types/examSession';

export const ACTIVE_EXAM_STORAGE_KEY = 'yokdil_active_exam_session_v1';
export const EXAM_HISTORY_STORAGE_KEY = 'yokdil_exam_history_v1';
export const LEARNER_EXPOSURES_STORAGE_KEY = 'yokdil_learner_exposures_v1';

export const EXAM_MODE_INFOS: Record<ExamSessionMode, ExamModeInfo> = {
  FULL_EXAM: {
    mode: 'FULL_EXAM',
    title: 'Tam Deneme Sınavı',
    description: 'YÖKDİL Fen Bilimleri sınav standartlarında tam 80 soruluk deneme sınavı (10 soru x 8 aile).',
    totalQuestions: 80,
    durationMinutes: 180,
    durationMs: 180 * 60 * 1000,
    tag: 'Resmi Format'
  },
  SHORT_EXAM_QUICK: {
    mode: 'SHORT_EXAM_QUICK',
    title: 'Acil Çalışma (10 Dk)',
    description: 'Zaman kısıtında hızlı odaklanma, sınav öncesi ısınma ve zihinsel aktivasyon seansı.',
    totalQuestions: 5,
    durationMinutes: 10,
    durationMs: 10 * 60 * 1000,
    tag: 'Hızlı Isınma'
  },
  SHORT_EXAM_STANDARD: {
    mode: 'SHORT_EXAM_STANDARD',
    title: 'Normal Çalışma (25 Dk)',
    description: 'Dengeli soru dağılımıyla odaklı günlük çalışma ve ilerleme seansı.',
    totalQuestions: 15,
    durationMinutes: 25,
    durationMs: 25 * 60 * 1000,
    tag: 'Standart Seans'
  },
  SHORT_EXAM_INTENSIVE: {
    mode: 'SHORT_EXAM_INTENSIVE',
    title: 'Yoğun Çalışma (50 Dk)',
    description: 'Zorlayıcı fen metinleri ve çoklu soru aileleriyle kapsamlı dayanıklılık ve hız çalışması.',
    totalQuestions: 30,
    durationMinutes: 50,
    durationMs: 50 * 60 * 1000,
    tag: 'Yoğun Odak'
  }
};

export const SHORT_BLUEPRINTS: Record<Exclude<ExamSessionMode, 'FULL_EXAM'>, ExamBlueprint> = {
  SHORT_EXAM_QUICK: {
    id: 'arcbrief-short-quick-5',
    version: '1',
    scope: 'MINI',
    total_questions: 5,
    time_limit_ms: 10 * 60 * 1000,
    family_targets: { GAP_FILL: 1, CLOZE_TEST: 1, SENTENCE_COMPLETION: 1, TRANSLATION_ENG_TR: 1, READING_COMPREHENSION: 1 },
    skill_minimums: {},
    reuse_policy: 'ALLOW_REUSE',
    source: { verification: 'UNVERIFIED', reference: 'ArcBrief short quick 5 blueprint' }
  },
  SHORT_EXAM_STANDARD: {
    id: 'arcbrief-short-standard-15',
    version: '1',
    scope: 'MINI',
    total_questions: 15,
    time_limit_ms: 25 * 60 * 1000,
    family_targets: {
      GAP_FILL: 2, CLOZE_TEST: 2, SENTENCE_COMPLETION: 2, TRANSLATION_ENG_TR: 2,
      TRANSLATION_TR_ENG: 2, PARAGRAPH_COMPLETION: 2, IRRELEVANT_SENTENCE: 1, READING_COMPREHENSION: 2
    },
    skill_minimums: {},
    reuse_policy: 'ALLOW_REUSE',
    source: { verification: 'UNVERIFIED', reference: 'ArcBrief short standard 15 blueprint' }
  },
  SHORT_EXAM_INTENSIVE: {
    id: 'arcbrief-short-intensive-30',
    version: '1',
    scope: 'MINI',
    total_questions: 30,
    time_limit_ms: 50 * 60 * 1000,
    family_targets: {
      GAP_FILL: 4, CLOZE_TEST: 4, SENTENCE_COMPLETION: 4, TRANSLATION_ENG_TR: 4,
      TRANSLATION_TR_ENG: 4, PARAGRAPH_COMPLETION: 4, IRRELEVANT_SENTENCE: 3, READING_COMPREHENSION: 3
    },
    skill_minimums: {},
    reuse_policy: 'ALLOW_REUSE',
    source: { verification: 'UNVERIFIED', reference: 'ArcBrief short intensive 30 blueprint' }
  }
};

/** Load stored learner exposures from localStorage */
export function getStoredLearnerExposures(): Record<string, { observedAt: number; count: number }> {
  try {
    const raw = typeof window !== 'undefined' ? window.localStorage?.getItem(LEARNER_EXPOSURES_STORAGE_KEY) : null;
    if (raw) return JSON.parse(raw);
  } catch {
    // fallback
  }
  return {};
}

/** Save learner exposures to localStorage */
export function storeLearnerExposures(exposures: Record<string, { observedAt: number; count: number }>): void {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage?.setItem(LEARNER_EXPOSURES_STORAGE_KEY, JSON.stringify(exposures));
    }
  } catch {
    // ignore
  }
}

/** Clear learner exposures from localStorage */
export function clearStoredLearnerExposures(): void {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage?.removeItem(LEARNER_EXPOSURES_STORAGE_KEY);
    }
  } catch {
    // ignore
  }
}

/** Builds an ExamPoolContext from stored exposures */
export function buildLearnerContext(asOf: number = Date.now()): ExamPoolContext {
  const stored = getStoredLearnerExposures();
  const exposures: ExposureObservation[] = productionBank.map((q) => {
    const record = stored[q.id];
    if (record) {
      return {
        question_id: q.id,
        state: 'SEEN' as const,
        observed_at: record.observedAt,
        method: 'RECORDED_EXPOSURE' as const,
        reference: `history:${q.id}`
      };
    }
    return {
      question_id: q.id,
      state: 'UNSEEN' as const,
      observed_at: asOf,
      method: 'CONTROLLED_INVENTORY' as const,
      reference: `inv:${q.id}`
    };
  });

  return {
    as_of: asOf,
    prior_attempts: [],
    exposures
  };
}

/** Check exposure counts and freshness */
export function getExposureSummary(): { total: number; freshCount: number; seenCount: number } {
  const stored = getStoredLearnerExposures();
  const seenCount = Object.keys(stored).length;
  return {
    total: productionBank.length,
    freshCount: Math.max(0, productionBank.length - seenCount),
    seenCount
  };
}

/** Start a new exam session */
export function startExamSession(
  mode: ExamSessionMode,
  seed: string = `session-${Date.now()}`,
  bank: readonly Question[] = productionBank
): ActiveExamSession {
  const asOf = Date.now();
  const context = buildLearnerContext(asOf);

  let blueprint: ExamBlueprint;
  if (mode === 'FULL_EXAM') {
    // For FULL_EXAM, if unseen capacity is enough, use UNSEEN_ONLY; else fallback to EXCLUDE_SEEN or ALLOW_REUSE
    const summary = getExposureSummary();
    const reusePolicy = summary.freshCount >= 80 ? 'UNSEEN_ONLY' : 'ALLOW_REUSE';
    blueprint = { ...INTERNAL_FULL_BLUEPRINT_80, reuse_policy: reusePolicy };
  } else {
    blueprint = SHORT_BLUEPRINTS[mode];
  }

  const result = buildExamForm({
    id: `exam-${mode.toLowerCase()}-${seed}`,
    blueprint,
    questions: bank,
    context,
    seed
  });

  if (result.status !== 'COMPLETE') {
    throw new Error(`Failed to build exam form: status ${result.status}`);
  }

  const form: ExamForm = result.form;
  const session: ActiveExamSession = {
    id: `session-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    mode,
    form,
    startedAt: asOf,
    timeLimitMs: form.blueprint.time_limit_ms,
    initialAsOf: asOf,
    currentIndex: 0,
    answers: Object.fromEntries(form.questions.map((q) => [q.id, null])),
    flaggedQuestionIds: [],
    eliminatedOptions: Object.fromEntries(form.questions.map((q) => [q.id, []])),
    questionTimeMs: Object.fromEntries(form.questions.map((q) => [q.id, 0])),
    isFinished: false,
    finishedAt: null,
    result: null
  };

  saveActiveExamSession(session);
  return session;
}

/** Save ongoing active exam session to localStorage */
export function saveActiveExamSession(session: ActiveExamSession): void {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage?.setItem(ACTIVE_EXAM_STORAGE_KEY, JSON.stringify(session));
    }
  } catch {
    // ignore
  }
}

/** Load ongoing active exam session from localStorage */
export function loadActiveExamSession(): ActiveExamSession | null {
  try {
    if (typeof window !== 'undefined') {
      const raw = window.localStorage?.getItem(ACTIVE_EXAM_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw) as ActiveExamSession;
      if (parsed && parsed.form && parsed.answers && !parsed.isFinished) {
        return parsed;
      }
    }
  } catch {
    // ignore
  }
  return null;
}

/** Clear active exam session from localStorage */
export function clearActiveExamSession(): void {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage?.removeItem(ACTIVE_EXAM_STORAGE_KEY);
    }
  } catch {
    // ignore
  }
}

/** Calculate YÖKDİL score out of 100 */
export function calculateYokdilScore(correctCount: number, totalQuestions: number): number {
  if (totalQuestions === 0) return 0;
  // 80 questions * 1.25 = 100 points
  const raw = (correctCount / totalQuestions) * 100;
  return Math.round(raw * 100) / 100;
}

/** Finish an active exam session and compute result report */
export async function finishExamSession(session: ActiveExamSession): Promise<ExamResultReport> {
  const completedAt = Date.now();
  const form = session.form;
  const questions = form.questions;
  const totalQuestions = questions.length;

  let answeredCount = 0;
  let blankCount = 0;
  let correctCount = 0;
  let incorrectCount = 0;

  const reviewItems: ExamReviewItem[] = [];

  interface MutableStat {
    total: number;
    correct: number;
    incorrect: number;
    blank: number;
    accuracy: number;
  }

  const mutableFamilyStats: Record<QuestionFamily, MutableStat> = Object.fromEntries(
    QUESTION_FAMILIES.map((f) => [f, { total: 0, correct: 0, incorrect: 0, blank: 0, accuracy: 0 }])
  ) as Record<QuestionFamily, MutableStat>;

  const mutableSkillStats: Record<string, MutableStat> = {};
  for (const s of PERFORMANCE_CONTENT_SKILLS) {
    mutableSkillStats[s] = { total: 0, correct: 0, incorrect: 0, blank: 0, accuracy: 0 };
  }

  const solverAttemptsToPersist: QuestionAttempt[] = [];

  for (let i = 0; i < questions.length; i++) {
    const q = questions[i]!;
    const selected = session.answers[q.id] ?? null;
    const isBlank = selected === null;
    const isCorrect = selected === q.correct_option;
    const isFlagged = session.flaggedQuestionIds.includes(q.id);
    const timeSpentMs = session.questionTimeMs[q.id] ?? 0;

    if (isBlank) blankCount++;
    else answeredCount++;

    if (isCorrect) correctCount++;
    else if (!isBlank) incorrectCount++;

    // Family stat
    const fam = mutableFamilyStats[q.family];
    if (fam) {
      fam.total++;
      if (isCorrect) fam.correct++;
      else if (!isBlank) fam.incorrect++;
      else fam.blank++;
    }

    // Skill stat
    const skill = primaryQuestionSkill(q);
    if (!mutableSkillStats[skill]) {
      mutableSkillStats[skill] = { total: 0, correct: 0, incorrect: 0, blank: 0, accuracy: 0 };
    }
    const sk = mutableSkillStats[skill]!;
    sk.total++;
    if (isCorrect) sk.correct++;
    else if (!isBlank) sk.incorrect++;
    else sk.blank++;

    reviewItems.push({
      index: i + 1,
      question: q,
      selectedOption: selected,
      correctOption: q.correct_option,
      isCorrect,
      isBlank,
      isFlagged,
      timeSpentMs
    });

    if (selected !== null) {
      solverAttemptsToPersist.push({
        id: `att-${session.id}-${q.id}`,
        question_id: q.id,
        session_id: session.id,
        family: q.family,
        subclass: q.subclass,
        selected_option: selected,
        is_correct: isCorrect,
        confidence_level: null,
        response_time_ms: timeSpentMs,
        attempted_at: completedAt,
        option_change_count: 0,
        eliminated_options: (session.eliminatedOptions[q.id] ?? []) as readonly OptionId[],
        distractor_flagged: [],
        words_clicked: [],
        hints_used_count: 0,
        error_attribution: null
      });
    }
  }

  // Calculate accuracies
  for (const f of QUESTION_FAMILIES) {
    const stat = mutableFamilyStats[f];
    stat.accuracy = stat.total > 0 ? Math.round((stat.correct / stat.total) * 100) : 0;
  }
  for (const s of Object.keys(mutableSkillStats)) {
    const stat = mutableSkillStats[s]!;
    stat.accuracy = stat.total > 0 ? Math.round((stat.correct / stat.total) * 100) : 0;
  }

  const familyStats: Record<QuestionFamily, FamilyStat> = mutableFamilyStats;
  const skillStats: Record<string, SkillStat> = mutableSkillStats;

  // Detect weak skills (skills with < 60% accuracy and at least 2 questions)
  const weakSkills = Object.entries(skillStats)
    .filter(([_, stat]) => stat.total >= 2 && stat.accuracy < 60)
    .map(([skill]) => skill);

  const isClockTampered = completedAt < session.startedAt;
  const totalTimeMs = isClockTampered ? 0 : Math.max(0, completedAt - session.startedAt);
  const averageTimePerQuestionMs = totalQuestions > 0 ? Math.round(totalTimeMs / totalQuestions) : 0;
  const yokdilScore = calculateYokdilScore(correctCount, totalQuestions);
  const target80Met = yokdilScore >= 80;

  const report: ExamResultReport = {
    examId: session.id,
    formId: form.id,
    mode: session.mode,
    completedAt,
    totalQuestions,
    answeredCount,
    blankCount,
    correctCount,
    incorrectCount,
    totalTimeMs,
    averageTimePerQuestionMs,
    yokdilScore,
    target80Met,
    isClockTampered,
    familyStats,
    skillStats,
    weakSkills,
    performanceSelection: null,
    items: reviewItems
  };

  // Update session
  session.isFinished = true;
  session.finishedAt = completedAt;
  session.result = report;

  // Record learner exposures
  const storedExposures = getStoredLearnerExposures();
  for (const q of questions) {
    const prev = storedExposures[q.id];
    storedExposures[q.id] = {
      observedAt: completedAt,
      count: (prev?.count ?? 0) + 1
    };
  }
  storeLearnerExposures(storedExposures);

  // Store in exam history
  storeExamHistoryEntry({
    id: session.id,
    formId: form.id,
    mode: session.mode,
    completedAt,
    totalQuestions,
    correctCount,
    incorrectCount,
    blankCount,
    yokdilScore,
    totalDurationMs: totalTimeMs,
    result: report
  });

  // Persist solver attempts to IndexedDB
  try {
    if (solverAttemptsToPersist.length > 0) {
      await persistSolverAttempts(solverAttemptsToPersist, questions, questionDb);
    }
  } catch {
    // Non-fatal if IndexedDB fails in certain web environments
  }

  // Clear active session
  clearActiveExamSession();

  return report;
}

/** Get list of past completed exams */
export function getExamHistory(): readonly ExamHistoryEntry[] {
  try {
    if (typeof window !== 'undefined') {
      const raw = window.localStorage?.getItem(EXAM_HISTORY_STORAGE_KEY);
      if (raw) {
        const list = JSON.parse(raw);
        if (Array.isArray(list)) return list;
      }
    }
  } catch {
    // ignore
  }
  return [];
}

/** Store a completed exam history entry */
export function storeExamHistoryEntry(entry: ExamHistoryEntry): void {
  try {
    if (typeof window !== 'undefined') {
      const history = [...getExamHistory(), entry];
      window.localStorage?.setItem(EXAM_HISTORY_STORAGE_KEY, JSON.stringify(history));
    }
  } catch {
    // ignore
  }
}

/** Clear all exam history entries from localStorage */
export function clearExamHistory(): void {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage?.removeItem(EXAM_HISTORY_STORAGE_KEY);
    }
  } catch {
    // ignore
  }
}
