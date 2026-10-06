import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createInitialVocab } from '../../src/data/initialVocab';
import { createLearnerSkillVector } from '../../src/types/learner';
import type { ProgressBackup } from '../../src/types/progress';
import { exportProgressToJson, importProgressFromJson, persistLexicalReview, seedInitialVocabulary, YokdilDatabase } from '../../src/services/db';
import type { PersistReviewInput } from '../../src/services/db';

let database: YokdilDatabase;
let target: YokdilDatabase;
beforeEach(() => {
  database = new YokdilDatabase(`test-source-${crypto.randomUUID()}`);
  target = new YokdilDatabase(`test-target-${crypto.randomUUID()}`);
});
afterEach(async () => { await database.delete(); await target.delete(); });

const input = (attempt_id = 'attempt-1'): PersistReviewInput => ({
  attempt_id, word_id: 'inhibit', question_id: 'q-1', session_id: null,
  skill_ids: ['VOCAB_CONTEXT'],
  review: { grade: 3, context_id: 'biology', response_time_ms: 3_000, reviewed_at: 1_000, assistance_used: false },
});

describe('local-first persistence', () => {
  it('seeds idempotently without overwriting existing progress', async () => {
    expect(await seedInitialVocabulary(database, 0)).toBe(12);
    const learned = await persistLexicalReview(input(), database);
    expect(await seedInitialVocabulary(database, 10_000)).toBe(0);
    expect(await database.lexical_store.get('inhibit')).toEqual(learned);
  });
  it('serializes duplicate attempts and concurrent distinct reviews without losing counters', async () => {
    await seedInitialVocabulary(database, 0);
    await Promise.all([persistLexicalReview(input(), database), persistLexicalReview(input(), database)]);
    expect(await database.question_attempts.count()).toBe(1);
    expect((await database.lexical_store.get('inhibit'))?.unaided_correct_count).toBe(1);
    await Promise.all([persistLexicalReview(input('a-2'), database), persistLexicalReview(input('a-3'), database)]);
    expect((await database.lexical_store.get('inhibit'))?.unaided_correct_count).toBe(3);
  });
  it('rejects reused attempt IDs with different scheduling evidence', async () => {
    await seedInitialVocabulary(database, 0);
    await persistLexicalReview(input(), database);
    await expect(persistLexicalReview({ ...input(), review: { ...input().review, grade: 2 } }, database)).rejects.toThrow('reused');
    expect((await database.lexical_store.get('inhibit'))?.unaided_correct_count).toBe(1);
  });
  it('rolls back the attempt if storing lexical progress fails', async () => {
    await seedInitialVocabulary(database, 0);
    vi.spyOn(database.lexical_store, 'put').mockRejectedValueOnce(new Error('quota exceeded'));
    await expect(persistLexicalReview(input(), database)).rejects.toThrow('quota exceeded');
    expect(await database.question_attempts.count()).toBe(0);
    expect((await database.lexical_store.get('inhibit'))?.unaided_correct_count).toBe(0);
  });
});

describe('JSON backup and atomic import', () => {
  it('round-trips all three tables and thirteen skill dimensions', async () => {
    await seedInitialVocabulary(database, 0);
    await database.daily_sessions.add({ id: 'session-1', date: '2026-10-01', time_zone: 'Europe/Istanbul',
      started_at: 0, ended_at: 2_000, active_ms: 1_000, skills: createLearnerSkillVector() });
    await persistLexicalReview({ ...input(), session_id: 'session-1' }, database);
    const json = await exportProgressToJson(database);
    const result = await importProgressFromJson(json, {}, target);
    expect(result.inserted).toEqual({ lexical_store: 12, question_attempts: 1, daily_sessions: 1 });
    expect(await target.lexical_store.toArray()).toEqual(await database.lexical_store.toArray());
    expect(await target.daily_sessions.toArray()).toEqual(await database.daily_sessions.toArray());
    expect(await target.question_attempts.toArray()).toEqual(await database.question_attempts.toArray());
    expect((await importProgressFromJson(json, {}, target)).unchanged).toBe(14);
  });
  it.each(['not json', '{"schema_version":99}', '{"format":"yokdil-fen-progress"}'])('rejects malformed/unsupported backup %s without edits', async (json) => {
    await seedInitialVocabulary(target, 0);
    await expect(importProgressFromJson(json, {}, target)).rejects.toThrow();
    expect(await target.lexical_store.count()).toBe(12);
  });
  it('rejects negative counters, unknown keys, duplicate IDs and broken references', async () => {
    await seedInitialVocabulary(database, 0);
    await persistLexicalReview(input(), database);
    const backup = JSON.parse(await exportProgressToJson(database)) as ProgressBackup;
    const first = backup.lexical_store[0];
    if (first === undefined) throw new Error('Missing fixture');
    const invalid = [
      { ...backup, lexical_store: [{ ...first, incorrect_count: -1 }] },
      { ...backup, lexical_store: [{ ...first, sneaky: true }] },
      { ...backup, lexical_store: [first, first] },
      { ...backup, lexical_store: [] },
    ];
    for (const candidate of invalid) {
      await expect(importProgressFromJson(JSON.stringify(candidate), {}, target)).rejects.toThrow();
      expect(await target.lexical_store.count()).toBe(0);
      expect(await target.question_attempts.count()).toBe(0);
    }
  });
  it('defaults to conflict rejection and supports explicit preservation of local rows', async () => {
    await seedInitialVocabulary(database, 0);
    await seedInitialVocabulary(target, 0);
    await persistLexicalReview(input(), target);
    const before = await target.lexical_store.get('inhibit');
    const json = await exportProgressToJson(database);
    await expect(importProgressFromJson(json, {}, target)).rejects.toThrow('conflict');
    const result = await importProgressFromJson(json, { on_conflict: 'keep-local' }, target);
    expect(result.conflicts).toContain('lexical_store:inhibit');
    expect(await target.lexical_store.get('inhibit')).toEqual(before);
    expect(await target.question_attempts.count()).toBe(1);
  });
  it('rolls back all import tables when a later write fails', async () => {
    await seedInitialVocabulary(database, 0);
    await persistLexicalReview(input(), database);
    const json = await exportProgressToJson(database);
    vi.spyOn(target.question_attempts, 'bulkAdd').mockRejectedValueOnce(new Error('disk full'));
    await expect(importProgressFromJson(json, {}, target)).rejects.toThrow('disk full');
    expect(await target.lexical_store.count()).toBe(0);
    expect(await target.question_attempts.count()).toBe(0);
  });
  it('does not confuse order of object fields with a data conflict', async () => {
    const word = createInitialVocab(0)[0];
    if (word === undefined) throw new Error('Missing fixture');
    await database.lexical_store.add(word);
    await target.lexical_store.add(Object.fromEntries(Object.entries(word).reverse()) as unknown as typeof word);
    expect((await importProgressFromJson(await exportProgressToJson(database), {}, target)).unchanged).toBe(1);
  });
});
