import type { ExamBlueprint, ExamContentSkill, ExamForm, ExamPoolContext, ExposureState } from '../../types/exam';
import type { Question, QuestionFamily } from '../../types/question';
import { QUESTION_FAMILIES } from '../../types/question';
import type {
  CapacityShortfallReason, CapacityTier, ExamFormSetRequest, ExamFormSetResult, ExposurePolicy, FamilyCapacity, FormCapacityRequest,
  FormCapacityResult, FormSetEntry, FormSetOverlapReport, FormSetReusePolicy, FreshnessTier, MultiFormExpansionPlan, MultiFormExpansionRequest,
  PairwiseOverlap, QualityGateSummary, SkillCapacity, TierCapacity,
} from '../../types/formCapacity';
import { PERFORMANCE_CONTENT_SKILLS } from '../performance/calibration';
import { primaryQuestionSkill } from '../evidence/mapping';
import { deepFreeze } from '../questions/attempts';
import { validateQuestionBank } from '../../questionBank';
import { validateExamBlueprint } from './blueprint';
import { preparePool } from './poolAnalysis';
import { allocateMinimums, cellKey } from './allocation';
import { buildExamForm } from './formBuilder';
import { compareText, fingerprint } from './provenance';

/** Centralized policy. The cap only bounds work; it is not a capacity claim. */
export const FORM_CAPACITY_POLICY = deepFreeze({ version: 'form-capacity-policy-v1', maxFormsPerSet: 20, defaultExposurePolicy: 'UNSEEN_ONLY' as ExposurePolicy });
const TIER_POLICY: Readonly<Record<CapacityTier, ExposurePolicy>> = { RAW: 'ALLOW_REUSE', FRESH_OR_UNKNOWN: 'EXCLUDE_SEEN', VERIFIED_FRESH: 'UNSEEN_ONLY' };
const TIER_OF: Readonly<Record<ExposureState, FreshnessTier>> = { UNSEEN: 'VERIFIED_FRESH', UNKNOWN: 'UNKNOWN_EXPOSURE', SEEN: 'KNOWN_SEEN' };
const EXPOSURE_POLICIES: readonly ExposurePolicy[] = ['ALLOW_REUSE', 'EXCLUDE_SEEN', 'UNSEEN_ONLY'];

type Gated = { readonly questions: readonly unknown[]; readonly gate: QualityGateSummary };
type Shortage = { readonly reasons: readonly CapacityShortfallReason[]; readonly familyShortfalls: Partial<Record<QuestionFamily, number>>; readonly skillShortfalls: Partial<Record<ExamContentSkill, number>> };
type BuildOutcome = { readonly ok: true; readonly forms: readonly ExamForm[] } | ({ readonly ok: false; readonly forms: readonly ExamForm[] } & Shortage);

