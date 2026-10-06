import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { createInitialVocab } from '../../../src/data/initialVocab';
import { createLearnerSkillVector, SKILL_IDS } from '../../../src/types/learner';
import { aggregateEvidence } from '../../../src/services/evidence/aggregateEvidence';
import { extractConfidenceCalibration, EVIDENCE_DAY_MS } from '../../../src/services/evidence/calibration';
import { extractSkillEvidence } from '../../../src/services/evidence/extractEvidence';
import { mapQuestionSkills, primaryQuestionSkill } from '../../../src/services/evidence/mapping';
import { updateLearnerSkillVector } from '../../../src/services/evidence/updateLearnerModel';
import { skillEvidenceSchema } from '../../../src/services/evidence/validation';
import { tacticalSolvers } from '../../../src/services/questions/strategies';
import { attempt, fractionalAttempt, question, TIME, vocab } from './fixtures';

describe('Evidence extraction v1', () => {
  it('correct unaided evidence is stronger than assisted evidence', () => {
    const plain = vocab(extractSkillEvidence(question(), attempt()));
    const assisted = vocab(extractSkillEvidence(question(), attempt('hint', true, { hints_used_count: 1 })));
    expect(plain.strength).toBeGreaterThan(assisted.strength);
    expect(assisted.strength).toBeGreaterThan(0);
    expect(assisted.assisted).toBe(true);
  });
  it('three hints and poor process reduce, but never reverse, correct evidence', () => {
    const q = { ...question(), global_benchmark_ms: 1_000 };
    const weak = extractSkillEvidence(q, { ...attempt('weak', true, { hints_used_count: 3, option_change_count: 3, words_clicked: ['inhibit'], confidence_level: 'LOW' }), response_time_ms: 30_000 });
    expect(weak.every((e) => e.direction === 'POSITIVE')).toBe(true);
    expect(vocab(weak).strength).toBeLessThan(vocab(extractSkillEvidence(q, attempt())).strength / 2);
  });
  it('wrong responses do not penalize every related skill equally', () => {
    const q = { ...question(), skill_ids: ['VOCAB_CONTEXT', 'CONNECTOR_DISCOURSE', 'TENSE_ASPECT'] as const };
    const rows = extractSkillEvidence(q, fractionalAttempt('fractional', q));
    expect(vocab(rows).direction).toBe('NEGATIVE');
    expect(rows.find((e) => e.skill_id === 'TENSE_ASPECT')?.direction).toBe('NEUTRAL');
    expect(rows.find((e) => e.skill_id === 'CONNECTOR_DISCOURSE')?.strength).toBe(0);
  });
  it('0.4 vocabulary attribution creates fractional negative evidence', () => {
    const e = vocab(extractSkillEvidence(question(), fractionalAttempt()));
    expect(e.attribution_weight).toBeCloseTo(0.4);
    expect(e.strength).toBeCloseTo(0.8 * 0.4 * e.mapping_weight);
    expect(e.reliability).toBeLessThan(0.7);
  });
  it('assistance also discounts negative evidence without erasing historical errors', () => {
    const unaided = fractionalAttempt();
    const assisted = { ...unaided, id: 'assisted-wrong', hints_used_count: 1 };
    const first = vocab(extractSkillEvidence(question(), unaided));
    const second = vocab(extractSkillEvidence(question(), assisted));
    expect(second.strength).toBeLessThan(first.strength);
    expect(second.attribution_weight).toBeCloseTo(first.attribution_weight ?? 0);
  });
  it('word click alone cannot create full vocabulary negative evidence', () => {
    const rows = extractSkillEvidence(question(), attempt('click', false, { words_clicked: ['inhibit'] }));
    expect(vocab(rows).strength).toBeLessThan(0.4);
    expect(extractSkillEvidence(question(), attempt('correct-click', true, { words_clicked: ['inhibit'] })).every((e) => e.direction === 'POSITIVE')).toBe(true);
  });
  it('LOW + correct remains positive and confidence is retained separately', () => {
    const a = attempt('low', true, { confidence_level: 'LOW' });
    expect(extractSkillEvidence(question(), a).every((e) => e.direction === 'POSITIVE')).toBe(true);
    expect(extractConfidenceCalibration(a)).toEqual({ attempt_id: 'low', confidence: 'LOW', correct: true });
    expect(extractConfidenceCalibration(attempt('null', true, { confidence_level: null }))).toBeNull();
    expect(extractConfidenceCalibration(attempt('high-wrong', false))?.correct).toBe(false);
  });
  it('wrong final answer plus valid eliminations and observed relation yields mixed evidence', () => {
    const q = question('sentence-concession');
    const a = attempt('tactics', false, {}, q);
    const options = q.options.filter((o) => o.id !== q.correct_option && o.id !== a.selected_option && tacticalSolvers[q.family].verify(q, o.id, { eliminated_options: [] }).verdict === 'REJECTED').map((o) => o.id);
    expect(options).toHaveLength(3);
    const rows = extractSkillEvidence(q, { ...a, eliminated_options: options }, { identified_relation: { relation: 'CONCESSION', recorded_at: TIME - 500 } });
    expect(rows.some((e) => e.skill_id === 'CONNECTOR_DISCOURSE' && e.source === 'TACTICAL_DECISION' && e.direction === 'POSITIVE')).toBe(true);
    expect(rows.some((e) => e.skill_id === 'SENTENCE_COMPLETION' && e.direction === 'NEGATIVE')).toBe(true);
    expect(rows.some((e) => e.skill_id === 'SENTENCE_COMPLETION' && e.source === 'TACTICAL_DECISION')).toBe(true);
  });
  it('does not infer learner reasoning from authored relations or reward eliminating the right option', () => {
    const q = question('sentence-concession');
    const a = attempt('bad-elimination', false, { eliminated_options: ['A', 'C', 'D', 'E'] }, q);
    expect(extractSkillEvidence(q, a).some((e) => e.source === 'TACTICAL_DECISION')).toBe(false);
  });
  it('confirmed transfer has more reliability than equivalent practice', () => {
    const a = attempt();
    const transfer = vocab(extractSkillEvidence(question(), a, { transfer: { unseen: true, exam_like: true, prior_practice_at: 0 } }));
    expect(transfer.evidence_kind).toBe('TRANSFER');
    expect(transfer.reliability).toBeGreaterThan(vocab(extractSkillEvidence(question(), a)).reliability);
  });
  it.each(['seen', 'assisted', 'recent', 'non-exam'] as const)('does not upgrade %s practice to transfer', (condition) => {
    const a = attempt('practice', true, { hints_used_count: condition === 'assisted' ? 1 : 0 });
    const rows = extractSkillEvidence(question(), a, { transfer: { unseen: condition !== 'seen', exam_like: condition !== 'non-exam', prior_practice_at: condition === 'recent' ? TIME - EVIDENCE_DAY_MS : 0 } });
    expect(rows.every((e) => e.evidence_kind === 'PRACTICE' && e.transfer_level === 0)).toBe(true);
  });
  it('isolated slow questions never produce pacing evidence even if metadata declares that skill', () => {
    const q = { ...question(), skill_ids: ['VOCAB_CONTEXT', 'PACING_STAMINA'] as const, global_benchmark_ms: 1_000 };
    const rows = extractSkillEvidence(q, { ...attempt(), response_time_ms: 500_000 });
    expect(rows.some((e) => e.skill_id === 'PACING_STAMINA')).toBe(false);
    expect(updateLearnerSkillVector(createLearnerSkillVector(), rows).PACING_STAMINA).toEqual(createLearnerSkillVector().PACING_STAMINA);
  });
  it('preserves attempts, lexical records, question metadata and solver analyses', () => {
    const q = question();
    const a = attempt();
    const words = createInitialVocab(0);
    const analysis = tacticalSolvers[q.family].triage(q);
    const before = JSON.stringify({ q, a, words, analysis });
    const rows = extractSkillEvidence(q, a);
    expect(JSON.stringify({ q, a, words, analysis })).toBe(before);
    expect(Object.isFrozen(rows)).toBe(true);
    expect(Object.isFrozen(rows[0])).toBe(true);
  });
  it('maps all non-pacing skills across fixtures using subtype, declared skills and tactical focus', () => {
    const skills = new Set(initialQuestions.flatMap((q) => mapQuestionSkills(q).map((m) => m.skill_id)));
    expect([...skills].sort()).toEqual(SKILL_IDS.filter((s) => s !== 'PACING_STAMINA').sort());
    expect(primaryQuestionSkill(question('reading-main'))).toBe('MAIN_IDEA');
    expect(primaryQuestionSkill(question('reading-detail'))).toBe('READING_DETAIL');
    expect(primaryQuestionSkill(question('reading-reference'))).toBe('COHESION_COHERENCE');
    const mapping = mapQuestionSkills(question('sentence-concession'));
    expect(mapping.some((m) => m.skill_id === 'TENSE_ASPECT')).toBe(true);
    expect(new Set(mapping.map((m) => m.weight)).size).toBeGreaterThan(1);
    expect(mapping.reduce((sum, m) => sum + m.weight, 0)).toBeCloseTo(1);
  });
});

