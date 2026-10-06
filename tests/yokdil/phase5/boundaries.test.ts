import { describe, expect, it } from 'vitest';
import { createLearnerSkillVector } from '../../../src/types/learner';
import type { SessionBlock, SessionEvent, TimedBlockResult } from '../../../src/types/session';
import { deriveTimedBlockResult, extractPacingBlockEvidence, isSessionEngaged, overlayPacingModel, PACING_V1, pacingBlockEvidenceSchema, projectAdaptiveSession, SESSION_V1 } from '../../../src/sessions';
import { actual, q, simplePlan } from './fixtures';

function timedFixture(duration = 200_000, planned = 5) {
  const attempts = Array.from({ length: 5 }, (_, i) => actual(q(i), `a-${i}`, 1_000 + (i + 1) * duration / 5, true, 0, duration / 5));
  const block: SessionBlock = { ...simplePlan('TIMED_BLOCK', 5).blocks[0]!, planned_minutes: planned, status: 'COMPLETED', started_at: 1_000,
    completed_at: 1_000 + duration, actual_duration_ms: duration, completed_question_ids: attempts.map((a) => a.question_id), completed_lexical_ids: [], question_attempt_ids: attempts.map((a) => a.id), lexical_attempt_ids: [] };
  const events: SessionEvent[] = attempts.map((a, i) => ({ id: `e-${i}`, session_id: 'session', at: a.attempted_at, sequence: i + 1,
    attempt_ref: `QUESTION:${a.id}`, command: { type: 'QUESTION', block_id: 'session/b', attempt_id: a.id, item_id: a.question_id, retry_of: null } }));
  return { attempts, block, events };
}
describe('Timer, state-machine and pacing boundaries', () => {
  it('does not classify a visible focused tab with two hours of inactivity as active', () => {
    expect(isSessionEngaged(true, true, 0, 2 * 60 * 60 * 1_000, SESSION_V1.inactivity_ms)).toBe(false);
    expect(isSessionEngaged(true, true, 0, 10_000, SESSION_V1.inactivity_ms)).toBe(true);
    expect(isSessionEngaged(false, true, 0, 10_000, SESSION_V1.inactivity_ms)).toBe(false);
    expect(isSessionEngaged(true, false, 0, 10_000, SESSION_V1.inactivity_ms)).toBe(false);
    expect(isSessionEngaged(true, true, 20_000, 10_000, SESSION_V1.inactivity_ms)).toBe(false);
  });
  it('rejects out-of-order events and missing sequence numbers', () => {
    const event: SessionEvent = { id: 'start', session_id: 'session', at: 1_000, sequence: 1, command: { type: 'START' } };
    expect(() => projectAdaptiveSession(simplePlan(), [event, { ...event, id: 'next', sequence: 3, command: { type: 'PAUSE' } }])).toThrow('order');
    expect(() => projectAdaptiveSession(simplePlan(), [event, { ...event, id: 'next', sequence: 2, at: 999, command: { type: 'PAUSE' } }])).toThrow('order');
  });
  it('produces weak negative pacing only from a sufficiently accurate qualified overrun', () => {
    const input = timedFixture(200_000, 2);
    const result = deriveTimedBlockResult('session', input.block, input.events, input.attempts);
    const evidence = extractPacingBlockEvidence(result, input.attempts);
    expect(result.qualified).toBe(true); expect(evidence?.direction).toBe('NEGATIVE');
    expect(evidence?.strength).toBe(PACING_V1.strength);
    expect(evidence?.strength).toBeLessThan(1);
  });
  it('does not qualify too short, incomplete, retried or inconsistent active-time blocks', () => {
    const short = timedFixture(100_000);
    expect(deriveTimedBlockResult('session', short.block, short.events, short.attempts).qualified).toBe(false);
    const input = timedFixture();
    expect(deriveTimedBlockResult('session', { ...input.block, actual_duration_ms: 180_000 }, input.events, input.attempts).disqualification_reasons).toContain('INCONSISTENT_ACTIVE_TIME');
    const duplicate = actual(q(0), 'retry', input.block.completed_at!, true, 0, 10_000);
    const repeat: SessionEvent = { id: 'repeat', session_id: 'session', at: duplicate.attempted_at, sequence: 6, attempt_ref: 'QUESTION:retry', command: { type: 'QUESTION', block_id: 'session/b', attempt_id: 'retry', item_id: q(0).id, retry_of: 'a-0' } };
    expect(deriveTimedBlockResult('session', input.block, [...input.events, repeat], [...input.attempts, duplicate]).disqualification_reasons).toContain('RETRY_IN_BLOCK');
  });
  it('requires qualified provenance and keeps the pacing overlay bounded and isolated', () => {
    const input = timedFixture(); const result = deriveTimedBlockResult('session', input.block, input.events, input.attempts);
    const evidence = extractPacingBlockEvidence(result, input.attempts); if (!evidence) throw new Error('Missing evidence');
    const before = createLearnerSkillVector();
    const after = overlayPacingModel(before, [{ result, evidence }], result.ended_at);
    expect(after.PACING_STAMINA.mastery).toBeGreaterThan(0); expect(after.PACING_STAMINA.mastery).toBeLessThan(0.1);
    expect(after.PACING_STAMINA.uncertainty).toBeLessThan(1);
    expect(after.VOCAB_CONTEXT).toEqual(before.VOCAB_CONTEXT);
    expect(before.PACING_STAMINA.mastery).toBe(0);
    expect(() => overlayPacingModel(before, [{ result, evidence }, { result, evidence }], result.ended_at)).toThrow('Duplicate');
    expect(() => overlayPacingModel(before, [{ result, evidence }], result.ended_at - 1)).toThrow();
    for (const value of [NaN, Infinity, -1, 1.1]) expect(pacingBlockEvidenceSchema.safeParse({ ...evidence, strength: value }).success).toBe(false);
  });
  it('uses neither one slow item nor an uncompleted block as block evidence', () => {
    const input = timedFixture();
    expect(() => deriveTimedBlockResult('session', { ...input.block, status: 'ACTIVE' }, input.events, input.attempts)).toThrow('completed');
    const unqualified: TimedBlockResult = { ...deriveTimedBlockResult('session', input.block, input.events, input.attempts), qualified: false };
    expect(extractPacingBlockEvidence(unqualified, input.attempts)).toBeNull();
  });
  it('does not trust a forged qualification flag or aggregate count', () => {
    const input = timedFixture(); const result = deriveTimedBlockResult('session', input.block, input.events, input.attempts);
    expect(() => extractPacingBlockEvidence({ ...result, completed_count: 1 }, input.attempts)).toThrow('contradicts');
    expect(() => extractPacingBlockEvidence({ ...result, total_active_ms: 1 }, input.attempts)).toThrow('contradicts');
    expect(() => extractPacingBlockEvidence({ ...result, correct_count: 0 }, input.attempts)).toThrow('contradicts');
  });
});
