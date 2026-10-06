import { describe, expect, it } from 'vitest';
import { createLearnerSkillVector, SKILL_IDS, type LearnerSkillVector, type SkillId, type SkillMetrics } from '../../../src/types/learner';
import type { EvidenceCoverageMap, PriorityContext, SkillEvidenceCoverage, TrainingAction } from '../../../src/types/priority';
import { buildScoreLeakMap, planNextBestAction, PRIORITY_DAY_MS, PRIORITY_V1 } from '../../../src/priority';

const NOW = 100 * PRIORITY_DAY_MS;
const COVERAGE: SkillEvidenceCoverage = { informative_attempt_count: 40, question_count: 10, family_count: 2,
  unaided_attempt_count: 30, transfer_attempt_count: 5, last_informative_at: NOW - 30 * PRIORITY_DAY_MS };
function learner(changes: Partial<SkillMetrics> = {}, skill: SkillId = 'VOCAB_CONTEXT'): LearnerSkillVector {
  return { ...createLearnerSkillVector(), [skill]: { mastery: 0.4, uncertainty: 0.2, evidence_count: 40,
    unaided_accuracy: 0.7, assisted_accuracy: 0.9, error_rate: 0.2, recency: COVERAGE.last_informative_at, ...changes } };
}
function context(coverage: EvidenceCoverageMap = { VOCAB_CONTEXT: COVERAGE }): PriorityContext {
  return { as_of: NOW, coverage };
}
function row(vector: LearnerSkillVector = learner(), ctx: PriorityContext = context(), skill: SkillId = 'VOCAB_CONTEXT') {
  const result = buildScoreLeakMap(vector, ctx).skills.find((s) => s.skill_id === skill);
  if (result === undefined) throw new Error('Missing skill');
  return result;
}
function action(id = 'practice', kind: TrainingAction['kind'] = 'TARGETED_PRACTICE', changes: Partial<TrainingAction> = {}): TrainingAction {
  return { id, title: 'Kelime bağlamı çalışması', kind, format: 'QUESTION_SET', available: true, expected_minutes: 10,
    targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 1 }], ...changes };
}

