import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { appendExamSimulationEvent, buildExamForm, projectExamSimulation, qualifyExamSimulation } from '../../../src/exam';
import { actual } from '../phase5/fixtures';
import type { ExamSimulationTranscript } from '../../../src/types/exam';
import { append, beforeCompletion, blueprint, completed, context, controlled, form, simulation } from './fixtures';

describe('Exam simulation journal', () => {
  it('starts and completes from actual QuestionAttempts with separate wall and active clocks', () => {
    const t = completed(), state = projectExamSimulation(t, 202_000);
    expect(state.status).toBe('COMPLETED'); expect(state.actual_elapsed_ms).toBe(200_000); expect(state.active_elapsed_ms).toBe(200_000);
    expect(state.answers).toHaveLength(5); expect(state.submitted_attempt_ids).toHaveLength(5);
    expect(t.definition.session_kind).toBe('EXAM_SIMULATION');
  });
  it('no execution means no observed success or calibration', () => {
    const t = simulation(), state = projectExamSimulation(t, 2_000), result = qualifyExamSimulation(t, 2_000);
    expect(state.status).toBe('PLANNED'); expect(result.qualified).toBe(false); expect(result.question_count).toBe(0);
  });
  it('complete exactly at the time limit is allowed', () => {
    const t = completed({ form: form(blueprint({ time_limit_ms: 200_000 })) });
    expect(qualifyExamSimulation(t, 202_000).qualified).toBe(true);
  });
  it('completion one millisecond late is timed out, with existing answers retained', () => {
    const t = completed({ form: form(blueprint({ time_limit_ms: 200_000 })) });
    const late = append({ ...t, events: t.events.slice(0, -1) }, { type: 'COMPLETE' }, 202_001);
    expect(projectExamSimulation(late, 202_001).status).toBe('TIMED_OUT');
    const q = qualifyExamSimulation(late, 202_001); expect(q.qualified).toBe(false); expect(q.question_count).toBe(5); expect(q.reasons).toContain('TIME_LIMIT');
  });
  it('strict active simulation times out by explicit projection time without a browser timer', () => {
    const t = append(simulation(), { type: 'START' }, 2_000);
    const state = projectExamSimulation(t, 302_001);
    expect(state.status).toBe('TIMED_OUT'); expect(state.active_elapsed_ms).toBe(0); expect(state.actual_elapsed_ms).toBe(300_000);
  });
  it('timeout cannot be declared early and late submissions cannot bypass strict deadline', () => {
    const t = append(simulation(), { type: 'START' }, 2_000);
    expect(() => append(t, { type: 'TIMEOUT' }, 2_001)).toThrow();
    expect(() => append(t, { type: 'SUBMIT', attempt: actual(t.definition.form.questions[0]!, 'late', 302_001), replaces_attempt_id: null }, 302_001)).toThrow('deadline');
    expect(projectExamSimulation(append(t, { type: 'TIMEOUT' }, 302_000), 302_000).status).toBe('TIMED_OUT');
  });
  it('pause/resume preserves practice execution but loses calibration', () => {
    const t = beforeCompletion(completed(), [{ type: 'PAUSE' }, { type: 'RESUME' }]);
    expect(projectExamSimulation(t, 202_000).answers).toHaveLength(5);
    expect(qualifyExamSimulation(t, 202_000).reasons).toContain('PAUSED');
  });
  it('long interruption resumes without turning pause duration into active work', () => {
    let t = append(simulation({ mode: 'PRACTICE_SIMULATION' }), { type: 'START' }, 2_000);
    t = append(t, { type: 'PULSE', engaged: true }, 22_000);
    t = append(t, { type: 'INTERRUPT' }, 22_000); t = append(t, { type: 'RESUME' }, 622_000);
    const state = projectExamSimulation(t, 622_000);
    expect(state.actual_elapsed_ms).toBe(620_000); expect(state.active_elapsed_ms).toBe(20_000);
    expect(state.conditions).toContain('INTERRUPTED');
  });
  it('resume requires an explicit prior pause/interruption', () => {
    expect(() => append(append(simulation(), { type: 'START' }, 2_000), { type: 'RESUME' }, 3_000)).toThrow('Resume');
  });
  it('silent heartbeat gap disqualifies strict timing even if enough active time remains', () => {
    const original = completed();
    const end = original.events[original.events.length - 1]!;
    const t = append({ ...original, events: original.events.slice(0, -1) }, { type: 'COMPLETE' }, end.at + 31_000);
    const q = qualifyExamSimulation(t, end.at + 31_000);
    expect(q.reasons).toContain('INTERRUPTED'); expect(q.qualified).toBe(false);
  });
  it('explicit extension keeps form identity and forfeits calibration', () => {
    const t = beforeCompletion(completed(), [{ type: 'EXTEND_TIME', additional_ms: 60_000 }]);
    const state = projectExamSimulation(t, 202_000);
    expect(state.time_limit_ms).toBe(360_000); expect(state.form_id).toBe(t.definition.form.id);
    expect(qualifyExamSimulation(t, 202_000).reasons).toContain('TIME_EXTENDED');
  });
  it('abandonment cannot produce completed calibration', () => {
    const original = completed(), t = append({ ...original, events: original.events.slice(0, -1) }, { type: 'ABANDON' }, 202_000);
    expect(projectExamSimulation(t, 202_000).status).toBe('ABANDONED'); expect(qualifyExamSimulation(t, 202_000).completion_valid).toBe(false);
  });
  it('incomplete completion cannot manufacture unanswered results', () => {
    const original = completed(); let t: ExamSimulationTranscript = { ...original, events: original.events.slice(0, -3) };
    t = append(t, { type: 'COMPLETE' }, 162_000);
    const q = qualifyExamSimulation(t, 162_000); expect(q.question_count).toBe(4); expect(q.reasons).toContain('INCOMPLETE'); expect(q.evidence).toBeNull();
  });
  it('strict final answers are immutable; practice replacement is explicitly linked', () => {
    const strict = completed(), first = strict.definition.form.questions[0]!;
    const a = actual(first, 'replacement', 202_000, false);
    const old = strict.events.find((e) => e.command.type === 'SUBMIT')!;
    const oldId = old.command.type === 'SUBMIT' ? old.command.attempt.id : '';
    expect(() => append({ ...strict, events: strict.events.slice(0, -1) }, { type: 'SUBMIT', attempt: a, replaces_attempt_id: oldId }, 202_000)).toThrow('immutable');
    const practice = completed({ mode: 'PRACTICE_SIMULATION' });
    const revised = append({ ...practice, events: practice.events.slice(0, -1) }, { type: 'SUBMIT', attempt: a, replaces_attempt_id: oldId }, 202_000);
    expect(projectExamSimulation(revised, 202_000).answers.find((r) => r.id === a.id)?.is_correct).toBe(false);
    expect(qualifyExamSimulation(revised, 202_000).evidence).toBeNull();
  });
  it('exact event retry and exact submission replay do not create extra attempts', () => {
    const t = completed(), last = t.events[t.events.length - 1]!;
    const retried = appendExamSimulationEvent(t, { id: last.id, at: last.at, command: last.command });
    expect(retried).toEqual(t);
    const lastAnswer = [...t.events].reverse().find((e) => e.command.type === 'SUBMIT')!;
    const duplicate = beforeCompletion(t, [lastAnswer.command]);
    expect(projectExamSimulation(duplicate, 202_000).submitted_attempt_ids).toHaveLength(5);
    expect(qualifyExamSimulation(duplicate, 202_000).qualified).toBe(true);
  });
  it('duplicated identical events and array reordering preserve semantic output', () => {
    const t = completed();
    const a = qualifyExamSimulation(t, 202_000), b = qualifyExamSimulation({ ...t, events: [...t.events, t.events[0]!].reverse() }, 202_000);
    expect(a).toEqual(b);
  });
  it('event identity conflicts and forged form binding are rejected', () => {
    const t = completed(), e = t.events[0]!;
    expect(qualifyExamSimulation({ ...t, events: [...t.events, { ...e, at: 3_000 }] }, 202_000).tier).toBe('NOT_ELIGIBLE');
    expect(qualifyExamSimulation({ ...t, events: [{ ...e, form_fingerprint: 'changed' }, ...t.events.slice(1)] }, 202_000).tier).toBe('NOT_ELIGIBLE');
  });
  it('a corrupt answer key/outcome or sequence cannot enter calibration', () => {
    const t = completed();
    const changed = t.events.map((e) => e.command.type === 'SUBMIT' ? { ...e, command: { ...e.command, attempt: { ...e.command.attempt, is_correct: false } } } : e);
    expect(qualifyExamSimulation({ ...t, events: changed }, 202_000).tier).toBe('NOT_ELIGIBLE');
    expect(qualifyExamSimulation({ ...t, events: t.events.map((e) => ({ ...e, sequence: e.sequence + 1 })) }, 202_000).tier).toBe('NOT_ELIGIBLE');
  });
  it('a partial form may execute only in practice mode', () => {
    const result = buildExamForm({ id: 'partial', blueprint: blueprint({ total_questions: 6, family_targets: { GAP_FILL: 6 } }), questions: initialQuestions, context: controlled(), allow_partial: true });
    expect(result.form).not.toBeNull();
    expect(() => simulation({ form: result.form! })).toThrow('complete form');
    expect(qualifyExamSimulation(completed({ form: result.form!, mode: 'PRACTICE_SIMULATION' }), 202_000).reasons).toContain('PARTIAL_FORM');
  });
  it('unknown exposure remains unknown through execution', () => {
    const t = completed({ form: form(blueprint(), context) });
    expect(qualifyExamSimulation(t, 202_000).novelty.UNKNOWN).toBe(5);
  });
  it('does not mutate a transcript during projection or qualification', () => {
    const t = completed(), before = JSON.stringify(t);
    projectExamSimulation(t, 202_000); qualifyExamSimulation(t, 202_000);
    expect(JSON.stringify(t)).toBe(before); expect(Object.isFrozen(t)).toBe(true);
  });
});
