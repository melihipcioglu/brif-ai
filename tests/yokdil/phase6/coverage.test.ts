import { describe, expect, it } from 'vitest';
import { analyzePerformanceCoverage } from '../../../src/services/performance/coverage';
import { selectPerformanceEvidence } from '../../../src/services/performance/selectEvidence';
import { estimatePerformance } from '../../../src/services/performance/estimate';
import { PERFORMANCE_CONTENT_SKILLS, PERFORMANCE_V1 } from '../../../src/services/performance/calibration';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { primaryQuestionSkill } from '../../../src/services/evidence/mapping';
import { QUESTION_FAMILIES } from '../../../src/types/question';
import { fixture } from './fixtures';

describe('Coverage and readiness', () => {
  it('uses precisely the existing eight families and twelve content dimensions', () => {
    expect(PERFORMANCE_V1.required_families).toEqual(QUESTION_FAMILIES);
    expect(PERFORMANCE_CONTENT_SKILLS).toHaveLength(12);
    expect(new Set(initialQuestions.map(primaryQuestionSkill)).size).toBe(12);
    expect(new Set(initialQuestions.map((q) => q.family)).size).toBe(8);
    expect(initialQuestions).toHaveLength(22);
  });
  it('distinguishes missing and underrepresented classes', () => {
    const coverage = analyzePerformanceCoverage(selectPerformanceEvidence(fixture()).records);
    expect(coverage.covered_families).toEqual(['GAP_FILL']);
    expect(coverage.underrepresented_skills).toContain('VOCAB_CONTEXT');
    expect(coverage.missing_skills).toContain('MAIN_IDEA');
    expect(coverage.family_concentration).toBe(1);
  });
  it('primary classification cannot multiply one trial into thirteen covered skills', () => {
    const rows = selectPerformanceEvidence(fixture()).records;
    const coverage = analyzePerformanceCoverage(rows);
    expect(Object.values(coverage.skill_counts).reduce((sum, n) => sum + n, 0)).toBe(rows.length);
  });
  it('block and session concentration are independent constraints', () => {
    const rows = selectPerformanceEvidence(fixture({ count: 66 })).records;
    const coverage = analyzePerformanceCoverage(rows.map((r) => ({ ...r, session_id: 'one-session', block_id: 'one-block' })));
    expect(coverage.block_concentration).toBe(1); expect(coverage.session_concentration).toBe(1);
    expect(coverage.block_count).toBe(1); expect(coverage.session_count).toBe(1);
  });
  it('one huge balanced block fails the readiness gate despite full family/skill coverage', () => {
    const result = estimatePerformance(fixture({ count: 66, blockSize: 66 }));
    expect(result.observed.eligible_question_count).toBe(66);
    expect(result.coverage.missing_families).toEqual([]); expect(result.coverage.missing_skills).toEqual([]);
    expect(result.status).toBe('PROVISIONAL'); expect(result.exam_range).toBeNull();
    expect(result.blockers).toContain('BLOCK_DIVERSITY'); expect(result.blockers).toContain('SESSION_DIVERSITY');
    expect(result.blockers).toContain('CONCENTRATED_EVIDENCE');
  });
  it('rejects duplicate attempts and repeated question identities in a standalone coverage call', () => {
    const rows = selectPerformanceEvidence(fixture()).records;
    expect(() => analyzePerformanceCoverage([...rows, rows[0]!])).toThrow();
    expect(() => analyzePerformanceCoverage([...rows, { ...rows[0]!, attempt_id: 'different-attempt' }])).toThrow();
  });
  it('more representative evidence changes readiness rather than merely metadata', () => {
    const small = estimatePerformance(fixture({ count: 10 })), broad = estimatePerformance(fixture({ count: 66 }));
    expect(small.status).toBe('OBSERVED_ONLY'); expect(broad.status).toBe('READY');
    expect(broad.coverage.covered_skills.length).toBeGreaterThan(small.coverage.covered_skills.length);
    expect(broad.blockers).toEqual([]);
  });
  it.each([true, false])('accuracy level (%s) does not determine evidence readiness', (correct) => {
    const result = estimatePerformance(fixture({ count: 66, correct }));
    expect(result.status).toBe('READY'); expect(result.exam_range).not.toBeNull();
    expect(result.exam_range!.lower_bound).toBeGreaterThanOrEqual(0);
    expect(result.exam_range!.upper_bound).toBeLessThanOrEqual(1);
    expect(result.uncertainty.calibrated_exam_prediction).toBe(false);
  });
  it('outputs immutable evidence and results', () => {
    const input = fixture(); const selected = selectPerformanceEvidence(input), result = estimatePerformance(input);
    expect(Object.isFrozen(selected.records)).toBe(true); expect(Object.isFrozen(result.observed)).toBe(true);
    expect(() => { Object.defineProperty(result.observed, 'accuracy', { value: 99 }); }).toThrow();
  });
});
