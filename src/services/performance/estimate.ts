import type { PerformanceEstimateBlocker, PerformanceEstimateResult, PerformanceSnapshot } from '../../types/performance';
import { deepFreeze } from '../questions/attempts';
import { analyzePerformanceCoverage } from './coverage';
import { DEFAULT_CONFIDENCE_LEVEL, PERFORMANCE_V1 as C } from './calibration';
import { selectPerformanceEvidence } from './selectEvidence';
import { wilsonInterval } from './statistics';

export function estimatePerformance(input: PerformanceSnapshot): PerformanceEstimateResult {
  const set = selectPerformanceEvidence(input), rows = set.records;
  const generalizable = rows.filter((r) => r.exam_like_transfer);
  const correct = rows.filter((r) => r.correct).length;
  const observedInterval = wilsonInterval(correct, rows.length);
  const interval = wilsonInterval(generalizable.filter((r) => r.correct).length, generalizable.length);
  const coverage = analyzePerformanceCoverage(generalizable), observedCoverage = analyzePerformanceCoverage(rows);
  const blockers: PerformanceEstimateBlocker[] = [];
  if (set.exclusions.some((e) => e.reason === 'UNTRUSTED_SOURCE')) blockers.push('SOURCE_NOT_VERIFIED');
  if (set.integrity === 'INVALID') blockers.push('INVALID_SOURCE_RECORDS');
  if (!rows.length) blockers.push('NO_ELIGIBLE_EVIDENCE');
  if (generalizable.length < C.min_questions) blockers.push('INSUFFICIENT_SAMPLE');
  if (!generalizable.length || rows.length > generalizable.length && generalizable.length < C.min_questions) blockers.push('EXAM_LIKE_CONTEXT');
  if (coverage.missing_families.length || coverage.underrepresented_families.length) blockers.push('FAMILY_COVERAGE');
  if (coverage.missing_skills.length || coverage.underrepresented_skills.length) blockers.push('SKILL_COVERAGE');
  if (coverage.block_count < C.min_blocks) blockers.push('BLOCK_DIVERSITY');
  if (coverage.session_count < C.min_sessions) blockers.push('SESSION_DIVERSITY');
  if (coverage.family_concentration > C.max_family_fraction || coverage.block_concentration > C.max_block_fraction || coverage.session_concentration > C.max_session_fraction) blockers.push('CONCENTRATED_EVIDENCE');
  if (interval === null || interval.upper_bound - interval.lower_bound > C.max_interval_width) blockers.push('WIDE_INTERVAL');
  const base = { observed: { eligible_question_count: rows.length, correct_count: correct, incorrect_count: rows.length - correct,
    accuracy: rows.length === 0 ? null : correct / rows.length, qualified_block_count: observedCoverage.block_count, interval: observedInterval },
    coverage, observed_coverage: observedCoverage, generalization: { sample_size: generalizable.length, interval },
    uncertainty: { sampling_width: interval === null ? null : interval.upper_bound - interval.lower_bound, calibrated_exam_prediction: false as const, scope: 'EXAM_LIKE_PRACTICE_PROXY' as const },
    provenance: { version: C.version, source: { ...input.source }, as_of: input.as_of, confidence_level: DEFAULT_CONFIDENCE_LEVEL,
      attempt_ids: rows.map((r) => r.attempt_id), block_ids: [...new Set(rows.map((r) => r.block_id))].sort(),
      generalization_attempt_ids: generalizable.map((r) => r.attempt_id), exclusions: set.exclusions,
      assumptions: ['SOURCE_ORIGIN_DECLARED_BY_INTEGRATION', 'COMPLETE_ATTEMPT_HISTORY_REQUIRED', 'UNRECORDED_EXPOSURE_UNKNOWN',
        'TRANSFER_CONTEXT_CALLER_OBSERVED', 'BINOMIAL_INDEPENDENCE_AND_COMPARABILITY_NOT_VERIFIED', 'NO_EXAM_BLUEPRINT_OR_POINT_SCALE', 'EDITORIAL_READINESS_GATES'] } };
  if (blockers.length === 0 && interval !== null) return deepFreeze({ ...base, status: 'READY',
    exam_range: { ...interval, scope: 'EXAM_LIKE_PRACTICE_PROXY', calibrated: false, point_scale: null }, blockers: [] });
  const status = rows.length === 0 ? 'INSUFFICIENT' : generalizable.length >= C.min_questions && coverage.covered_families.length >= 2 ? 'PROVISIONAL' : 'OBSERVED_ONLY';
  return deepFreeze({ ...base, status, exam_range: null, blockers });
}
