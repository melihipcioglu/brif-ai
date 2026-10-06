import { afterEach, describe, expect, it } from 'vitest';
import { questionAttemptSchema } from '../../../src/services/questions/validation';
import { evidenceRunSchema, skillEvidenceSchema } from '../../../src/services/evidence/validation';
import { sessionEventSchema, sessionPlanSchema } from '../../../src/services/session/validation';
import { deriveTimedBlockResult, extractPacingBlockEvidence } from '../../../src/services/session/pacing';
import { projectAdaptiveSession } from '../../../src/services/session/execution';
import { SessionDatabase, storeSessionPlan, recordSessionQuestion, executeSessionCommand, extendAdaptiveSession, importSessionProgressFromJson, exportSessionProgressToJson } from '../../../src/services/session/db';
import { loadPerformanceEstimate } from '../../../src/services/performance/db';
import { estimatePerformance } from '../../../src/services/performance/estimate';
import type { PerformanceSnapshot } from '../../../src/types/performance';
import type { SessionEvent, PacingBlockEvidence, TimedBlockResult } from '../../../src/types/session';
import { fixture } from './fixtures';

const opened: SessionDatabase[] = []; let number = 0;
function database(name = `phase6-user-${++number}`): SessionDatabase { const db = new SessionDatabase(name); opened.push(db); return db; }
afterEach(async () => { for (const db of opened.splice(0)) await db.delete(); });
async function contents(db: SessionDatabase): Promise<string> { return JSON.stringify(await Promise.all(db.tables.map(async (t) => ({ name: t.name, rows: await t.toArray() as unknown[] })))); }
async function execute(input: PerformanceSnapshot, db: SessionDatabase): Promise<void> {
  const plans = input.plans.map((p) => sessionPlanSchema.parse(p));
  for (const plan of plans) {
    await storeSessionPlan(plan, input.questions, db);
    const events = input.events.map((e) => sessionEventSchema.parse(e)).filter((e) => e.session_id === plan.session_id).sort((a, b) => a.sequence - b.sequence);
    for (const event of events) {
      const { sequence, attempt_ref: _ref, ...command } = event;
      if (event.command.type === 'QUESTION') {
        const id = event.command.attempt_id;
        const a = input.attempts.map((a) => questionAttemptSchema.parse(a)).find((a) => a.id === id)!;
        const q = input.questions.find((q) => q.id === a.question_id)!;
        const run = input.evidence_runs.map((r) => evidenceRunSchema.parse(r)).find((r) => r.attempt_id === id)!;
        await recordSessionQuestion(command, sequence - 1, a, q, run.context, db);
      } else if (event.command.type === 'EXTEND') await extendAdaptiveSession(command, sequence - 1, input.questions, db);
      else await executeSessionCommand(command, sequence - 1, input.questions, db);
    }
  }
}
function derived(input: PerformanceSnapshot): PerformanceSnapshot {
  const events = input.events.map((e) => sessionEventSchema.parse(e)), attempts = input.attempts.map((a) => questionAttemptSchema.parse(a));
  const results: TimedBlockResult[] = [], pacing: PacingBlockEvidence[] = [];
  for (const raw of input.plans) {
    const plan = sessionPlanSchema.parse(raw), local = events.filter((e) => e.session_id === plan.session_id), state = projectAdaptiveSession(plan, local);
    for (const b of state.blocks) if (b.type === 'TIMED_BLOCK' && b.status === 'COMPLETED') {
      const r = deriveTimedBlockResult(state.id, b, local, attempts), pe = extractPacingBlockEvidence(r, attempts);
      results.push(r); if (pe) pacing.push(pe);
    }
  }
  return { ...input, timed_results: results, pacing_evidence: pacing };
}