/** Phase 8 quality gate: only production-eligible questions can contribute to any capacity, including RAW. */
function qualityGate(raw: readonly unknown[]): Gated {
  const validated = validateQuestionBank(raw);
  if (validated.results.length !== raw.length) throw new RangeError('Quality gate results are not aligned with input');
  const questions = raw.filter((_, i) => validated.results[i]!.productionEligible);
  return { questions, gate: { submitted: raw.length, productionEligible: questions.length, rejected: raw.length - questions.length } };
}
const withPolicy = (b: ExamBlueprint, policy: ExposurePolicy): ExamBlueprint => deepFreeze({ ...b, reuse_policy: policy });
const skillOf = (q: Question): string => primaryQuestionSkill(q);
const rank = (seed: string, salt: string, id: string): string => fingerprint([seed, salt, id]);
const families = (b: ExamBlueprint): readonly QuestionFamily[] => QUESTION_FAMILIES.filter((f) => (b.family_targets[f] ?? 0) > 0);
const minimumSkills = (b: ExamBlueprint): readonly ExamContentSkill[] => PERFORMANCE_CONTENT_SKILLS.filter((s) => (b.skill_minimums[s] ?? 0) > 0);
function count<K extends string>(pool: readonly Question[], key: (q: Question) => string, keys: readonly K[]): Record<K, number> {
  const out = Object.fromEntries(keys.map((k) => [k, 0])) as Record<K, number>;
  for (const q of pool) { const k = key(q) as K; if (k in out) out[k] += 1; }
  return out;
}
function capacities(pool: readonly Question[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const q of pool) { const k = cellKey(q.family, skillOf(q)); m.set(k, (m.get(k) ?? 0) + 1); }
  return m;
}
/** Shortages for N content-disjoint forms; never doubles the bank blindly, only per-family/per-skill need minus availability. */
function disjointShortage(b: ExamBlueprint, pool: readonly Question[], n: number): Shortage {
  const fam = count(pool, (q) => q.family, QUESTION_FAMILIES), sk = count(pool, skillOf, PERFORMANCE_CONTENT_SKILLS);
  const familyShortfalls: Partial<Record<QuestionFamily, number>> = {}, skillShortfalls: Partial<Record<ExamContentSkill, number>> = {};
  for (const f of families(b)) { const need = n * b.family_targets[f]! - fam[f]; if (need > 0) familyShortfalls[f] = need; }
  for (const s of minimumSkills(b)) { const need = n * b.skill_minimums[s]! - sk[s]; if (need > 0) skillShortfalls[s] = need; }
  const reasons: CapacityShortfallReason[] = [];
  if (Object.keys(familyShortfalls).length) reasons.push('FAMILY_CAPACITY');
  if (Object.keys(skillShortfalls).length) reasons.push('SKILL_CAPACITY');
  return { reasons, familyShortfalls, skillShortfalls };
}
function verifyForm(b: ExamBlueprint, subset: readonly Question[], context: ExamPoolContext, id: string, seed: string): ExamForm | null {
  const built = buildExamForm({ id, blueprint: b, questions: subset, context, seed });
  if (built.status !== 'COMPLETE') return null;
  const ids = new Set(subset.map((q) => q.id));
  return built.form.question_ids.length === ids.size && built.form.question_ids.every((x) => ids.has(x)) ? built.form : null;
}

/**
 * NO_REUSE: one global allocation over the whole set (quotas x N), then a round-robin partition that gives every form
 * exactly its family targets. Each form is re-verified by the unchanged Phase 7 builder.
 */
function buildDisjoint(b: ExamBlueprint, pool: readonly Question[], n: number, context: ExamPoolContext, setId: string, seed: string): BuildOutcome {
  const short = disjointShortage(b, pool, n);
  if (short.reasons.length) return { ok: false, forms: [], ...short };
  const aggregate: ExamBlueprint = { ...b, total_questions: b.total_questions * n,
    family_targets: Object.fromEntries(families(b).map((f) => [f, b.family_targets[f]! * n])),
    skill_minimums: Object.fromEntries(minimumSkills(b).map((s) => [s, b.skill_minimums[s]! * n])) };
  const allocation = allocateMinimums(aggregate, capacities(pool));
  if (allocation.shortfall > 0) return { ok: false, forms: [], reasons: ['SKILL_CAPACITY'], familyShortfalls: {}, skillShortfalls: {} };
  const ranked = [...pool].sort((x, y) => compareText(rank(seed, 'set', x.id), rank(seed, 'set', y.id)) || compareText(x.id, y.id));
  const chosen = new Set<string>();
  for (const [key, c] of allocation.cells) for (const q of ranked.filter((q) => cellKey(q.family, skillOf(q)) === key).slice(0, c)) chosen.add(q.id);
  for (const f of families(b)) {
    const have = ranked.filter((q) => chosen.has(q.id) && q.family === f).length;
    for (const q of ranked.filter((q) => q.family === f && !chosen.has(q.id)).slice(0, Math.max(0, aggregate.family_targets[f]! - have))) chosen.add(q.id);
  }
  const parts: Question[][] = Array.from({ length: n }, () => []);
  let cursor = 0; // One counter across families: n*T_f items from any offset give each form exactly T_f.
  for (const f of families(b)) {
    const list = ranked.filter((q) => chosen.has(q.id) && q.family === f).sort((x, y) => compareText(skillOf(x), skillOf(y)));
    for (const q of list) { parts[cursor % n]!.push(q); cursor += 1; }
  }
  const forms: ExamForm[] = [];
  for (const [i, part] of parts.entries()) {
    const form = verifyForm(b, part, context, `${setId}-form-${i + 1}`, `${seed}:form-${i + 1}`);
    if (!form) return { ok: false, forms: [], reasons: ['PARTITION_UNVERIFIED'], familyShortfalls: {}, skillShortfalls: {} };
    forms.push(form);
  }
  return { ok: true, forms };
}

