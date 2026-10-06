import Dexie from 'dexie';
import type { Table } from 'dexie';
import type { SkillId } from '../types/learner';
import type { LexicalRecord, LexicalReview } from '../types/lexical';
import type { DailySession, LexicalAttempt, ProgressBackup } from '../types/progress';
import { createInitialVocab } from '../data/initialVocab';
import { recordEncounter, scheduleLexicalReview, SCHEDULER_VERSION } from './lexicalScheduler';
import { idSchema, lexicalAttemptSchema, progressBackupSchema, timestampSchema } from './validation';
import { migrateProgressV1ToV2, parseProgressBackup } from './progressMigration';
import type { ParsedProgressBackup } from './progressMigration';

const STORES = {
  lexical_store: '&word_id, lemma, tier, lexical_state, next_review_date, review_priority',
  question_attempts: '&id, question_id, session_id, attempted_at, *lexical_ids, *skill_ids',
  daily_sessions: '&id, date, started_at',
};

export class YokdilDatabase extends Dexie {
  readonly lexical_store: Table<LexicalRecord, string>;
  /** Historical store name retained; its entities are lexical evidence, not Phase 2 questions. */
  readonly question_attempts: Table<LexicalAttempt, string>;
  readonly daily_sessions: Table<DailySession, string>;

  constructor(name = 'yokdil-fen-80-plus') {
    super(name);
    this.version(1).stores(STORES);
    this.version(2).stores(STORES).upgrade(async (transaction) => {
      // Version upgrade is itself atomic. Validate everything before replacing any row.
      const migrated = migrateProgressV1ToV2({
        format: 'yokdil-fen-progress', schema_version: 1, scheduler_version: SCHEDULER_VERSION, exported_at: 0,
        lexical_store: await transaction.table<unknown, string>('lexical_store').toArray(),
        question_attempts: await transaction.table<unknown, string>('question_attempts').toArray(),
        daily_sessions: await transaction.table<unknown, string>('daily_sessions').toArray(),
      });
      assertReferences(migrated.question_attempts, migrated.lexical_store, migrated.daily_sessions);
      await transaction.table<LexicalRecord, string>('lexical_store').bulkPut([...migrated.lexical_store]);
      await transaction.table<DailySession, string>('daily_sessions').bulkPut([...migrated.daily_sessions]);
    });
    this.lexical_store = this.table('lexical_store');
    this.question_attempts = this.table('question_attempts');
    this.daily_sessions = this.table('daily_sessions');
  }
}

/** Constructing the singleton does not open or seed IndexedDB. */
export const db = new YokdilDatabase();

/** Add only missing words: restarting or seeding from another tab never resets progress. */
export async function seedInitialVocabulary(database: YokdilDatabase = db, now = Date.now()): Promise<number> {
  const seed = createInitialVocab(now);
  return database.transaction('rw', database.lexical_store, async () => {
    const existing = new Set(await database.lexical_store.toCollection().primaryKeys());
    const missing = seed.filter((entry) => !existing.has(entry.word_id));
    if (missing.length > 0) await database.lexical_store.bulkAdd(missing);
    return missing.length;
  });
}

/** Best-effort request; callers display a backup reminder if the browser declines. */
export async function requestPersistentStorage(): Promise<boolean> {
  if (typeof navigator === 'undefined' || !navigator.storage?.persist) return false;
  try {
    if (await navigator.storage.persisted()) return true;
    return await navigator.storage.persist();
  } catch { return false; }
}

export class ProgressImportError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = 'ProgressImportError';
  }
}

const MAX_BACKUP_BYTES = 20 * 1024 * 1024;

