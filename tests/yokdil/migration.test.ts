import Dexie from 'dexie';
import { afterEach, describe, expect, it } from 'vitest';
import { createInitialVocab } from '../../src/data/initialVocab';
import type { LexicalRecord } from '../../src/types/lexical';
import { createLearnerSkillVector } from '../../src/types/learner';
import type { ProgressBackup } from '../../src/types/progress';
import { exportProgressToJson, importProgressFromJson, persistLexicalReview, YokdilDatabase } from '../../src/services/db';
import { DAY_MS, scheduleLexicalReview } from '../../src/services/lexicalScheduler';
import { legacyProgressBackupV1Schema } from '../../src/services/validation';
import { migrateProgressV1ToV2, parseProgressBackup } from '../../src/services/progressMigration';

const databases: Dexie[] = [];
const names = new Set<string>();
function track<T extends Dexie>(database: T): T {
  databases.push(database);
  names.add(database.name);
  return database;
}
const target = (): YokdilDatabase => track(new YokdilDatabase(`migration-${crypto.randomUUID()}`));
afterEach(async () => {
  for (const database of databases) database.close();
  for (const name of names) await Dexie.delete(name);
  databases.length = 0;
  names.clear();
});

function fresh(): LexicalRecord {
  const word = createInitialVocab(0)[0];
  if (word === undefined) throw new Error('Missing fixture');
  return word;
}

/** Explicit old JSON shape, not a v2 record with a changed version label. */
function legacyBackup() {
  const seed = fresh();
  const { unaided_success_contexts: _contexts, mastery_requirements: _requirements, evidence: _evidence, ...oldFields } = seed;
  const skills = createLearnerSkillVector();
  return legacyProgressBackupV1Schema.parse({
    format: 'yokdil-fen-progress', schema_version: 1, scheduler_version: 'ass-v1', exported_at: 21 * DAY_MS,
    lexical_store: [{
      ...oldFields, lexical_state: 'MASTERED', mastery_score: 100, encounter_count: 3,
      unaided_correct_count: 3, contexts_seen: ['exposure-a', 'exposure-b', 'exposure-c'],
      last_seen_at: 21 * DAY_MS, last_success_at: 21 * DAY_MS, response_time_avg_ms: 3_000,
      evidence: { delayed_unaided_correct_count: 1, max_unaided_delay_days: 14,
        distractor_correct_count: 3, distractor_attempt_count: 3 },
    }],
    question_attempts: [{
      id: 'v1-attempt', question_id: 'q-1', session_id: 'session-1', lexical_ids: ['inhibit'],
      skill_ids: ['VOCAB_CONTEXT'], context_id: 'exposure-c', outcome: 'unassisted',
      response_ms: 3_000, attempted_at: 21 * DAY_MS,
      lexical_review: { grade: 3, assistance_used: false, user_lexical_factor: 1,
        distractor_test: { word: 'inhabit', resisted: true }, tested_collocation: null },
    }],
    daily_sessions: [{
      id: 'session-1', date: '2026-10-01', time_zone: 'Europe/Istanbul', started_at: 0,
      ended_at: 21 * DAY_MS, active_ms: 3_000,
      skills: { ...skills, VOCAB_CONTEXT: { ...skills.VOCAB_CONTEXT, mastery: 80 },
        MAIN_IDEA: { ...skills.MAIN_IDEA, mastery: 0.8 } },
    }],
  });
}

async function createV1Database(name: string, backup: ReturnType<typeof legacyBackup>): Promise<Dexie> {
  const legacy = track(new Dexie(name));
  legacy.version(1).stores({
    lexical_store: '&word_id, lemma, tier, lexical_state, next_review_date, review_priority',
    question_attempts: '&id, question_id, session_id, attempted_at, *lexical_ids, *skill_ids',
    daily_sessions: '&id, date, started_at',
  });
  await legacy.table('lexical_store').bulkAdd(backup.lexical_store);
  await legacy.table('question_attempts').bulkAdd(backup.question_attempts);
  await legacy.table('daily_sessions').bulkAdd(backup.daily_sessions);
  legacy.close();
  return legacy;
}

