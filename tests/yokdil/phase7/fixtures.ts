import { initialQuestions } from '../../../src/data/initialQuestions';
import { appendExamSimulationEvent, buildExamForm, createExamSimulation } from '../../../src/exam';
import { actual } from '../phase5/fixtures';
import type { ExamBlueprint, ExamForm, ExamPoolContext, ExamSimulationCommand, ExamSimulationEvent, ExamSimulationTranscript, SimulationMode } from '../../../src/types/exam';
import type { Question } from '../../../src/types/question';
import type { PerformanceSource } from '../../../src/types/performance';

export const blueprint = (changes: Partial<ExamBlueprint> = {}): ExamBlueprint => ({ id: 'internal-mini', version: '1', scope: 'MINI',
  total_questions: 5, time_limit_ms: 300_000, family_targets: { GAP_FILL: 5 }, skill_minimums: {}, reuse_policy: 'ALLOW_REUSE',
  source: { verification: 'INTERNAL', reference: 'project:test-blueprint' }, ...changes });
export const context: ExamPoolContext = { as_of: 1_000, prior_attempts: [], exposures: [] };
export function controlled(pool: readonly Question[] = initialQuestions): ExamPoolContext {
  return { ...context, exposures: pool.map((q) => ({ question_id: q.id, state: 'UNSEEN', observed_at: 1_000,
    method: 'CONTROLLED_INVENTORY', reference: `fixture-controlled-inventory:${q.id}` })) };
}
export function form(bp = blueprint(), ctx = controlled(), pool: readonly Question[] = initialQuestions, id = 'form'): ExamForm {
  const built = buildExamForm({ id, blueprint: bp, questions: pool, context: ctx });
  if (!built.form) throw new Error('Fixture form unavailable'); return built.form;
}
export function append(t: ExamSimulationTranscript, command: ExamSimulationCommand, at: number, id = `event-${t.events.length}`): ExamSimulationTranscript {
  return appendExamSimulationEvent(t, { id, at, command });
}
export function simulation(options: { form?: ExamForm; mode?: SimulationMode; id?: string; source?: PerformanceSource; monitoring?: 'COMPLETE' | 'UNKNOWN' } = {}): ExamSimulationTranscript {
  const monitoring = options.monitoring ?? 'COMPLETE';
  return createExamSimulation({ id: options.id ?? 'simulation', form: options.form ?? form(), mode: options.mode ?? 'STRICT_SIMULATION', created_at: 2_000,
    source: options.source ?? { kind: 'USER_EXECUTION', reference: 'fixture-user-stream' },
    monitoring: { assistance: monitoring, interruptions: monitoring, reference: monitoring === 'COMPLETE' ? 'fixture-runtime-instrumentation' : null } });
}
export function completed(options: Parameters<typeof simulation>[0] & { correct?: boolean; hint?: boolean; changes?: boolean } = {}): ExamSimulationTranscript {
  const t = simulation(options), events: ExamSimulationEvent[] = [];
  const push = (command: ExamSimulationCommand, at: number): void => { events.push({ id: `event-${events.length}`, sequence: events.length + 1,
    simulation_id: t.definition.id, form_id: t.definition.form.id, form_fingerprint: t.definition.form.fingerprint, command, at }); };
  push({ type: 'START' }, 2_000);
  let at = 2_000;
  for (const [i, q] of t.definition.form.questions.entries()) {
    push({ type: 'PULSE', engaged: true }, at + 20_000); at += 40_000;
    const a = actual(q, `${t.definition.id}-a${i}`, at, options.correct ?? true, options.hint && i === 0 ? 1 : 0, 40_000);
    push({ type: 'SUBMIT', attempt: options.changes && i === 0 ? { ...a, option_change_count: 1 } : a, replaces_attempt_id: null }, at);
  }
  return append({ definition: t.definition, events }, { type: 'COMPLETE' }, at);
}
export function beforeCompletion(t: ExamSimulationTranscript, commands: readonly ExamSimulationCommand[]): ExamSimulationTranscript {
  const end = t.events[t.events.length - 1]!; let next: ExamSimulationTranscript = { ...t, events: t.events.slice(0, -1) };
  for (const c of commands) next = append(next, c, end.at);
  return append(next, { type: 'COMPLETE' }, end.at);
}
/** Test-only expansion: does not modify or pretend to be the production question bank. */
export function syntheticPool(count = 80): readonly Question[] {
  const representatives = [...new Map(initialQuestions.map((q) => [q.family, q])).values()];
  return Array.from({ length: count }, (_, i) => { const q = representatives[i % representatives.length]!;
    return { ...q, id: `synthetic-${i}`, stem: `${q.stem} fixture ${i}`, ...(q.passage === undefined ? {} : { passage: `${q.passage} fixture ${i}` }) }; });
}
