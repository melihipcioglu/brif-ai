import { z } from 'zod';
import type { CalibrationReason, ExamSimulationDefinition, ExamSimulationEvent, ExamSimulationEventInput, ExamSimulationState, ExamSimulationTranscript } from '../../types/exam';
import type { QuestionAttempt } from '../../types/question';
import type { SessionEvent, SessionPlan } from '../../types/session';
import { deepFreeze } from '../questions/attempts';
import { questionAttemptSchema, validateAttemptForQuestion } from '../questions/validation';
import { canonicalEvidence } from '../evidence/validation';
import { performanceSourceSchema } from '../performance/selectEvidence';
import { timestampSchema } from '../validation';
import { SESSION_V1 } from '../session/calibration';
import { projectAdaptiveSession } from '../session/execution';
import { parseExamForm } from './formBuilder';
import { CALIBRATION_POLICY } from './policies';

const id = z.string().min(1).max(100);
const definitionSchema = z.strictObject({ id, session_kind: z.literal('EXAM_SIMULATION'), mode: z.enum(['PRACTICE_SIMULATION', 'STRICT_SIMULATION']),
  form: z.unknown(), created_at: timestampSchema, source: performanceSourceSchema, policy_version: z.literal(CALIBRATION_POLICY),
  monitoring: z.strictObject({ assistance: z.enum(['COMPLETE', 'UNKNOWN']), interruptions: z.enum(['COMPLETE', 'UNKNOWN']), reference: z.string().min(1).max(500).nullable() }),
});
const eventSchema: z.ZodType<ExamSimulationEvent> = z.strictObject({
  id: z.string().min(1).max(200), simulation_id: id, form_id: id, form_fingerprint: z.string(), sequence: z.number().int().positive().max(1_000_000), at: timestampSchema,
  command: z.discriminatedUnion('type', [
    z.strictObject({ type: z.literal('START') }), z.strictObject({ type: z.literal('PAUSE') }), z.strictObject({ type: z.literal('RESUME') }),
    z.strictObject({ type: z.literal('INTERRUPT') }), z.strictObject({ type: z.literal('COMPLETE') }), z.strictObject({ type: z.literal('ABANDON') }), z.strictObject({ type: z.literal('TIMEOUT') }),
    z.strictObject({ type: z.literal('PULSE'), engaged: z.boolean() }),
    z.strictObject({ type: z.literal('SUBMIT'), attempt: questionAttemptSchema, replaces_attempt_id: z.string().min(1).max(200).nullable() }),
    z.strictObject({ type: z.literal('HELP'), kind: z.enum(['HINT', 'WORD_POPOVER', 'VOCABULARY_REVEAL', 'ANSWER_REVEAL', 'EXPLANATION_REVEAL']) }),
    z.strictObject({ type: z.literal('ANSWER_EDIT'), question_id: z.string().min(1).max(200) }),
    z.strictObject({ type: z.literal('EXTEND_TIME'), additional_ms: z.number().int().positive().max(86_400_000) }),
  ]),
});
export function parseDefinition(input: unknown): ExamSimulationDefinition {
  const d = definitionSchema.parse(input), form = parseExamForm(d.form);
  if (d.created_at < form.created_at || d.mode === 'STRICT_SIMULATION' && form.quality !== 'COMPLETE') throw new RangeError('Strict mode requires a complete form created before execution');
  if ((d.monitoring.assistance === 'COMPLETE' || d.monitoring.interruptions === 'COMPLETE') && d.monitoring.reference === null) throw new RangeError('Complete monitoring needs provenance');
  return deepFreeze({ ...d, form });
}
export function createExamSimulation(input: Omit<ExamSimulationDefinition, 'session_kind' | 'policy_version'>): ExamSimulationTranscript {
  return deepFreeze({ definition: parseDefinition({ ...input, session_kind: 'EXAM_SIMULATION', policy_version: CALIBRATION_POLICY }), events: [] });
}
/** Pure journal replay: clocks and actual answer linkage reuse Phase 5 without saving a study session. */
export function projectExamSimulation(input: ExamSimulationTranscript, asOf: number): ExamSimulationState {
  timestampSchema.parse(asOf); const d = parseDefinition(input.definition), form = d.form;
  if (asOf < d.created_at) throw new RangeError('Projection precedes definition');
  const unique = new Map<string, ExamSimulationEvent>(), duplicates = new Set<string>();
  for (const raw of input.events) {
    const event = eventSchema.parse(raw), old = unique.get(event.id);
    if (old && canonicalEvidence(old) !== canonicalEvidence(event)) throw new RangeError('Conflicting event ID');
    if (old) duplicates.add(event.id); else unique.set(event.id, event);
  }
  const events = [...unique.values()].sort((a, b) => a.sequence - b.sequence);
  const blockId = `${d.id}/exam`, minutes = Math.min(180, form.blueprint.time_limit_ms / 60_000);
  const plan: SessionPlan = { id: `${d.id}/plan`, session_id: d.id, mode: 'NORMAL', created_at: d.created_at, planned_minutes: minutes, allocated_minutes: minutes,
    notes: ['Exam wrapper clock/linkage projection; not a stored study session.'], config: SESSION_V1,
    blocks: [{ id: blockId, type: 'TIMED_BLOCK', target_skills: ['PACING_STAMINA'], planned_minutes: minutes, question_ids: form.question_ids,
      candidate_ids: [form.id], lexical_ids: [], cognitive_load: 'HIGH', timed_enabled: true, explanation: 'Exam form execution' }] };
  const journal: SessionEvent[] = [], submitted = new Map<string, QuestionAttempt>(), answers = new Map<string, QuestionAttempt>(), conditions = new Set<CalibrationReason>();
  let status: ExamSimulationState['status'] = 'PLANNED', started: number | null = null, ended: number | null = null;
  let paused = false, engaged = false, last = d.created_at, limit = form.blueprint.time_limit_ms;
  const emit = (at: number, command: SessionEvent['command']): void => { journal.push({ id: `${d.id}/projection/${journal.length}`, session_id: d.id, at, sequence: journal.length + 1,
    command, ...(command.type === 'QUESTION' ? { attempt_ref: `QUESTION:${command.attempt_id}` } : {}) }); };
  for (const [i, e] of events.entries()) {
    if (e.sequence !== i + 1 || e.simulation_id !== d.id || e.form_id !== form.id || e.form_fingerprint !== form.fingerprint || e.at < last || e.at > asOf) throw new RangeError('Invalid event identity/order/time');
    const cmd = e.command;
    if (status === 'ACTIVE' && e.at - last > SESSION_V1.idle_lease_ms) conditions.add('INTERRUPTED');
    if (cmd.type !== 'START' && status !== 'ACTIVE') throw new RangeError('Simulation is not active');
    const elapsed = started === null ? 0 : e.at - started;
    if (d.mode === 'STRICT_SIMULATION' && elapsed > limit && !['COMPLETE', 'TIMEOUT', 'ABANDON'].includes(cmd.type)) throw new RangeError('Strict deadline exceeded; finalize timeout');
    switch (cmd.type) {
      case 'START':
        if (status !== 'PLANNED') throw new RangeError('Already started');
        status = 'ACTIVE'; started = e.at; engaged = true; emit(e.at, { type: 'START' }); emit(e.at, { type: 'START_BLOCK', block_id: blockId }); break;
      case 'PULSE':
        if (paused && cmd.engaged) throw new RangeError('Explicit resume required');
        engaged = cmd.engaged; if (!engaged) conditions.add('INTERRUPTED'); emit(e.at, { type: 'PULSE', engaged }); break;
      case 'PAUSE': case 'INTERRUPT':
        if (paused) throw new RangeError('Already paused'); paused = true; engaged = false;
        conditions.add(cmd.type === 'PAUSE' ? 'PAUSED' : 'INTERRUPTED'); emit(e.at, { type: 'PAUSE' }); break;
      case 'RESUME':
        if (!paused) throw new RangeError('Resume requires pause/interruption'); paused = false; engaged = true; emit(e.at, { type: 'RESUME' }); break;
      case 'HELP': conditions.add('ASSISTANCE'); emit(e.at, { type: 'PULSE', engaged }); break;
      case 'ANSWER_EDIT':
        if (!form.question_ids.includes(cmd.question_id)) throw new RangeError('Edit references unknown item');
        conditions.add('ANSWER_REVISION'); emit(e.at, { type: 'PULSE', engaged }); break;
      case 'EXTEND_TIME':
        if (limit + cmd.additional_ms > 86_400_000) throw new RangeError('Extended simulation exceeds technical limit');
        limit += cmd.additional_ms; conditions.add('TIME_EXTENDED'); emit(e.at, { type: 'PULSE', engaged }); break;
      case 'SUBMIT': {
        if (paused || !engaged) throw new RangeError('Cannot submit while inactive');
        const q = form.questions.find((q) => q.id === cmd.attempt.question_id);
        if (!q) throw new RangeError('Question outside immutable form');
        const a = validateAttemptForQuestion(cmd.attempt, q);
        if (a.session_id !== null || a.attempted_at !== e.at || started === null || a.response_time_ms > elapsed) throw new RangeError('Invalid submitted attempt linkage/timing');
        const same = submitted.get(a.id);
        if (same) {
          if (canonicalEvidence(same) !== canonicalEvidence(a)) throw new RangeError('Final answer ID conflict');
          emit(e.at, { type: 'PULSE', engaged }); break;
        }
        const previous = answers.get(a.question_id);
        if (previous && d.mode === 'STRICT_SIMULATION') throw new RangeError('Strict finalized answer is immutable');
        if ((previous?.id ?? null) !== cmd.replaces_attempt_id) throw new RangeError('Invalid answer replacement link');
        if (previous || a.option_change_count > 0) conditions.add('ANSWER_REVISION');
        if (a.words_clicked.length || a.hints_used_count > 0) conditions.add('ASSISTANCE');
        submitted.set(a.id, a); answers.set(a.question_id, a);
        emit(e.at, { type: 'QUESTION', block_id: blockId, attempt_id: a.id, item_id: a.question_id, retry_of: previous?.id ?? null }); break;
      }
      case 'COMPLETE':
        status = elapsed > limit ? 'TIMED_OUT' : 'COMPLETED'; ended = e.at;
        if (status === 'TIMED_OUT') { conditions.add('TIME_LIMIT'); emit(e.at, { type: 'ABANDON' }); }
        else { emit(e.at, { type: 'COMPLETE_BLOCK', block_id: blockId }); emit(e.at, { type: 'FINISH' }); }
        break;
      case 'ABANDON': status = 'ABANDONED'; ended = e.at; emit(e.at, { type: 'ABANDON' }); break;
      case 'TIMEOUT':
        if (elapsed < limit) throw new RangeError('Timeout precedes deadline');
        status = 'TIMED_OUT'; ended = e.at; conditions.add('TIME_LIMIT'); emit(e.at, { type: 'ABANDON' }); break;
    }
    if (elapsed > form.blueprint.time_limit_ms) conditions.add('TIME_LIMIT');
    last = e.at;
  }
  if (status === 'ACTIVE' && started !== null && d.mode === 'STRICT_SIMULATION' && asOf - started > limit) {
    status = 'TIMED_OUT'; ended = started + limit; conditions.add('TIME_LIMIT');
  }
  if (status === 'ACTIVE' && asOf - last > SESSION_V1.idle_lease_ms) conditions.add('INTERRUPTED');
  const projection = projectAdaptiveSession(plan, journal);
  return deepFreeze({ simulation_id: d.id, form_id: form.id, mode: d.mode, status, started_at: started, ended_at: ended,
    time_limit_ms: limit, actual_elapsed_ms: started === null ? 0 : (ended ?? asOf) - started,
    active_elapsed_ms: projection.blocks[0]?.actual_duration_ms ?? 0, paused,
    answers: form.question_ids.flatMap((id) => { const a = answers.get(id); return a ? [a] : []; }), submitted_attempt_ids: [...submitted.keys()].sort(),
    conditions: [...conditions].sort(), duplicate_event_ids: [...duplicates].sort(), execution: { plan, events: journal, projection } });
}
/** Append-safe portable transcript; the host may persist it without changing existing IndexedDB stores. */
export function appendExamSimulationEvent(input: ExamSimulationTranscript, command: Pick<ExamSimulationEventInput, 'id' | 'at' | 'command'>): ExamSimulationTranscript {
  const d = parseDefinition(input.definition);
  const old = input.events.find((e) => e.id === command.id);
  const sequence = old?.sequence ?? new Set(input.events.map((e) => e.id)).size + 1;
  const event = eventSchema.parse({ ...command, simulation_id: d.id, form_id: d.form.id, form_fingerprint: d.form.fingerprint, sequence });
  if (old && canonicalEvidence(old) !== canonicalEvidence(event)) throw new RangeError('Event ID conflict');
  const next = { definition: d, events: old ? [...input.events] : [...input.events, event] };
  projectExamSimulation(next, Math.max(d.created_at, ...next.events.map((e) => e.at)));
  return deepFreeze(next);
}