/**
 * LIMITED_REUSE / ALLOW_REUSE: forms are built in order, each preferring least-used questions. Form i depends only on
 * forms before it, so building N forms is a prefix of building N+1 forms.
 */
function* leastUsedForms(b: ExamBlueprint, pool: readonly Question[], context: ExamPoolContext, setId: string, seed: string): Generator<ExamForm | null> {
  const usage = new Map<string, number>(), cells = allocateMinimums(b, capacities(pool));
  for (let i = 0; ; i++) {
    const salt = `form-${i + 1}`;
    const ranked = [...pool].sort((x, y) => (usage.get(x.id) ?? 0) - (usage.get(y.id) ?? 0) || compareText(rank(seed, salt, x.id), rank(seed, salt, y.id)) || compareText(x.id, y.id));
    const chosen = new Set<string>();
    for (const [key, c] of cells.cells) for (const q of ranked.filter((q) => cellKey(q.family, skillOf(q)) === key).slice(0, c)) chosen.add(q.id);
    for (const f of families(b)) {
      const have = ranked.filter((q) => chosen.has(q.id) && q.family === f).length;
      for (const q of ranked.filter((q) => q.family === f && !chosen.has(q.id)).slice(0, Math.max(0, b.family_targets[f]! - have))) chosen.add(q.id);
    }
    const form = cells.shortfall > 0 ? null : verifyForm(b, ranked.filter((q) => chosen.has(q.id)), context, `${setId}-${salt}`, `${seed}:${salt}`);
    if (form) for (const id of form.question_ids) usage.set(id, (usage.get(id) ?? 0) + 1);
    yield form;
  }
}
function maxShared(forms: readonly ExamForm[]): number {
  let max = 0;
  for (let i = 0; i < forms.length; i++) for (let j = i + 1; j < forms.length; j++) {
    const a = new Set(forms[i]!.question_ids); max = Math.max(max, forms[j]!.question_ids.filter((x) => a.has(x)).length);
  }
  return max;
}
function buildReusing(b: ExamBlueprint, pool: readonly Question[], n: number, context: ExamPoolContext, setId: string, seed: string, limit: number | null): BuildOutcome {
  const forms: ExamForm[] = [], gen = leastUsedForms(b, pool, context, setId, seed);
  for (let i = 0; i < n; i++) {
    const form = gen.next().value;
    if (!form) { const s = disjointShortage(b, pool, 1); return { ok: false, forms: [], reasons: ['SINGLE_FORM_UNAVAILABLE', ...s.reasons], familyShortfalls: s.familyShortfalls, skillShortfalls: s.skillShortfalls }; }
    forms.push(form);
    if (limit !== null && maxShared(forms) > limit) return { ok: false, forms, reasons: ['OVERLAP_LIMIT_EXCEEDED'], familyShortfalls: {}, skillShortfalls: {} };
  }
  return { ok: true, forms };
}

