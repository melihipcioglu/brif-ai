import { afterEach, describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { analyzeExamPool, appendExamSimulationEvent, projectExamSimulation, qualifyExamSimulation, selectCalibrationPerformanceEvidence } from '../../../src/exam';
import { SessionDatabase } from '../../../src/services/session/db';
import { seedInitialVocabulary } from '../../../src/services/db';
import { persistAttemptWithEvidence } from '../../../src/services/evidence/db';
import { actual } from '../phase5/fixtures';
import type { ExamSimulationTranscript } from '../../../src/types/exam';
import { append, blueprint, completed, context, controlled, simulation } from './fixtures';

const databases: SessionDatabase[] = [];
afterEach(async () => { for (const db of databases.splice(0)) await db.delete(); });

describe('Calibration boundary checks', () => {
  it('stale inventory observation does not prove current unseen status', () => {
    const result = analyzeExamPool(blueprint(), initialQuestions, { ...controlled(), as_of: 2_000 });
    if (result.status === 'INVALID_BLUEPRINT') throw new Error('Unexpected blueprint');
    expect(result.report.novelty.UNKNOWN).toBe(5); expect(result.report.novelty.UNSEEN).toBe(0);
  });
  it('lexical click telemetry alone excludes calibration', () => {
    const t = completed();
    const events = t.events.map((e) => {
      if (e.command.type !== 'SUBMIT') return e;
      const question = t.definition.form.questions.find((q) => e.command.type === 'SUBMIT' && q.id === e.command.attempt.question_id)!;
      const word = question.lexical_ids?.[0];
      return word === undefined ? e : { ...e, command: { ...e.command, attempt: { ...e.command.attempt, words_clicked: [word] } } };
    });
    const result = qualifyExamSimulation({ ...t, events }, 202_000);
    expect(result.reasons).toContain('ASSISTANCE'); expect(result.qualified).toBe(false);
  });
  it('a silent attempt content change conflicts even under the same attempt ID', () => {
    const t = completed(), event = [...t.events].reverse().find((e) => e.command.type === 'SUBMIT')!;
    if (event.command.type !== 'SUBMIT') throw new Error('Fixture');
    const command = { ...event.command, attempt: { ...event.command.attempt, response_time_ms: 20_000 } };
    expect(() => append({ ...t, events: t.events.slice(0, -1) }, command, event.at)).toThrow('conflict');
  });
  it('portable transcript JSON can resume and preserves its original form', () => {
    const t = completed(), partial: ExamSimulationTranscript = { ...t, events: t.events.slice(0, 3) };
    const restored = JSON.parse(JSON.stringify(partial)) as ExamSimulationTranscript;
    expect(projectExamSimulation(restored, restored.events[2]!.at).answers).toHaveLength(1);
    let continued = restored;
    for (const e of t.events.slice(3)) continued = appendExamSimulationEvent(continued, { id: e.id, at: e.at, command: e.command });
    expect(qualifyExamSimulation(continued, 202_000)).toEqual(qualifyExamSimulation(t, 202_000));
  });
  it('Phase 5 events cannot be relabeled as a strict exam journal', () => {
    const t = completed(), state = projectExamSimulation(t, 202_000);
    const relabeled = { ...t, events: state.execution.events } as unknown as ExamSimulationTranscript;
    expect(qualifyExamSimulation(relabeled, 202_000).tier).toBe('NOT_ELIGIBLE');
  });
  it('form mutations and misleading COMPLETE flags are rejected', () => {
    const t = completed();
    const corrupt = { ...t, definition: { ...t.definition, form: { ...t.definition.form, question_ids: [] } } };
    expect(qualifyExamSimulation(corrupt, 202_000).tier).toBe('NOT_ELIGIBLE');
  });
  it('submission during pause and heartbeat-based implicit resume are invalid', () => {
    let t = append(simulation(), { type: 'START' }, 2_000); t = append(t, { type: 'PAUSE' }, 22_000);
    const a = actual(t.definition.form.questions[0]!, 'a', 42_000);
    expect(() => append(t, { type: 'SUBMIT', attempt: a, replaces_attempt_id: null }, 42_000)).toThrow('inactive');
    expect(() => append(t, { type: 'PULSE', engaged: true }, 42_000)).toThrow('resume');
  });
  it('no simulation/adapter computation changes existing v5 progress, learner or schema', async () => {
    const db = new SessionDatabase('phase7-existing-progress'); databases.push(db);
    await seedInitialVocabulary(db); const q = initialQuestions[0]!;
    await persistAttemptWithEvidence(q, actual(q, 'old-study-attempt', 1_000), {}, db);
    const snapshot = async () => JSON.stringify(await Promise.all(db.tables.map(async (t) => ({ name: t.name, rows: await t.toArray() as unknown[] }))));
    const before = await snapshot(), version = db.verno;
    const result = selectCalibrationPerformanceEvidence([completed()], 202_000);
    expect(result.evidence.records).toHaveLength(5); expect(await snapshot()).toBe(before);
    expect(db.verno).toBe(version); expect(db.tables).toHaveLength(11);
  });
  it('input pool and history order do not change exposure classification', () => {
    const ctx = { ...context, exposures: [...controlled().exposures].reverse() };
    expect(analyzeExamPool(blueprint(), [...initialQuestions].reverse(), ctx)).toEqual(analyzeExamPool(blueprint(), initialQuestions, controlled()));
  });
});
