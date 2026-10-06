import { describe, expect, it } from 'vitest';
import { estimatePerformance } from '../../../src/services/performance/estimate';
import { fixture } from './fixtures';

describe('Phase 6 read/derive contract', () => {
  it('empty evidence is a typed insufficient state', () => {
    const result = estimatePerformance(fixture({ count: 0 }));
    expect(result.status).toBe('INSUFFICIENT'); expect(result.exam_range).toBeNull();
    expect(result.observed.accuracy).toBeNull(); expect(result.observed.interval).toBeNull();
  });
  it('a self-reported completed one-question block is not qualified', () => {
    const result = estimatePerformance(fixture({ count: 1 }));
    expect(result.observed.eligible_question_count).toBe(0);
    expect(result.exam_range).toBeNull();
  });
  it('reports qualified observations without manufacturing exam readiness', () => {
    const result = estimatePerformance(fixture());
    expect(result.observed.eligible_question_count).toBe(5);
    expect(result.observed.correct_count).toBe(5); expect(result.observed.accuracy).toBe(1);
    expect(result.status).toBe('OBSERVED_ONLY'); expect(result.exam_range).toBeNull();
  });
  it('sufficient, distributed first-attempt exam-like evidence can pass the conditional range gate', () => {
    const result = estimatePerformance(fixture({ count: 66 }));
    expect(result.status).toBe('READY'); expect(result.exam_range).not.toBeNull();
    expect(result.exam_range?.unit).toBe('CORRECT_RESPONSE_PROPORTION');
    expect(result.coverage.missing_families).toEqual([]);
    expect(result.coverage.missing_skills).toEqual([]);
  });
  it('many observations in one family do not pass', () => {
    const result = estimatePerformance(fixture({ count: 80, familyOnly: true }));
    expect(result.exam_range).toBeNull(); expect(result.coverage.family_concentration).toBe(1);
    expect(result.blockers).toContain('FAMILY_COVERAGE');
  });
  it('practice without stored transfer context remains observed only', () => {
    const result = estimatePerformance(fixture({ count: 66, transfer: false }));
    expect(result.observed.eligible_question_count).toBe(66);
    expect(result.exam_range).toBeNull(); expect(result.generalization.sample_size).toBe(0);
  });
  it('the current 22-item pool cannot become READY merely by repeating its questions', () => {
    const result = estimatePerformance(fixture({ count: 22 }));
    expect(result.observed.eligible_question_count).toBe(22); expect(result.exam_range).toBeNull();
    expect(result.blockers).toContain('INSUFFICIENT_SAMPLE');
  });
  it('array order has no effect and input is not mutated', () => {
    const input = fixture({ count: 10 }), before = JSON.stringify(input);
    const reversed = { ...input, questions: [...input.questions].reverse(), plans: [...input.plans].reverse(), events: [...input.events].reverse(),
      attempts: [...input.attempts].reverse(), timed_results: [...input.timed_results].reverse(), pacing_evidence: [...input.pacing_evidence].reverse(),
      evidence_runs: [...input.evidence_runs].reverse(), skill_evidence: [...input.skill_evidence].reverse() };
    expect(estimatePerformance(reversed)).toEqual(estimatePerformance(input));
    expect(JSON.stringify(input)).toBe(before);
  });
  it.each(['DEMO', 'SYNTHETIC', 'UNKNOWN'] as const)('excludes %s data regardless of apparent success', (kind) => {
    const input = fixture(); const result = estimatePerformance({ ...input, source: { kind, reference: 'source' } });
    expect(result.observed.eligible_question_count).toBe(0); expect(result.exam_range).toBeNull();
  });
});
