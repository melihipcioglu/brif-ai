import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { QUESTION_FAMILIES } from '../../../src/types/question';
import { qualifyExamSimulation, selectCalibrationPerformanceEvidence } from '../../../src/exam';
import { wilsonInterval } from '../../../src/performance';
import { actual } from '../phase5/fixtures';
import { beforeCompletion, blueprint, completed, context, controlled, form, syntheticPool } from './fixtures';

describe('Calibration qualification', () => {
  it('clean controlled strict mini produces partial calibration with source references', () => {
    const result = qualifyExamSimulation(completed(), 202_000);
    expect(result.qualified).toBe(true); expect(result.tier).toBe('PARTIAL_CALIBRATION');
    expect(result.evidence?.kind).toBe('CALIBRATION_MOCK'); expect(result.evidence?.official_exam).toBe(false);
    expect(result.evidence?.records).toHaveLength(5); expect(result.evidence?.novelty_references).toHaveLength(5);
  });
  it('a full verified hypothetical test blueprint can qualify; no actual official blueprint is shipped', () => {
    const pool = syntheticPool(), bp = blueprint({ id: 'fixture-full', scope: 'FULL', total_questions: 80, time_limit_ms: 4_000_000,
      family_targets: Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, 10])),
      source: { verification: 'OFFICIAL_VERIFIED', reference: 'fixture-only:verified-config', verified_at: 0, verified_by: 'test-harness' } });
    const t = completed({ form: form(bp, controlled(pool), pool) });
    const result = qualifyExamSimulation(t, 3_202_000);
    expect(result.tier).toBe('FULL_CALIBRATION'); expect(result.evidence?.official_score_mapping).toBeNull(); expect(initialQuestions).toHaveLength(22);
  });
  it('internal FULL blueprint is never promoted to official full calibration', () => {
    expect(qualifyExamSimulation(completed({ form: form(blueprint({ scope: 'FULL' })) }), 202_000).tier).toBe('PARTIAL_CALIBRATION');
  });
  it('unverified blueprint remains practice only', () => {
    const t = completed({ form: form(blueprint({ source: { verification: 'UNVERIFIED', reference: null } })) });
    expect(qualifyExamSimulation(t, 202_000).reasons).toContain('UNVERIFIED_BLUEPRINT');
  });
  it.each(['HINT', 'WORD_POPOVER', 'VOCABULARY_REVEAL', 'ANSWER_REVEAL', 'EXPLANATION_REVEAL'] as const)('%s excludes calibration while preserving practice answers', (kind) => {
    const t = beforeCompletion(completed(), [{ type: 'HELP', kind }]);
    const result = qualifyExamSimulation(t, 202_000);
    expect(result.qualified).toBe(false); expect(result.question_count).toBe(5); expect(result.reasons).toContain('ASSISTANCE');
  });
  it('attempt hint telemetry excludes calibration without a separate help event', () => {
    expect(qualifyExamSimulation(completed({ hint: true }), 202_000).reasons).toContain('ASSISTANCE');
  });
  it('pre-submission answer changes or reported answer edits invalidate calibration', () => {
    expect(qualifyExamSimulation(completed({ changes: true }), 202_000).reasons).toContain('ANSWER_REVISION');
    const t = completed();
    expect(qualifyExamSimulation(beforeCompletion(t, [{ type: 'ANSWER_EDIT', question_id: t.definition.form.question_ids[0]! }]), 202_000).reasons).toContain('ANSWER_REVISION');
  });
  it('absence of help events is not proof of complete monitoring', () => {
    expect(qualifyExamSimulation(completed({ monitoring: 'UNKNOWN' }), 202_000).reasons).toContain('MONITORING_UNKNOWN');
  });
  it.each(['UNKNOWN', 'DEMO', 'SYNTHETIC'] as const)('refuses %s execution source', (kind) => {
    expect(qualifyExamSimulation(completed({ source: { kind, reference: 'source' } }), 202_000).reasons).toContain('UNTRUSTED_SOURCE');
  });
  it('seen and unknown novelty disqualify; missing history is not unseen', () => {
    const q = initialQuestions[0]!, ctx = { ...controlled(), prior_attempts: [actual(q, 'seen', 500)] };
    expect(qualifyExamSimulation(completed({ form: form(blueprint(), ctx) }), 202_000).reasons).toContain('SEEN_QUESTIONS');
    expect(qualifyExamSimulation(completed({ form: form(blueprint(), context) }), 202_000).reasons).toContain('UNKNOWN_EXPOSURE');
  });
  it('all-wrong clean execution still provides valid calibration rather than cherry-picked success', () => {
    const result = qualifyExamSimulation(completed({ correct: false }), 202_000);
    expect(result.qualified).toBe(true); expect(result.observed_accuracy).toBe(0); expect(result.interval).toEqual(wilsonInterval(0, 5));
  });
  it('a one-question mini is valid practice but cannot satisfy Phase 5 qualification', () => {
    const t = completed({ form: form(blueprint({ total_questions: 1, family_targets: { GAP_FILL: 1 } })) });
    expect(qualifyExamSimulation(t, 42_000).reasons).toContain('NOT_QUALIFIED_BLOCK');
  });
});

describe('Phase 6-compatible additive adapter', () => {
  it('accepts only qualified calibration and reuses the unchanged Wilson function', () => {
    const t = completed(), result = selectCalibrationPerformanceEvidence([t], 202_000);
    expect(result.evidence.records).toHaveLength(5); expect(result.interval).toEqual(wilsonInterval(5, 5));
    expect(result.calibration_references).toHaveLength(1); expect(result.exam_range).toBeNull();
    expect(result.evidence.records.every((r) => r.exam_like_transfer === false)).toBe(true);
  });
  it('practice mode and disqualified strict simulation are never promoted', () => {
    const t = completed({ mode: 'PRACTICE_SIMULATION' });
    const result = selectCalibrationPerformanceEvidence([t, completed({ id: 'bad', hint: true })], 202_000);
    expect(result.evidence.records).toHaveLength(0); expect(result.rejected).toHaveLength(2);
  });
  it('duplicate calibration consumption is idempotent and order independent', () => {
    const t = completed();
    expect(selectCalibrationPerformanceEvidence([t, t], 202_000)).toEqual(selectCalibrationPerformanceEvidence([t], 202_000));
    const other = completed({ id: 'other' });
    const a = selectCalibrationPerformanceEvidence([t, other], 202_000), b = selectCalibrationPerformanceEvidence([other, t], 202_000);
    expect(a).toEqual(b); expect(a.evidence.records).toHaveLength(5);
  });
  it('conflicting clean and disqualified journals cannot pick the cleaner copy', () => {
    const t = completed(), altered = beforeCompletion(t, [{ type: 'HELP', kind: 'ANSWER_REVEAL' }]);
    const result = selectCalibrationPerformanceEvidence([t, altered], 202_000);
    expect(result.evidence.records).toHaveLength(0); expect(result.rejected[0]?.reasons).toContain('CONFLICTING_SIMULATION');
  });
  it('empty input has no interval and no fabricated exam range', () => {
    const result = selectCalibrationPerformanceEvidence([], 0);
    expect(result.interval).toBeNull(); expect(result.observed_accuracy).toBeNull(); expect(result.exam_range).toBeNull();
  });
});
