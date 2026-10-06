import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { createLearnerSkillVector, SKILL_IDS } from '../../../src/types/learner';
import type { Question } from '../../../src/types/question';
import { extractSkillEvidence } from '../../../src/services/evidence/extractEvidence';
import { updateLearnerSkillVector } from '../../../src/services/evidence/updateLearnerModel';
import { createAttemptDraft, submitQuestionAttempt } from '../../../src/services/questions/attempts';
import { buildScoreLeakMap, deriveEvidenceCoverage, planNextBestAction, PRIORITY_DAY_MS } from '../../../src/priority';

const NOW = 30 * PRIORITY_DAY_MS;
function question(): Question {
  const q = initialQuestions.find((q) => q.id === 'sentence-concession');
  if (q === undefined) throw new Error('Missing fixture'); return q;
}
function evidence(id: string, assisted = false, transfer = false) {
  const q = question();
  const a = submitQuestionAttempt(q, { ...createAttemptDraft(), selected_option: q.correct_option, hints_used_count: assisted ? 1 : 0 },
    { id, session_id: null, attempted_at: NOW, response_time_ms: 2_000 });
  return extractSkillEvidence(q, a, { identified_relation: { relation: 'CONCESSION', recorded_at: NOW - 1_000 },
    ...(transfer ? { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } } : {}) });
}

describe('Phase 3 to Phase 4 coverage bridge', () => {
  it('returns known empty coverage for all 13 skills without history', () => {
    const result = deriveEvidenceCoverage([]);
    expect(Object.keys(result)).toEqual([...SKILL_IDS]);
    expect(result.PACING_STAMINA.informative_attempt_count).toBe(0);
    expect(result.PACING_STAMINA.last_informative_at).toBeNull();
  });
  it('counts distinct attempts, questions and families rather than event rows', () => {
    const first = evidence('one');
    const rows = [...first, ...first, ...evidence('two', true), ...evidence('three', false, true)];
    const result = deriveEvidenceCoverage(rows).CONNECTOR_DISCOURSE;
    expect(first.filter((e) => e.skill_id === 'CONNECTOR_DISCOURSE')).toHaveLength(2);
    expect(result).toEqual({ informative_attempt_count: 3, question_count: 1, family_count: 1,
      unaided_attempt_count: 2, transfer_attempt_count: 1, last_informative_at: NOW });
  });
  it('ignores neutral and zero-reliability records when measuring informative coverage', () => {
    const rows = evidence('one').map((e) => ({ ...e, reliability: 0 }));
    expect(deriveEvidenceCoverage(rows).CONNECTOR_DISCOURSE.informative_attempt_count).toBe(0);
    const q = question();
    const a = submitQuestionAttempt(q, { ...createAttemptDraft(), selected_option: 'B' }, { id: 'wrong', session_id: null, attempted_at: NOW, response_time_ms: 2_000 });
    const neutral = extractSkillEvidence(q, { ...a, error_attribution: { probabilities: { CARELESS: 1 }, primary_category: 'CARELESS', confidence: 0 } });
    expect(neutral.every((e) => e.direction === 'NEUTRAL')).toBe(true);
    expect(deriveEvidenceCoverage(neutral).CONNECTOR_DISCOURSE.informative_attempt_count).toBe(0);
  });
  it('rejects conflicting retry evidence instead of inflating coverage', () => {
    const rows = evidence('one'); const first = rows[0];
    if (first === undefined) throw new Error('Missing fixture');
    expect(() => deriveEvidenceCoverage([...rows, { ...first, strength: first.strength / 2 }])).toThrow('Conflicting');
  });
  it('integrates the frozen learner model into planning without changing history or learner metrics', () => {
    const history = [...evidence('one'), ...evidence('two', true)];
    const learner = updateLearnerSkillVector(createLearnerSkillVector(), history, NOW);
    const before = JSON.stringify({ learner, history });
    const coverage = deriveEvidenceCoverage(history);
    const context = { as_of: NOW, coverage };
    const map = buildScoreLeakMap(learner, context);
    const plan = planNextBestAction(learner, [{ id: 'connector-diagnostic', title: 'Bağlaç ilişkisi değerlendirmesi', kind: 'DIAGNOSTIC', format: 'QUESTION_SET',
      available: true, expected_minutes: 5, targets: [{ skill_id: 'CONNECTOR_DISCOURSE', weight: 1 }] }], context, 10);
    expect(plan.score_leak_map).toEqual(map);
    expect(plan.selected?.action.id).toBe('connector-diagnostic');
    expect(JSON.stringify({ learner, history })).toBe(before);
    expect(Object.isFrozen(coverage.CONNECTOR_DISCOURSE)).toBe(true);
    expect(map.skills.find((s) => s.skill_id === 'PACING_STAMINA')?.reasons).not.toContain('SUPPORTED_SKILL_GAP');
  });
});