describe('Score Leak priority semantics', () => {
  it('uses exactly SkillGap = 1 - mastery for all thirteen dimensions', () => {
    const result = buildScoreLeakMap(learner(), context());
    expect(result.skills).toHaveLength(13);
    for (const item of result.skills) expect(item.skill_gap).toBe(1 - learner()[item.skill_id].mastery);
    expect(row().skill_gap).toBeCloseTo(0.6);
    expect(result.unit).toBe('INDEX_0_100');
    expect(result.interpretation).toBe('RELATIVE_TRAINING_PRIORITY');
  });
  it('keeps cold-start evidence uncertainty distinct from a supported skill gap', () => {
    const result = buildScoreLeakMap(createLearnerSkillVector(), { as_of: NOW });
    expect(result.skills.map((s) => s.skill_id)).toEqual([...SKILL_IDS]);
    for (const item of result.skills) {
      expect(item.skill_gap).toBe(1); expect(item.coverage_status).toBe('UNKNOWN');
      expect(item.evidence_support).toBe(0); expect(item.diagnostic_need).toBe(1);
      expect(item.practice_need).toBe(0.25); expect(item.retention_need).toBe(0);
      expect(item.reasons).not.toContain('SUPPORTED_SKILL_GAP');
    }
  });
  it('distinguishes missing coverage from known empty coverage', () => {
    const empty: SkillEvidenceCoverage = { informative_attempt_count: 0, question_count: 0, family_count: 0,
      unaided_attempt_count: 0, transfer_attempt_count: 0, last_informative_at: null };
    expect(row(learner(), { as_of: NOW }).coverage).toBeNull();
    const known = row(createLearnerSkillVector(), context({ VOCAB_CONTEXT: empty }));
    expect(known.coverage_status).toBe('KNOWN'); expect(known.coverage).toEqual(empty);
    expect(known.retention_need).toBe(0);
  });
  it('routes higher uncertainty toward diagnostic need instead of treating it as established weakness', () => {
    const supported = row(learner({ uncertainty: 0.1 }));
    const uncertain = row(learner({ uncertainty: 0.9 }));
    expect(uncertain.skill_gap).toBe(supported.skill_gap);
    expect(uncertain.diagnostic_need).toBeGreaterThan(supported.diagnostic_need);
    expect(uncertain.practice_need).toBeLessThan(supported.practice_need);
    expect(uncertain.retention_need).toBeLessThan(supported.retention_need);
  });
  it('recognizes evidence quantity and breadth without equating repeated questions to broad coverage', () => {
    const broad = row();
    const narrow = row(learner(), context({ VOCAB_CONTEXT: { ...COVERAGE, question_count: 1, family_count: 1 } }));
    const few = row(learner(), context({ VOCAB_CONTEXT: { ...COVERAGE, informative_attempt_count: 2,
      question_count: 2, family_count: 2, unaided_attempt_count: 2, transfer_attempt_count: 0 } }));
    expect(narrow.coverage_index).toBeLessThan(broad.coverage_index);
    expect(few.coverage_index).toBeLessThan(broad.coverage_index);
    expect(narrow.diagnostic_need).toBeGreaterThan(broad.diagnostic_need);
  });
  it('increases practice need with supported skill gap, holding other factors fixed', () => {
    expect(row(learner({ mastery: 0.2 })).practice_need).toBeGreaterThan(row(learner({ mastery: 0.8 })).practice_need);
  });
  it('increases retention need with age without decaying mastery or changing SkillGap', () => {
    const vector = learner({ mastery: 0.9 });
    const before = JSON.stringify(vector);
    const recent = row(vector, { ...context(), as_of: COVERAGE.last_informative_at! });
    const old = row(vector, { ...context(), as_of: NOW + 120 * PRIORITY_DAY_MS });
    expect(recent.retention_need).toBe(0); expect(old.retention_need).toBeGreaterThan(0.5);
    expect(recent.skill_gap).toBe(old.skill_gap); expect(JSON.stringify(vector)).toBe(before);
  });
  it('does not invent retention urgency from missing evidence even with an old snapshot', () => {
    expect(row(learner(), { as_of: NOW }).retention_need).toBe(0);
    expect(row(learner(), { as_of: NOW }).age_days).toBeNull();
  });
  it('uses editorial relevance as a relative multiplier, not a frequency or exam points', () => {
    const half = row(learner(), { ...context(), profiles: { VOCAB_CONTEXT: { ...PRIORITY_V1.default_profile, exam_relevance: 0.5 } } });
    expect(half.priority_index).toBeCloseTo(row().priority_index / 2);
    const irrelevant = row(learner(), { ...context(), profiles: { VOCAB_CONTEXT: { ...PRIORITY_V1.default_profile, exam_relevance: 0 } } });
    expect(irrelevant.priority_index).toBe(0); expect(irrelevant.reasons).toContain('NO_EXAM_RELEVANCE');
  });
  it('exposes additive priority components and stays bounded over boundary combinations', () => {
    for (const mastery of [0, 0.5, 1]) for (const uncertainty of [0, 0.5, 1]) for (const relevance of [0, 0.5, 1]) {
      const item = row(learner({ mastery, uncertainty }), { ...context(), as_of: NOW + 10_000 * PRIORITY_DAY_MS,
        profiles: { VOCAB_CONTEXT: { ...PRIORITY_V1.default_profile, exam_relevance: relevance } } });
      expect(item.priority_index).toBeGreaterThanOrEqual(0); expect(item.priority_index).toBeLessThanOrEqual(100);
      expect(item.priority_index).toBeCloseTo(Object.values(item.priority_components).reduce((a, b) => a + b, 0));
      for (const value of [item.coverage_index, item.evidence_support, item.practice_need, item.diagnostic_need, item.retention_need]) {
        expect(value).toBeGreaterThanOrEqual(0); expect(value).toBeLessThanOrEqual(1);
      }
    }
  });
  it('is pure, deeply immutable, deterministic, and skill-specific', () => {
    const vector = learner(); const ctx = context(); const snapshot = JSON.stringify({ vector, ctx, config: PRIORITY_V1 });
    const first = buildScoreLeakMap(vector, ctx);
    expect(buildScoreLeakMap(vector, ctx)).toEqual(first);
    expect(Object.isFrozen(first.skills)).toBe(true); expect(Object.isFrozen(first.skills[0]?.profile)).toBe(true);
    expect(JSON.stringify({ vector, ctx, config: PRIORITY_V1 })).toBe(snapshot);
    const another = buildScoreLeakMap(learner({ mastery: 0.9 }), ctx);
    expect(another.skills.find((s) => s.skill_id === 'READING_INFERENCE')).toEqual(first.skills.find((s) => s.skill_id === 'READING_INFERENCE'));
  });
});