/** Audit metrics only; no confidence penalty is derived from overlap. */
export function analyzeFormOverlap(forms: readonly ExamForm[]): FormSetOverlapReport {
  const pairs: PairwiseOverlap[] = [];
  for (let i = 0; i < forms.length; i++) for (let j = i + 1; j < forms.length; j++) {
    const a = forms[i]!, b = forms[j]!, setA = new Set(a.question_ids), setB = new Set(b.question_ids);
    const shared = [...setA].filter((x) => setB.has(x)).length, size = Math.max(setA.size, setB.size);
    pairs.push({ formA: a.id, formB: b.id, sharedQuestionCount: shared, overlapRatio: size === 0 ? 0 : shared / size, uniqueToA: setA.size - shared, uniqueToB: setB.size - shared });
  }
  const placements = forms.reduce((n, f) => n + f.question_ids.length, 0), unique = new Set(forms.flatMap((f) => f.question_ids)).size;
  return deepFreeze({ pairs, totalUniqueQuestions: unique, totalPlacements: placements, reuseCount: placements - unique,
    maxPairwiseShared: pairs.reduce((m, p) => Math.max(m, p.sharedQuestionCount), 0),
    maxPairwiseOverlapRatio: pairs.length ? pairs.reduce((m, p) => Math.max(m, p.overlapRatio), 0) : null,
    meanPairwiseOverlapRatio: pairs.length ? pairs.reduce((s, p) => s + p.overlapRatio, 0) / pairs.length : null,
    orderDistinctForms: new Set(forms.map((f) => f.question_ids.join('\u0000'))).size,
    contentDistinctForms: new Set(forms.map((f) => [...f.question_ids].sort(compareText).join('\u0000'))).size,
    allPairwiseDisjoint: pairs.every((p) => p.sharedQuestionCount === 0) });
}
function profile(form: ExamForm): Record<FreshnessTier, number> {
  const out: Record<FreshnessTier, number> = { VERIFIED_FRESH: 0, UNKNOWN_EXPOSURE: 0, KNOWN_SEEN: 0 };
  for (const id of form.question_ids) out[TIER_OF[form.exposure[id]!.state]] += 1;
  return out;
}
function entries(forms: readonly ExamForm[]): FormSetEntry[] {
  return forms.map((form, i) => {
    const others = new Set(forms.filter((_, j) => j !== i).flatMap((f) => f.question_ids));
    const exposureProfile = profile(form), sharedWithOtherForms = form.question_ids.filter((x) => others.has(x)).length;
    const qualification = exposureProfile.KNOWN_SEEN > 0 || sharedWithOtherForms > 0 ? 'REUSED_FULL' : exposureProfile.UNKNOWN_EXPOSURE > 0 ? 'UNKNOWN_EXPOSURE_FULL' : 'FRESH_FULL';
    return { form, complete: true, exposureProfile, sharedWithOtherForms, qualification, calibrationFresh: qualification === 'FRESH_FULL' };
  });
}

function checkForms(n: unknown, issues: string[]): void {
  if (typeof n !== 'number' || !Number.isInteger(n) || n < 1 || n > FORM_CAPACITY_POLICY.maxFormsPerSet) issues.push(`forms: integer in [1, ${FORM_CAPACITY_POLICY.maxFormsPerSet}] required`);
}
function checkExposure(p: unknown, issues: string[]): void {
  if (p !== undefined && !EXPOSURE_POLICIES.includes(p as ExposurePolicy)) issues.push('exposurePolicy: unsupported');
}
function prepared(b: ExamBlueprint, gated: Gated, context: ExamPoolContext, policy: ExposurePolicy) {
  return preparePool(withPolicy(b, policy), gated.questions, context);
}

export function buildExamFormSet(request: ExamFormSetRequest): ExamFormSetResult {
  const parsed = validateExamBlueprint(request.blueprint), issues: string[] = parsed.status === 'INVALID' ? [...parsed.issues] : [];
  checkForms(request.forms, issues); checkExposure(request.exposurePolicy, issues);
  if (typeof request.seed !== 'string' || request.seed.length < 1 || request.seed.length > 150) issues.push('seed: 1-150 characters required');
  if (typeof request.id !== 'string' || request.id.length < 1 || request.id.length > 80) issues.push('id: 1-80 characters required');
  const reuse: FormSetReusePolicy = request.reuse;
  if (reuse.kind === 'LIMITED_REUSE' && (!Number.isInteger(reuse.maxSharedQuestionsPerPair) || reuse.maxSharedQuestionsPerPair < 0)) issues.push('reuse.maxSharedQuestionsPerPair: non-negative integer required');
  if (parsed.status === 'INVALID' || issues.length) return deepFreeze({ status: 'INVALID_REQUEST', issues: issues.sort(compareText) });
  const exposurePolicy = request.exposurePolicy ?? FORM_CAPACITY_POLICY.defaultExposurePolicy, b = withPolicy(parsed.blueprint, exposurePolicy);
  const gated = qualityGate(request.questions), pool = prepared(b, gated, request.context, exposurePolicy).questions;
  const outcome = reuse.kind === 'NO_REUSE' || reuse.kind === 'LIMITED_REUSE' && reuse.maxSharedQuestionsPerPair === 0
    ? buildDisjoint(b, pool, request.forms, request.context, request.id, request.seed)
    : buildReusing(b, pool, request.forms, request.context, request.id, request.seed, reuse.kind === 'LIMITED_REUSE' ? reuse.maxSharedQuestionsPerPair : null);
  const base = { requestedForms: request.forms, reuse, exposurePolicy, qualityGate: gated.gate };
  if (!outcome.ok) return deepFreeze({ ...base, status: 'INSUFFICIENT_CAPACITY', reasons: outcome.reasons, familyShortfalls: outcome.familyShortfalls,
    skillShortfalls: outcome.skillShortfalls, forms: [], overlap: outcome.forms.length ? analyzeFormOverlap(outcome.forms) : null });
  const overlap = analyzeFormOverlap(outcome.forms);
  const qualification = overlap.allPairwiseDisjoint ? 'ALL_DISJOINT' : overlap.contentDistinctForms === 1 ? 'FULLY_REUSED' : 'PARTIALLY_OVERLAPPING';
  return deepFreeze({ ...base, status: 'BUILT', forms: entries(outcome.forms), overlap, qualification });
}

