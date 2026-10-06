import { afterEach, describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { EvidenceDatabase, persistAttemptWithEvidence } from '../../../src/services/evidence/db';
import { createAttemptDraft, submitQuestionAttempt } from '../../../src/services/questions/attempts';
import { loadNextBestActionPlan, PRIORITY_DAY_MS } from '../../../src/priority';
import type { TrainingAction } from '../../../src/types/priority';

const opened: EvidenceDatabase[] = [];
const NOW = 30 * PRIORITY_DAY_MS;
const actions: readonly TrainingAction[] = [{ id: 'vocab-assessment', title: 'Kelime bağlamı değerlendirmesi',
  kind: 'DIAGNOSTIC', format: 'QUESTION_SET', available: true, expected_minutes: 5, targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 1 }] }];
function database(): EvidenceDatabase {
  const db = new EvidenceDatabase(`phase4-${crypto.randomUUID()}`); opened.push(db); return db;
}
afterEach(async () => { for (const db of opened.splice(0)) await db.delete(); });
async function seed(db: EvidenceDatabase): Promise<void> {
  const question = initialQuestions[0];
  if (question === undefined) throw new Error('Missing question');
  const attempt = submitQuestionAttempt(question, { ...createAttemptDraft(), selected_option: question.correct_option },
    { id: 'first', session_id: null, attempted_at: NOW, response_time_ms: 2_000 });
  await persistAttemptWithEvidence(question, attempt, {}, db);
}
async function snapshot(db: EvidenceDatabase): Promise<string> {
  return JSON.stringify(await Promise.all(db.tables.map(async (table) => ({ name: table.name, rows: await table.toArray() as unknown[] }))));
}

describe('Read-only v4 planning integration', () => {
  it('audits evidence and derives model and coverage from one snapshot without writes or a schema upgrade', async () => {
    const db = database(); await seed(db);
    const before = await snapshot(db);
    const request = { questions: initialQuestions, actions, as_of: NOW, available_minutes: 10 };
    const plan = await loadNextBestActionPlan(request, db);
    expect(plan.selected?.action.id).toBe('vocab-assessment');
    expect(plan.score_leak_map.skills.find((s) => s.skill_id === 'VOCAB_CONTEXT')?.coverage?.informative_attempt_count).toBe(1);
    expect(await loadNextBestActionPlan(request, db)).toEqual(plan);
    expect(await snapshot(db)).toBe(before); expect(db.verno).toBe(4); expect(db.tables).toHaveLength(7);
  });
  it('does not produce a plan from tampered Phase 3 evidence', async () => {
    const db = database(); await seed(db);
    const first = (await db.skill_evidence.toArray())[0];
    if (first === undefined) throw new Error('Missing evidence');
    await db.skill_evidence.put({ ...first, strength: first.strength / 2 });
    const before = await snapshot(db);
    await expect(loadNextBestActionPlan({ questions: initialQuestions, actions, as_of: NOW, available_minutes: 10 }, db)).rejects.toThrow('does not match');
    expect(await snapshot(db)).toBe(before);
  });
  it('rejects an incomplete source catalog and never writes fallback learner values', async () => {
    const db = database(); await seed(db); const before = await snapshot(db);
    await expect(loadNextBestActionPlan({ questions: [], actions, as_of: NOW, available_minutes: 10 }, db)).rejects.toThrow();
    expect(await snapshot(db)).toBe(before);
  });
});
