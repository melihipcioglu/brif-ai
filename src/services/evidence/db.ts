import type { Table } from 'dexie';
import { z } from 'zod';
import type { ConfidenceCalibrationRecord, EvidenceContext, EvidenceRun, SkillEvidence } from '../../types/evidence';
import { createLearnerSkillVector, type LearnerSkillVector } from '../../types/learner';
import type { Question, QuestionAttempt } from '../../types/question';
import { deepFreeze } from '../questions/attempts';
import { exportSolverProgressToJson, importSolverProgressFromJson, persistQuestionAttempt, QuestionDatabase } from '../questions/db';
import { questionAttemptSchema, questionSchema, validateAttemptForQuestion } from '../questions/validation';
import { extractConfidenceCalibration } from './calibration';
import { extractSkillEvidence } from './extractEvidence';
import { updateLearnerSkillVector } from './updateLearnerModel';
import { canonicalEvidence, confidenceCalibrationSchema, evidenceContextSchema, evidenceRunSchema, skillEvidenceSchema } from './validation';

/** Additive v4 only: inherited v1–v3 declarations and data are untouched. */
export class EvidenceDatabase extends QuestionDatabase {
  readonly skill_evidence: Table<SkillEvidence, string>;
  readonly confidence_calibration: Table<ConfidenceCalibrationRecord, string>;
  readonly evidence_runs: Table<EvidenceRun, string>;
  constructor(name = 'yokdil-fen-80-plus') {
    super(name);
    this.version(4).stores({
      skill_evidence: '&id, skill_id, attempt_id, created_at, source',
      confidence_calibration: '&attempt_id', evidence_runs: '&attempt_id, question_id, created_at',
    });
    this.skill_evidence = this.table('skill_evidence');
    this.confidence_calibration = this.table('confidence_calibration');
    this.evidence_runs = this.table('evidence_runs');
  }
}
export const evidenceDb = new EvidenceDatabase();
function tables(db: EvidenceDatabase) {
  return [db.lexical_store, db.question_attempts, db.daily_sessions, db.solver_attempts, db.skill_evidence, db.confidence_calibration, db.evidence_runs];
}
function catalog(questions: readonly Question[]): ReadonlyMap<string, Question> {
  const parsed = questions.map((q) => questionSchema.parse(q));
  const bank = new Map(parsed.map((q) => [q.id, q]));
  if (bank.size !== parsed.length) throw new RangeError('Duplicate question IDs');
  return bank;
}
interface Bundle {
  readonly run: EvidenceRun;
  readonly evidence: readonly SkillEvidence[];
  readonly calibration: ConfidenceCalibrationRecord | null;
}
function bundle(q: Question, a: QuestionAttempt, context: EvidenceContext): Bundle {
  const ctx = evidenceContextSchema.parse(context);
  const evidence = extractSkillEvidence(q, a, ctx);
  return { evidence, calibration: extractConfidenceCalibration(a), run: evidenceRunSchema.parse({
    attempt_id: a.id, question_id: q.id, extractor_version: 'v1', context: ctx, evidence_ids: evidence.map((e) => e.id), created_at: a.attempted_at,
  }) };
}
async function append<T>(table: Table<T, string>, key: string, value: T): Promise<number> {
  const previous = await table.get(key);
  if (previous !== undefined) {
    if (canonicalEvidence(previous) !== canonicalEvidence(value)) throw new RangeError('Append-only ID conflict');
    return 0;
  }
  await table.add(value);
  return 1;
}
async function checkUnseen(b: Bundle, a: QuestionAttempt, database: EvidenceDatabase): Promise<void> {
  if (!b.evidence.some((e) => e.evidence_kind === 'TRANSFER')) return;
  const seen = await database.solver_attempts.where('question_id').equals(a.question_id).toArray();
  if (seen.some((other) => other.id !== a.id && other.attempted_at <= a.attempted_at)) throw new RangeError('Transfer question was already attempted');
}
async function appendBundle(b: Bundle, database: EvidenceDatabase): Promise<number> {
  await append(database.evidence_runs, b.run.attempt_id, b.run);
  let inserted = 0;
  for (const e of b.evidence) inserted += await append(database.skill_evidence, e.id, e);
  if (b.calibration !== null) await append(database.confidence_calibration, b.calibration.attempt_id, b.calibration);
  return inserted;
}
/** Reprocess an already stored attempt. A retry with altered context aborts instead of adding evidence. */
export async function processStoredAttempt(question: Question, attemptId: string, context: EvidenceContext = {}, database: EvidenceDatabase = evidenceDb): Promise<readonly SkillEvidence[]> {
  const q = questionSchema.parse(question);
  return database.transaction('rw', tables(database), async () => {
    const stored = await database.solver_attempts.get(attemptId);
    if (stored === undefined) throw new RangeError('Unknown attempt');
    const a = validateAttemptForQuestion(stored, q);
    if (a.session_id !== null && await database.daily_sessions.get(a.session_id) === undefined) throw new RangeError('Unknown session');
    const b = bundle(q, a, context);
    await checkUnseen(b, a, database);
    await appendBundle(b, database);
    // Backdated telemetry must not silently invalidate an earlier immutable transfer receipt.
    const relatedRuns = await database.evidence_runs.where('question_id').equals(q.id).toArray();
    for (const run of relatedRuns) {
      if (run.attempt_id === a.id || run.context.transfer === undefined) continue;
      const previous = await database.solver_attempts.get(run.attempt_id);
      if (previous === undefined) throw new RangeError('Unknown evidence reference');
      await checkUnseen(bundle(q, previous, run.context), previous, database);
    }
    return b.evidence;
  });
}
/** Optional Phase 2 saveAttempt adapter: raw telemetry + evidence commit in one transaction. */
export async function persistAttemptWithEvidence(question: Question, attempt: QuestionAttempt, context: EvidenceContext = {}, database: EvidenceDatabase = evidenceDb): Promise<void> {
  await database.transaction('rw', tables(database), async () => {
    await persistQuestionAttempt(attempt, question, database);
    await processStoredAttempt(question, attempt.id, context, database);
  });
}

