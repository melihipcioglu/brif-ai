import { describe, expect, it } from 'vitest';
import { phase9Bank as productionBank } from '../../../src/data/productionBank';
import { INTERNAL_FULL_BLUEPRINT_80 as full, analyzeFormCapacity, analyzeFormOverlap, buildExamFormSet, planMultiFormExpansion } from '../../../src/formCapacity';
import { buildExamForm } from '../../../src/exam';
import { primaryQuestionSkill } from '../../../src/services/evidence/mapping';
import { actual } from '../phase5/fixtures';
import type { ExamBlueprint, ExamPoolContext, ExposureObservation } from '../../../src/types/exam';
import type { FormCapacityResult, ExamFormSetResult, MultiFormExpansionPlan } from '../../../src/types/formCapacity';
import type { Question, QuestionFamily } from '../../../src/types/question';

const AS_OF = 1_000;
const unseen = (qs: readonly Question[], at = AS_OF): ExposureObservation[] => qs.map((q) => ({ question_id: q.id, state: 'UNSEEN', observed_at: at, method: 'CONTROLLED_INVENTORY', reference: `inv:${q.id}` }));
const seen = (qs: readonly Question[]): ExposureObservation[] => qs.map((q) => ({ question_id: q.id, state: 'SEEN', observed_at: 900, method: 'RECORDED_EXPOSURE', reference: `exp:${q.id}` }));
const ctx = (exposures: readonly ExposureObservation[] = [], prior_attempts: readonly unknown[] = []): ExamPoolContext => ({ as_of: AS_OF, prior_attempts, exposures });
const inventory = ctx(unseen(productionBank));
const noHistory = ctx();
const mini: ExamBlueprint = { ...full, id: 'mini-3-2', scope: 'MINI', total_questions: 5, family_targets: { GAP_FILL: 3, CLOZE_TEST: 2 } };
const byFamily = (f: QuestionFamily): readonly Question[] => productionBank.filter((q) => q.family === f);
const familyCount = (f: QuestionFamily): number => byFamily(f).length;

function analyzed(r: FormCapacityResult): Extract<FormCapacityResult, { status: 'ANALYZED' }> { if (r.status !== 'ANALYZED') throw new Error(JSON.stringify(r)); return r; }
function built(r: ExamFormSetResult): Extract<ExamFormSetResult, { status: 'BUILT' }> { if (r.status !== 'BUILT') throw new Error(JSON.stringify(r).slice(0, 500)); return r; }
function short(r: ExamFormSetResult): Extract<ExamFormSetResult, { status: 'INSUFFICIENT_CAPACITY' }> { if (r.status !== 'INSUFFICIENT_CAPACITY') throw new Error(r.status); return r; }
function planned(r: MultiFormExpansionPlan): Extract<MultiFormExpansionPlan, { status: 'PLANNED' }> { if (r.status !== 'PLANNED') throw new Error(JSON.stringify(r)); return r; }
const set = (o: Partial<Parameters<typeof buildExamFormSet>[0]> = {}) => buildExamFormSet({ id: 'set', blueprint: full, questions: productionBank, context: inventory, forms: 1, seed: 'seed-1', reuse: { kind: 'NO_REUSE' }, ...o });

