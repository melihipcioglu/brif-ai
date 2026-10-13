import type { QuestionFamily } from './question';

export type VocabLearningState =
  | 'NOT_STARTED'
  | 'LEARNING'
  | 'REVIEW_DUE'
  | 'RETAINED'
  | 'MASTERED';

export type VocabEncounterContext =
  | 'CARD_INTRO'
  | 'PREDICTION'
  | 'FILL_BLANK'
  | 'COLLOCATION'
  | 'READING'
  | 'PRACTICE_QUESTION';

export interface VocabEncounter {
  readonly timestamp: number;
  readonly context: VocabEncounterContext;
  readonly success: boolean;
  readonly responseMs?: number | undefined;
}

export interface VocabProgressRecord {
  readonly wordId: string;
  readonly state: VocabLearningState;
  readonly consecutiveCorrect: number;
  readonly totalEncounters: number;
  readonly successEncounters: number;
  readonly lastReviewedAt: number;
  readonly nextReviewAt: number;
  readonly intervalDays: number;
  readonly difficultyFactor: number;
  readonly encounters: readonly VocabEncounter[];
  readonly recognitionMastered?: boolean;
  readonly comprehensionMastered?: boolean;
  readonly transferMastered?: boolean;
  readonly distinctDaysTested?: readonly string[];
}

export interface TrapWordComparison {
  readonly trapWord: string;
  readonly trapMeaning: string;
  readonly confusionReason: string;
  readonly memoryHook: string;
}

export interface WordProgressionStep {
  readonly level: 0 | 1 | 2 | 3;
  readonly title: string;
  readonly englishText: string;
  readonly turkishTranslation: string;
  readonly focusPoint: string;
  readonly tokens: readonly SentenceSyntacticToken[];
}

export interface AcademicVocabEntry {
  readonly word_id: string;
  readonly lemma: string;
  readonly pos: 'noun' | 'verb' | 'adjective' | 'adverb';
  readonly tier: 1 | 2 | 3;
  readonly priority_score: number;
  readonly meaning_tr: string;
  readonly polarity_symbol?: '↑' | '↓' | '=';
  readonly word_family: readonly {
    readonly pos: string;
    readonly form: string;
    readonly meaning_tr: string;
  }[];
  readonly science_domain: 'biology' | 'chemistry' | 'physics' | 'environment' | 'medicine' | 'technology';
  readonly exam_sentence: string;
  readonly exam_sentence_tr: string;
  readonly critical_collocations: readonly {
    readonly phrase: string;
    readonly meaning_tr: string;
  }[];
  readonly synonyms: readonly string[];
  readonly antonyms: readonly string[];
  readonly mnemonic_hint: string;
  readonly distractors: readonly {
    readonly word: string;
    readonly meaning_tr: string;
    readonly explanation_tr: string;
  }[];
  readonly trap_words?: readonly TrapWordComparison[];
  readonly progression?: readonly WordProgressionStep[];
}

export type ReadingStrategyTopic =
  | 'SUBJECT_VERB_IDENTIFICATION'
  | 'CLAUSE_DECOMPOSITION'
  | 'CONNECTOR_DISCOURSE'
  | 'RELATIVE_CLAUSE_UNPACKING'
  | 'PASSIVE_VOICE_ANALYSIS'
  | 'NOUN_PHRASE_DECOMPOSITION'
  | 'CONTEXTUAL_VOCABULARY'
  | 'MAIN_IDEA_EXTRACTION'
  | 'INFERENCE_EXTRACTION'
  | 'DISTRACTOR_ELIMINATION';

export type ScaffoldLevel = 'SYSTEM_MODEL' | 'GUIDED_PROMPT' | 'INDEPENDENT';

export type SyntacticRole =
  | 'SUBJECT'
  | 'VERB'
  | 'OBJECT'
  | 'CONNECTOR'
  | 'SUBORDINATE'
  | 'MODIFIER'
  | 'TARGET_WORD'
  | 'PUNCTUATION';

export interface SentenceSyntacticToken {
  readonly text: string;
  readonly role: SyntacticRole;
  readonly explanation_tr: string;
  readonly isTargetWord?: boolean;
}

export interface AcademicSentenceBreakdown {
  readonly id: string;
  readonly sentence: string;
  readonly translation_tr: string;
  readonly science_domain: string;
  readonly target_word_ids: readonly string[];
  readonly tokens: readonly SentenceSyntacticToken[];
  readonly main_clause: {
    readonly subject: string;
    readonly verb: string;
    readonly object?: string;
  };
  readonly subordinate_clause?: {
    readonly connector: string;
    readonly clause: string;
    readonly function_tr: string;
  };
  readonly pedagogical_focus: ReadingStrategyTopic;
  readonly pedagogical_tip_tr: string;
  readonly interactive_question?: {
    readonly prompt: string;
    readonly options: readonly string[];
    readonly correct_index: number;
    readonly rationale_tr: string;
  };
}