function tierCapacity(tier: CapacityTier, b: ExamBlueprint, pool: readonly Question[], context: ExamPoolContext, seed: string): TierCapacity {
  const fam = count(pool, (q) => q.family, QUESTION_FAMILIES), sk = count(pool, skillOf, PERFORMANCE_CONTENT_SKILLS);
  const familyRows: FamilyCapacity[] = QUESTION_FAMILIES.map((f) => { const r = b.family_targets[f] ?? 0;
    return { family: f, requiredPerForm: r, available: fam[f], formsSupportedWithoutReuse: r > 0 ? Math.floor(fam[f] / r) : null }; });
  const skillRows: SkillCapacity[] = PERFORMANCE_CONTENT_SKILLS.map((s) => { const m = b.skill_minimums[s] ?? 0;
    return { skill: s, minimumPerForm: m, available: sk[s], formsSupportedWithoutReuse: m > 0 ? Math.floor(sk[s] / m) : null }; });
  const bounds = [Math.floor(pool.length / b.total_questions), ...[...familyRows, ...skillRows].flatMap((r) => r.formsSupportedWithoutReuse === null ? [] : [r.formsSupportedWithoutReuse])];
  const raw = Math.min(...bounds), upperBound = Math.min(raw, FORM_CAPACITY_POLICY.maxFormsPerSet);
  const familyBound = Math.min(...familyRows.flatMap((r) => r.formsSupportedWithoutReuse === null ? [] : [r.formsSupportedWithoutReuse]));
  let verified = 0;
  for (let k = upperBound; k >= 1; k--) if (buildDisjoint(b, pool, k, context, `capacity-${tier}`, seed).ok) { verified = k; break; }
  return { tier, exposurePolicy: b.reuse_policy, eligibleQuestions: pool.length, families: familyRows, skills: skillRows, upperBound, upperBoundCapped: raw > upperBound,
    bottleneckFamilies: familyRows.filter((r) => r.formsSupportedWithoutReuse === familyBound).map((r) => r.family), verifiedDisjointFullForms: verified };
}

export function analyzeFormCapacity(request: FormCapacityRequest): FormCapacityResult {
  const parsed = validateExamBlueprint(request.blueprint), issues: string[] = parsed.status === 'INVALID' ? [...parsed.issues] : [];
  const limited = request.limitedReuse;
  if (limited && (!Number.isInteger(limited.maxSharedQuestionsPerPair) || limited.maxSharedQuestionsPerPair < 0)) issues.push('limitedReuse.maxSharedQuestionsPerPair: non-negative integer required');
  if (limited) checkExposure(limited.exposurePolicy, issues);
  if (parsed.status === 'INVALID' || issues.length) return deepFreeze({ status: 'INVALID_REQUEST', issues: issues.sort(compareText) });
  const seed = request.seed ?? 'capacity', gated = qualityGate(request.questions), b = parsed.blueprint;
  const tiers = Object.fromEntries((Object.keys(TIER_POLICY) as CapacityTier[]).map((t) => {
    const policyBp = withPolicy(b, TIER_POLICY[t]);
    return [t, tierCapacity(t, policyBp, prepared(b, gated, request.context, TIER_POLICY[t]).questions, request.context, seed)];
  })) as Record<CapacityTier, TierCapacity>;
  const novelty = prepared(b, gated, request.context, 'ALLOW_REUSE').report.novelty;
  let limitedReuse: Extract<FormCapacityResult, { status: 'ANALYZED' }>['limitedReuse'] = null;
  if (limited) {
    const policy = limited.exposurePolicy ?? FORM_CAPACITY_POLICY.defaultExposurePolicy, lb = withPolicy(b, policy);
    const pool = prepared(b, gated, request.context, policy).questions, built: ExamForm[] = [], gen = leastUsedForms(lb, pool, request.context, 'capacity-limited', seed);
    while (built.length < FORM_CAPACITY_POLICY.maxFormsPerSet) {
      const form = gen.next().value; if (!form) break;
      if (maxShared([...built, form]) > limited.maxSharedQuestionsPerPair) break;
      built.push(form);
    }
    limitedReuse = { maxSharedQuestionsPerPair: limited.maxSharedQuestionsPerPair, exposurePolicy: policy, verifiedFullForms: built.length, capped: built.length === FORM_CAPACITY_POLICY.maxFormsPerSet };
  }
  return deepFreeze({ status: 'ANALYZED', policyVersion: FORM_CAPACITY_POLICY.version, blueprint: b, qualityGate: gated.gate,
    exposure: { VERIFIED_FRESH: novelty.UNSEEN, UNKNOWN_EXPOSURE: novelty.UNKNOWN, KNOWN_SEEN: novelty.SEEN }, tiers, limitedReuse,
    reuseAllowed: { fullFormBuildable: tiers.RAW.verifiedDisjointFullForms >= 1, countsAsFreshCapacity: false } });
}

