import type { Table } from 'dexie';
import { z } from 'zod';
import type { EvidenceContext } from '../../types/evidence';
import type { LearnerSkillVector } from '../../types/learner';
import type { Question, QuestionAttempt } from '../../types/question';
import type { AdaptiveStudySession, PacingBlockEvidence, SessionConfig, SessionEvent, SessionEventInput, SessionPlan, TimedBlockResult } from '../../types/session';
import type { EvidenceCoverageMap } from '../../types/priority';
import { persistLexicalReview, type PersistReviewInput } from '../db';
import { EvidenceDatabase, exportEvidenceProgressToJson, importEvidenceProgressFromJson, loadLearnerSkillVector, persistAttemptWithEvidence } from '../evidence/db';
import { canonicalEvidence } from '../evidence/validation';
import { deepFreeze } from '../questions/attempts';
import { questionAttemptSchema, questionSchema } from '../questions/validation';
import { deriveEvidenceCoverage } from '../priority/coverage';
import { lexicalAttemptSchema } from '../validation';
import { SESSION_V1 } from './calibration';
import { buildSessionCandidatePool } from './candidates';
import { projectAdaptiveSession } from './execution';
import { deriveTimedBlockResult, extractPacingBlockEvidence, overlayPacingModel, pacingBlockEvidenceSchema } from './pacing';
import { planDailySession, type SessionPlanningRequest } from './planner';
import { sessionConfigSchema, sessionEventInputSchema, sessionEventSchema, sessionPlanSchema } from './validation';

/** Additive v5. The existing seven tables and all prior migrations retain their original declarations. */
export class SessionDatabase extends EvidenceDatabase {
  readonly adaptive_sessions: Table<SessionPlan, string>;
  readonly session_events: Table<SessionEvent, string>;
  readonly timed_block_results: Table<TimedBlockResult, string>;
  readonly pacing_evidence: Table<PacingBlockEvidence, string>;
  constructor(name = 'yokdil-fen-80-plus') {
    super(name);
    this.version(5).stores({ adaptive_sessions: '&session_id, id, created_at',
      session_events: '&id, &[session_id+sequence], session_id, &attempt_ref',
      timed_block_results: '&block_id, session_id', pacing_evidence: '&id, &block_id, session_id, created_at' });
    this.adaptive_sessions = this.table('adaptive_sessions'); this.session_events = this.table('session_events');
    this.timed_block_results = this.table('timed_block_results'); this.pacing_evidence = this.table('pacing_evidence');
  }
}
export const sessionDb = new SessionDatabase();
async function append<T>(table: Table<T, string>, id: string, value: T): Promise<void> {
  const old = await table.get(id);
  if (old !== undefined) { if (canonicalEvidence(old) !== canonicalEvidence(value)) throw new RangeError('Append-only session ID conflict'); }
  else await table.add(value);
}
async function journal(id: string, db: SessionDatabase): Promise<{ plan: SessionPlan; events: SessionEvent[] }> {
  const raw = await db.adaptive_sessions.get(id); if (raw === undefined) throw new RangeError('Unknown adaptive session');
  return { plan: sessionPlanSchema.parse(raw), events: (await db.session_events.where('session_id').equals(id).sortBy('sequence')).map((e) => sessionEventSchema.parse(e)) };
}
export async function restoreAdaptiveSession(id: string, database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  return database.transaction('r', [database.adaptive_sessions, database.session_events], async () => {
    const { plan, events } = await journal(id, database); return projectAdaptiveSession(plan, events);
  });
}
async function checkPlanContent(plan: SessionPlan, questions: readonly Question[], db: SessionDatabase): Promise<void> {
  const bank = new Map(questions.map((q) => { const parsed = questionSchema.parse(q); return [parsed.id, parsed] as const; }));
  if (bank.size !== questions.length) throw new RangeError('Duplicate question catalog');
  for (const b of plan.blocks) {
    if (b.question_ids.some((id) => !bank.has(id))) throw new RangeError('Phantom question in plan');
    for (const id of b.lexical_ids) if (await db.lexical_store.get(id) === undefined) throw new RangeError('Phantom lexical item in plan');
  }
  const otherPlans = (await db.adaptive_sessions.toArray()).filter((p) => p.session_id !== plan.session_id);
  const otherExtensions = (await db.session_events.toArray()).filter((e) => e.session_id !== plan.session_id && e.command.type === 'EXTEND');
  const occupied = new Set([...otherPlans.flatMap((p) => p.blocks.map((b) => b.id)), ...otherExtensions.flatMap((e) => e.command.type === 'EXTEND' ? e.command.plan.blocks.map((b) => b.id) : [])]);
  if (plan.blocks.some((b) => occupied.has(b.id))) throw new RangeError('Block ID belongs to another session');
}
/** Persist an immutable plan only. It creates no attempts, block results or learner evidence. */
export async function storeSessionPlan(input: SessionPlan, questions: readonly Question[], database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  const plan = sessionPlanSchema.parse(input);
  return database.transaction('rw', database.tables, async () => {
    await checkPlanContent(plan, questions, database); await append(database.adaptive_sessions, plan.session_id, plan);
    return restoreAdaptiveSession(plan.session_id, database);
  });
}

