import type { Question, OptionId, QuestionFamily } from './question';
import type { ExamForm } from './exam';
import type { CalibrationPerformanceSelection } from './exam';

export type ExamSessionMode = 
  | 'FULL_EXAM'
  | 'SHORT_EXAM_QUICK'
  | 'SHORT_EXAM_STANDARD'
  | 'SHORT_EXAM_INTENSIVE';

export interface ExamModeInfo {
  readonly mode: ExamSessionMode;
  readonly title: string;
  readonly description: string;
  readonly totalQuestions: number;
  readonly durationMinutes: number;
  readonly durationMs: number;
  readonly tag: string;
}

export interface ActiveExamSession {
  readonly id: string;
  readonly mode: ExamSessionMode;
  readonly form: ExamForm;
  readonly startedAt: number;
  readonly timeLimitMs: number;
  readonly initialAsOf: number;
  
  currentIndex: number;
  answers: Record<string, OptionId | null>;
  flaggedQuestionIds: string[];
  eliminatedOptions: Record<string, OptionId[]>;
  questionTimeMs: Record<string, number>;
  
  isFinished: boolean;
  finishedAt: number | null;
  result: ExamResultReport | null;
}

export interface ExamReviewItem {
  readonly index: number;
  readonly question: Question;
  readonly selectedOption: OptionId | null;
  readonly correctOption: OptionId;
  readonly isCorrect: boolean;
  readonly isBlank: boolean;
  readonly isFlagged: boolean;
  readonly timeSpentMs: number;
}

export interface FamilyStat {
  readonly total: number;
  readonly correct: number;
  readonly incorrect: number;
  readonly blank: number;
  readonly accuracy: number;
}

export interface SkillStat {
  readonly total: number;
  readonly correct: number;
  readonly incorrect: number;
  readonly blank: number;
  readonly accuracy: number;
}

export interface ExamResultReport {
  readonly examId: string;
  readonly formId: string;
  readonly mode: ExamSessionMode;
  readonly completedAt: number;
  readonly totalQuestions: number;
  readonly answeredCount: number;
  readonly blankCount: number;
  readonly correctCount: number;
  readonly incorrectCount: number;
  readonly totalTimeMs: number;
  readonly averageTimePerQuestionMs: number;
  readonly yokdilScore: number;
  readonly target80Met: boolean;
  readonly isClockTampered?: boolean;
  
  readonly familyStats: Record<QuestionFamily, FamilyStat>;
  readonly skillStats: Record<string, SkillStat>;
  readonly weakSkills: readonly string[];
  readonly performanceSelection: CalibrationPerformanceSelection | null;
  
  readonly items: readonly ExamReviewItem[];
}

export interface ExamHistoryEntry {
  readonly id: string;
  readonly formId: string;
  readonly mode: ExamSessionMode;
  readonly completedAt: number;
  readonly totalQuestions: number;
  readonly correctCount: number;
  readonly incorrectCount: number;
  readonly blankCount: number;
  readonly yokdilScore: number;
  readonly totalDurationMs: number;
  readonly result: ExamResultReport;
}