describe('explicit schema v1 -> v2 migration', () => {
  it('never copies v1 exposure contexts to success contexts, even when an old attempt is unaided', () => {
    const legacy = legacyBackup();
    const before = structuredClone(legacy);
    const migrated = migrateProgressV1ToV2(legacy);
    const word = migrated.lexical_store[0];
    expect(migrated.schema_version).toBe(2);
    expect(word?.contexts_seen).toEqual(['exposure-a', 'exposure-b', 'exposure-c']);
    expect(word?.unaided_success_contexts).toEqual([]);
    expect(word?.mastery_score).toBe(70.54);
    expect(word?.lexical_state).toBe('FAMILIAR');
    expect(word?.evidence.delayed_unaided_correct_count_14d).toBe(1);
    expect(word?.evidence.delayed_unaided_correct_count_3d).toBe(1);
    expect(migrated.question_attempts).toEqual(legacy.question_attempts);
    expect(legacy).toEqual(before);
  });
  it('converts every v1 percentage exactly once, including fractions below one', () => {
    const migrated = migrateProgressV1ToV2(legacyBackup());
    expect(migrated.daily_sessions[0]?.skills.VOCAB_CONTEXT.mastery).toBe(0.8);
    expect(migrated.daily_sessions[0]?.skills.MAIN_IDEA.mastery).toBe(0.008);
    const parsedAgain = parseProgressBackup(migrated);
    expect(parsedAgain.migrated_from).toBeNull();
    expect(parsedAgain.backup).toEqual(migrated);
  });
  it('requalifies old same-day FAMILIAR and derives only proven three-day evidence', () => {
    const legacy = legacyBackup();
    const word = legacy.lexical_store[0];
    if (word === undefined) throw new Error('Missing fixture');
    const sameDay = { ...legacy, lexical_store: [{ ...word, lexical_state: 'FAMILIAR',
      evidence: { ...word.evidence, delayed_unaided_correct_count: 0, max_unaided_delay_days: 0 } }] };
    const noDelay = migrateProgressV1ToV2(sameDay).lexical_store[0];
    expect(noDelay?.lexical_state).toBe('LEARNING');
    expect(noDelay?.evidence.delayed_unaided_correct_count_3d).toBe(0);
    const threeDays = migrateProgressV1ToV2({ ...legacy, lexical_store: [{ ...word,
      evidence: { ...word.evidence, delayed_unaided_correct_count: 0, max_unaided_delay_days: 3 } }] }).lexical_store[0];
    expect(threeDays?.evidence.delayed_unaided_correct_count_3d).toBe(1);
    expect(threeDays?.evidence.delayed_unaided_correct_count_14d).toBe(0);
  });
  it('imports old backups non-destructively and reports the conversion; retries are idempotent', async () => {
    const database = target();
    const json = JSON.stringify(legacyBackup());
    expect((await importProgressFromJson(json, {}, database)).migrated_from).toBe(1);
    expect((await database.lexical_store.get('inhibit'))?.unaided_success_contexts).toEqual([]);
    expect((await importProgressFromJson(json, {}, database)).unchanged).toBe(3);
    const exported = JSON.parse(await exportProgressToJson(database)) as ProgressBackup;
    expect(exported.schema_version).toBe(2);
    expect(exported.daily_sessions[0]?.skills.VOCAB_CONTEXT.mastery).toBe(0.8);
  });
  it('preserves new evidence, requirements and skill fractions in a v2 round trip', async () => {
    const source = target();
    const destination = target();
    let word: LexicalRecord = { ...fresh(), mastery_requirements: { collocation_required: true, distractor_required: true } };
    for (const [day, context] of [[0, 'a'], [3, 'b'], [17, 'c']] as const) {
      word = scheduleLexicalReview(word, {
        grade: 3, reviewed_at: day * DAY_MS, context_id: context, response_time_ms: 3_000,
        assistance_used: false, tested_collocation: 'inhibit growth', distractor_test: { word: 'inhabit', resisted: true },
      }).record;
    }
    expect(word.lexical_state).toBe('MASTERED');
    await source.lexical_store.add(word);
    const session = migrateProgressV1ToV2(legacyBackup()).daily_sessions[0];
    if (session === undefined) throw new Error('Missing fixture');
    await source.daily_sessions.add(session);
    expect((await importProgressFromJson(await exportProgressToJson(source), {}, destination)).migrated_from).toBeNull();
    expect(await destination.lexical_store.get(word.word_id)).toEqual(word);
    expect(await destination.daily_sessions.get(session.id)).toEqual(session);
  });
  it('rejects percent mastery inside a v2 backup rather than guessing its scale', async () => {
    const database = target();
    const v2 = migrateProgressV1ToV2(legacyBackup());
    const session = legacyBackup().daily_sessions[0];
    await expect(importProgressFromJson(JSON.stringify({ ...v2, daily_sessions: [session] }), {}, database)).rejects.toThrow();
    expect(await database.lexical_store.count()).toBe(0);
  });
  it('rejects masquerading v2 data labeled as v1 without replacing local rows', async () => {
    const database = target();
    await database.lexical_store.add(fresh());
    const v2 = migrateProgressV1ToV2(legacyBackup());
    await expect(importProgressFromJson(JSON.stringify({ ...v2, schema_version: 1 }), {}, database)).rejects.toThrow();
    expect((await database.lexical_store.get('inhibit'))?.lexical_state).toBe('NEW');
  });
});

