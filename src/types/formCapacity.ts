import type { ExamBlueprint, ExamContentSkill, ExamForm, ExamPoolContext } from './exam';
import type { QuestionFamily } from './question';

/**
 * Learner-exposure policy. Reuses the Phase 7 blueprint vocabulary unchanged:
 * UNSEEN_ONLY = verified fresh only, EXCLUDE_SEEN = fresh or unknown, ALLOW_REUSE = seen allowed.
 */
export type ExposurePolicy = ExamBlueprint['reuse_policy'];
/** Learner exposure confidence. This is NOT question quality. */
export type FreshnessTier = 'VERIFIED_FRESH' | 'UNKNOWN_EXPOSURE' | 'KNOWN_SEEN';
/** Cross-form reuse inside one requested form set (independent of learner exposure). */
export type FormSetReusePolicy =
  | { readonly kind: 'NO_REUSE' }
  | { readonly kind: 'LIMITED_REUSE'; readonly maxSharedQuestionsPerPair: number }
  | { readonly kind: 'ALLOW_REUSE' };
export type CapacityTier = 'RAW' | 'FRESH_OR_UNKNOWN' | 'VERIFIED_FRESH';

export interface QualityGateSummary {
  readonly submitted: number;
  readonly productionEligible: number;
  readonly rejected: number;
}
export interface FamilyCapacity {
  readonly family: QuestionFamily;
  readonly requiredPerForm: number;
  readonly available: number;
  /** null when the blueprint does not request this family. */
  readonly formsSupportedWithoutReuse: number | null;
}
export interface SkillCapacity {
  readonly skill: ExamContentSkill;
  readonly minimumPerForm: number;
  readonly available: number;
  /** null when the blueprint sets no minimum for this skill; no quota is invented. */
  readonly formsSupportedWithoutReuse: number | null;
}
export interface TierCapacity {
  readonly tier: CapacityTier;
  readonly exposurePolicy: ExposurePolicy;
  readonly eligibleQuestions: number;
  readonly families: readonly FamilyCapacity[];
  readonly skills: readonly SkillCapacity[];
  /** Arithmetic bound from family/skill/total bottlenecks, capped at the policy maximum. */
  readonly upperBound: number;
  readonly upperBoundCapped: boolean;
  readonly bottleneckFamilies: readonly QuestionFamily[];
  /** Largest N for which the real NO_REUSE allocator + Phase 7 builder produced N complete disjoint forms. */
  readonly verifiedDisjointFullForms: number;
}
export interface LimitedReuseCapacity {
  readonly maxSharedQuestionsPerPair: number;
  readonly exposurePolicy: ExposurePolicy;
  readonly verifiedFullForms: number;
  readonly capped: boolean;
}
export type FormCapacityResult =
  | { readonly status: 'INVALID_REQUEST'; readonly issues: readonly string[] }
  | {
    readonly status: 'ANALYZED';
    readonly policyVersion: string;
    readonly blueprint: ExamBlueprint;
    readonly qualityGate: QualityGateSummary;
    readonly exposure: Readonly<Record<FreshnessTier, number>>;
    readonly tiers: Readonly<Record<CapacityTier, TierCapacity>>;
    readonly limitedReuse: LimitedReuseCapacity | null;
    /** Reused forms are buildable but never counted as fresh or independent capacity. */
    readonly reuseAllowed: { readonly fullFormBuildable: boolean; readonly countsAsFreshCapacity: false };
  };
export interface FormCapacityRequest {
  readonly blueprint: unknown;
  readonly questions: readonly unknown[];
  readonly context: ExamPoolContext;
  readonly seed?: string;
  readonly limitedReuse?: { readonly maxSharedQuestionsPerPair: number; readonly exposurePolicy?: ExposurePolicy };
}

