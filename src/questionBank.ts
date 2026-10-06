import type { Question, QuestionFamily } from './types/question';
import { QUESTION_FAMILIES } from './types/question';
import type { ExamContentSkill, ExamBlueprint } from './types/exam';
import { PERFORMANCE_CONTENT_SKILLS } from './services/performance/calibration';
import type { QuestionValidationResult, BankValidationResult, ExpansionPlan, HardErrorCode, WarningCode } from './types/questionBank';
import { questionSchema } from './services/questions/validation';
import { fingerprint, questionContentKey } from './services/exam/provenance';
import { primaryQuestionSkill } from './services/evidence/mapping';

export const VALIDATION_POLICY_VERSION = 'question-validation-v1';
export const DUPLICATE_POLICY_VERSION = 'question-duplicate-v1';

function normalizedStemTokens(stem: string): Set<string> {
  return new Set(stem.toLowerCase().replace(/[^a-z0-9ğüşıöç]/g, ' ').split(/\s+/).filter(w => w.length > 2));
}

function calculateJaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 1;
  const intersection = new Set([...a].filter(x => b.has(x)));
  const union = new Set([...a, ...b]);
  return intersection.size / union.size;
}

export function validateQuestion(input: unknown): QuestionValidationResult {
  const errors: HardErrorCode[] = [];
  const warnings: WarningCode[] = [];
  
  const parsed = questionSchema.safeParse(input);
  if (!parsed.success) {
    // Collect some specific errors before general rejection
    const raw = input as Record<string, any>;
    if (!raw.stem || typeof raw.stem !== 'string' || raw.stem.trim().length === 0) errors.push('EMPTY_STEM');
    if (!raw.options || !Array.isArray(raw.options) || raw.options.length !== 5) errors.push('INVALID_OPTION_COUNT');
    if (Array.isArray(raw.options)) {
      if (raw.options.some(o => !o.text || typeof o.text !== 'string' || o.text.trim().length === 0)) errors.push('EMPTY_OPTION');
      const ids = raw.options.map(o => o.id);
      if (new Set(ids).size !== ids.length) errors.push('DUPLICATE_OPTION');
      const texts = raw.options.map(o => typeof o.text === 'string' ? o.text.trim().toLowerCase() : '');
      if (new Set(texts).size !== texts.length) errors.push('DUPLICATE_OPTION');
    }
    if (!raw.correct_option || !['A', 'B', 'C', 'D', 'E'].includes(raw.correct_option)) errors.push('INVALID_ANSWER_KEY');
    if (raw.family && !QUESTION_FAMILIES.includes(raw.family as any)) errors.push('UNSUPPORTED_FAMILY');
    if (raw.skill_ids && Array.isArray(raw.skill_ids)) {
      if (raw.skill_ids.some((s: string) => !PERFORMANCE_CONTENT_SKILLS.includes(s as any))) errors.push('UNSUPPORTED_SKILL');
    }
    if (!raw.provenance) errors.push('MISSING_PROVENANCE');
    else if (raw.provenance === 'UNKNOWN') errors.push('UNKNOWN_PROVENANCE');
    else if (raw.provenance !== 'ORIGINAL_PRACTICE') errors.push('MALFORMED_SOURCE'); // Expand if needed
    
    // If none of the specific heuristics matched but schema failed, we must flag at least something or just fail
    if (errors.length === 0) errors.push('MISSING_ANSWER'); // fallback error
    
    return {
      questionId: raw.id || 'unknown',
      valid: false,
      productionEligible: false,
      status: 'REJECTED',
      errors,
      warnings,
      fingerprint: '',
      policyVersion: VALIDATION_POLICY_VERSION
    };
  }

  const q = parsed.data;
  
  if (q.stem.trim().length === 0) errors.push('EMPTY_STEM');
  if (q.options.some(o => o.text.trim().length === 0)) errors.push('EMPTY_OPTION');
  
  const correctOpt = q.options.find(o => o.id === q.correct_option);
  if (!correctOpt || correctOpt.text.trim().length === 0) errors.push('EMPTY_OPTION');
  
  const texts = q.options.map(o => o.text.trim().toLowerCase());
  if (new Set(texts).size !== texts.length) errors.push('DUPLICATE_OPTION');

  if (!QUESTION_FAMILIES.includes(q.family)) errors.push('UNSUPPORTED_FAMILY');
  if (q.skill_ids.some((s: any) => !PERFORMANCE_CONTENT_SKILLS.includes(s))) errors.push('UNSUPPORTED_SKILL');
  if (!q.provenance) errors.push('MISSING_PROVENANCE');
  if (q.provenance === 'UNKNOWN' as any) errors.push('UNKNOWN_PROVENANCE');

  // Warnings
  const stemWords = q.stem.split(/\s+/).length;
  if (stemWords > 150) warnings.push('VERY_LONG_STEM');

  if (correctOpt) {
    const stemLower = q.stem.toLowerCase();
    const optLower = correctOpt.text.toLowerCase();
    if (optLower.length > 3 && stemLower.includes(optLower)) {
      warnings.push('LEXICAL_LEAKAGE');
    }
  }

  const valid = errors.length === 0;
  
  return {
    questionId: q.id,
    valid,
    productionEligible: valid, // For Phase 8, valid implies eligible
    status: valid ? (warnings.length > 0 ? 'VALIDATED' : 'PRODUCTION_ELIGIBLE') : 'REJECTED',
    errors,
    warnings,
    fingerprint: fingerprint(q),
    policyVersion: VALIDATION_POLICY_VERSION
  };
}