describe('Actual Phase 5 -> Phase 6 integration', () => {
  it('reads qualified persisted execution without changing any of the eleven tables', async () => {
    const input = fixture(), db = database(); await execute(input, db);
    const before = await contents(db), version = db.verno;
    const result = await loadPerformanceEstimate(input.questions, input.as_of, input.source, db);
    expect(result.observed.eligible_question_count).toBe(5);
    expect(result).toEqual(estimatePerformance(input)); expect(await contents(db)).toBe(before);
    expect(db.verno).toBe(version); expect(db.tables).toHaveLength(11);
  });
  it('resumes after persisted interruption without double counting completed questions', async () => {
    const input = fixture(), db = database();
    const original = input.events.map((e) => sessionEventSchema.parse(e));
    const index = original.findIndex((e) => e.command.type === 'QUESTION');
    const anchor = original[index]!;
    const gap = 600_000;
    const extra: SessionEvent[] = [
      { id: 'pause', session_id: anchor.session_id, at: anchor.at, sequence: 1, command: { type: 'PAUSE' } },
      { id: 'resume', session_id: anchor.session_id, at: anchor.at + gap, sequence: 1, command: { type: 'RESUME' } },
    ];
    const events = [...original.slice(0, index + 1), ...extra, ...original.slice(index + 1).map((e) => ({ ...e, at: e.at + gap }))].map((e, i) => ({ ...e, sequence: i + 1 }));
    const shifted = derived({ ...input, events,
      attempts: input.attempts.map((raw) => { const a = questionAttemptSchema.parse(raw); return a.attempted_at <= anchor.at ? a : { ...a, attempted_at: a.attempted_at + gap }; }),
      evidence_runs: input.evidence_runs.map((raw) => { const r = evidenceRunSchema.parse(raw); return r.created_at <= anchor.at ? r : { ...r, created_at: r.created_at + gap }; }),
      skill_evidence: input.skill_evidence.map((raw) => { const e = skillEvidenceSchema.parse(raw); return e.created_at <= anchor.at ? e : { ...e, created_at: e.created_at + gap }; }) });
    await execute({ ...shifted, events: events.slice(0, index + 2) }, db); db.close(); await db.open();
    expect((await loadPerformanceEstimate(input.questions, input.as_of, input.source, db)).observed.eligible_question_count).toBe(0);
    await execute(shifted, db);
    const result = await loadPerformanceEstimate(input.questions, input.as_of, input.source, db);
    expect(result.observed.eligible_question_count).toBe(5);
    expect((await db.timed_block_results.toArray())[0]?.total_active_ms).toBe(200_000);
  });
  it('extension appends another qualified block without counting the first twice', async () => {
    const input = fixture({ count: 10 }), plans = input.plans.map((p) => sessionPlanSchema.parse(p));
    const first = plans[0]!, second = plans[1]!;
    const firstEvents = input.events.map((e) => sessionEventSchema.parse(e)).filter((e) => e.session_id === first.session_id);
    const extension = { ...second, session_id: first.session_id };
    const extend: SessionEvent = { id: 'extension', session_id: first.session_id, sequence: 0, at: second.created_at, command: { type: 'EXTEND', plan: extension } };
    const tail = input.events.map((e) => sessionEventSchema.parse(e)).filter((e) => e.session_id === second.session_id && e.command.type !== 'START').map((e) => ({ ...e, session_id: first.session_id }));
    const events = [...firstEvents, extend, ...tail].map((e, i) => ({ ...e, sequence: i + 1 }));
    const combined = derived({ ...input, plans: [first], events });
    const db = database(); await execute(combined, db);
    const result = await loadPerformanceEstimate(input.questions, input.as_of, input.source, db);
    expect(result.observed.eligible_question_count).toBe(10); expect(result.observed.qualified_block_count).toBe(2);
    expect(result.observed_coverage.session_count).toBe(1);
  });
  it('an interrupted active block contributes nothing even after actual answers', async () => {
    const input = fixture(); const events = input.events.map((e) => sessionEventSchema.parse(e)).filter((e) => e.command.type !== 'COMPLETE_BLOCK' && e.command.type !== 'FINISH');
    const interrupted = derived({ ...input, events }), db = database(); await execute(interrupted, db);
    const result = await loadPerformanceEstimate(input.questions, input.as_of, input.source, db);
    expect(result.observed.eligible_question_count).toBe(0); expect(result.exam_range).toBeNull();
  });
  it('an abandoned unqualified block adds no observations', async () => {
    const input = fixture(), original = input.events.map((e) => sessionEventSchema.parse(e));
    const events = original.filter((e) => e.command.type !== 'COMPLETE_BLOCK' && e.command.type !== 'FINISH');
    const last = events[events.length - 1]!;
    events.push({ id: 'abandon', session_id: last.session_id, sequence: last.sequence + 1, at: last.at, command: { type: 'ABANDON' } });
    const abandoned = derived({ ...input, events });
    expect(estimatePerformance(abandoned).observed.eligible_question_count).toBe(0);
  });
  it('completed qualified block is retained when the surrounding session is abandoned', async () => {
    const input = fixture(); const events = input.events.map((e) => sessionEventSchema.parse(e)).map((e) => e.command.type === 'FINISH' ? { ...e, command: { type: 'ABANDON' as const } } : e);
    const abandoned = derived({ ...input, events });
    expect(estimatePerformance(abandoned).observed.eligible_question_count).toBe(5);
  });
  it('a clock gap cannot manufacture sufficient active time from planned duration', () => {
    const input = fixture();
    const events = input.events.map((e) => sessionEventSchema.parse(e)).filter((e) => e.command.type !== 'PULSE').map((e, i) => ({ ...e, sequence: i + 1 }));
    const slow = derived({ ...input, events });
    const result = estimatePerformance(slow);
    expect(result.observed.eligible_question_count).toBe(0);
    expect(result.provenance.exclusions.some((e) => e.reason === 'INSUFFICIENT_TIME')).toBe(true);
  });
  it('round-trip imported real history produces the same observations, with explicit import provenance', async () => {
    const input = fixture(), a = database(), b = database(); await execute(input, a);
    await importSessionProgressFromJson(await exportSessionProgressToJson(input.questions, a), input.questions, b);
    const imported = await loadPerformanceEstimate(input.questions, input.as_of, { kind: 'IMPORTED_USER_EXECUTION', reference: 'user-backup' }, b);
    expect(imported.observed).toEqual(estimatePerformance(input).observed);
    expect(imported.provenance.source.kind).toBe('IMPORTED_USER_EXECUTION');
  });
  it('corrupt persisted results fail closed without rewriting anything', async () => {
    const input = fixture(), db = database(); await execute(input, db);
    const row = (await db.timed_block_results.toArray())[0]!;
    await db.timed_block_results.put({ ...row, correct_count: row.correct_count - 1 });
    const before = await contents(db), result = await loadPerformanceEstimate(input.questions, input.as_of, input.source, db);
    expect(result.blockers).toContain('INVALID_SOURCE_RECORDS'); expect(await contents(db)).toBe(before);
  });
  it('known demo database is refused even if the caller labels it user execution', async () => {
    const input = fixture(), db = database('yokdil-fen-phase2-demo'); await execute(input, db);
    const result = await loadPerformanceEstimate(input.questions, input.as_of, input.source, db);
    expect(result.observed.eligible_question_count).toBe(0); expect(result.blockers).toContain('SOURCE_NOT_VERIFIED');
  });
});