async function validateActualLinks(events: readonly SessionEvent[], db: SessionDatabase): Promise<void> {
  for (const e of events) {
    const cmd = e.command;
    if (cmd.type === 'QUESTION') {
      const a = questionAttemptSchema.parse(await db.solver_attempts.get(cmd.attempt_id));
      if (a.question_id !== cmd.item_id || a.attempted_at !== e.at || a.session_id !== null || await db.evidence_runs.get(a.id) === undefined) throw new RangeError('Invalid actual question linkage');
    } else if (cmd.type === 'LEXICAL') {
      const a = lexicalAttemptSchema.parse(await db.question_attempts.get(cmd.attempt_id));
      if (a.lexical_ids.length !== 1 || a.lexical_ids[0] !== cmd.item_id || a.attempted_at !== e.at || a.session_id !== null) throw new RangeError('Invalid actual lexical linkage');
    }
  }
}
/** Reconstruct all derived results from immutable events and authoritative attempts. */
async function auditSessions(questions: readonly Question[], db: SessionDatabase): Promise<readonly { result: TimedBlockResult; evidence: PacingBlockEvidence }[]> {
  const plans = await db.adaptive_sessions.toArray(), allEvents = await db.session_events.toArray();
  const attempts = await db.solver_attempts.toArray();
  const resultIds = new Set<string>(), evidenceIds = new Set<string>(); const records: { result: TimedBlockResult; evidence: PacingBlockEvidence }[] = [];
  const planIds = new Set(plans.map((p) => p.session_id));
  if (allEvents.some((e) => !planIds.has(e.session_id))) throw new RangeError('Orphan session event');
  for (const raw of plans) {
    const plan = sessionPlanSchema.parse(raw); await checkPlanContent(plan, questions, db);
    const events = allEvents.filter((e) => e.session_id === plan.session_id);
    for (const e of events) if (e.command.type === 'EXTEND') await checkPlanContent(e.command.plan, questions, db);
    const state = projectAdaptiveSession(plan, events); await validateActualLinks(events, db);
    for (const block of state.blocks) if (block.type === 'TIMED_BLOCK' && block.status === 'COMPLETED') {
      const result = deriveTimedBlockResult(state.id, block, events, attempts);
      if (canonicalEvidence(await db.timed_block_results.get(block.id)) !== canonicalEvidence(result)) throw new RangeError('Timed result does not match actual telemetry');
      resultIds.add(block.id);
      const evidence = extractPacingBlockEvidence(result, attempts);
      if (evidence !== null) {
        if (canonicalEvidence(await db.pacing_evidence.get(evidence.id)) !== canonicalEvidence(evidence)) throw new RangeError('Pacing evidence does not match qualified block');
        evidenceIds.add(evidence.id); records.push({ result, evidence });
      }
    }
  }
  if (resultIds.size !== await db.timed_block_results.count() || evidenceIds.size !== await db.pacing_evidence.count()) throw new RangeError('Orphan block result or pacing evidence');
  return records;
}
export async function loadSessionLearnerSnapshot(questions: readonly Question[], asOf: number, database: SessionDatabase = sessionDb): Promise<{ readonly learner: LearnerSkillVector; readonly coverage: EvidenceCoverageMap }> {
  return database.transaction('r', database.tables, async () => {
    const base = await loadLearnerSkillVector(questions, database, asOf);
    const records = await auditSessions(questions, database);
    const learner = overlayPacingModel(base, records, asOf);
    const coverage = { ...deriveEvidenceCoverage(await database.skill_evidence.toArray()) };
    const useful = records.filter((r) => r.evidence.strength * r.evidence.reliability > 0);
    coverage.PACING_STAMINA = { informative_attempt_count: useful.length, question_count: new Set(useful.map((r) => r.evidence.question_id)).size,
      family_count: new Set(useful.map((r) => r.evidence.question_family)).size, unaided_attempt_count: useful.filter((r) => !r.evidence.assisted).length,
      transfer_attempt_count: 0, last_informative_at: useful.reduce<number | null>((t, r) => Math.max(t ?? 0, r.evidence.created_at), null) };
    return deepFreeze({ learner, coverage });
  });
}

