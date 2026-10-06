import { afterEach, describe, expect, it, vi } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { createLearnerSkillVector } from '../../../src/types/learner';
import type { SkillEvidence, EvidenceRun, ConfidenceCalibrationRecord } from '../../../src/types/evidence';
import { persistLexicalReview, seedInitialVocabulary } from '../../../src/services/db';
import { EvidenceDatabase, exportEvidenceProgressToJson, importEvidenceProgressFromJson, loadLearnerSkillVector, persistAttemptWithEvidence, processStoredAttempt } from '../../../src/services/evidence/db';
import { persistQuestionAttempt, QuestionDatabase } from '../../../src/services/questions/db';
import { attempt, question, TIME } from './fixtures';

const opened: QuestionDatabase[] = [];
function database(): EvidenceDatabase {
  const db = new EvidenceDatabase(`phase3-${crypto.randomUUID()}`); opened.push(db); return db;
}
afterEach(async () => { vi.restoreAllMocks(); for (const db of opened.splice(0)) await db.delete(); });
async function inherited(db: QuestionDatabase): Promise<string> {
  return JSON.stringify([await db.lexical_store.toArray(), await db.question_attempts.toArray(), await db.daily_sessions.toArray(), await db.solver_attempts.toArray()]);
}
async function allRows(db: EvidenceDatabase): Promise<string> {
  return JSON.stringify([await inherited(db), await db.skill_evidence.toArray(), await db.confidence_calibration.toArray(), await db.evidence_runs.toArray()]);
}
async function seed(db: QuestionDatabase): Promise<void> {
  await seedInitialVocabulary(db, 0);
  await db.daily_sessions.add({ id: 's', date: '2026-10-03', time_zone: 'Europe/Istanbul', started_at: 0, ended_at: null, active_ms: 0, skills: createLearnerSkillVector() });
  await persistLexicalReview({ attempt_id: 'lexical', question_id: question().id, word_id: 'inhibit', session_id: 's', skill_ids: ['VOCAB_CONTEXT'],
    review: { grade: 3, reviewed_at: 1_000, response_time_ms: 500, context_id: 'context', assistance_used: false } }, db);
  await persistQuestionAttempt({ ...attempt(), session_id: 's' }, question(), db);
}
interface Backup {
  format: string;
  schema_version: number;
  question_progress: unknown;
  skill_evidence: SkillEvidence[];
  confidence_calibration: ConfidenceCalibrationRecord[];
  evidence_runs: EvidenceRun[];
}

