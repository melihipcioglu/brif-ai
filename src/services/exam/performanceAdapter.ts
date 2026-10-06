import type { CalibrationEvidence, CalibrationPerformanceSelection, ExamSimulationTranscript } from '../../types/exam';
import type { PerformanceEvidence, PerformanceExclusion } from '../../types/performance';
import { canonicalEvidence } from '../evidence/validation';
import { deepFreeze } from '../questions/attempts';
import { analyzePerformanceCoverage } from '../performance/coverage';
import { wilsonInterval } from '../performance/statistics';
import { timestampSchema } from '../validation';
import { qualifyExamSimulation } from './calibration';
import { compareText } from './provenance';

/** Additive representation adapter. No fake study blocks, transfer receipts or automatic Phase 6 READY. */
export function selectCalibrationPerformanceEvidence(inputs: readonly ExamSimulationTranscript[], asOf: number): CalibrationPerformanceSelection {
  timestampSchema.parse(asOf);
  const groups = new Map<string, ExamSimulationTranscript[]>();
  for (const t of inputs) { const group = groups.get(t.definition.id) ?? []; group.push(t); groups.set(t.definition.id, group); }
  const accepted: CalibrationEvidence[] = [], rejected: { simulation_id: string; reasons: readonly string[] }[] = [];
  for (const [id, group] of [...groups].sort(([a], [b]) => compareText(a, b))) {
    // Same simulation identity must not select the cleaner of two conflicting journals.
    const signatures = new Set(group.map((t) => canonicalEvidence({ definition: t.definition,
      events: [...new Map(t.events.map((e) => [canonicalEvidence(e), e])).values()].sort((a, b) => a.sequence - b.sequence || compareText(a.id, b.id)) })));
    if (signatures.size !== 1) { rejected.push({ simulation_id: id, reasons: ['CONFLICTING_SIMULATION'] }); continue; }
    const result = qualifyExamSimulation(group[0]!, asOf);
    if (result.qualified) accepted.push(result.evidence); else rejected.push({ simulation_id: id, reasons: result.reasons });
  }
  const candidates = accepted.flatMap((e) => e.records.map((r) => ({ record: r, content: e.question_content_keys[r.question_id]!, calibration: e })));
  candidates.sort((a, b) => a.record.attempted_at - b.record.attempted_at || compareText(a.record.attempt_id, b.record.attempt_id) || compareText(a.calibration.id, b.calibration.id));
  const attemptIds = new Set<string>(), questionIds = new Set<string>(), contentKeys = new Set<string>(), included = new Set<string>();
  const records: PerformanceEvidence[] = [], exclusions: PerformanceExclusion[] = [];
  for (const { record, content, calibration } of candidates) {
    if (attemptIds.has(record.attempt_id) || questionIds.has(record.question_id) || contentKeys.has(content)) {
      exclusions.push({ kind: 'ATTEMPT', id: record.attempt_id, reason: 'DUPLICATE' }); continue;
    }
    attemptIds.add(record.attempt_id); questionIds.add(record.question_id); contentKeys.add(content); included.add(calibration.id); records.push(record);
  }
  const correct = records.filter((r) => r.correct).length;
  return deepFreeze({ evidence: { records, exclusions: [...new Map(exclusions.map((e) => [canonicalEvidence(e), e])).values()], integrity: 'VALID' },
    calibration_references: accepted.filter((e) => included.has(e.id)).map((e) => ({ id: e.id, tier: e.tier, form_id: e.form_id })), rejected,
    coverage: analyzePerformanceCoverage(records), interval: wilsonInterval(correct, records.length),
    observed_accuracy: records.length ? correct / records.length : null, exam_range: null, scope: 'CALIBRATION_OBSERVATION' });
}