describe('IndexedDB version upgrade through Dexie', () => {
  it('upgrades existing v1 tables atomically and preserves attempts, IDs and retry behavior', async () => {
    const name = `native-upgrade-${crypto.randomUUID()}`;
    const backup = legacyBackup();
    await createV1Database(name, backup);
    const database = track(new YokdilDatabase(name));
    await database.open();
    expect(database.verno).toBe(2);
    const expected = migrateProgressV1ToV2(backup);
    expect(await database.lexical_store.toArray()).toEqual(expected.lexical_store);
    expect(await database.daily_sessions.toArray()).toEqual(expected.daily_sessions);
    expect(await database.question_attempts.toArray()).toEqual(backup.question_attempts);
    const word = await persistLexicalReview({
      attempt_id: 'v1-attempt', word_id: 'inhibit', question_id: 'q-1', session_id: 'session-1',
      skill_ids: ['VOCAB_CONTEXT'], review: { grade: 3, context_id: 'exposure-c', response_time_ms: 3_000,
        reviewed_at: 21 * DAY_MS, assistance_used: false, distractor_test: { word: 'inhabit', resisted: true } },
    }, database);
    expect(word.unaided_correct_count).toBe(3);
    expect(word.unaided_success_contexts).toEqual([]);
    database.close();
    await database.open();
    expect((await database.daily_sessions.get('session-1'))?.skills.VOCAB_CONTEXT.mastery).toBe(0.8);
  });
  it('aborts a failed v1 upgrade without losing original data or committing version 2', async () => {
    const name = `native-upgrade-failure-${crypto.randomUUID()}`;
    const backup = legacyBackup();
    const legacy = await createV1Database(name, backup);
    await legacy.open();
    await legacy.table('daily_sessions').update('session-1', { 'skills.VOCAB_CONTEXT.mastery': 101 });
    const beforeWords = await legacy.table('lexical_store').toArray();
    const beforeSessions = await legacy.table('daily_sessions').toArray();
    legacy.close();
    const database = track(new YokdilDatabase(name));
    await expect(database.open()).rejects.toThrow();
    database.close();
    await legacy.open();
    expect(legacy.verno).toBe(1);
    expect(await legacy.table('lexical_store').toArray()).toEqual(beforeWords);
    expect(await legacy.table('daily_sessions').toArray()).toEqual(beforeSessions);
    expect(await legacy.table('question_attempts').toArray()).toEqual(backup.question_attempts);
  });
});
