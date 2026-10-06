import { z } from 'zod';
import type { CalibrationEvidence, CalibrationQualificationResult, CalibrationReason, ExamSimulationTranscript } from '../../types/exam';
import type { PerformanceEvidence } from '../../types/performance';
import { primaryQuestionSkill } from '../evidence/mapping';
import { deepFreeze } from '../questions/attempts';
import { analyzePerformanceCoverage } from '../performance/coverage';
import { wilsonInterval } from '../performance/statistics';
import { deriveTimedBlockResult } from '../session/pacing';
import { timestampSchema } from '../validation';
import { parseDefinition, projectExamSimulation } from './runtime';
import { CALIBRATION_POLICY } from './policies';
import { questionContentKey } from './provenance';

/** Always recompute from the source transcript; never accept qualified=true from an input record. */
export function qualifyExamSimulation(input: ExamSimulationTranscript, asOf: number): CalibrationQualificationResult {
  timestampSchema.parse(asOf);
  try {
    const d = parseDefinition(input.definition), state = projectExamSimulation(input, asOf), form = d.form;
    const reasons = new Set<CalibrationReason>(state.conditions), novelty = { SEEN: 0, UNSEEN: 0, UNKNOWN: 0 };
    for (const e of Object.values(form.exposure)) novelty[e.state]++;
    if (d.mode !== 'STRICT_SIMULATION') reasons.add('PRACTICE_MODE');
    if (form.quality !== 'COMPLETE') reasons.add('PARTIAL_FORM');
    if (form.blueprint.source.verification === 'UNVERIFIED') reasons.add('UNVERIFIED_BLUEPRINT');
    if (!['USER_EXECUTION', 'IMPORTED_USER_EXECUTION'].includes(d.source.kind)) reasons.add('UNTRUSTED_SOURCE');
    if (d.monitoring.assistance !== 'COMPLETE' || d.monitoring.interruptions !== 'COMPLETE') reasons.add('MONITORING_UNKNOWN');
    const complete = state.status === 'COMPLETED' && state.answers.length === form.blueprint.total_questions;
    if (!complete) reasons.add('INCOMPLETE');
    if (state.status === 'TIMED_OUT' || state.actual_elapsed_ms > form.blueprint.time_limit_ms) reasons.add('TIME_LIMIT');
    if (novelty.SEEN > 0) reasons.add('SEEN_QUESTIONS');
    if (novelty.UNKNOWN > 0) reasons.add('UNKNOWN_EXPOSURE');
    let blockQualified = false;
    const block = state.execution.projection.blocks[0];
    if (block?.status === 'COMPLETED') {
      // Phase 5 qualification is necessary, not sufficient, for strict calibration.
      const attempts = input.events.flatMap((e) => e.command.type === 'SUBMIT' ? [e.command.attempt] : []);
      const result = deriveTimedBlockResult(d.id, block, state.execution.events, attempts);
      blockQualified = result.qualified;
      if (result.disqualification_reasons.some((r) => ['INSUFFICIENT_ACTIVE_DURATION', 'INCONSISTENT_ACTIVE_TIME'].includes(r))) reasons.add('INSUFFICIENT_TIMING_EVIDENCE');
    }
    if (!blockQualified) reasons.add('NOT_QUALIFIED_BLOCK');
    const records: PerformanceEvidence[] = state.answers.map((a) => {
      const q = form.questions.find((q) => q.id === a.question_id)!;
      const skill = primaryQuestionSkill(q); if (skill === 'PACING_STAMINA') throw new RangeError('Invalid content skill');
      return { attempt_id: a.id, question_id: q.id, block_id: `${d.id}/exam`, session_id: d.id, family: q.family,
        primary_skill: skill, correct: a.is_correct, attempted_at: a.attempted_at, exam_like_transfer: false };
    });
    const correct = records.filter((r) => r.correct).length;
    const base = { simulation_id: d.id, form_id: form.id, blueprint_id: form.blueprint.id, reasons: [...reasons].sort(),
      question_count: records.length, coverage: analyzePerformanceCoverage(records), observed_accuracy: records.length ? correct / records.length : null,
      interval: wilsonInterval(correct, records.length), novelty, completion_valid: complete,
      timing_valid: blockQualified && ![...reasons].some((r) => ['TIME_LIMIT', 'TIME_EXTENDED', 'PAUSED', 'INTERRUPTED', 'INSUFFICIENT_TIMING_EVIDENCE'].includes(r)),
      assistance_valid: d.monitoring.assistance === 'COMPLETE' && !reasons.has('ASSISTANCE') && !reasons.has('ANSWER_REVISION') };
    if (reasons.size) return deepFreeze({ ...base, qualified: false, tier: 'PRACTICE_ONLY', evidence: null });
    const tier = form.blueprint.scope === 'FULL' && form.blueprint.source.verification === 'OFFICIAL_VERIFIED' ? 'FULL_CALIBRATION' : 'PARTIAL_CALIBRATION';
    const evidence: CalibrationEvidence = { id: `calibration:${d.id}:${form.fingerprint}`, kind: 'CALIBRATION_MOCK', tier,
      policy_version: CALIBRATION_POLICY, simulation_id: d.id, form_id: form.id, form_fingerprint: form.fingerprint,
      blueprint_id: form.blueprint.id, blueprint_version: form.blueprint.version, blueprint_source: form.blueprint.source, source: d.source,
      seed: form.seed, execution_event_ids: [...new Map(input.events.map((e) => [e.id, e])).values()].sort((a, b) => a.sequence - b.sequence).map((e) => e.id),
      novelty_references: [...new Set(Object.values(form.exposure).flatMap((e) => e.references))].sort(), records,
      question_content_keys: Object.fromEntries(form.questions.map((q) => [q.id, questionContentKey(q)])), official_exam: false, official_score_mapping: null };
    return deepFreeze({ ...base, qualified: true, tier, evidence });
  } catch (error) {
    if (!(error instanceof z.ZodError) && !(error instanceof RangeError)) throw error;
    const refs = z.object({ definition: z.object({ id: z.string(), form: z.object({ id: z.string(), blueprint: z.object({ id: z.string() }) }) }) }).safeParse(input);
    return deepFreeze({ qualified: false, tier: 'NOT_ELIGIBLE', evidence: null, simulation_id: refs.success ? refs.data.definition.id : 'invalid',
      form_id: refs.success ? refs.data.definition.form.id : 'invalid', blueprint_id: refs.success ? refs.data.definition.form.blueprint.id : 'invalid',
      reasons: ['INVALID_EXECUTION'], question_count: 0, coverage: analyzePerformanceCoverage([]), observed_accuracy: null, interval: null,
      timing_valid: false, assistance_valid: false, completion_valid: false, novelty: { UNSEEN: 0, SEEN: 0, UNKNOWN: 0 } });
  }
}