describe('FAZ 10 capacity: current 80-question production bank', () => {
  it('derives one disjoint full form from the real blueprint, with every requested family as a bottleneck', () => {
    const cap = analyzed(analyzeFormCapacity({ blueprint: full, questions: productionBank, context: inventory }));
    expect(cap.qualityGate).toEqual({ submitted: productionBank.length, productionEligible: productionBank.length, rejected: 0 });
    const expectedBound = Math.min(...Object.entries(full.family_targets).map(([f, t]) => Math.floor(familyCount(f as QuestionFamily) / t!)));
    for (const tier of [cap.tiers.RAW, cap.tiers.FRESH_OR_UNKNOWN, cap.tiers.VERIFIED_FRESH]) {
      expect(tier.upperBound).toBe(expectedBound);
      expect(tier.verifiedDisjointFullForms).toBe(expectedBound);
    }
    expect(expectedBound).toBe(1);
    expect(cap.tiers.RAW.bottleneckFamilies).toEqual(Object.keys(full.family_targets).filter((f) => familyCount(f as QuestionFamily) === full.family_targets[f as QuestionFamily]));
    expect(cap.tiers.RAW.skills.every((s) => s.formsSupportedWithoutReuse === null)).toBe(true); // skill_minimums = {} -> no invented quota
    expect(cap.reuseAllowed).toEqual({ fullFormBuildable: true, countsAsFreshCapacity: false });
  });

  it('builds 1 NO_REUSE form; 2 and 3 NO_REUSE forms fail with exact per-family shortages', () => {
    const one = built(set());
    expect(one.forms).toHaveLength(1);
    expect(one.qualification).toBe('ALL_DISJOINT');
    expect(one.forms[0]!.form.quality).toBe('COMPLETE');
    for (const n of [2, 3]) {
      const r = short(set({ forms: n }));
      expect(r.reasons).toContain('FAMILY_CAPACITY');
      const expected = Object.fromEntries(Object.entries(full.family_targets).flatMap(([f, t]) => { const d = n * t! - familyCount(f as QuestionFamily); return d > 0 ? [[f, d]] : []; }));
      expect(r.familyShortfalls).toEqual(expected);
      expect(r.forms).toEqual([]);
    }
  });

  it('plans 2- and 3-form expansion from family structure, not by blindly multiplying the bank', () => {
    for (const n of [2, 3]) {
      const plan = planned(planMultiFormExpansion({ blueprint: full, questions: productionBank, context: inventory, forms: n }));
      const fam = Object.entries(full.family_targets).map(([f, t]) => Math.max(0, n * t! - familyCount(f as QuestionFamily)));
      expect(plan.additionalQuestionsRequired).toBe(fam.reduce((s, x) => s + x, 0));
      expect(plan.exact).toBe(true);
      expect(plan.currentlyFeasible).toBe(false);
      expect(plan.currentVerifiedDisjointForms).toBe(1);
      expect(plan.operationalTarget).toBeNull(); // no invented margin
    }
  });
});

describe('FAZ 10 capacity: surplus and global allocation (MINI blueprint on the real bank)', () => {
  it('uses the real family bottleneck and counts surplus instead of doubling', () => {
    const cap = analyzed(analyzeFormCapacity({ blueprint: mini, questions: productionBank, context: inventory }));
    const bound = Math.min(Math.floor(familyCount('GAP_FILL') / 3), Math.floor(familyCount('CLOZE_TEST') / 2));
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(bound);
    const plan = planned(planMultiFormExpansion({ blueprint: mini, questions: productionBank, context: inventory, forms: bound + 1 }));
    expect(plan.familyShortfalls.GAP_FILL).toBe(Math.max(0, 3 * (bound + 1) - familyCount('GAP_FILL')));
    expect(plan.familyShortfalls.CLOZE_TEST).toBe(Math.max(0, 2 * (bound + 1) - familyCount('CLOZE_TEST')));
    expect(plan.familySurplus.CLOZE_TEST).toBe(Math.max(0, familyCount('CLOZE_TEST') - 2 * (bound + 1)));
    expect(plan.additionalQuestionsRequired).toBe(plan.familyShortfalls.GAP_FILL + plan.familyShortfalls.CLOZE_TEST);
    expect(plan.additionalQuestionsRequired).toBeLessThan(5 * (bound + 1));
  });

  it('satisfies per-form skill minimums across the whole set (global allocation)', () => {
    const skill = primaryQuestionSkill(byFamily('GAP_FILL')[0]!);
    if (skill === 'PACING_STAMINA') throw new Error('unexpected skill');
    const bp: ExamBlueprint = { ...full, id: 'mini-skill', scope: 'MINI', total_questions: 2, family_targets: { GAP_FILL: 2 }, skill_minimums: { [skill]: 1 } };
    const skillCount = byFamily('GAP_FILL').filter((q) => primaryQuestionSkill(q) === skill).length;
    const expected = Math.min(Math.floor(familyCount('GAP_FILL') / 2), skillCount);
    const cap = analyzed(analyzeFormCapacity({ blueprint: bp, questions: productionBank, context: inventory }));
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(expected);
    const r = built(set({ blueprint: bp, forms: expected }));
    for (const e of r.forms) expect(e.form.questions.filter((q) => primaryQuestionSkill(q) === skill).length).toBeGreaterThanOrEqual(1);
    expect(r.overlap.allPairwiseDisjoint).toBe(true);
  });
});