const backupSchema = z.strictObject({
  format: z.literal('yokdil-evidence-progress'), schema_version: z.literal(4), question_progress: z.unknown(),
  skill_evidence: z.array(skillEvidenceSchema).max(500_000),
  confidence_calibration: z.array(confidenceCalibrationSchema).max(100_000), evidence_runs: z.array(evidenceRunSchema).max(100_000),
});
type EvidenceBackup = z.infer<typeof backupSchema>;
function checkSize(json: string): void {
  const limit = 20 * 1024 * 1024;
  if (json.length > limit || new TextEncoder().encode(json).byteLength > limit) throw new RangeError('Backup exceeds 20 MiB');
}
function uniqueMap<T>(rows: readonly T[], key: (row: T) => string): Map<string, T> {
  const map = new Map(rows.map((row) => [key(row), row]));
  if (map.size !== rows.length) throw new RangeError('Duplicate backup rows');
  return map;
}
/** Validate references AND regenerate every event. In-range fabricated weights cannot pass import. */
async function validateBackupEvidence(backup: EvidenceBackup, questions: readonly Question[], database: EvidenceDatabase): Promise<readonly Bundle[]> {
  const bank = catalog(questions);
  const evidence = uniqueMap(backup.skill_evidence, (e) => e.id);
  const calibrations = uniqueMap(backup.confidence_calibration, (c) => c.attempt_id);
  uniqueMap(backup.evidence_runs, (r) => r.attempt_id);
  const enclosed = z.object({ solver_attempts: z.array(questionAttemptSchema) }).parse(backup.question_progress);
  const enclosedAttempts = uniqueMap(enclosed.solver_attempts, (a) => a.id);
  const expectedIds = new Set<string>();
  const expectedCalibration = new Set<string>();
  const bundles: Bundle[] = [];
  for (const run of backup.evidence_runs) {
    const q = bank.get(run.question_id);
    const a = enclosedAttempts.get(run.attempt_id);
    if (q === undefined || a === undefined) throw new RangeError('Unknown evidence reference');
    validateAttemptForQuestion(a, q);
    const b = bundle(q, a, run.context);
    if (canonicalEvidence(run) !== canonicalEvidence(b.run)) throw new RangeError('Evidence receipt mismatch');
    for (const row of b.evidence) {
      if (canonicalEvidence(evidence.get(row.id)) !== canonicalEvidence(row)) throw new RangeError('Evidence does not match its attempt and context');
      expectedIds.add(row.id);
    }
    if (b.calibration !== null) {
      if (canonicalEvidence(calibrations.get(a.id)) !== canonicalEvidence(b.calibration)) throw new RangeError('Confidence record mismatch');
      expectedCalibration.add(a.id);
    }
    await checkUnseen(b, a, database);
    bundles.push(b);
  }
  if (expectedIds.size !== evidence.size || expectedCalibration.size !== calibrations.size) throw new RangeError('Orphan evidence or calibration');
  return bundles;
}
async function snapshot(questions: readonly Question[], database: EvidenceDatabase): Promise<EvidenceBackup> {
  const result = backupSchema.parse({ format: 'yokdil-evidence-progress', schema_version: 4,
    question_progress: JSON.parse(await exportSolverProgressToJson(questions, database)) as unknown,
    skill_evidence: await database.skill_evidence.toArray(), confidence_calibration: await database.confidence_calibration.toArray(), evidence_runs: await database.evidence_runs.toArray() });
  await validateBackupEvidence(result, questions, database);
  return result;
}
export async function exportEvidenceProgressToJson(questions: readonly Question[], database: EvidenceDatabase = evidenceDb): Promise<string> {
  return database.transaction('r', tables(database), async () => {
    const json = JSON.stringify(await snapshot(questions, database), null, 2);
    checkSize(json); return json;
  });
}
/** Merge only. Exact retries are no-ops; any conflict rolls back all seven stores, including inherited writes. */
export async function importEvidenceProgressFromJson(json: string, questions: readonly Question[], database: EvidenceDatabase = evidenceDb): Promise<{ readonly evidence_inserted: number }> {
  checkSize(json);
  const backup = backupSchema.parse(JSON.parse(json) as unknown);
  return database.transaction('rw', tables(database), async () => {
    await importSolverProgressFromJson(JSON.stringify(backup.question_progress), questions, database);
    const bundles = await validateBackupEvidence(backup, questions, database);
    let evidence_inserted = 0;
    for (const b of bundles) evidence_inserted += await appendBundle(b, database);
    // Also detect conflicts between incoming historical attempts and existing transfer receipts.
    await snapshot(questions, database);
    return { evidence_inserted };
  });
}
/** Rebuild from the complete audited event store; no snapshot is used as evidence or as a prior. */
export async function loadLearnerSkillVector(questions: readonly Question[], database: EvidenceDatabase = evidenceDb, asOf?: number): Promise<LearnerSkillVector> {
  return database.transaction('r', tables(database), async () => {
    const backup = await snapshot(questions, database);
    return deepFreeze(updateLearnerSkillVector(createLearnerSkillVector(), backup.skill_evidence, asOf));
  });
}
