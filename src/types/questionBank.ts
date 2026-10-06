import type { QuestionFamily } from './question';
import type { ExamContentSkill } from './exam';

export type QuestionQualityStatus = 'VALIDATED' | 'REJECTED' | 'PRODUCTION_ELIGIBLE' | 'DRAFT';

export type HardErrorCode = 
  | 'MISSING_ANSWER' 
  | 'INVALID_ANSWER_KEY' 
  | 'DUPLICATE_OPTION' 
  | 'EMPTY_OPTION' 
  | 'EMPTY_STEM' 
  | 'INVALID_OPTION_COUNT'
  | 'UNSUPPORTED_FAMILY' 
  | 'UNSUPPORTED_SKILL' 
  | 'MISSING_PROVENANCE' 
  | 'UNKNOWN_PROVENANCE' 
  | 'MALFORMED_SOURCE'
  | 'EXACT_DUPLICATE_CONTENT'
  | 'ID_CONFLICT';

export type WarningCode = 
  | 'VERY_LONG_STEM'
  | 'VERY_SHORT_DISTRACTOR'
  | 'ANSWER_POSITION_CONCENTRATION'
  | 'FAMILY_CONCENTRATION'
  | 'UNCALIBRATED_DIFFICULTY'
  | 'NEAR_DUPLICATE'
  | 'LEXICAL_LEAKAGE';

export interface QuestionValidationResult {
  readonly questionId: string;
  readonly valid: boolean;
  readonly productionEligible: boolean;
  readonly status: QuestionQualityStatus;
  readonly errors: readonly HardErrorCode[];
  readonly warnings: readonly WarningCode[];
  readonly fingerprint: string;
  readonly policyVersion: string;
}

export interface BankValidationResult {
  readonly total: number;
  readonly valid: number;
  readonly productionEligible: number;
  readonly rejected: number;
  readonly warnings: number;
  readonly families: Readonly<Record<QuestionFamily, number>>;
  readonly skills: Readonly<Record<ExamContentSkill, number>>;
  readonly sourceDistribution: Readonly<Record<string, number>>;
  readonly answerPositionDistribution: Readonly<Record<string, number>>;
  readonly exactDuplicatesFound: number;
  readonly nearDuplicatesFound: number;
  readonly results: readonly QuestionValidationResult[];
}

export interface ExpansionPlan {
  readonly canBuildOneForm: boolean;
  readonly canBuildMultipleDistinctForms: boolean;
  readonly minimumAdditionalQuestions: number;
  readonly recommendedOperationalTarget: number;
  readonly familyShortages: Readonly<Record<QuestionFamily, number>>;
  readonly skillShortages: Readonly<Record<ExamContentSkill, number>>;
}
