import { afterEach, describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { createLearnerSkillVector } from '../../../src/types/learner';
import { YokdilDatabase, persistLexicalReview, seedInitialVocabulary } from '../../../src/services/db';
import { createAttemptDraft, submitQuestionAttempt, updateDraft } from '../../../src/services/questions/attempts';
import { exportSolverProgressToJson, getQuestionAttempts, importSolverProgressFromJson, persistQuestionAttempt, persistSolverAttempts, QuestionDatabase } from '../../../src/services/questions/db';
import type { QuestionAttempt } from '../../../src/types/question';

const opened: YokdilDatabase[] = [];
const database = (): QuestionDatabase => { const db = new QuestionDatabase(`phase2-${crypto.randomUUID()}`); opened.push(db); return db; };
const q = initialQuestions[0];
if (q === undefined) throw new Error('Missing question');
const question = q;
function attempt(id = 'a-1'): QuestionAttempt {
  return submitQuestionAttempt(question, updateDraft(createAttemptDraft(), { type: 'select', option: 'B' }), { id, session_id: null, response_time_ms: 2_000, attempted_at: 2_000 });
}
afterEach(async () => { for (const db of opened.splice(0)) await db.delete(); });

describe('Additive v3 persistence', () => {
  it('preserves every Phase 1 v2 row byte-for-byte across upgrade', async () => {
    const name = `upgrade-${crypto.randomUUID()}`;
    const old = new YokdilDatabase(name);
    await seedInitialVocabulary(old, 0);
    await old.daily_sessions.add({ id: 'session-1', date: '2026-10-02', time_zone: 'Europe/Istanbul', started_at: 0, ended_at: null, active_ms: 0, skills: createLearnerSkillVector() });
    await persistLexicalReview({ attempt_id: 'lexical-1', question_id: question.id, word_id: 'inhibit', session_id: 'session-1', skill_ids: ['VOCAB_CONTEXT'],
      review: { grade: 3, reviewed_at: 1_000, response_time_ms: 500, context_id: 'context-1', assistance_used: false } }, old);
    const words = await old.lexical_store.toArray();
    const lexicalAttempts = await old.question_attempts.toArray();
    const sessions = await old.daily_sessions.toArray();
    expect(old.verno).toBe(2);
    old.close();
    const next = new QuestionDatabase(name);
    opened.push(next);
    await next.open();
    expect(next.verno).toBe(3);
    expect(await next.lexical_store.toArray()).toEqual(words);
    expect(await next.question_attempts.toArray()).toEqual(lexicalAttempts);
    expect(await next.daily_sessions.toArray()).toEqual(sessions);
    expect(await next.solver_attempts.count()).toBe(0);
    await persistQuestionAttempt({ ...attempt(), session_id: 'session-1' }, question, next);
    expect(await next.question_attempts.toArray()).toEqual(lexicalAttempts);
    expect(await next.lexical_store.toArray()).toEqual(words);
  });
  it('deduplicates concurrent exact retries and rejects conflicting attempt IDs', async () => {
    const db = database();
    await Promise.all([persistQuestionAttempt(attempt(), question, db), persistQuestionAttempt(attempt(), question, db)]);
    expect(await db.solver_attempts.count()).toBe(1);
    await expect(persistQuestionAttempt({ ...attempt(), confidence_level: 'HIGH' }, question, db)).rejects.toThrow('reused');
    expect((await db.solver_attempts.get('a-1'))?.confidence_level).toBeNull();
    await persistQuestionAttempt(attempt('a-2'), question, db);
    expect(await db.solver_attempts.count()).toBe(2);
  });
  it('rolls back earlier batch inserts when a later attempt fails validation', async () => {
    const db = database();
    await expect(persistSolverAttempts([attempt(), { ...attempt('a-2'), response_time_ms: -1 }], [question], db)).rejects.toThrow();
    expect(await db.solver_attempts.count()).toBe(0);
    await expect(persistQuestionAttempt({ ...attempt(), session_id: 'missing' }, question, db)).rejects.toThrow('Unknown session');
    expect(await db.solver_attempts.count()).toBe(0);
  });
  it('returns immutable validated records without affecting historical lexical evidence', async () => {
    const db = database();
    await persistQuestionAttempt(attempt(), question, db);
    const rows = await getQuestionAttempts(question.id, db);
    expect(Object.isFrozen(rows)).toBe(true);
    expect(Object.isFrozen(rows[0])).toBe(true);
    expect(await db.question_attempts.count()).toBe(0);
  });
});
describe('v3 envelope backup', () => {
  it('round-trips all four tables and preserves exact retry semantics', async () => {
    const source = database();
    const target = database();
    await seedInitialVocabulary(source, 0);
    await source.daily_sessions.add({ id: 's', date: '2026-10-02', time_zone: 'Europe/Istanbul', started_at: 0, ended_at: null, active_ms: 0, skills: createLearnerSkillVector() });
    await persistLexicalReview({ attempt_id: 'l', word_id: 'inhibit', question_id: question.id, session_id: 's', skill_ids: ['VOCAB_CONTEXT'],
      review: { grade: 1, context_id: 'c', response_time_ms: 800, reviewed_at: 1_000, assistance_used: true } }, source);
    await persistQuestionAttempt({ ...attempt(), session_id: 's' }, question, source);
    const json = await exportSolverProgressToJson(initialQuestions, source);
    expect(await importSolverProgressFromJson(json, initialQuestions, target)).toEqual({ solver_inserted: 1 });
    expect(await target.lexical_store.toArray()).toEqual(await source.lexical_store.toArray());
    expect(await target.question_attempts.toArray()).toEqual(await source.question_attempts.toArray());
    expect(await target.daily_sessions.toArray()).toEqual(await source.daily_sessions.toArray());
    expect(await target.solver_attempts.toArray()).toEqual(await source.solver_attempts.toArray());
    expect(await importSolverProgressFromJson(json, initialQuestions, target)).toEqual({ solver_inserted: 0 });
  });
  it('rolls back Phase 1 additions when a solver conflict aborts import', async () => {
    const source = database();
    const target = database();
    await seedInitialVocabulary(source, 0);
    await persistQuestionAttempt(attempt(), question, source);
    await persistQuestionAttempt({ ...attempt(), confidence_level: 'LOW' }, question, target);
    const json = await exportSolverProgressToJson(initialQuestions, source);
    await expect(importSolverProgressFromJson(json, initialQuestions, target)).rejects.toThrow('reused');
    expect(await target.lexical_store.count()).toBe(0);
    expect((await target.solver_attempts.get('a-1'))?.confidence_level).toBe('LOW');
  });
  it('rejects malformed backups and unknown question references without partial imports', async () => {
    const source = database();
    const target = database();
    await seedInitialVocabulary(source, 0);
    await persistQuestionAttempt(attempt(), question, source);
    const json = await exportSolverProgressToJson(initialQuestions, source);
    await expect(importSolverProgressFromJson(json, [], target)).rejects.toThrow('Unknown question');
    await expect(importSolverProgressFromJson('{', initialQuestions, target)).rejects.toThrow();
    expect(await target.lexical_store.count()).toBe(0);
    expect(await target.solver_attempts.count()).toBe(0);
  });
});