describe('ExpectedTrainingValue and Next Best Action', () => {
  it('prefers diagnostic evidence collection in cold start', () => {
    const plan = planNextBestAction(createLearnerSkillVector(), [action(), action('diagnose', 'DIAGNOSTIC')], { as_of: NOW }, 15);
    expect(plan.selected?.action.id).toBe('diagnose');
    expect(plan.selected?.value_unit).toBe('PRIORITY_INDEX_PER_MINUTE');
  });
  it('can select targeted practice for a supported gap', () => {
    const plan = planNextBestAction(learner({ mastery: 0.1, uncertainty: 0.05 }), [action(), action('diagnose', 'DIAGNOSTIC')], context(), 15);
    expect(plan.selected?.action.id).toBe('practice');
  });
  it('can select review for supported high mastery with an old observation', () => {
    const plan = planNextBestAction(learner({ mastery: 0.95, uncertainty: 0.05 }), [action(), action('diagnose', 'DIAGNOSTIC'), action('review', 'RETENTION_REVIEW')],
      { ...context(), as_of: NOW + 180 * PRIORITY_DAY_MS }, 15);
    expect(plan.selected?.action.id).toBe('review');
  });
  it('compares value per minute using a bounded minimum time cost', () => {
    const plan = planNextBestAction(learner(), [action('ten'), action('five', 'TARGETED_PRACTICE', { expected_minutes: 5 }),
      action('one', 'TARGETED_PRACTICE', { expected_minutes: 1 })], context(), 20);
    const five = plan.ranked_actions.find((r) => r.action.id === 'five');
    const ten = plan.ranked_actions.find((r) => r.action.id === 'ten');
    const one = plan.ranked_actions.find((r) => r.action.id === 'one');
    expect(five?.expected_training_value).toBeCloseTo((ten?.expected_training_value ?? 0) * 2);
    expect(one?.expected_training_value).toBe(five?.expected_training_value);
    expect(one?.effective_minutes).toBe(5);
  });
  it('incorporates trainability without changing the evidence-based skill gap', () => {
    const ctx = { ...context(), profiles: { VOCAB_CONTEXT: { ...PRIORITY_V1.default_profile, trainability: 0.5 } } };
    const normal = planNextBestAction(learner(), [action()], context(), 20);
    const lower = planNextBestAction(learner(), [action()], ctx, 20);
    expect(lower.selected?.expected_training_value).toBeCloseTo((normal.selected?.expected_training_value ?? 0) / 2);
    expect(lower.score_leak_map.skills.find((s) => s.skill_id === 'VOCAB_CONTEXT')?.skill_gap).toBeCloseTo(0.6);
  });
  it('averages multiple target contributions rather than rewarding extra skills without cost', () => {
    const mixed = action('mixed', 'TARGETED_PRACTICE', { targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 0.7 }, { skill_id: 'MAIN_IDEA', weight: 0.3 }] });
    const plan = planNextBestAction(learner(), [mixed], context(), 15);
    const selected = plan.selected;
    expect(selected?.contributions).toHaveLength(2);
    expect(selected?.training_value_index).toBeCloseTo(selected?.contributions.reduce((sum, c) => sum + c.value_index, 0) ?? -1);
    expect(selected?.training_value_index).toBeLessThanOrEqual(100);
  });
  it('excludes unavailable and over-budget actions, accepts exact budget', () => {
    const plan = planNextBestAction(learner(), [action('unavailable', 'TARGETED_PRACTICE', { available: false }), action('long', 'TARGETED_PRACTICE', { expected_minutes: 11 }), action('exact')], context(), 10);
    expect(plan.selected?.action.id).toBe('exact');
    expect(plan.excluded_actions).toContainEqual({ action_id: 'long', reasons: ['OVER_TIME_BUDGET'] });
    expect(plan.excluded_actions).toContainEqual({ action_id: 'unavailable', reasons: ['UNAVAILABLE'] });
  });
  it('returns no recommendation instead of inventing content or exceeding zero budget', () => {
    for (const plan of [planNextBestAction(learner(), [], context(), 10), planNextBestAction(learner(), [action()], context(), 0)]) {
      expect(plan.status).toBe('NO_ELIGIBLE_ACTION'); expect(plan.selected).toBeNull(); expect(plan.ranked_actions).toEqual([]);
    }
  });
  it('does not recommend unsupported review or zero-value training', () => {
    const plan = planNextBestAction(createLearnerSkillVector(), [action('review', 'RETENTION_REVIEW')], { as_of: NOW }, 20);
    expect(plan.selected).toBeNull(); expect(plan.excluded_actions[0]?.reasons).toContain('NO_SUPPORTED_REVIEW');
    const zero = planNextBestAction(learner(), [action()], { ...context(), profiles: { VOCAB_CONTEXT: { ...PRIORITY_V1.default_profile, trainability: 0 } } }, 20);
    expect(zero.selected).toBeNull(); expect(zero.excluded_actions[0]?.reasons).toContain('NO_TRAINING_VALUE');
  });
  it('requires a timed block candidate for pacing and never updates its mastery', () => {
    const vector = createLearnerSkillVector();
    const targets = [{ skill_id: 'PACING_STAMINA' as const, weight: 1 }];
    const plan = planNextBestAction(vector, [action('single', 'DIAGNOSTIC', { format: 'SINGLE_QUESTION', targets }), action('block', 'DIAGNOSTIC', { format: 'TIMED_BLOCK', targets })], { as_of: NOW }, 20);
    expect(plan.selected?.action.id).toBe('block');
    expect(plan.excluded_actions[0]?.reasons).toContain('PACING_REQUIRES_TIMED_BLOCK');
    expect(vector.PACING_STAMINA).toEqual(createLearnerSkillVector().PACING_STAMINA);
  });
  it('breaks ties deterministically independent of candidate order', () => {
    const candidates = [action('z'), action('a'), action('m')];
    const first = planNextBestAction(learner(), candidates, context(), 10);
    expect(first.ranked_actions.map((r) => r.action.id)).toEqual(['a', 'm', 'z']);
    expect(planNextBestAction(learner(), [...candidates].reverse(), context(), 10)).toEqual(first);
    expect(Object.isFrozen(first.selected?.action.targets)).toBe(true);
    expect(candidates.map((c) => c.id)).toEqual(['z', 'a', 'm']);
  });
  it('returns planning indices and explanations without probability or score-gain claims', () => {
    const plan = planNextBestAction(learner(), [action()], context(), 15);
    const json = JSON.stringify(plan);
    expect(json).not.toMatch(/error_probability|errorProbability|exam_score|score_gain|lost_points|verified_score_gain|hata ihtimali|kesin kayıp|\+\d+ puan|%\d/i);
    expect(plan.selected?.expected_training_value).toBeCloseTo((plan.selected?.training_value_index ?? 0) / 10);
  });
});