describe('Historical learner aggregation', () => {
  const initial = createLearnerSkillVector();
  it('one attempt cannot move mastery from zero to near one', () => {
    const next = updateLearnerSkillVector(initial, extractSkillEvidence(question(), attempt()));
    expect(next.VOCAB_CONTEXT.mastery).toBeGreaterThan(0);
    expect(next.VOCAB_CONTEXT.mastery).toBeLessThan(0.12);
    expect(initial.VOCAB_CONTEXT.mastery).toBe(0);
  });
  it('retains bounded mastery and uncertainty over substantial mixed history', () => {
    const rows = Array.from({ length: 250 }, (_, i) => extractSkillEvidence(question(), attempt(`history-${i}`, i % 3 !== 0, { hints_used_count: i % 2 }))).flat();
    const next = updateLearnerSkillVector(initial, rows);
    for (const metric of Object.values(next)) {
      expect(metric.mastery).toBeGreaterThanOrEqual(0); expect(metric.mastery).toBeLessThanOrEqual(1);
      expect(metric.uncertainty).toBeGreaterThanOrEqual(0); expect(metric.uncertainty).toBeLessThanOrEqual(1);
    }
    expect(next.VOCAB_CONTEXT.uncertainty).toBeGreaterThanOrEqual(0.35);
    const mass = aggregateEvidence(rows).find((m) => m.skill_id === 'VOCAB_CONTEXT');
    expect(mass?.positive_mass).toBeGreaterThan(0); expect(mass?.negative_mass).toBeGreaterThan(0);
  });
  it('decreases only related uncertainty as evidence accumulates', () => {
    const first = extractSkillEvidence(question(), attempt());
    const more = [...first, ...extractSkillEvidence(question(), attempt('a-2'))];
    const one = updateLearnerSkillVector(initial, first);
    const two = updateLearnerSkillVector(one, more);
    expect(one.VOCAB_CONTEXT.uncertainty).toBeLessThan(1);
    expect(two.VOCAB_CONTEXT.uncertainty).toBeLessThan(one.VOCAB_CONTEXT.uncertainty);
    expect(two.READING_INFERENCE).toEqual(initial.READING_INFERENCE);
  });
  it.each([false, true])('aggregates historical accuracy with assisted=%s separately', (assisted) => {
    const changes = { hints_used_count: assisted ? 1 : 0 };
    const rows = [attempt('correct-1', true, changes), attempt('correct-2', true, changes), attempt('wrong', false, changes)].flatMap((a) => extractSkillEvidence(question(), a));
    const metrics = updateLearnerSkillVector(initial, rows).VOCAB_CONTEXT;
    expect(assisted ? metrics.assisted_accuracy : metrics.unaided_accuracy).toBeCloseTo(2 / 3);
    expect(assisted ? metrics.unaided_accuracy : metrics.assisted_accuracy).toBe(0);
  });
  it('uses fractional attribution for error_rate rather than counting a full error', () => {
    const rows = extractSkillEvidence(question(), fractionalAttempt());
    expect(updateLearnerSkillVector(initial, rows).VOCAB_CONTEXT.error_rate).toBeCloseTo(0.4);
    expect(updateLearnerSkillVector(initial, [...rows, ...extractSkillEvidence(question(), attempt())]).VOCAB_CONTEXT.error_rate).toBeCloseTo(0.2);
  });
  it('deduplicates exact IDs and is independent of input order or current snapshot', () => {
    const rows = [...extractSkillEvidence(question(), attempt()), ...extractSkillEvidence(question(), attempt('wrong', false))];
    const next = updateLearnerSkillVector(initial, rows);
    expect(updateLearnerSkillVector(next, [...rows].reverse())).toEqual(next);
    expect(updateLearnerSkillVector(initial, [...rows, ...rows])).toEqual(next);
    const first = vocab(rows);
    expect(() => aggregateEvidence([...rows, { ...first, strength: first.strength / 2 }])).toThrow('Conflicting');
    expect(() => updateLearnerSkillVector(next, extractSkillEvidence(question(), attempt()))).toThrow('Full evidence history');
  });
  it('gives recent evidence a modest premium and rejects a backwards evaluation time', () => {
    const recent = extractSkillEvidence(question(), attempt());
    const old = extractSkillEvidence(question(), { ...attempt('old'), attempted_at: 0 });
    const r = aggregateEvidence(recent, TIME)[0];
    const o = aggregateEvidence(old, TIME)[0];
    expect(r?.positive_mass).toBeGreaterThan(o?.positive_mass ?? 0);
    expect((o?.positive_mass ?? 0) / (r?.positive_mass ?? 1)).toBeGreaterThanOrEqual(0.75);
    expect(() => aggregateEvidence(recent, TIME - 1)).toThrow();
  });
  it('a neutral attribution signal does not pretend to reduce uncertainty', () => {
    const a = { ...fractionalAttempt(), error_attribution: { probabilities: { CARELESS: 1 }, primary_category: 'CARELESS' as const, confidence: 0 } };
    const next = updateLearnerSkillVector(initial, extractSkillEvidence(question(), a));
    expect(next.VOCAB_CONTEXT.uncertainty).toBe(1);
    expect(next.VOCAB_CONTEXT.error_rate).toBe(0);
  });
});

