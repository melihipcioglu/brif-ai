export type SimilarityKind = 'EXACT_STEM' | 'NEAR_STEM' | 'SHARED_PASSAGE' | 'OPTION_OVERLAP';

export interface SimilarityPair {
  questionIdA: string;
  questionIdB: string;
  similarityScore: number;
  kind: SimilarityKind;
  details: string;
}

export interface PassageLeakage {
  formIdA: string;
  formIdB: string;
  questionIdA: string;
  questionIdB: string;
  passageSnippet: string;
  overlapScore: number;
}

export interface DistractorLeakage {
  questionIdA: string;
  questionIdB: string;
  leakedText: string;
  details: string;
}

export interface FormSetSimilarityAudit {
  formCount: number;
  allPairwiseDisjoint: boolean;
  sharedQuestionIds: string[];
  crossFormPassageLeakages: PassageLeakage[];
  crossFormNearDuplicates: SimilarityPair[];
  distractorLeakages: DistractorLeakage[];
  pass: boolean;
  summary: {
    totalItems: number;
    distinctItems: number;
    crossFormLeakageCount: number;
    crossFormNearDuplicateCount: number;
  };
}

export interface BankSimilarityAudit {
  totalQuestions: number;
  exactDuplicates: SimilarityPair[];
  nearDuplicates: SimilarityPair[];
  sharedPassageGroups: { snippet: string; questionIds: string[] }[];
  pass: boolean;
}