describe('Planning input validation', () => {
  it.each([NaN, Infinity, -Infinity, -0.1, 1.1])('rejects invalid fractions %s', (bad) => {
    expect(() => buildScoreLeakMap(learner({ mastery: bad }), context())).toThrow();
    expect(() => buildScoreLeakMap(learner({ uncertainty: bad }), context())).toThrow();
    expect(() => buildScoreLeakMap(learner(), { ...context(), profiles: { VOCAB_CONTEXT: { ...PRIORITY_V1.default_profile, exam_relevance: bad } } })).toThrow();
  });
  it('rejects invalid times and costs, unknown fields, unsupported skills and duplicate IDs', () => {
    for (const cost of [0, -1, NaN, Infinity, 1_441]) expect(() => planNextBestAction(learner(), [action('bad', 'TARGETED_PRACTICE', { expected_minutes: cost })], context(), 10)).toThrow();
    for (const budget of [-1, NaN, Infinity]) expect(() => planNextBestAction(learner(), [], context(), budget)).toThrow();
    expect(() => planNextBestAction(learner(), [action(), action()], context(), 10)).toThrow('Duplicate action');
    expect(() => planNextBestAction(learner(), [{ ...action(), predicted_points: 2 } as TrainingAction], context(), 10)).toThrow();
    expect(() => planNextBestAction(learner(), [action('bad', 'TARGETED_PRACTICE', { targets: [{ skill_id: 'UNKNOWN' as SkillId, weight: 1 }] })], context(), 10)).toThrow();
  });
  it('rejects invalid weights and ambiguous repeated target skills', () => {
    expect(() => buildScoreLeakMap(learner(), context(), { ...PRIORITY_V1, weights: { practice: 1, diagnostic: 1, retention: 1 } })).toThrow();
    expect(() => planNextBestAction(learner(), [action('bad', 'TARGETED_PRACTICE', { targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 0.5 }] })], context(), 10)).toThrow();
    expect(() => planNextBestAction(learner(), [action('bad', 'TARGETED_PRACTICE', { targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 0.5 }, { skill_id: 'VOCAB_CONTEXT', weight: 0.5 }] })], context(), 10)).toThrow();
  });
  it('rejects future snapshots and coverage inconsistent with the learner model', () => {
    expect(() => buildScoreLeakMap(learner({ recency: NOW + 1 }), context())).toThrow('future');
    expect(() => buildScoreLeakMap(learner({ evidence_count: 1 }), context())).toThrow('inconsistent');
    expect(() => buildScoreLeakMap(learner(), context({ VOCAB_CONTEXT: { ...COVERAGE, last_informative_at: NOW } }))).toThrow('inconsistent');
    expect(() => buildScoreLeakMap(learner(), context({ VOCAB_CONTEXT: { ...COVERAGE, family_count: 8, question_count: 2 } }))).toThrow();
    expect(() => buildScoreLeakMap(learner(), context({ VOCAB_CONTEXT: { ...COVERAGE, last_informative_at: null } }))).toThrow();
  });
});