describe('Evidence validation', () => {
  it.each([NaN, Infinity, -Infinity, -0.1, 1.1])('rejects invalid evidence fractions %s', (value) => {
    const row = vocab(extractSkillEvidence(question(), attempt()));
    for (const key of ['strength', 'reliability', 'transfer_level', 'attribution_weight', 'mapping_weight'] as const) {
      expect(skillEvidenceSchema.safeParse({ ...row, [key]: value }).success).toBe(false);
    }
  });
  it('rejects unknown skills, forged IDs, unsupported timed data and invalid transfer contracts', () => {
    const row = vocab(extractSkillEvidence(question(), attempt()));
    for (const edit of [{ skill_id: 'OTHER' }, { id: 'forged' }, { evidence_kind: 'TRANSFER' }, { source: 'TIMED_PERFORMANCE' }, { evidence_kind: 'PRACTICE', transfer_level: 1 }]) {
      expect(skillEvidenceSchema.safeParse({ ...row, ...edit }).success).toBe(false);
    }
    expect(() => extractSkillEvidence(question(), attempt(), { identified_relation: { relation: 'CAUSE', recorded_at: TIME + 1 } })).toThrow();
    expect(() => extractSkillEvidence(question(), attempt(), { transfer: { unseen: true, exam_like: true, prior_practice_at: TIME + 1 } })).toThrow();
  });
});
