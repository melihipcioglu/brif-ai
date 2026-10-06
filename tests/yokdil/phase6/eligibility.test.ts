import { describe, expect, it } from 'vitest';
import type { LexicalAttempt } from '../../../src/types/progress';
import { questionAttemptSchema } from '../../../src/services/questions/validation';
import { sessionEventSchema, sessionPlanSchema } from '../../../src/services/session/validation';
import { estimatePerformance } from '../../../src/services/performance/estimate';
import { PERFORMANCE_V1 } from '../../../src/services/performance/calibration';
import { fixture } from './fixtures';

const lexical: LexicalAttempt = { id: 'lexical', question_id: 'word-micro-test', session_id: null, lexical_ids: ['inhibit'], skill_ids: ['VOCAB_CONTEXT'],
  context_id: 'context', outcome: 'unassisted', response_ms: 500, attempted_at: 1, lexical_review: null };

describe('Evidence selection and leakage boundaries', () => {
  it.each([{ correct: true, expected: 1 }, { correct: false, expected: 0 }, { alternating: true, expected: .5 }])('observes outcomes independently of pacing direction: %j', ({ expected, ...options }) => {
    const result = estimatePerformance(fixture({ count: 10, ...options }));
    expect(result.observed.accuracy).toBe(expected); expect(result.observed.eligible_question_count).toBe(10);
  });
  it('does not turn a plan with no execution into evidence', () => {
    const input = fixture();
    const result = estimatePerformance({ ...input, events: [], attempts: [], timed_results: [], pacing_evidence: [], evidence_runs: [], skill_evidence: [] });
    expect(result.observed.eligible_question_count).toBe(0);
    expect(result.provenance.exclusions.some((e) => e.reason === 'INCOMPLETE')).toBe(true);
  });
  it('deduplicates exact records at every level without additional credit', () => {
    const input = fixture(); const dup = <T>(xs: readonly T[]) => [...xs, ...xs];
    const result = estimatePerformance({ ...input, plans: dup(input.plans), events: dup(input.events), attempts: dup(input.attempts),
      timed_results: dup(input.timed_results), pacing_evidence: dup(input.pacing_evidence), evidence_runs: dup(input.evidence_runs), skill_evidence: dup(input.skill_evidence) });
    expect(result.observed).toEqual(estimatePerformance(input).observed);
    expect(result.provenance.exclusions.some((e) => e.reason === 'DUPLICATE')).toBe(true);
  });
  it('conflicting duplicate IDs fail closed in either input order', () => {
    const input = fixture(), a = questionAttemptSchema.parse(input.attempts[0]);
    const bad = { ...a, response_time_ms: a.response_time_ms + 1 };
    const left = estimatePerformance({ ...input, attempts: [...input.attempts, bad] });
    const right = estimatePerformance({ ...input, attempts: [bad, ...input.attempts] });
    expect(left).toEqual(right); expect(left.blockers).toContain('INVALID_SOURCE_RECORDS');
    expect(left.observed.eligible_question_count).toBe(0);
  });
  it('does not substitute a later correct attempt for an earlier attempt outside qualified blocks', () => {
    const input = fixture({ transfer: false }), a = questionAttemptSchema.parse(input.attempts[0]);
    const result = estimatePerformance({ ...input, attempts: [...input.attempts, { ...a, id: 'prior', attempted_at: a.attempted_at - 1 }] });
    expect(result.observed.eligible_question_count).toBe(4);
    expect(result.provenance.exclusions).toContainEqual({ kind: 'ATTEMPT', id: a.id, reason: 'REPEATED_QUESTION' });
  });
  it('recognizes identical question content under a different ID as prior exposure', () => {
    const input = fixture({ transfer: false }), a = questionAttemptSchema.parse(input.attempts[0]);
    const alias = { ...input.questions[0]!, id: 'alias' };
    const result = estimatePerformance({ ...input, questions: [...input.questions, alias], attempts: [...input.attempts, { ...a, id: 'prior', question_id: 'alias', attempted_at: a.attempted_at - 1 }] });
    expect(result.observed.eligible_question_count).toBe(4);
  });
  it('timestamp ties do not choose an arbitrary successful first attempt', () => {
    const input = fixture({ transfer: false }), a = questionAttemptSchema.parse(input.attempts[0]);
    const result = estimatePerformance({ ...input, attempts: [...input.attempts, { ...a, id: 'simultaneous' }] });
    expect(result.observed.eligible_question_count).toBe(4);
  });
  it('lexical-only and mixed lexical records never add trials', () => {
    const empty = fixture({ count: 0 });
    expect(estimatePerformance({ ...empty, attempts: [lexical], lexical_attempt_ids: [lexical.id] }).observed.eligible_question_count).toBe(0);
    const input = fixture();
    const result = estimatePerformance({ ...input, attempts: [...input.attempts, lexical], lexical_attempt_ids: [lexical.id] });
    expect(result.observed).toEqual(estimatePerformance(input).observed);
    expect(result.provenance.exclusions).toContainEqual({ kind: 'ATTEMPT', id: 'lexical', reason: 'LEXICAL_ATTEMPT' });
  });
  it('assisted answers are excluded even though Phase 5 can qualify the block', () => {
    const result = estimatePerformance(fixture({ assisted: true }));
    expect(result.observed.eligible_question_count).toBe(4);
    expect(result.provenance.exclusions.some((e) => e.reason === 'ASSISTED')).toBe(true);
  });
  it.each([NaN, Infinity, -1])('invalid response duration %s invalidates the snapshot rather than cherry-picking', (duration) => {
    const input = fixture(), a = questionAttemptSchema.parse(input.attempts[0]);
    const result = estimatePerformance({ ...input, attempts: [{ ...a, response_time_ms: duration }, ...input.attempts.slice(1)] });
    expect(result.blockers).toContain('INVALID_SOURCE_RECORDS'); expect(result.observed.eligible_question_count).toBe(0);
  });
  it('does not trust a forged aggregate result or detached pacing record', () => {
    const input = fixture();
    expect(estimatePerformance({ ...input, timed_results: [{ block_id: 'p6-s-0/b', qualified: true, correct_count: 100 }] }).blockers).toContain('INVALID_SOURCE_RECORDS');
    expect(estimatePerformance({ ...input, pacing_evidence: [] }).blockers).toContain('INVALID_SOURCE_RECORDS');
  });
  it('rejects result/evidence tampering within otherwise valid ranges', () => {
    const input = fixture();
    const rows = input.skill_evidence.map((e) => ({ ...(e as object), strength: .99 }));
    expect(estimatePerformance({ ...input, skill_evidence: rows }).blockers).toContain('INVALID_SOURCE_RECORDS');
  });
  it('optional difficulty and benchmark fields are not required or used as score adjustment', () => {
    expect(estimatePerformance(fixture({ noOptional: true })).observed).toEqual(estimatePerformance(fixture()).observed);
  });
  it('one eligible question left in a qualified block still cannot generalize', () => {
    const input = fixture({ transfer: false });
    const prior = input.attempts.slice(0, 4).map((raw) => { const a = questionAttemptSchema.parse(raw); return { ...a, id: `prior-${a.id}`, attempted_at: a.attempted_at - 1 }; });
    const result = estimatePerformance({ ...input, attempts: [...input.attempts, ...prior] });
    expect(result.observed.eligible_question_count).toBe(1); expect(result.observed.interval?.sample_size).toBe(1);
    expect(result.exam_range).toBeNull();
  });
  it('old evidence is excluded using explicit caller time', () => {
    const input = fixture();
    const latest = Math.max(...input.attempts.map((a) => questionAttemptSchema.parse(a).attempted_at));
    const result = estimatePerformance({ ...input, as_of: latest + PERFORMANCE_V1.max_age_ms + 1 });
    expect(result.observed.eligible_question_count).toBe(0);
    expect(result.provenance.exclusions.filter((e) => e.reason === 'OUTSIDE_WINDOW')).toHaveLength(5);
  });
  it('rejects future records and broken execution sequence', () => {
    const input = fixture();
    expect(estimatePerformance({ ...input, as_of: 0 }).blockers).toContain('INVALID_SOURCE_RECORDS');
    const e = sessionEventSchema.parse(input.events[0]);
    expect(estimatePerformance({ ...input, events: [{ ...e, sequence: 999 }, ...input.events.slice(1)] }).blockers).toContain('INVALID_SOURCE_RECORDS');
  });
  it('non-timed complete blocks do not become performance evidence', () => {
    const input = fixture(), plan = sessionPlanSchema.parse(input.plans[0]);
    const ordinary = { ...plan, blocks: plan.blocks.map((b) => ({ ...b, type: 'TARGETED_PRACTICE' as const, target_skills: ['VOCAB_CONTEXT' as const], timed_enabled: false })) };
    const result = estimatePerformance({ ...input, plans: [ordinary], timed_results: [], pacing_evidence: [] });
    expect(result.observed.eligible_question_count).toBe(0);
    expect(result.provenance.exclusions.some((e) => e.reason === 'NOT_TIMED')).toBe(true);
  });
});