/** Snapshot all three tables in one read transaction. Caller owns file download/sharing. */
export async function exportProgressToJson(database: YokdilDatabase = db): Promise<string> {
  const backup = await database.transaction(
    'r', [database.lexical_store, database.question_attempts, database.daily_sessions], async (): Promise<ProgressBackup> => ({
      format: 'yokdil-fen-progress', schema_version: 2, scheduler_version: SCHEDULER_VERSION,
      exported_at: Date.now(),
      lexical_store: await database.lexical_store.toArray(),
      question_attempts: await database.question_attempts.toArray(),
      daily_sessions: await database.daily_sessions.toArray(),
    }),
  );
  // Also refuse to export corrupt data inserted outside the supported write helpers.
  const validated = progressBackupSchema.parse(backup);
  assertReferences(validated.question_attempts, validated.lexical_store, validated.daily_sessions);
  const json = JSON.stringify(validated, null, 2);
  if (new TextEncoder().encode(json).byteLength > MAX_BACKUP_BYTES) {
    throw new ProgressImportError('Backup exceeds the 20 MiB supported import size');
  }
  return json;
}

function assertReferences(
  attempts: readonly LexicalAttempt[], words: readonly LexicalRecord[], sessions: readonly DailySession[],
): void {
  const wordIds = new Set(words.map((row) => row.word_id));
  const sessionIds = new Set(sessions.map((row) => row.id));
  for (const attempt of attempts) {
    if (attempt.lexical_ids.some((id) => !wordIds.has(id))) {
      throw new ProgressImportError(`Attempt ${attempt.id} references a missing word`);
    }
    if (attempt.session_id !== null && !sessionIds.has(attempt.session_id)) {
      throw new ProgressImportError(`Attempt ${attempt.id} references a missing session`);
    }
  }
}

/** Stable comparison ignores JSON object key order, including distractor_errors keys. */
function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map((item: unknown) => canonicalJson(item)).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(object[key])}`).join(',')}}`;
  }
  return JSON.stringify(value) ?? 'null';
}

export interface ImportProgressOptions {
  /** Default: abort the whole import on conflict. No mode deletes or overwrites local progress. */
  readonly on_conflict?: 'error' | 'keep-local';
}
export interface ImportProgressResult {
  readonly migrated_from: 1 | null;
  readonly inserted: { readonly lexical_store: number; readonly question_attempts: number; readonly daily_sessions: number };
  readonly unchanged: number;
  readonly conflicts: readonly string[];
}

/** Validate before writes, then import in one transaction. A failure rolls back every table. */
export async function importProgressFromJson(
  json: string,
  options: ImportProgressOptions = {},
  database: YokdilDatabase = db,
): Promise<ImportProgressResult> {
  if (options.on_conflict !== undefined && !['error', 'keep-local'].includes(options.on_conflict)) {
    throw new ProgressImportError('Unsupported conflict policy');
  }
  if (json.length > MAX_BACKUP_BYTES || new TextEncoder().encode(json).byteLength > MAX_BACKUP_BYTES) {
    throw new ProgressImportError('Backup exceeds 20 MiB');
  }
  let parsed: unknown;
  try { parsed = JSON.parse(json) as unknown; }
  catch (cause) { throw new ProgressImportError('Backup is not valid JSON', { cause }); }
  let normalized: ParsedProgressBackup;
  try { normalized = parseProgressBackup(parsed); }
  catch (cause) {
    throw new ProgressImportError('Backup schema or evidence is invalid or unsupported', { cause });
  }
  const { backup, migrated_from } = normalized;
  return database.transaction('rw', [database.lexical_store, database.question_attempts, database.daily_sessions], async () => {
    const localWords = await database.lexical_store.toArray();
    const localAttempts = await database.question_attempts.toArray();
    const localSessions = await database.daily_sessions.toArray();
    let unchanged = 0;
    const conflicts: string[] = [];
    const additions = <T>(incoming: readonly T[], local: readonly T[], key: (item: T) => string, table: string): T[] => {
      const existing = new Map(local.map((row) => [key(row), row]));
      return incoming.filter((row) => {
        const previous = existing.get(key(row));
        if (previous === undefined) return true;
        if (canonicalJson(previous) === canonicalJson(row)) { unchanged += 1; return false; }
        conflicts.push(`${table}:${key(row)}`);
        return false;
      });
    };
    const words = additions(backup.lexical_store, localWords, (row) => row.word_id, 'lexical_store');
    const attempts = additions(backup.question_attempts, localAttempts, (row) => row.id, 'question_attempts');
    const sessions = additions(backup.daily_sessions, localSessions, (row) => row.id, 'daily_sessions');
    if (conflicts.length > 0 && options.on_conflict !== 'keep-local') {
      throw new ProgressImportError(`Import would conflict with local progress: ${conflicts.slice(0, 5).join(', ')}`);
    }
    assertReferences([...localAttempts, ...attempts], [...localWords, ...words], [...localSessions, ...sessions]);
    if (words.length > 0) await database.lexical_store.bulkAdd(words);
    if (sessions.length > 0) await database.daily_sessions.bulkAdd(sessions);
    if (attempts.length > 0) await database.question_attempts.bulkAdd(attempts);
    return { inserted: { lexical_store: words.length, question_attempts: attempts.length, daily_sessions: sessions.length }, unchanged, conflicts, migrated_from };
  });
}