describe('Additive v4 evidence persistence', () => {
  it('v3 to v4 preserves every prior store byte-equivalent and processing preserves lexical/attempt rows', async () => {
    const name = `upgrade-phase3-${crypto.randomUUID()}`;
    const old = new QuestionDatabase(name);
    await seed(old);
    const before = await inherited(old);
    expect(old.verno).toBe(3); old.close();
    const next = new EvidenceDatabase(name); opened.push(next);
    await next.open(); expect(next.verno).toBe(4);
    expect(await inherited(next)).toBe(before);
    expect(await next.skill_evidence.count()).toBe(0);
    await processStoredAttempt(question(), 'a-1', {}, next);
    expect(await inherited(next)).toBe(before);
    expect(await next.skill_evidence.count()).toBeGreaterThan(0);
  });
  it('same attempt processed concurrently is append-only and idempotent', async () => {
    const db = database(); const a = attempt();
    await Promise.all([persistAttemptWithEvidence(question(), a, {}, db), persistAttemptWithEvidence(question(), a, {}, db)]);
    const before = await allRows(db);
    const rows = await processStoredAttempt(question(), a.id, {}, db);
    expect(await db.skill_evidence.count()).toBe(rows.length);
    expect(await db.evidence_runs.count()).toBe(1);
    expect(await db.confidence_calibration.count()).toBe(1);
    expect(await allRows(db)).toBe(before);
    expect(Object.isFrozen(rows[0])).toBe(true);
  });
  it('rejects changed retry context without new or overwritten evidence', async () => {
    const db = database();
    await persistAttemptWithEvidence(question(), attempt(), {}, db);
    const before = await allRows(db);
    await expect(processStoredAttempt(question(), 'a-1', { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } }, db)).rejects.toThrow('conflict');
    expect(await allRows(db)).toBe(before);
  });
  it('rejects changed raw attempt IDs and nonexistent references', async () => {
    const db = database();
    await persistAttemptWithEvidence(question(), attempt(), {}, db);
    const before = await allRows(db);
    await expect(persistAttemptWithEvidence(question(), { ...attempt(), confidence_level: 'LOW' }, {}, db)).rejects.toThrow('reused');
    await expect(processStoredAttempt(question(), 'missing', {}, db)).rejects.toThrow('Unknown attempt');
    await expect(processStoredAttempt(question('gap-grammar'), 'a-1', {}, db)).rejects.toThrow();
    await expect(persistAttemptWithEvidence(question(), { ...attempt('new'), session_id: 'missing' }, {}, db)).rejects.toThrow('Unknown session');
    expect(await allRows(db)).toBe(before);
  });
  it('rolls back attempt, receipt, calibration and evidence on a storage failure', async () => {
    const db = database();
    const before = await allRows(db);
    vi.spyOn(db.skill_evidence, 'add').mockRejectedValueOnce(new Error('quota exceeded'));
    await expect(persistAttemptWithEvidence(question(), attempt(), {}, db)).rejects.toThrow('quota exceeded');
    expect(await allRows(db)).toBe(before);
  });
  it('detects known prior exposure when caller incorrectly claims unseen transfer', async () => {
    const db = database();
    await persistAttemptWithEvidence(question(), { ...attempt('first'), attempted_at: TIME - 1_000 }, {}, db);
    const before = await allRows(db);
    await expect(persistAttemptWithEvidence(question(), attempt('transfer'), { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } }, db)).rejects.toThrow('already attempted');
    expect(await allRows(db)).toBe(before);
  });
  it('rebuilds the complete learner model instead of using a previous snapshot as evidence', async () => {
    const db = database();
    await persistAttemptWithEvidence(question(), attempt(), {}, db);
    await persistAttemptWithEvidence(question(), attempt('wrong', false), {}, db);
    const model = await loadLearnerSkillVector(initialQuestions, db);
    expect(model.VOCAB_CONTEXT.unaided_accuracy).toBeCloseTo(0.5);
    expect(model.VOCAB_CONTEXT.evidence_count).toBe(2);
    expect(model.PACING_STAMINA).toEqual(createLearnerSkillVector().PACING_STAMINA);
    expect(await loadLearnerSkillVector(initialQuestions, db)).toEqual(model);
  });
  it('atomically rejects backdated telemetry that would invalidate an existing transfer receipt', async () => {
    const db = database();
    await persistAttemptWithEvidence(question(), attempt('transfer'), { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } }, db);
    const before = await allRows(db);
    await expect(persistAttemptWithEvidence(question(), { ...attempt('earlier'), attempted_at: TIME - 1_000 }, {}, db)).rejects.toThrow('already attempted');
    expect(await allRows(db)).toBe(before);
  });
});