export interface CreateSessionRequest extends SessionPlanningRequest { readonly as_of: number; readonly timed_enabled?: boolean }
export async function createAdaptiveSession(request: CreateSessionRequest, questions: readonly Question[], database: SessionDatabase = sessionDb, config: SessionConfig = SESSION_V1): Promise<AdaptiveStudySession> {
  return database.transaction('rw', database.tables, async () => {
    const settings = sessionConfigSchema.parse(config);
    const signature = canonicalEvidence({ id: request.id, session_id: request.session_id, mode: request.mode,
      available_minutes: request.available_minutes ?? settings.mode_minutes[request.mode], as_of: request.as_of,
      timed_enabled: request.timed_enabled ?? false, config: settings,
      used_candidate_ids: [...(request.used_candidate_ids ?? [])].sort(), used_question_ids: [...(request.used_question_ids ?? [])].sort(), used_lexical_ids: [...(request.used_lexical_ids ?? [])].sort() });
    const existing = await database.adaptive_sessions.get(request.session_id);
    if (existing !== undefined) {
      if (existing.creation_signature !== signature) throw new RangeError('Session creation ID conflict');
      return restoreAdaptiveSession(request.session_id, database);
    }
    const snapshot = await loadSessionLearnerSnapshot(questions, request.as_of, database);
    const content = { questions, lexical_records: await database.lexical_store.toArray(), attempts: await database.solver_attempts.toArray() };
    const candidates = buildSessionCandidatePool(content, request.as_of, request.timed_enabled ?? false, config);
    const plan = planDailySession(request, snapshot.learner, candidates, content, { as_of: request.as_of, coverage: snapshot.coverage }, config);
    return storeSessionPlan({ ...plan, creation_signature: signature }, questions, database);
  });
}