export interface PairwiseOverlap {
  readonly formA: string;
  readonly formB: string;
  readonly sharedQuestionCount: number;
  readonly overlapRatio: number;
  readonly uniqueToA: number;
  readonly uniqueToB: number;
}
export interface FormSetOverlapReport {
  readonly pairs: readonly PairwiseOverlap[];
  readonly totalUniqueQuestions: number;
  readonly totalPlacements: number;
  readonly reuseCount: number;
  readonly maxPairwiseShared: number;
  readonly maxPairwiseOverlapRatio: number | null;
  readonly meanPairwiseOverlapRatio: number | null;
  /** Different order counts here; it never implies different content. */
  readonly orderDistinctForms: number;
  readonly contentDistinctForms: number;
  readonly allPairwiseDisjoint: boolean;
}
export type FormQualification = 'FRESH_FULL' | 'UNKNOWN_EXPOSURE_FULL' | 'REUSED_FULL';
export interface FormSetEntry {
  readonly form: ExamForm;
  /** Completeness is separate from calibration freshness. */
  readonly complete: true;
  readonly exposureProfile: Readonly<Record<FreshnessTier, number>>;
  readonly sharedWithOtherForms: number;
  readonly qualification: FormQualification;
  readonly calibrationFresh: boolean;
}
export type FormSetQualification = 'ALL_DISJOINT' | 'PARTIALLY_OVERLAPPING' | 'FULLY_REUSED';
export type CapacityShortfallReason =
  | 'FAMILY_CAPACITY' | 'SKILL_CAPACITY' | 'PARTITION_UNVERIFIED' | 'OVERLAP_LIMIT_EXCEEDED' | 'SINGLE_FORM_UNAVAILABLE';
export interface ExamFormSetRequest {
  readonly id: string;
  readonly blueprint: unknown;
  readonly questions: readonly unknown[];
  readonly context: ExamPoolContext;
  readonly forms: number;
  readonly seed: string;
  readonly reuse: FormSetReusePolicy;
  /** Defaults to the safest policy, UNSEEN_ONLY. */
  readonly exposurePolicy?: ExposurePolicy;
}
interface FormSetResultBase {
  readonly requestedForms: number;
  readonly reuse: FormSetReusePolicy;
  readonly exposurePolicy: ExposurePolicy;
  readonly qualityGate: QualityGateSummary;
}
export type ExamFormSetResult =
  | { readonly status: 'INVALID_REQUEST'; readonly issues: readonly string[] }
  | (FormSetResultBase & {
    readonly status: 'INSUFFICIENT_CAPACITY';
    readonly reasons: readonly CapacityShortfallReason[];
    readonly familyShortfalls: Readonly<Partial<Record<QuestionFamily, number>>>;
    readonly skillShortfalls: Readonly<Partial<Record<ExamContentSkill, number>>>;
    readonly forms: readonly [];
    /** Present when forms were constructed but rejected (e.g. overlap limit). */
    readonly overlap: FormSetOverlapReport | null;
  })
  | (FormSetResultBase & {
    readonly status: 'BUILT';
    readonly forms: readonly FormSetEntry[];
    readonly overlap: FormSetOverlapReport;
    readonly qualification: FormSetQualification;
  });

export interface MultiFormExpansionRequest {
  readonly blueprint: unknown;
  readonly questions: readonly unknown[];
  readonly context: ExamPoolContext;
  readonly forms: number;
  readonly exposurePolicy?: ExposurePolicy;
  readonly seed?: string;
  /** Optional, caller-stated candidate loss rate in [0, 1). No default is invented. */
  readonly assumedLossRate?: number;
}
export type MultiFormExpansionPlan =
  | { readonly status: 'INVALID_REQUEST'; readonly issues: readonly string[] }
  | {
    readonly status: 'PLANNED';
    readonly requestedForms: number;
    readonly reuse: 'NO_REUSE';
    readonly exposurePolicy: ExposurePolicy;
    readonly availableQuestions: number;
    readonly currentVerifiedDisjointForms: number;
    readonly currentlyFeasible: boolean;
    /** Mathematical minimum of new production-eligible questions (exact when no skill minimums apply). */
    readonly additionalQuestionsRequired: number;
    readonly exact: boolean;
    readonly familyShortfalls: Readonly<Record<QuestionFamily, number>>;
    readonly familySurplus: Readonly<Record<QuestionFamily, number>>;
    readonly skillShortfalls: Readonly<Partial<Record<ExamContentSkill, number>>>;
    readonly operationalTarget: null | { readonly assumedLossRate: number; readonly candidatesToAuthor: number };
    readonly assumptions: readonly string[];
  };
