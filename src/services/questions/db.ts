import type { Table } from 'dexie';
import { z } from 'zod';
import type { Question, QuestionAttempt } from '../../types/question';
import { exportProgressToJson, importProgressFromJson, YokdilDatabase } from '../db';
import { timestampSchema } from '../validation';
import { questionAttemptSchema, questionSchema, validateAttemptForQuestion } from './validation';
import { deepFreeze } from './attempts';

/** Additive v3. All inherited v1/v2 stores and upgrade behavior stay untouched. */
export class QuestionDatabase extends YokdilDatabase {
  readonly solver_attempts: Table<QuestionAttempt, string>;
  constructor(name = 'yokdil-fen-80-plus') {
    super(name);
    this.version(3).stores({ solver_attempts: '&id, question_id, session_id, attempted_at, family' });
    this.solver_attempts = this.table('solver_attempts');
  }
}
export const questionDb = new QuestionDatabase();

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') return `{${Object.entries(value).filter(([, v]) => v !== undefined).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${JSON.stringify(k)}:${canonical(v)}`).join(',')}}`;
  return JSON.stringify(value) ?? 'null';
}
function catalog(questions: readonly Question[]): ReadonlyMap<string, Question> {
  const validated = questions.map((q) => questionSchema.parse(q));
  const result = new Map(validated.map((q) => [q.id, q]));
  if (result.size !== validated.length) throw new RangeError('Duplicate question IDs');
  return result;
}

/** Append-only and idempotent for exact retry; conflicting ID reuse aborts the whole batch. */
export async function persistSolverAttempts(attempts: readonly QuestionAttempt[], questions: readonly Question[], database: QuestionDatabase = questionDb): Promise<number> {
  const bank = catalog(questions);
  return database.transaction('rw', [database.solver_attempts, database.daily_sessions], async () => {
    let inserted = 0;
    for (const input of attempts) {
      const question = bank.get(input.question_id);
      if (question === undefined) throw new RangeError('Unknown question');
      const attempt = validateAttemptForQuestion(input, question);
      if (attempt.session_id !== null && await database.daily_sessions.get(attempt.session_id) === undefined) throw new RangeError('Unknown session');
      const previous = await database.solver_attempts.get(attempt.id);
      if (previous !== undefined) {
        if (canonical(previous) !== canonical(attempt)) throw new RangeError('Attempt ID reused with different evidence');
      } else { await database.solver_attempts.add(attempt); inserted += 1; }
    }
    return inserted;
  });
}
export async function persistQuestionAttempt(attempt: QuestionAttempt, question: Question, database: QuestionDatabase = questionDb): Promise<void> {
  await persistSolverAttempts([attempt], [question], database);
}
export async function getQuestionAttempts(questionId: string, database: QuestionDatabase = questionDb): Promise<readonly QuestionAttempt[]> {
  const rows = await database.solver_attempts.where('question_id').equals(questionId).sortBy('attempted_at');
  return deepFreeze(rows.map((row) => questionAttemptSchema.parse(row)));
}

const backupSchema = z.strictObject({
  format: z.literal('yokdil-question-progress'), schema_version: z.literal(3), exported_at: timestampSchema,
  lexical_progress: z.unknown(), solver_attempts: z.array(questionAttemptSchema).max(100_000),
}).refine((b) => new Set(b.solver_attempts.map((a) => a.id)).size === b.solver_attempts.length, 'Duplicate attempt IDs');
const MAX_BACKUP_BYTES = 20 * 1024 * 1024;
function checkSize(json: string): void {
  if (json.length > MAX_BACKUP_BYTES || new TextEncoder().encode(json).byteLength > MAX_BACKUP_BYTES) throw new RangeError('Backup exceeds 20 MiB');
}
/** v3 envelope preserves the unmodified Phase 1 v2 backup contract inside it. */
export async function exportSolverProgressToJson(questions: readonly Question[], database: QuestionDatabase = questionDb): Promise<string> {
  const bank = catalog(questions);
  return database.transaction('r', [database.lexical_store, database.question_attempts, database.daily_sessions, database.solver_attempts], async () => {
    const attempts = await database.solver_attempts.toArray();
    for (const a of attempts) {
      const q = bank.get(a.question_id);
      if (q === undefined) throw new RangeError('Backup requires the complete question catalog');
      validateAttemptForQuestion(a, q);
      if (a.session_id !== null && await database.daily_sessions.get(a.session_id) === undefined) throw new RangeError('Unknown session');
    }
    const json = JSON.stringify(backupSchema.parse({ format: 'yokdil-question-progress', schema_version: 3, exported_at: Date.now(),
      lexical_progress: JSON.parse(await exportProgressToJson(database)) as unknown, solver_attempts: attempts }), null, 2);
    checkSize(json);
    return json;
  });
}
export async function importSolverProgressFromJson(json: string, questions: readonly Question[], database: QuestionDatabase = questionDb): Promise<{ readonly solver_inserted: number }> {
  checkSize(json);
  const backup = backupSchema.parse(JSON.parse(json) as unknown);
  return database.transaction('rw', [database.lexical_store, database.question_attempts, database.daily_sessions, database.solver_attempts], async () => {
    await importProgressFromJson(JSON.stringify(backup.lexical_progress), {}, database);
    const solver_inserted = await persistSolverAttempts(backup.solver_attempts, questions, database);
    return { solver_inserted };
  });
}