async function commit(input: SessionEventInput, expectedRevision: number, questions: readonly Question[], db: SessionDatabase): Promise<AdaptiveStudySession> {
  const parsed = sessionEventInputSchema.parse(input);
  const previous = await db.session_events.get(parsed.id);
  if (previous !== undefined) {
    const { sequence: _sequence, attempt_ref: _ref, ...original } = previous;
    if (canonicalEvidence(original) !== canonicalEvidence(parsed)) throw new RangeError('Event ID conflict');
    return restoreAdaptiveSession(parsed.session_id, db);
  }
  const { plan, events } = await journal(parsed.session_id, db);
  if (events.length !== expectedRevision) throw new RangeError('Stale session revision; restore before retry');
  const command = parsed.command;
  if (command.type === 'EXTEND') await checkPlanContent(command.plan, questions, db);
  const event: SessionEvent = { ...parsed, sequence: events.length + 1,
    ...(['QUESTION', 'LEXICAL'].includes(command.type) && 'attempt_id' in command ? { attempt_ref: `${command.type}:${command.attempt_id}` } : {}) };
  const next = projectAdaptiveSession(plan, [...events, event]);
  await validateActualLinks([event], db);
  await db.session_events.add(event);
  if (command.type === 'COMPLETE_BLOCK') {
    const block = next.blocks.find((b) => b.id === command.block_id);
    if (block?.type === 'TIMED_BLOCK') {
      // Validate Phase 3 evidence before deriving any new pacing observation.
      await exportEvidenceProgressToJson(questions, db);
      const attempts = await db.solver_attempts.toArray();
      const result = deriveTimedBlockResult(next.id, block, [...events, event], attempts);
      await append(db.timed_block_results, block.id, result);
      const evidence = extractPacingBlockEvidence(result, attempts);
      if (evidence !== null) await append(db.pacing_evidence, evidence.id, evidence);
    }
  }
  return next;
}
export async function executeSessionCommand(input: SessionEventInput, expectedRevision: number, questions: readonly Question[], database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  if (['QUESTION', 'LEXICAL', 'EXTEND'].includes(input.command.type)) throw new RangeError('Use the actual-result or extension adapter');
  return database.transaction('rw', database.tables, async () => commit(input, expectedRevision, questions, database));
}
export async function recordSessionQuestion(input: SessionEventInput, expectedRevision: number, attempt: QuestionAttempt, question: Question, context: EvidenceContext = {}, database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  if (input.command.type !== 'QUESTION' || input.command.attempt_id !== attempt.id || input.command.item_id !== attempt.question_id || input.at !== attempt.attempted_at || attempt.session_id !== null) throw new RangeError('Question event must link the actual submitted attempt; adaptive linkage is separate from legacy sessions');
  return database.transaction('rw', database.tables, async () => {
    await persistAttemptWithEvidence(question, attempt, context, database);
    return commit(input, expectedRevision, [question], database);
  });
}
export async function recordSessionLexicalReview(input: SessionEventInput, expectedRevision: number, review: PersistReviewInput, database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  if (input.command.type !== 'LEXICAL' || input.command.attempt_id !== review.attempt_id || input.command.item_id !== review.word_id || input.at !== review.review.reviewed_at || review.session_id !== null) throw new RangeError('Lexical event must link an actual review');
  return database.transaction('rw', database.tables, async () => {
    await persistLexicalReview(review, database); return commit(input, expectedRevision, [], database);
  });
}
/** Explicit caller request only, at a completed/skipped block boundary. Prior plan blocks remain immutable. */
export async function extendAdaptiveSession(input: SessionEventInput, expectedRevision: number, questions: readonly Question[], database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  if (input.command.type !== 'EXTEND') throw new RangeError('Expected appended extension');
  return database.transaction('rw', database.tables, async () => commit(input, expectedRevision, questions, database));
}
/** Generate the next slice from fresh audited evidence, excluding all previously allocated content. */
export async function planSessionExtension(sessionId: string, extensionId: string, minutes: number, asOf: number, questions: readonly Question[], database: SessionDatabase = sessionDb, timedEnabled = false): Promise<SessionPlan> {
  return database.transaction('r', database.tables, async () => {
    const { plan, events } = await journal(sessionId, database); const state = projectAdaptiveSession(plan, events);
    if (state.blocks.some((b) => b.status === 'ACTIVE') || !['ACTIVE', 'COMPLETED'].includes(state.status)) throw new RangeError('Replanning requires a block boundary');
    const snapshot = await loadSessionLearnerSnapshot(questions, asOf, database);
    const content = { questions, lexical_records: await database.lexical_store.toArray(), attempts: await database.solver_attempts.toArray() };
    return planDailySession({ id: extensionId, session_id: sessionId, mode: state.mode, available_minutes: minutes,
      used_candidate_ids: state.blocks.flatMap((b) => b.candidate_ids), used_question_ids: state.blocks.flatMap((b) => b.question_ids), used_lexical_ids: state.blocks.flatMap((b) => b.lexical_ids) },
    snapshot.learner, buildSessionCandidatePool(content, asOf, timedEnabled, plan.config), content, { as_of: asOf, coverage: snapshot.coverage }, plan.config);
  });
}