export function validateQuestionBank(questions: readonly unknown[]): BankValidationResult {
  const families = Object.fromEntries(QUESTION_FAMILIES.map(f => [f, 0])) as Record<QuestionFamily, number>;
  const skills = Object.fromEntries(PERFORMANCE_CONTENT_SKILLS.map(s => [s, 0])) as Record<ExamContentSkill, number>;
  const sourceDist: Record<string, number> = {};
  const answerDist: Record<string, number> = {};
  
  let validCount = 0;
  let rejectedCount = 0;
  let warningsCount = 0;
  let exactDuplicates = 0;
  let nearDuplicates = 0;
  
  const results: QuestionValidationResult[] = [];
  
  // Dedup structures
  const seenIds = new Set<string>();
  const seenContent = new Set<string>();
  const tokenSets: { id: string, tokens: Set<string> }[] = [];

  for (const raw of questions) {
    const res = validateQuestion(raw);
    const qRaw = raw as Question;
    
    let isDuplicate = false;
    
    if (res.valid) {
      if (seenIds.has(res.questionId)) {
        (res.errors as HardErrorCode[]).push('ID_CONFLICT');
        isDuplicate = true;
      }
      const cKey = questionContentKey(qRaw);
      if (seenContent.has(cKey)) {
        (res.errors as HardErrorCode[]).push('EXACT_DUPLICATE_CONTENT');
        isDuplicate = true;
      }
      
      if (isDuplicate) {
        exactDuplicates++;
        (res as any).valid = false;
        (res as any).productionEligible = false;
        (res as any).status = 'REJECTED';
      } else {
        seenIds.add(res.questionId);
        seenContent.add(cKey);
        
        // Near dup check
        const tokens = normalizedStemTokens(qRaw.stem);
        let nearDupFound = false;
        for (const prev of tokenSets) {
          if (calculateJaccard(tokens, prev.tokens) > 0.85) {
            nearDupFound = true;
            break;
          }
        }
        if (nearDupFound) {
          (res.warnings as WarningCode[]).push('NEAR_DUPLICATE');
          nearDuplicates++;
        }
        tokenSets.push({ id: res.questionId, tokens });
      }
    }

    results.push(res);
    
    if (res.valid) {
      validCount++;
      families[qRaw.family]++;
      const s = primaryQuestionSkill(qRaw);
      if (s !== 'PACING_STAMINA') skills[s]++;
      sourceDist[qRaw.provenance] = (sourceDist[qRaw.provenance] || 0) + 1;
      answerDist[qRaw.correct_option] = (answerDist[qRaw.correct_option] || 0) + 1;
    } else {
      rejectedCount++;
    }
    
    if (res.warnings.length > 0) warningsCount++;
  }

  return {
    total: questions.length,
    valid: validCount,
    productionEligible: validCount,
    rejected: rejectedCount,
    warnings: warningsCount,
    families,
    skills,
    sourceDistribution: sourceDist,
    answerPositionDistribution: answerDist,
    exactDuplicatesFound: exactDuplicates,
    nearDuplicatesFound: nearDuplicates,
    results
  };
}

export function planQuestionBankExpansion(
  validatedBank: BankValidationResult,
  blueprint: ExamBlueprint,
  desiredDistinctForms: number
): ExpansionPlan {
  const familyShortages = Object.fromEntries(QUESTION_FAMILIES.map(f => [f, 0])) as Record<QuestionFamily, number>;
  const skillShortages = Object.fromEntries(PERFORMANCE_CONTENT_SKILLS.map(s => [s, 0])) as Record<ExamContentSkill, number>;
  
  let totalMinShortage = 0;
  
  for (const f of QUESTION_FAMILIES) {
    const required = (blueprint.family_targets[f] ?? 0) * desiredDistinctForms;
    const have = validatedBank.families[f] ?? 0;
    const short = Math.max(0, required - have);
    familyShortages[f] = short;
    totalMinShortage += short;
  }
  
  for (const s of PERFORMANCE_CONTENT_SKILLS) {
    const required = (blueprint.skill_minimums[s] ?? 0) * desiredDistinctForms;
    const have = validatedBank.skills[s] ?? 0;
    skillShortages[s] = Math.max(0, required - have);
  }

  const oneFormPlan = desiredDistinctForms === 1 ? totalMinShortage : 
    Object.values(QUESTION_FAMILIES).reduce((sum, f) => sum + Math.max(0, (blueprint.family_targets[f] ?? 0) - (validatedBank.families[f] ?? 0)), 0);

  const canBuildOneForm = oneFormPlan === 0;
  const canBuildMultipleDistinctForms = totalMinShortage === 0;

  return {
    canBuildOneForm,
    canBuildMultipleDistinctForms,
    minimumAdditionalQuestions: totalMinShortage,
    recommendedOperationalTarget: Math.ceil(totalMinShortage * 1.5), // 50% buffer
    familyShortages,
    skillShortages
  };
}