export interface PersistReviewInput {
  readonly attempt_id: string;
  readonly word_id: string;
  readonly question_id: string;
  readonly session_id: string | null;
  readonly skill_ids: readonly SkillId[];
  readonly review: LexicalReview;
  readonly user_lexical_factor?: number;
}

/** Serializes competing tabs and atomically writes the attempt and lexical update. */
export async function persistLexicalReview(input: PersistReviewInput, database: YokdilDatabase = db): Promise<LexicalRecord> {
  idSchema.parse(input.attempt_id);
  return database.transaction('rw', [database.lexical_store, database.question_attempts, database.daily_sessions], async () => {
    const record = await database.lexical_store.get(input.word_id);
    if (record === undefined) throw new RangeError(`Unknown word: ${input.word_id}`);
    // Derive the canonical attempt before scheduling so exact retry is safe after a commit.
    const outcome = input.review.grade === 0 ? 'incorrect' :
      input.review.assistance_used || input.review.grade === 1 ? 'assisted' : 'unassisted';
    const attempt = lexicalAttemptSchema.parse({
      id: input.attempt_id, question_id: input.question_id, session_id: input.session_id,
      lexical_ids: [input.word_id], skill_ids: input.skill_ids, context_id: input.review.context_id,
      outcome, response_ms: input.review.response_time_ms, attempted_at: input.review.reviewed_at,
      lexical_review: {
        grade: input.review.grade, assistance_used: input.review.assistance_used,
        user_lexical_factor: input.user_lexical_factor ?? 1,
        distractor_test: input.review.distractor_test ?? null,
        tested_collocation: input.review.tested_collocation ?? null,
      },
    });
    const previous = await database.question_attempts.get(attempt.id);
    if (previous !== undefined) {
      if (canonicalJson(previous) !== canonicalJson(attempt)) throw new RangeError('Attempt ID was reused with different evidence');
      return record;
    }
    if (input.session_id !== null && await database.daily_sessions.get(input.session_id) === undefined) {
      throw new RangeError('Unknown session');
    }
    const scheduled = scheduleLexicalReview(record, input.review, input.user_lexical_factor);
    await database.question_attempts.add(attempt);
    await database.lexical_store.put(scheduled.record);
    return scheduled.record;
  });
}

export async function persistEncounter(wordId: string, contextId: string, now = Date.now(), database: YokdilDatabase = db): Promise<LexicalRecord> {
  timestampSchema.parse(now);
  return database.transaction('rw', database.lexical_store, async () => {
    const record = await database.lexical_store.get(wordId);
    if (record === undefined) throw new RangeError(`Unknown word: ${wordId}`);
    const next = recordEncounter(record, contextId, now);
    await database.lexical_store.put(next);
    return next;
  });
}