/** Explicit boundary adaptation: mark only untouched blocks skipped and append, atomically. */
export async function adaptAdaptiveSession(input: SessionEventInput, expectedRevision: number, questions: readonly Question[], database: SessionDatabase = sessionDb): Promise<AdaptiveStudySession> {
  if (input.command.type !== 'EXTEND') throw new RangeError('Adaptation requires an appended plan');
  return database.transaction('rw', database.tables, async () => {
    // An exact retry must not insert a second set of skip events.
    if (await database.session_events.get(input.id) !== undefined) return commit(input, expectedRevision, questions, database);
    let state = await restoreAdaptiveSession(input.session_id, database);
    if (state.revision !== expectedRevision || state.blocks.some((b) => b.status === 'ACTIVE')) throw new RangeError('Adaptation requires the current block boundary');
    for (const block of state.blocks.filter((b) => b.status === 'PLANNED')) {
      state = await commit({ id: `${input.id}:skip:${state.revision}`, session_id: input.session_id, at: input.at,
        command: { type: 'SKIP_BLOCK', block_id: block.id, reason: 'ADAPTATION' } }, state.revision, questions, database);
    }
    return commit(input, state.revision, questions, database);
  });
}

const backupSchema = z.strictObject({ format: z.literal('yokdil-session-progress'), schema_version: z.literal(5), evidence_progress: z.unknown(),
  adaptive_sessions: z.array(sessionPlanSchema).max(10_000), session_events: z.array(sessionEventSchema).max(500_000),
  timed_block_results: z.array(z.unknown()).max(100_000), pacing_evidence: z.array(pacingBlockEvidenceSchema).max(100_000),
});
function size(json: string): void { if (json.length > 20 * 1024 * 1024 || new TextEncoder().encode(json).byteLength > 20 * 1024 * 1024) throw new RangeError('Backup exceeds 20 MiB'); }
export async function exportSessionProgressToJson(questions: readonly Question[], database: SessionDatabase = sessionDb): Promise<string> {
  return database.transaction('r', database.tables, async () => {
    const evidence_progress: unknown = JSON.parse(await exportEvidenceProgressToJson(questions, database)); await auditSessions(questions, database);
    const json = JSON.stringify(backupSchema.parse({ format: 'yokdil-session-progress', schema_version: 5, evidence_progress,
      adaptive_sessions: await database.adaptive_sessions.toArray(), session_events: await database.session_events.toArray(),
      timed_block_results: await database.timed_block_results.toArray(), pacing_evidence: await database.pacing_evidence.toArray() }), null, 2);
    size(json); return json;
  });
}
export async function importSessionProgressFromJson(json: string, questions: readonly Question[], database: SessionDatabase = sessionDb): Promise<void> {
  size(json); const backup = backupSchema.parse(JSON.parse(json) as unknown);
  for (const ids of [backup.adaptive_sessions.map((p) => p.session_id), backup.session_events.map((e) => e.id), backup.pacing_evidence.map((e) => e.id)]) if (new Set(ids).size !== ids.length) throw new RangeError('Duplicate backup entries');
  await database.transaction('rw', database.tables, async () => {
    await importEvidenceProgressFromJson(JSON.stringify(backup.evidence_progress), questions, database);
    for (const plan of backup.adaptive_sessions) await append(database.adaptive_sessions, plan.session_id, plan);
    for (const event of backup.session_events) await append(database.session_events, event.id, event);
    // Derive expected block results before accepting the untrusted result payload; no unchecked cast is written.
    const expected = new Map<string, TimedBlockResult>(); const attempts = await database.solver_attempts.toArray();
    for (const plan of backup.adaptive_sessions) {
      const events = backup.session_events.filter((e) => e.session_id === plan.session_id);
      const state = projectAdaptiveSession(plan, events);
      for (const block of state.blocks) if (block.status === 'COMPLETED' && block.type === 'TIMED_BLOCK') expected.set(block.id, deriveTimedBlockResult(state.id, block, events, attempts));
    }
    if (backup.timed_block_results.length !== expected.size) throw new RangeError('Missing or extra timed results');
    const received = new Set<string>();
    for (const raw of backup.timed_block_results) {
      const { block_id } = z.object({ block_id: z.string() }).parse(raw); const result = expected.get(block_id);
      if (!result || received.has(block_id) || canonicalEvidence(raw) !== canonicalEvidence(result)) throw new RangeError('Corrupt timed result');
      received.add(block_id); await append(database.timed_block_results, block_id, result);
    }
    for (const evidence of backup.pacing_evidence) await append(database.pacing_evidence, evidence.id, evidence);
    await auditSessions(questions, database);
  });
}
