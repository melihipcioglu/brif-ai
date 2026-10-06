import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { createLearnerSkillVector } from '../../../src/types/learner';
import { calculateReviewPriority } from '../../../src/services/lexicalScheduler';
import { buildSessionCandidatePool, planDailySession, SESSION_V1 } from '../../../src/sessions';
import type { SessionCandidate } from '../../../src/types/session';
import { actual, candidate, dueWords, NOW, q } from './fixtures';

const content = { questions: initialQuestions, lexical_records: dueWords(), attempts: [] };
const vector = createLearnerSkillVector();
const context = { as_of: NOW };
function plan(minutes: number, candidates = buildSessionCandidatePool(content, NOW)) {
  return planDailySession({ id: 'plan', session_id: 's', mode: 'NORMAL', available_minutes: minutes }, vector, candidates, content, context);
}
describe('Constrained time-first session planning', () => {
  it.each([10, 24, 27, 30, 47, 60])('fits an explicit %s-minute budget', (minutes) => {
    const result = plan(minutes);
    expect(result.allocated_minutes).toBeLessThanOrEqual(minutes + 1e-9);
    expect(result.planned_minutes).toBe(minutes);
    expect(result.blocks.length).toBeGreaterThan(0);
  });
  it('uses configurable mode defaults and explicit duration overrides', () => {
    for (const mode of ['EMERGENCY', 'NORMAL', 'INTENSIVE'] as const) {
      const result = planDailySession({ id: mode, session_id: mode, mode }, vector, [], content, context);
      expect(result.planned_minutes).toBe(SESSION_V1.mode_minutes[mode]);
      expect(planDailySession({ id: mode, session_id: mode, mode, available_minutes: 27 }, vector, [], content, context).planned_minutes).toBe(27);
    }
  });
  it('adapts question count to actual speed history, not a fixed mode quota', () => {
    const speedContent = (ms: number) => ({ ...content, lexical_records: [], attempts: initialQuestions.flatMap((question, i) => Array.from({ length: 3 }, (_, n) => actual(question, `a-${i}-${n}`, NOW - 1, true, 0, ms))) });
    const make = (ms: number) => { const source = speedContent(ms); return planDailySession({ id: 'p', session_id: 's', mode: 'EMERGENCY' }, vector, buildSessionCandidatePool(source, NOW), source, context); };
    const fast = make(60_000), slow = make(180_000);
    expect(fast.blocks.flatMap((b) => b.question_ids).length).toBeGreaterThan(slow.blocks.flatMap((b) => b.question_ids).length);
  });
  it('reserves due lexical capacity without allowing SRS to consume the session', () => {
    const result = plan(10);
    const lexical = result.blocks.filter((b) => b.type === 'LEXICAL_REVIEW');
    expect(lexical.length).toBeGreaterThan(0);
    expect(lexical.reduce((sum, b) => sum + b.planned_minutes, 0)).toBeLessThanOrEqual(2.5 + 1e-9);
    expect(result.blocks.some((b) => b.question_ids.length > 0)).toBe(true);
    expect(plan(10, buildSessionCandidatePool({ ...content, questions: [] }, NOW)).allocated_minutes).toBeLessThan(10);
  });
  it('uses live scheduler priority and never creates review evidence while planning', () => {
    const before = JSON.stringify(content);
    const pool = buildSessionCandidatePool(content, NOW);
    const result = plan(2, pool);
    expect(result.blocks.some((b) => b.type === 'LEXICAL_REVIEW')).toBe(true);
    const chosenWord = result.blocks.find((b) => b.type === 'LEXICAL_REVIEW')?.lexical_ids[0];
    const highest = Math.max(...content.lexical_records.map((word) => calculateReviewPriority(word, NOW)));
    expect(calculateReviewPriority(content.lexical_records.find((word) => word.word_id === chosenWord)!, NOW)).toBe(highest);
    expect(JSON.stringify(content)).toBe(before);
    const future = { ...content, lexical_records: dueWords().map((w) => ({ ...w, next_review_date: NOW + 1 })) };
    expect(buildSessionCandidatePool(future, NOW).some((c) => c.type === 'LEXICAL_REVIEW')).toBe(false);
  });
  it('prevents one high-value skill from monopolizing while alternatives exist', () => {
    const candidates = initialQuestions.slice(0, 12).map((question, i) => candidate(`c-${i}`, question, i < 6 ? 'CONNECTOR_DISCOURSE' : i < 9 ? 'VOCAB_CONTEXT' : 'TENSE_ASPECT'));
    const result = plan(16, candidates);
    const connector = result.blocks.filter((b) => b.target_skills.includes('CONNECTOR_DISCOURSE')).reduce((s, b) => s + b.planned_minutes, 0);
    expect(connector).toBeLessThanOrEqual(8); expect(new Set(result.blocks.flatMap((b) => b.target_skills)).size).toBe(3);
  });
  it('relaxes repetition when only one usable skill exists', () => {
    const candidates = initialQuestions.slice(0, 6).map((question, i) => candidate(`c-${i}`, question, 'CONNECTOR_DISCOURSE'));
    const result = plan(10, candidates);
    expect(result.allocated_minutes).toBe(10); expect(result.notes.some((n) => n.includes('esnetildi'))).toBe(true);
  });
  it('allocates limited cold-start diagnostics and explores multiple families', () => {
    const result = plan(20);
    const diagnostic = result.blocks.filter((b) => b.type === 'DIAGNOSTIC');
    expect(diagnostic.length).toBeGreaterThan(0);
    expect(diagnostic.reduce((s, b) => s + b.planned_minutes, 0)).toBeLessThanOrEqual(12);
    expect(result.blocks.some((b) => b.type === 'TARGETED_PRACTICE')).toBe(true);
    const families = new Set(result.blocks.flatMap((b) => b.question_ids).map((id) => initialQuestions.find((q) => q.id === id)?.family));
    expect(families.size).toBeGreaterThanOrEqual(2);
  });
  it('targets high uncertainty and low coverage even outside cold start', () => {
    const learner = { ...vector, VOCAB_CONTEXT: { ...vector.VOCAB_CONTEXT, evidence_count: 1, recency: NOW - 1 } };
    const pool = [candidate('d', q(), 'VOCAB_CONTEXT', 'DIAGNOSTIC')];
    const result = planDailySession({ id: 'p', session_id: 's', mode: 'NORMAL' }, learner, pool, content, context);
    expect(result.blocks[0]?.type).toBe('DIAGNOSTIC');
  });
  it('can select retention for high mastery with stale supported evidence', () => {
    const learner = { ...vector, VOCAB_CONTEXT: { ...vector.VOCAB_CONTEXT, mastery: 0.9, uncertainty: 0.1, evidence_count: 30, recency: 1 } };
    const result = planDailySession({ id: 'p', session_id: 's', mode: 'NORMAL' }, learner, [candidate('review', q(), 'VOCAB_CONTEXT', 'RETENTION_REVIEW')], content,
      { as_of: 90 * 86_400_000, coverage: { VOCAB_CONTEXT: { informative_attempt_count: 30, question_count: 10, family_count: 2, unaided_attempt_count: 30, transfer_attempt_count: 0, last_informative_at: 1 } } });
    expect(result.blocks[0]?.type).toBe('RETENTION_REVIEW');
  });
  it('separates heavy blocks when lighter alternatives are available', () => {
    const candidates = initialQuestions.slice(0, 6).map((question, i) => ({ ...candidate(`c-${i}`, question, i % 2 ? 'TENSE_ASPECT' : 'VOCAB_CONTEXT'), cognitive_load: i < 3 ? 'HIGH' as const : 'MEDIUM' as const }));
    const result = plan(12, candidates);
    expect(result.blocks[0]?.cognitive_load).toBe('MEDIUM');
    for (let i = 1; i < result.blocks.length; i++) expect(result.blocks[i - 1]?.cognitive_load === 'HIGH' && result.blocks[i]?.cognitive_load === 'HIGH').toBe(false);
  });
  it('uses a lighter candidate even when high-value heavy candidates could fill the budget', () => {
    const pool = initialQuestions.slice(0, 9).map((question, i) => ({ ...candidate(`h-${i}`, question, 'VOCAB_CONTEXT'), cognitive_load: 'HIGH' as const }));
    const result = plan(8, [...pool, { ...candidate('light', q(10), 'TENSE_ASPECT'), cognitive_load: 'LOW' }]);
    expect(result.blocks.some((b) => b.cognitive_load === 'LOW')).toBe(true);
  });
  it('creates no phantom activities for empty, unavailable, missing or already-used content', () => {
    expect(plan(10, []).blocks).toEqual([]);
    expect(plan(10, [{ ...candidate('off', q(), 'VOCAB_CONTEXT'), available: false }]).blocks).toEqual([]);
    expect(plan(10, [{ ...candidate('missing', q(), 'VOCAB_CONTEXT'), question_ids: ['unknown'] }]).blocks).toEqual([]);
    const result = planDailySession({ id: 'p', session_id: 's', mode: 'NORMAL', used_question_ids: [q().id] }, vector, [candidate('used', q(), 'VOCAB_CONTEXT')], content, context);
    expect(result.blocks).toEqual([]);
  });
  it('does not repeat content across candidate variants or alter learner values', () => {
    const before = JSON.stringify(vector); const result = plan(60);
    const ids = result.blocks.flatMap((b) => b.question_ids); expect(new Set(ids).size).toBe(ids.length);
    expect(JSON.stringify(vector)).toBe(before); expect(Object.isFrozen(result.blocks)).toBe(true);
    expect(JSON.stringify(result)).not.toMatch(/predicted_points|verified_score_gain|exam_score|\+\d.*puan/i);
  });
  it('requires explicit timed context and real minimum content', () => {
    expect(buildSessionCandidatePool(content, NOW).some((c) => c.type === 'TIMED_BLOCK')).toBe(false);
    const pool = buildSessionCandidatePool(content, NOW, true);
    expect(pool.some((c) => c.type === 'TIMED_BLOCK' && c.question_ids.length >= 5)).toBe(true);
    const timed: SessionCandidate = { ...candidate('timed', q(), 'PACING_STAMINA'), type: 'TIMED_BLOCK', timed_enabled: true };
    expect(plan(10, [timed]).blocks).toEqual([]);
  });
  it('validates invalid budgets and targets and is deterministic under pool reordering', () => {
    for (const bad of [NaN, Infinity, -1, 0]) expect(() => plan(bad)).toThrow();
    const pool = buildSessionCandidatePool(content, NOW);
    expect(plan(27, [...pool].reverse())).toEqual(plan(27, pool));
    expect(() => plan(10, [{ ...candidate('bad', q(), 'VOCAB_CONTEXT'), targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 0.5 }] }])).toThrow();
  });
});