describe('Audited v4 JSON envelope', () => {
  it('round trips all seven stores including transfer provenance and repeats without duplicates', async () => {
    const source = database(), target = database();
    await seed(source);
    await processStoredAttempt(question(), 'a-1', { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } }, source);
    const json = await exportEvidenceProgressToJson(initialQuestions, source);
    const result = await importEvidenceProgressFromJson(json, initialQuestions, target);
    expect(result.evidence_inserted).toBeGreaterThan(0);
    expect(await allRows(target)).toBe(await allRows(source));
    expect(await importEvidenceProgressFromJson(json, initialQuestions, target)).toEqual({ evidence_inserted: 0 });
    expect(await loadLearnerSkillVector(initialQuestions, target)).toEqual(await loadLearnerSkillVector(initialQuestions, source));
  });
  it.each(['strength', 'reference', 'id', 'missing', 'duplicate', 'receipt', 'calibration', 'transfer', 'unknown-skill'] as const)('atomically rejects corrupt %s, including nested Phase 1 additions', async (mutation) => {
    const source = database(), target = database();
    await seed(source); await processStoredAttempt(question(), 'a-1', {}, source);
    const backup = JSON.parse(await exportEvidenceProgressToJson(initialQuestions, source)) as Backup;
    const row = backup.skill_evidence[0];
    const run = backup.evidence_runs[0];
    if (row === undefined || run === undefined) throw new Error('Missing evidence fixture');
    switch (mutation) {
      case 'strength': backup.skill_evidence[0] = { ...row, strength: row.strength / 2 }; break;
      case 'reference': backup.skill_evidence[0] = { ...row, question_id: 'unknown' }; break;
      case 'id': backup.skill_evidence[0] = { ...row, id: 'forged' }; break;
      case 'missing': backup.skill_evidence.pop(); break;
      case 'duplicate': backup.skill_evidence.push(row); break;
      case 'receipt': backup.evidence_runs[0] = { ...run, created_at: run.created_at + 1 }; break;
      case 'calibration': backup.confidence_calibration = [{ attempt_id: 'a-1', confidence: 'LOW', correct: true }]; break;
      case 'transfer': backup.skill_evidence[0] = { ...row, evidence_kind: 'TRANSFER', transfer_level: 1 }; break;
      case 'unknown-skill': backup.skill_evidence[0] = { ...row, skill_id: 'UNKNOWN' as SkillEvidence['skill_id'] }; break;
    }
    const before = await allRows(target);
    await expect(importEvidenceProgressFromJson(JSON.stringify(backup), initialQuestions, target)).rejects.toThrow();
    expect(await allRows(target)).toBe(before);
  });
  it('rolls back a structurally valid import when an existing receipt conflicts', async () => {
    const source = database(), target = database();
    await seed(source); await processStoredAttempt(question(), 'a-1', {}, source);
    await target.daily_sessions.add((await source.daily_sessions.toArray())[0]!);
    await persistAttemptWithEvidence(question(), { ...attempt(), session_id: 's' }, { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } }, target);
    const before = await allRows(target);
    const json = await exportEvidenceProgressToJson(initialQuestions, source);
    await expect(importEvidenceProgressFromJson(json, initialQuestions, target)).rejects.toThrow('conflict');
    expect(await allRows(target)).toBe(before);
  });
  it('does not export or aggregate in-range tampering performed outside the append-only API', async () => {
    const db = database(); await persistAttemptWithEvidence(question(), attempt(), {}, db);
    const row = (await db.skill_evidence.toArray())[0];
    if (row === undefined) throw new Error('Missing fixture');
    await db.skill_evidence.put({ ...row, strength: row.strength / 2 });
    await expect(exportEvidenceProgressToJson(initialQuestions, db)).rejects.toThrow('does not match');
    await expect(loadLearnerSkillVector(initialQuestions, db)).rejects.toThrow('does not match');
  });
  it('rejects malformed JSON, unsupported schema and incomplete question catalogs', async () => {
    const db = database(); const source = database();
    await persistAttemptWithEvidence(question(), attempt(), {}, source);
    const json = await exportEvidenceProgressToJson(initialQuestions, source);
    for (const bad of ['{', '{"schema_version":99}']) await expect(importEvidenceProgressFromJson(bad, initialQuestions, db)).rejects.toThrow();
    await expect(importEvidenceProgressFromJson(json, [], db)).rejects.toThrow();
    expect(await db.solver_attempts.count()).toBe(0);
  });
});