describe('FAZ 10 determinism', () => {
  it('same input and seed produce the same form set; input order does not matter', () => {
    const a = built(set({ blueprint: mini, forms: 3 })), b = built(set({ blueprint: mini, forms: 3 }));
    const c = built(set({ blueprint: mini, forms: 3, questions: [...productionBank].reverse() }));
    const ids = (r: typeof a) => r.forms.map((e) => e.form.question_ids);
    expect(ids(b)).toEqual(ids(a));
    expect(ids(c)).toEqual(ids(a));
    expect(b.forms.map((e) => e.form.fingerprint)).toEqual(a.forms.map((e) => e.form.fingerprint));
  });

  it('different seeds change order but never fake independent capacity', () => {
    const s1 = built(set({ seed: 'seed-1' })).forms[0]!.form, s2 = built(set({ seed: 'seed-2' })).forms[0]!.form;
    expect(s1.question_ids).not.toEqual(s2.question_ids);
    const overlap = analyzeFormOverlap([s1, s2]);
    expect(overlap.orderDistinctForms).toBe(2);
    expect(overlap.contentDistinctForms).toBe(1);
    expect(overlap.allPairwiseDisjoint).toBe(false);
    expect(overlap.pairs[0]!.sharedQuestionCount).toBe(full.total_questions);
    expect(analyzed(analyzeFormCapacity({ blueprint: full, questions: productionBank, context: inventory, seed: 'seed-2' })).tiers.RAW.verifiedDisjointFullForms).toBe(1);
  });
});

describe('FAZ 10 overlap and cross-form reuse', () => {
  it('NO_REUSE overlap is zero', () => {
    const r = built(set({ blueprint: mini, forms: 3 }));
    expect(r.overlap.maxPairwiseShared).toBe(0);
    expect(r.overlap.reuseCount).toBe(0);
    expect(r.overlap.totalUniqueQuestions).toBe(15);
    expect(r.forms.every((e) => e.sharedWithOtherForms === 0 && e.qualification === 'FRESH_FULL' && e.calibrationFresh)).toBe(true);
  });

  it('LIMITED_REUSE respects its explicit threshold; limit 0 behaves like NO_REUSE', () => {
    const cap = analyzed(analyzeFormCapacity({ blueprint: mini, questions: productionBank, context: inventory })).tiers.VERIFIED_FRESH.verifiedDisjointFullForms;
    expect(short(set({ blueprint: mini, forms: cap + 1, reuse: { kind: 'LIMITED_REUSE', maxSharedQuestionsPerPair: 0 } })).reasons).toContain('FAMILY_CAPACITY');
    for (const limit of [1, 2, 5]) {
      const r = set({ blueprint: mini, forms: cap + 2, reuse: { kind: 'LIMITED_REUSE', maxSharedQuestionsPerPair: limit } });
      if (r.status === 'BUILT') expect(r.overlap.maxPairwiseShared).toBeLessThanOrEqual(limit);
      else { const s = short(r); expect(s.reasons).toEqual(['OVERLAP_LIMIT_EXCEEDED']); expect(s.overlap!.maxPairwiseShared).toBeGreaterThan(limit); }
    }
    const loose = built(set({ blueprint: mini, forms: cap + 2, reuse: { kind: 'LIMITED_REUSE', maxSharedQuestionsPerPair: 5 } }));
    expect(loose.qualification).toBe('PARTIALLY_OVERLAPPING');
    const limitedCap = analyzed(analyzeFormCapacity({ blueprint: mini, questions: productionBank, context: inventory, limitedReuse: { maxSharedQuestionsPerPair: 1 } })).limitedReuse!;
    expect(limitedCap.verifiedFullForms).toBeGreaterThanOrEqual(cap);
  });

  it('ALLOW_REUSE reports the actual reuse and never counts it as fresh', () => {
    const r = built(set({ forms: 2, reuse: { kind: 'ALLOW_REUSE' } }));
    expect(r.qualification).toBe('FULLY_REUSED');
    expect(r.overlap.reuseCount).toBe(full.total_questions);
    expect(r.overlap.contentDistinctForms).toBe(1);
    expect(r.forms.every((e) => e.complete && e.qualification === 'REUSED_FULL' && !e.calibrationFresh)).toBe(true);
    const p = r.overlap.pairs[0]!;
    expect(p.uniqueToA + p.sharedQuestionCount).toBe(full.total_questions);
    expect(p.overlapRatio).toBe(1);
  });
});