export function planMultiFormExpansion(request: MultiFormExpansionRequest): MultiFormExpansionPlan {
  const parsed = validateExamBlueprint(request.blueprint), issues: string[] = parsed.status === 'INVALID' ? [...parsed.issues] : [];
  checkForms(request.forms, issues); checkExposure(request.exposurePolicy, issues);
  const loss = request.assumedLossRate;
  if (loss !== undefined && !(Number.isFinite(loss) && loss >= 0 && loss < 1)) issues.push('assumedLossRate: number in [0, 1) required');
  if (parsed.status === 'INVALID' || issues.length) return deepFreeze({ status: 'INVALID_REQUEST', issues: issues.sort(compareText) });
  const exposurePolicy = request.exposurePolicy ?? FORM_CAPACITY_POLICY.defaultExposurePolicy, b = withPolicy(parsed.blueprint, exposurePolicy);
  const gated = qualityGate(request.questions), pool = prepared(b, gated, request.context, exposurePolicy).questions, n = request.forms;
  const fam = count(pool, (q) => q.family, QUESTION_FAMILIES), sk = count(pool, skillOf, PERFORMANCE_CONTENT_SKILLS);
  const familyShortfalls = Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, Math.max(0, n * (b.family_targets[f] ?? 0) - fam[f])])) as Record<QuestionFamily, number>;
  const familySurplus = Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, (b.family_targets[f] ?? 0) > 0 ? Math.max(0, fam[f] - n * b.family_targets[f]!) : 0])) as Record<QuestionFamily, number>;
  const skillShortfalls = Object.fromEntries(minimumSkills(b).flatMap((s) => { const d = n * b.skill_minimums[s]! - sk[s]; return d > 0 ? [[s, d]] : []; }));
  const familyTotal = Object.values(familyShortfalls).reduce((s, x) => s + x, 0), skillTotal = Object.values(skillShortfalls).reduce((s, x) => s + x, 0);
  const exact = minimumSkills(b).length === 0, additional = exact ? familyTotal : Math.max(familyTotal, skillTotal);
  const tier = tierCapacity('RAW', b, pool, request.context, request.seed ?? 'capacity');
  const assumptions = ['Counts only Phase 8 production-eligible questions.', `Exposure policy ${exposurePolicy}; UNKNOWN exposure is never treated as UNSEEN.`,
    'Surplus in one family cannot cover a shortage in another family.', 'Each new question is assumed to land in the family that needs it.'];
  if (!exact) assumptions.push('Skill minimums present: the minimum is a lower bound because family/skill routing may require more.');
  return deepFreeze({ status: 'PLANNED', requestedForms: n, reuse: 'NO_REUSE', exposurePolicy, availableQuestions: pool.length,
    currentVerifiedDisjointForms: tier.verifiedDisjointFullForms, currentlyFeasible: tier.verifiedDisjointFullForms >= n,
    additionalQuestionsRequired: additional, exact, familyShortfalls, familySurplus, skillShortfalls,
    operationalTarget: loss === undefined ? null : { assumedLossRate: loss, candidatesToAuthor: Math.ceil(additional / (1 - loss)) }, assumptions });
}
