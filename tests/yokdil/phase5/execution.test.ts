import { afterEach, describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { EvidenceDatabase, persistAttemptWithEvidence } from '../../../src/services/evidence/db';
import { persistLexicalReview, seedInitialVocabulary } from '../../../src/services/db';
import { createLearnerSkillVector } from '../../../src/types/learner';
import { skillEvidenceSchema } from '../../../src/services/evidence/validation';
import type { SessionCommand, SessionEventInput, SessionPlan } from '../../../src/types/session';
import { adaptAdaptiveSession, createAdaptiveSession, executeSessionCommand, exportSessionProgressToJson, extendAdaptiveSession, importSessionProgressFromJson,
  loadSessionLearnerSnapshot, pacingBlockEvidenceSchema, planSessionExtension, recordSessionLexicalReview, recordSessionQuestion,
  restoreAdaptiveSession, SessionDatabase, storeSessionPlan } from '../../../src/sessions';
import { actual, NOW, q, simplePlan } from './fixtures';

const opened: EvidenceDatabase[] = []; let counter = 0;
function database(): SessionDatabase { const db = new SessionDatabase(`phase5-${crypto.randomUUID()}`); opened.push(db); return db; }
afterEach(async () => { for (const db of opened.splice(0)) await db.delete(); });
async function snapshot(db: EvidenceDatabase): Promise<string> { return JSON.stringify(await Promise.all(db.tables.map(async (t) => ({ name: t.name, data: await t.toArray() as unknown[] })))); }
function event(command: SessionCommand, at: number, session = 'session'): SessionEventInput { return { id: `e-${counter++}`, session_id: session, at, command }; }
async function control(db: SessionDatabase, command: SessionCommand, at: number, session = 'session') {
  const state = await restoreAdaptiveSession(session, db);
  return executeSessionCommand(event(command, at, session), state.revision, initialQuestions, db);
}
async function start(db: SessionDatabase, plan: SessionPlan = simplePlan()) {
  await storeSessionPlan(plan, initialQuestions, db); await control(db, { type: 'START' }, 1_000, plan.session_id);
  return control(db, { type: 'START_BLOCK', block_id: plan.blocks[0]!.id }, 1_000, plan.session_id);
}
async function answer(db: SessionDatabase, index: number, at: number, correct = true, hints = 0, response = 20_000) {
  const a = actual(q(index), `a-${index}-${counter}`, at, correct, hints, response);
  const state = await restoreAdaptiveSession('session', db);
  const e = event({ type: 'QUESTION', block_id: 'session/b', attempt_id: a.id, item_id: a.question_id, retry_of: null }, at);
  const next = await recordSessionQuestion(e, state.revision, a, q(index), {}, db); return { a, e, next };
}
async function timed(db: SessionDatabase, options: { count?: number; completed?: number; assisted?: number; wrongLast?: number } = {}) {
  const count = options.count ?? 5, completed = options.completed ?? count;
  const plan = { ...simplePlan('TIMED_BLOCK', count), planned_minutes: Math.max(10, count), allocated_minutes: count,
    blocks: simplePlan('TIMED_BLOCK', count).blocks.map((b) => ({ ...b, planned_minutes: count })) };
  await start(db, plan); let at = 1_000;
  for (let i = 0; i < completed; i++) {
    await control(db, { type: 'PULSE', engaged: true }, at + 20_000);
    at += 40_000;
    await answer(db, i, at, i < completed - (options.wrongLast ?? 0), i < (options.assisted ?? 0) ? 1 : 0, 40_000);
  }
  const state = await restoreAdaptiveSession('session', db);
  const completion = event({ type: 'COMPLETE_BLOCK', block_id: 'session/b' }, at);
  await executeSessionCommand(completion, state.revision, initialQuestions, db);
  return { completion, revision: state.revision, at };
}

describe('Actual session execution', () => {
  it('keeps plans separate from actual durations and never credits completion as learning evidence', async () => {
    const db = database(); await start(db, simplePlan('REFLECTION'));
    const before = await loadSessionLearnerSnapshot(initialQuestions, 1_000, db);
    const state = await control(db, { type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 21_000);
    expect(state.blocks[0]?.planned_minutes).toBe(5); expect(state.blocks[0]?.actual_duration_ms).toBe(20_000);
    await control(db, { type: 'FINISH' }, 21_000);
    expect((await loadSessionLearnerSnapshot(initialQuestions, 21_000, db)).learner).toEqual(before.learner);
    expect(await db.solver_attempts.count()).toBe(0); expect(await db.pacing_evidence.count()).toBe(0);
  });
  it('skip creates no attempt or skill evidence and retains the original plan', async () => {
    const db = database(); const plan = simplePlan(); await start(db, plan);
    const state = await control(db, { type: 'SKIP_BLOCK', block_id: 'session/b', reason: 'USER' }, 2_000);
    expect(state.blocks[0]?.status).toBe('SKIPPED'); expect(await db.adaptive_sessions.get('session')).toEqual(plan);
    expect(await db.skill_evidence.count()).toBe(0); expect(await db.question_attempts.count()).toBe(0);
  });
  it('actual QuestionAttempt flows through frozen Phase 3 atomically and retry does not duplicate', async () => {
    const db = database(); await start(db);
    const result = await answer(db, 0, 21_000);
    expect(await db.solver_attempts.get(result.a.id)).toEqual(result.a); expect(await db.skill_evidence.count()).toBeGreaterThan(0);
    const before = await snapshot(db);
    await recordSessionQuestion(result.e, 2, result.a, q(), {}, db);
    expect(await snapshot(db)).toBe(before);
    expect(result.next.questions_attempted).toBe(1);
    expect((await db.adaptive_sessions.get('session'))?.blocks[0]?.planned_minutes).toBe(5);
  });
  it('stale revision rolls back both raw question and evidence writes', async () => {
    const db = database(); await start(db); const before = await snapshot(db);
    const a = actual(q(), 'stale', 21_000);
    await expect(recordSessionQuestion(event({ type: 'QUESTION', block_id: 'session/b', attempt_id: a.id, item_id: a.question_id, retry_of: null }, 21_000), 0, a, q(), {}, db)).rejects.toThrow('Stale');
    expect(await snapshot(db)).toBe(before);
  });
  it('does not allow completing an unanswered block or raw telemetry via control commands', async () => {
    const db = database(); await start(db);
    await expect(control(db, { type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 21_000)).rejects.toThrow('not completed');
    await expect(control(db, { type: 'QUESTION', block_id: 'session/b', item_id: q().id, attempt_id: 'fake', retry_of: null }, 21_000)).rejects.toThrow('actual-result');
  });
  it('updates lexical scheduling only after an actual completed review and deduplicates retry', async () => {
    const db = database(); await seedInitialVocabulary(db, 0);
    const word = await db.lexical_store.get('inhibit'); await start(db, simplePlan('LEXICAL_REVIEW'));
    expect(await db.lexical_store.get('inhibit')).toEqual(word);
    const review = { attempt_id: 'lexical-real', word_id: 'inhibit', question_id: 'recall', session_id: null, skill_ids: ['VOCAB_CONTEXT'] as const,
      review: { grade: 3 as const, reviewed_at: 21_000, response_time_ms: 20_000, context_id: 'science', assistance_used: false } };
    const e = event({ type: 'LEXICAL', block_id: 'session/b', attempt_id: review.attempt_id, item_id: 'inhibit', retry_of: null }, 21_000);
    const state = await recordSessionLexicalReview(e, 2, review, db);
    expect(state.lexical_reviews_completed).toBe(1); expect(await db.lexical_store.get('inhibit')).not.toEqual(word);
    const before = await snapshot(db); await recordSessionLexicalReview(e, 2, review, db); expect(await snapshot(db)).toBe(before);
  });
  it('restores active block metadata after closing and reopening while counting a long absence as pause', async () => {
    const db = database(); await start(db); await control(db, { type: 'PULSE', engaged: true }, 21_000);
    const name = db.name; db.close(); const reopened = new SessionDatabase(name); opened.push(reopened);
    const restored = await restoreAdaptiveSession('session', reopened); expect(restored.blocks[0]?.status).toBe('ACTIVE');
    const resumed = await control(reopened, { type: 'RESUME' }, 3_621_000);
    expect(resumed.actual_active_ms).toBe(20_000); expect(resumed.pause_ms).toBe(3_600_000);
    expect(await reopened.solver_attempts.count()).toBe(0);
  });
  it('restores exactly which items were actually submitted without saving an unfinished draft', async () => {
    const db = database(); await start(db, simplePlan('TIMED_BLOCK', 5));
    const submitted = await answer(db, 0, 21_000);
    const restored = await restoreAdaptiveSession('session', db);
    expect(restored.blocks[0]?.completed_question_ids).toEqual([q().id]);
    expect(restored.blocks[0]?.question_attempt_ids).toEqual([submitted.a.id]);
    expect(restored.blocks[0]?.question_ids.filter((id) => !restored.blocks[0]?.completed_question_ids.includes(id))).toHaveLength(4);
    expect(await db.timed_block_results.count()).toBe(0);
  });
  it('separates active time, explicit pause and wall clock time', async () => {
    const db = database(); await start(db);
    await control(db, { type: 'PAUSE' }, 21_000); await control(db, { type: 'RESUME' }, 81_000);
    const state = await control(db, { type: 'PULSE', engaged: true }, 101_000);
    expect(state.actual_active_ms).toBe(40_000); expect(state.pause_ms).toBe(60_000); expect(state.wall_clock_ms).toBe(100_000);
  });
  it('explicit retry is required for repeated questions and uses a new actual attempt', async () => {
    const db = database(); await start(db); const first = await answer(db, 0, 21_000, false);
    const second = actual(q(), 'retry', 41_000);
    await expect(recordSessionQuestion(event({ type: 'QUESTION', block_id: 'session/b', attempt_id: 'retry', item_id: q().id, retry_of: null }, 41_000), first.next.revision, second, q(), {}, db)).rejects.toThrow('explicit retry');
    const state = await recordSessionQuestion(event({ type: 'QUESTION', block_id: 'session/b', attempt_id: 'retry', item_id: q().id, retry_of: first.a.id }, 41_000), first.next.revision, second, q(), {}, db);
    expect(state.questions_attempted).toBe(2);
  });
  it('appends an extension after early completion without rewriting the original plan', async () => {
    const db = database(); const original = simplePlan('REFLECTION'); await start(db, original);
    await control(db, { type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 21_000); const complete = await control(db, { type: 'FINISH' }, 21_000);
    const extension = await planSessionExtension('session', 'extension', 5, 22_000, initialQuestions, db);
    expect(extension.allocated_minutes).toBeLessThanOrEqual(5);
    const state = await extendAdaptiveSession(event({ type: 'EXTEND', plan: extension }, 22_000), complete.revision, initialQuestions, db);
    expect(state.planned_minutes).toBe(10); expect(state.total_budget_minutes).toBe(15);
    expect(state.blocks[0]?.status).toBe('COMPLETED'); expect(await db.adaptive_sessions.get('session')).toEqual(original);
    expect(await db.skill_evidence.count()).toBe(0);
  });
  it('replans only at block boundaries, with append-safe adaptation', async () => {
    const db = database(); await start(db);
    await expect(planSessionExtension('session', 'extension', 5, 21_000, initialQuestions, db)).rejects.toThrow('boundary');
    await answer(db, 0, 21_000); expect(await db.session_events.toCollection().filter((e) => e.command.type === 'EXTEND').count()).toBe(0);
    await control(db, { type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 21_000);
    const extension = await planSessionExtension('session', 'extension', 5, 22_000, initialQuestions, db);
    const state = await restoreAdaptiveSession('session', db);
    const request = event({ type: 'EXTEND', plan: extension }, 22_000);
    const adapted = await adaptAdaptiveSession(request, state.revision, initialQuestions, db);
    expect(adapted.blocks[0]?.status).toBe('COMPLETED'); expect(adapted.blocks.slice(1).some((b) => b.question_ids.includes(q().id))).toBe(false);
    const before = await snapshot(db); await adaptAdaptiveSession(request, state.revision, initialQuestions, db); expect(await snapshot(db)).toBe(before);
  });
  it('supports abandoning a session without inventing completion evidence', async () => {
    const db = database(); await start(db); const state = await control(db, { type: 'ABANDON' }, 21_000);
    expect(state.status).toBe('ABANDONED'); expect(state.blocks[0]?.status).toBe('SKIPPED');
    await expect(control(db, { type: 'RESUME' }, 22_000)).rejects.toThrow('not active'); expect(await db.skill_evidence.count()).toBe(0);
  });
  it('rolls back all adaptation skips if the appended plan is invalid', async () => {
    const db = database(); const original = simplePlan('REFLECTION');
    const second = { ...original.blocks[0]!, id: 'session/second', candidate_ids: ['second'], planned_minutes: 2 };
    await start(db, { ...original, allocated_minutes: 7, blocks: [...original.blocks, second] });
    await control(db, { type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 21_000);
    const extension = await planSessionExtension('session', 'extension', 5, 22_000, initialQuestions, db);
    const malformed = { ...extension, blocks: extension.blocks.map((b) => ({ ...b, question_ids: ['missing-question'] })) };
    const before = await snapshot(db), state = await restoreAdaptiveSession('session', db);
    await expect(adaptAdaptiveSession(event({ type: 'EXTEND', plan: malformed }, 22_000), state.revision, initialQuestions, db)).rejects.toThrow();
    expect(await snapshot(db)).toBe(before);
    expect((await restoreAdaptiveSession('session', db)).blocks[1]?.status).toBe('PLANNED');
  });
  it('serializes concurrent exact completion retries into one journal event', async () => {
    const db = database(); await start(db, simplePlan('REFLECTION'));
    const done = event({ type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 21_000);
    await Promise.all([executeSessionCommand(done, 2, initialQuestions, db), executeSessionCommand(done, 2, initialQuestions, db)]);
    expect(await db.session_events.count()).toBe(3);
    expect((await restoreAdaptiveSession('session', db)).blocks[0]?.actual_duration_ms).toBe(20_000);
  });
});

describe('Qualified timed blocks and pacing extension', () => {
  it('a single slow question never creates pacing evidence', async () => {
    const db = database(); await start(db); await answer(db, 0, 301_000, true, 0, 300_000);
    await control(db, { type: 'COMPLETE_BLOCK', block_id: 'session/b' }, 301_000);
    expect(await db.pacing_evidence.count()).toBe(0);
    expect((await loadSessionLearnerSnapshot(initialQuestions, 301_000, db)).learner.PACING_STAMINA).toEqual(createLearnerSkillVector().PACING_STAMINA);
  });
  it('qualified completion creates bounded pacing evidence and the frozen v1 validator still rejects it', async () => {
    const db = database(); const done = await timed(db);
    const result = await db.timed_block_results.get('session/b'); const evidence = (await db.pacing_evidence.toArray())[0];
    expect(result?.qualified).toBe(true); expect(result?.completed_count).toBe(5);
    expect(evidence?.direction).toBe('POSITIVE'); expect(pacingBlockEvidenceSchema.safeParse(evidence).success).toBe(true);
    expect(skillEvidenceSchema.safeParse(evidence).success).toBe(false);
    expect(evidence?.strength).toBeGreaterThanOrEqual(0); expect(evidence?.strength).toBeLessThanOrEqual(1);
    expect(evidence?.reliability).toBeLessThanOrEqual(1);
    expect((await loadSessionLearnerSnapshot(initialQuestions, done.at, db)).learner.PACING_STAMINA.mastery).toBeGreaterThan(0);
  });
  it.each([{ completed: 1 }, { assisted: 3 }, { count: 10, completed: 5 }])('unqualified timed context %j creates no pacing evidence', async (options) => {
    const db = database(); await timed(db, options);
    expect((await db.timed_block_results.get('session/b'))?.qualified).toBe(false); expect(await db.pacing_evidence.count()).toBe(0);
  });
  it('does not infer timing weakness from inaccurate guessing, and requires sufficient degradation samples', async () => {
    const short = database(); await timed(short, { wrongLast: 3 });
    expect((await short.pacing_evidence.toArray())[0]?.direction).toBe('NEUTRAL');
    expect((await short.timed_block_results.get('session/b'))?.degradation_signal).toBeNull();
    const long = database(); await timed(long, { count: 8, wrongLast: 4 });
    expect((await long.timed_block_results.get('session/b'))?.degradation_signal).toEqual({ first_accuracy: 1, last_accuracy: 0, decline: 1 });
  });
  it('completes idempotently and keeps block evidence out of the frozen store', async () => {
    const db = database(); const done = await timed(db); const before = await snapshot(db);
    await executeSessionCommand(done.completion, done.revision, initialQuestions, db);
    expect(await snapshot(db)).toBe(before); expect(await db.timed_block_results.count()).toBe(1);
    expect((await db.skill_evidence.toArray()).some((e) => e.skill_id === 'PACING_STAMINA')).toBe(false);
  });
});

describe('Additive v5 storage and audited backups', () => {
  it('upgrades v4 to v5 preserving all seven existing stores byte-equivalent', async () => {
    const old = new EvidenceDatabase(`phase5-upgrade-${crypto.randomUUID()}`); await seedInitialVocabulary(old, 0);
    await old.daily_sessions.add({ id: 'legacy', date: '2026-10-03', time_zone: 'Europe/Istanbul', started_at: 0, ended_at: null, active_ms: 0, skills: createLearnerSkillVector() });
    await persistLexicalReview({ attempt_id: 'old-word', question_id: q().id, word_id: 'inhibit', session_id: 'legacy', skill_ids: ['VOCAB_CONTEXT'],
      review: { grade: 3, reviewed_at: 1_000, response_time_ms: 500, context_id: 'old', assistance_used: false } }, old);
    await persistAttemptWithEvidence(q(), { ...actual(q(), 'old-question', 2_000), confidence_level: 'HIGH' }, {}, old);
    const snapshots = await Promise.all(old.tables.map(async (table) => ({ name: table.name, json: JSON.stringify(await table.toArray()) })));
    expect(snapshots).toHaveLength(7); old.close(); const db = new SessionDatabase(old.name); opened.push(db); await db.open();
    expect(db.verno).toBe(5); expect(db.tables).toHaveLength(11);
    for (const table of snapshots) expect(JSON.stringify(await db.table(table.name).toArray())).toBe(table.json);
  });
  it('round trips active sessions, raw attempts, timed results and pacing, with idempotent import', async () => {
    const source = database(), target = database(); await timed(source);
    const json = await exportSessionProgressToJson(initialQuestions, source);
    await importSessionProgressFromJson(json, initialQuestions, target);
    expect(await snapshot(target)).toBe(await snapshot(source));
    await importSessionProgressFromJson(json, initialQuestions, target); expect(await snapshot(target)).toBe(await snapshot(source));
    expect(await restoreAdaptiveSession('session', target)).toEqual(await restoreAdaptiveSession('session', source));
  });
  it.each(['budget', 'event', 'result', 'pacing', 'reference'])('rejects corrupt %s imports atomically including legacy additions', async (kind) => {
    const source = database(), target = database(); await seedInitialVocabulary(source, 0); await timed(source);
    const raw = JSON.parse(await exportSessionProgressToJson(initialQuestions, source)) as {
      adaptive_sessions: SessionPlan[]; session_events: SessionEventInput[]; timed_block_results: { total_active_ms: number }[]; pacing_evidence: { strength: number }[];
    };
    if (kind === 'budget') raw.adaptive_sessions[0] = { ...raw.adaptive_sessions[0]!, planned_minutes: 1 };
    if (kind === 'event') raw.session_events[0] = { ...raw.session_events[0]!, at: NOW };
    if (kind === 'result') raw.timed_block_results[0]!.total_active_ms += 1;
    if (kind === 'pacing') raw.pacing_evidence[0]!.strength /= 2;
    if (kind === 'reference') raw.adaptive_sessions[0] = { ...raw.adaptive_sessions[0]!, blocks: raw.adaptive_sessions[0]!.blocks.map((b) => ({ ...b, question_ids: ['unknown'] })) };
    const before = await snapshot(target);
    await expect(importSessionProgressFromJson(JSON.stringify(raw), initialQuestions, target)).rejects.toThrow();
    expect(await snapshot(target)).toBe(before);
  });
  it('creates a real-content plan from an audited snapshot without writing learning evidence', async () => {
    const db = database(); const state = await createAdaptiveSession({ id: 'auto', session_id: 'auto', mode: 'EMERGENCY', as_of: NOW }, initialQuestions, db);
    expect(state.status).toBe('PLANNED'); expect(state.blocks.length).toBeGreaterThan(0);
    expect(await db.solver_attempts.count()).toBe(0); expect(await db.skill_evidence.count()).toBe(0); expect(await db.pacing_evidence.count()).toBe(0);
  });
  it('retries creation without replanning an already started session', async () => {
    const db = database(); const request = { id: 'auto', session_id: 'auto', mode: 'EMERGENCY' as const, as_of: NOW };
    await createAdaptiveSession(request, initialQuestions, db);
    await control(db, { type: 'START' }, NOW, 'auto'); const before = await snapshot(db);
    const restored = await createAdaptiveSession(request, initialQuestions, db);
    expect(restored.status).toBe('ACTIVE'); expect(await snapshot(db)).toBe(before);
    await expect(createAdaptiveSession({ ...request, available_minutes: 20 }, initialQuestions, db)).rejects.toThrow('conflict');
  });
  it('rejects conflicting manually supplied block IDs across sessions before execution', async () => {
    const db = database(); const first = simplePlan(); await storeSessionPlan(first, initialQuestions, db);
    await expect(storeSessionPlan({ ...first, id: 'other', session_id: 'other' }, initialQuestions, db)).rejects.toThrow('another session');
    expect(await db.adaptive_sessions.count()).toBe(1);
  });
});