describe('FAZ 10 exposure-aware capacity', () => {
  const tiers = (c: ExamPoolContext) => analyzed(analyzeFormCapacity({ blueprint: full, questions: productionBank, context: c }));
  it('Case A: zero seen with a current controlled inventory', () => {
    const cap = tiers(inventory);
    expect(cap.exposure).toEqual({ VERIFIED_FRESH: productionBank.length, UNKNOWN_EXPOSURE: 0, KNOWN_SEEN: 0 });
    expect(built(set()).forms[0]!.qualification).toBe('FRESH_FULL');
  });
  it('Case B: one required-family question seen removes fresh capacity but not raw capacity', () => {
    const one = byFamily('GAP_FILL')[0]!;
    const c = ctx([...unseen(productionBank.filter((q) => q.id !== one.id)), ...seen([one])]);
    const cap = tiers(c);
    expect([cap.tiers.RAW.verifiedDisjointFullForms, cap.tiers.FRESH_OR_UNKNOWN.verifiedDisjointFullForms, cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms]).toEqual([1, 0, 0]);
    const plan = planned(planMultiFormExpansion({ blueprint: full, questions: productionBank, context: c, forms: 1, exposurePolicy: 'EXCLUDE_SEEN' }));
    expect(plan.additionalQuestionsRequired).toBe(1);
    expect(plan.familyShortfalls.GAP_FILL).toBe(1);
    const reused = built(set({ context: c, exposurePolicy: 'ALLOW_REUSE' }));
    expect(reused.forms[0]!.qualification).toBe('REUSED_FULL');
    expect(reused.forms[0]!.exposureProfile.KNOWN_SEEN).toBe(1);
  });
  it('Case C: ten questions seen from one family', () => {
    const rc = byFamily('READING_COMPREHENSION');
    const c = ctx([...unseen(productionBank.filter((q) => q.family !== 'READING_COMPREHENSION')), ...seen(rc)]);
    const plan = planned(planMultiFormExpansion({ blueprint: full, questions: productionBank, context: c, forms: 1 }));
    expect(rc.length).toBe(full.family_targets.READING_COMPREHENSION); // all of the family is seen -> 0 fresh available
    expect(plan.familyShortfalls.READING_COMPREHENSION).toBe(full.family_targets.READING_COMPREHENSION);
    expect(plan.additionalQuestionsRequired).toBe(full.family_targets.READING_COMPREHENSION);
  });
  it('Case D: mixed verified-fresh / unknown / seen', () => {
    const fresh = productionBank.slice(0, 40), seenQs = productionBank.slice(40, 45);
    const cap = tiers(ctx([...unseen(fresh), ...seen(seenQs)]));
    expect(cap.exposure).toEqual({ VERIFIED_FRESH: 40, UNKNOWN_EXPOSURE: productionBank.length - 45, KNOWN_SEEN: 5 });
    expect(cap.tiers.VERIFIED_FRESH.eligibleQuestions).toBe(40);
    expect(cap.tiers.FRESH_OR_UNKNOWN.eligibleQuestions).toBe(productionBank.length - 5);
    expect(cap.tiers.RAW.eligibleQuestions).toBe(productionBank.length);
  });
  it('Case E: all seen', () => {
    const c = ctx(seen(productionBank));
    const cap = tiers(c);
    expect([cap.tiers.RAW.verifiedDisjointFullForms, cap.tiers.FRESH_OR_UNKNOWN.verifiedDisjointFullForms, cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms]).toEqual([1, 0, 0]);
    expect(planned(planMultiFormExpansion({ blueprint: full, questions: productionBank, context: c, forms: 1, exposurePolicy: 'EXCLUDE_SEEN' })).additionalQuestionsRequired).toBe(full.total_questions);
  });
  it('Case F: history unavailable keeps UNKNOWN, never UNSEEN', () => {
    const cap = tiers(noHistory);
    expect(cap.exposure).toEqual({ VERIFIED_FRESH: 0, UNKNOWN_EXPOSURE: productionBank.length, KNOWN_SEEN: 0 });
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(0);
    expect(cap.tiers.FRESH_OR_UNKNOWN.verifiedDisjointFullForms).toBe(1);
    expect(short(set({ context: noHistory })).reasons).toContain('FAMILY_CAPACITY'); // default policy is the safest (UNSEEN_ONLY)
    const unknown = built(set({ context: noHistory, exposurePolicy: 'EXCLUDE_SEEN' })).forms[0]!;
    expect(unknown.qualification).toBe('UNKNOWN_EXPOSURE_FULL');
    expect(unknown.complete).toBe(true);
    expect(unknown.calibrationFresh).toBe(false);
  });
  it('a stale inventory is UNKNOWN, and a stored attempt makes a question SEEN', () => {
    expect(tiers(ctx(unseen(productionBank, 999))).exposure.VERIFIED_FRESH).toBe(0);
    const q = byFamily('CLOZE_TEST')[0]!;
    const cap = tiers(ctx(unseen(productionBank), [actual(q, 'attempt-1', 500)]));
    expect(cap.exposure.KNOWN_SEEN).toBe(1);
    expect(cap.tiers.VERIFIED_FRESH.verifiedDisjointFullForms).toBe(0);
  });
});