export interface AcademicReadingPassage {
  readonly id: string;
  readonly title: string;
  readonly science_domain: string;
  readonly target_words: readonly string[];
  readonly sentences: readonly AcademicSentenceBreakdown[];
  readonly main_idea_tr: string;
  readonly paragraph_text: string;
  readonly scaffold_questions: readonly {
    readonly type: 'MAIN_IDEA' | 'DETAIL' | 'INFERENCE';
    readonly prompt: string;
    readonly options: readonly string[];
    readonly correct_index: number;
    readonly explanation_tr: string;
  }[];
}

export interface LearningPracticeQuestion {
  readonly id: string;
  readonly kind: 'LEARNING_PRACTICE';
  readonly family: QuestionFamily;
  readonly science_domain: string;
  readonly target_word_ids: readonly string[];
  readonly stem: string;
  readonly passage?: string;
  readonly options: readonly {
    readonly id: 'A' | 'B' | 'C' | 'D' | 'E';
    readonly text: string;
  }[];
  readonly correct_option: 'A' | 'B' | 'C' | 'D' | 'E';
  readonly pedagogical_explanation: {
    readonly triage_tr: string;
    readonly target_word_insight_tr: string;
    readonly distractor_breakdowns: Record<'A' | 'B' | 'C' | 'D' | 'E', string>;
  };
}

export type DailyStudySessionMode =
  | 'EMERGENCY_10'
  | 'SHORT_15'
  | 'NORMAL_25'
  | 'INTENSIVE_50';

export interface DailyStudyPlan {
  readonly dayNumber: number;
  readonly dateString: string;
  readonly newWordIds: readonly string[];
  readonly reviewWordIds: readonly string[];
  readonly relapsingWordIds: readonly string[];
  readonly readingSkillTopic: ReadingStrategyTopic;
  readonly readingPassageId: string;
  readonly practiceQuestionIds: readonly string[];
  readonly completedSteps: {
    readonly vocabLearned: number;
    readonly vocabReviewed: number;
    readonly readingCompleted: boolean;
    readonly practiceQuestionsCompleted: number;
  };
  readonly isCompleted: boolean;
}

export type LearnerLevel = 'FOUNDATIONAL' | 'INTERMEDIATE' | 'ADVANCED';

export interface DiagnosticQuestion {
  readonly id: string;
  readonly type: 'VOCAB_RECOGNITION' | 'SYNTAX_IDENTIFICATION' | 'CONNECTOR_DIRECTION';
  readonly prompt: string;
  readonly sentence?: string;
  readonly options: readonly {
    readonly id: string;
    readonly text: string;
    readonly isCorrect: boolean;
    readonly feedback: string;
  }[];
  readonly scaffoldTip: string;
}

export interface DiagnosticResult {
  readonly score: number;
  readonly total: number;
  readonly vocabScore: number;
  readonly syntaxScore: number;
  readonly connectorScore: number;
  readonly assignedLevel: LearnerLevel;
  readonly completedAt: number;
}

export interface InteractiveDecompositionTask {
  readonly id: string;
  readonly mode: 'I_DO' | 'WE_DO' | 'YOU_DO';
  readonly sentence: string;
  readonly prompt: string;
  readonly targetRole: SyntacticRole;
  readonly correctTokenIndices: readonly number[];
  readonly tokens: readonly SentenceSyntacticToken[];
  readonly pedagogicalRationale: string;
  readonly tokenExplanations: Record<number, string>;
}

export interface LearnerProfile {
  readonly createdAt: number;
  readonly lastActiveDate: string;
  readonly streakDays: number;
  readonly totalWordsLearned: number;
  readonly totalWordsMastered: number;
  readonly wordsReviewDueCount: number;
  readonly readingMastery: Record<
    ReadingStrategyTopic,
    {
      readonly encounters: number;
      readonly accuracy: number;
      readonly scaffoldLevel: ScaffoldLevel;
    }
  >;
  readonly wordRecords: Record<string, VocabProgressRecord>;
  readonly completedSessionsCount: number;
  readonly todayPlan: DailyStudyPlan;
  readonly diagnosticResult?: DiagnosticResult | null;
  readonly learnerLevel?: LearnerLevel;
}