describe('FAZ 10 quality gate and safety', () => {
  it('rejected and duplicate questions never increase any capacity, including RAW', () => {
    const bad = { ...productionBank[0]!, id: 'bad-candidate', stem: '' };
    const dup = { ...productionBank[1]!, id: 'duplicate-content' };
    const cap = analyzed(analyzeFormCapacity({ blueprint: full, questions: [...productionBank, bad, dup], context: inventory }));
    expect(cap.qualityGate).toEqual({ submitted: productionBank.length + 2, productionEligible: productionBank.length, rejected: 2 });
    expect(cap.tiers.RAW.eligibleQuestions).toBe(productionBank.length);
    expect(cap.tiers.RAW.verifiedDisjointFullForms).toBe(1);
  });

  it('rejects unsafe requests without heavy work', () => {
    for (const forms of [0, 1.5, -1, 21, 1_000]) expect(set({ forms }).status).toBe('INVALID_REQUEST');
    expect(set({ reuse: { kind: 'LIMITED_REUSE', maxSharedQuestionsPerPair: -1 } }).status).toBe('INVALID_REQUEST');
    expect(planMultiFormExpansion({ blueprint: full, questions: productionBank, context: inventory, forms: 2, assumedLossRate: 1 }).status).toBe('INVALID_REQUEST');
    expect(analyzeFormCapacity({ blueprint: { ...full, total_questions: 79 }, questions: productionBank, context: inventory }).status).toBe('INVALID_REQUEST');
  });

  it('operational target only exists from an explicit caller assumption', () => {
    const plan = planned(planMultiFormExpansion({ blueprint: full, questions: productionBank, context: inventory, forms: 2, assumedLossRate: 0.2 }));
    expect(plan.operationalTarget).toEqual({ assumedLossRate: 0.2, candidatesToAuthor: Math.ceil(plan.additionalQuestionsRequired / 0.8) });
  });

  it('does not mutate learner context or the bank, and is consistent with the unchanged Phase 7 builder', () => {
    const c = ctx(unseen(productionBank), [actual(byFamily('GAP_FILL')[0]!, 'attempt-x', 500)]);
    const before = JSON.stringify([c, productionBank]);
    set({ context: c, exposurePolicy: 'ALLOW_REUSE', forms: 2, reuse: { kind: 'ALLOW_REUSE' } });
    analyzeFormCapacity({ blueprint: full, questions: productionBank, context: c });
    expect(JSON.stringify([c, productionBank])).toBe(before);
    const direct = buildExamForm({ id: 'direct', blueprint: { ...full, reuse_policy: 'EXCLUDE_SEEN' }, questions: productionBank, context: noHistory });
    expect(direct.status).toBe('COMPLETE');
    const viaSet = built(set({ context: noHistory, exposurePolicy: 'EXCLUDE_SEEN' })).forms[0]!.form;
    expect([...viaSet.question_ids].sort()).toEqual([...direct.form!.question_ids].sort());
  });
});
