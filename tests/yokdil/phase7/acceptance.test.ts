import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { QUESTION_FAMILIES } from '../../../src/types/question';
import { analyzeExamPool, buildExamForm, createExamSimulation, projectExamSimulation, qualifyExamSimulation, selectCalibrationPerformanceEvidence, validateExamBlueprint } from '../../../src/exam';
import { fingerprint, questionContentKey } from '../../../src/services/exam/provenance';
import { actual } from '../phase5/fixtures';
import type { ExamForm, ExamSimulationCommand, ExamSimulationTranscript } from '../../../src/types/exam';
import type { Question } from '../../../src/types/question';
import { append, beforeCompletion, blueprint, completed, context, controlled, form, simulation, syntheticPool } from './fixtures';

/** Explicitly configured test blueprint. 80 / 10-per-family is NOT an official YÖKDİL distribution. */
const configuredFull = (source: ExamForm['blueprint']['source'] = { verification: 'UNVERIFIED', reference: null }) =>
  blueprint({ id: 'configured-full', scope: 'FULL', total_questions: 80, time_limit_ms: 10_800_000,
    family_targets: Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, 10])), source });
const officialFixture = { verification: 'OFFICIAL_VERIFIED', reference: 'fixture-only:verified-config', verified_at: 0, verified_by: 'test-harness' } as const;

function reseal(f: ExamForm, changes: Partial<ExamForm>): ExamForm {
  const { fingerprint: _old, ...body } = { ...f, ...changes };
  return { ...body, fingerprint: fingerprint(body) } as ExamForm;
}
/** Manual execution through the public append API, so every step is validated by projection. */
function execute(t: ExamSimulationTranscript, before: readonly ExamSimulationCommand[] = []): ExamSimulationTranscript {
  let x = append(t, { type: 'START' }, 2_000);
  for (const c of before) x = append(x, c, 2_000);
  let at = 2_000;
  for (const [i, q] of x.definition.form.questions.entries()) {
    x = append(x, { type: 'PULSE', engaged: true }, at + 20_000); at += 40_000;
    x = append(x, { type: 'SUBMIT', attempt: actual(q, `${x.definition.id}-m${i}`, at, true, 0, 40_000), replaces_attempt_id: null }, at);
  }
  return append(x, { type: 'COMPLETE' }, at);
}

describe('Production pool availability (22 real questions)', () => {
  it('a configured full blueprint is a typed insufficiency, not an engine failure', () => {
    const result = analyzeExamPool(configuredFull(), initialQuestions, context);
    expect(result.status).toBe('INSUFFICIENT_POOL'); if (result.status === 'INVALID_BLUEPRINT') return;
    expect(result.report).toMatchObject({ required: 80, available: 22, eligible: 22, shortfall: 58, novelty: { UNSEEN: 0, SEEN: 0, UNKNOWN: 22 } });
    expect(result.report.family_shortfalls).toEqual({ GAP_FILL: 5, CLOZE_TEST: 8, SENTENCE_COMPLETION: 8, TRANSLATION_ENG_TR: 8,
      TRANSLATION_TR_ENG: 8, PARAGRAPH_COMPLETION: 8, IRRELEVANT_SENTENCE: 8, READING_COMPREHENSION: 5 });
    const built = buildExamForm({ id: 'prod-full', blueprint: configuredFull(), questions: initialQuestions, context });
    expect(built.status).toBe('INSUFFICIENT_POOL'); expect(built.form).toBeNull();
  });
  it('explicit partial request yields a 22-item practice form that strict mode refuses and that never calibrates', () => {
    const built = buildExamForm({ id: 'prod-partial', blueprint: configuredFull(), questions: initialQuestions, context, allow_partial: true, seed: 'p' });
    expect(built.status).toBe('PARTIAL'); expect(built.form?.quality).toBe('PARTIAL'); expect(built.form?.questions).toHaveLength(22);
    expect(() => simulation({ form: built.form! })).toThrow('complete form');
    const result = qualifyExamSimulation(completed({ form: built.form!, mode: 'PRACTICE_SIMULATION' }), 882_000);
    expect(result.tier).toBe('PRACTICE_ONLY'); expect(result.evidence).toBeNull(); expect(result.question_count).toBe(22);
    expect(result.reasons).toEqual(expect.arrayContaining(['PARTIAL_FORM', 'PRACTICE_MODE', 'UNVERIFIED_BLUEPRINT', 'UNKNOWN_EXPOSURE', 'INCOMPLETE']));
  });
  it('allow_partial does not downgrade an adequate pool', () => {
    expect(buildExamForm({ id: 'f', blueprint: blueprint(), questions: initialQuestions, context, allow_partial: true }).status).toBe('COMPLETE');
  });
});

describe('Blueprint validation edges', () => {
  it.each([
    { family_targets: { UNKNOWN_FAMILY: 5 } }, { skill_minimums: { PACING_STAMINA: 1 } }, { total_questions: 2.5 },
    { time_limit_ms: 86_400_001 }, { reuse_policy: 'ANY' }, { extra: true }, { source: { verification: 'INTERNAL', reference: '  ' } },
    { source: { verification: 'OFFICIAL_VERIFIED', reference: 'x', verified_at: 0 } },
  ])('rejects %j', (change) => { expect(validateExamBlueprint({ ...blueprint(), ...change }).status).toBe('INVALID'); });
  it('verification dated after form construction is rejected', () => {
    expect(() => analyzeExamPool(blueprint({ source: { ...officialFixture, verified_at: 5_000 } }), initialQuestions, context)).toThrow('future');
  });
});

describe('Deterministic, duplicate-safe selection', () => {
  const pool = syntheticPool(32), bp = blueprint({ total_questions: 8, family_targets: Object.fromEntries(QUESTION_FAMILIES.map((f) => [f, 1])) });
  it.each(['s0', 's1', 's2', 's3', 's4'])('seed %s: stable under reordering and exact duplicates; family quota met', (seed) => {
    const a = buildExamForm({ id: 'det', blueprint: bp, questions: pool, context: controlled(pool), seed });
    const b = buildExamForm({ id: 'det', blueprint: bp, questions: [...pool, ...pool.slice(0, 5)].reverse(), context: controlled(pool), seed });
    expect(a.form?.question_ids).toEqual(b.form?.question_ids); expect(a.form?.fingerprint).toBe(b.form?.fingerprint);
    expect(new Set(a.form?.question_ids).size).toBe(8);
    for (const f of QUESTION_FAMILIES) expect(a.form?.questions.filter((q) => q.family === f)).toHaveLength(1);
  });
  it('content aliases under new IDs never appear twice in one form', () => {
    const aliased: Question[] = [...pool, ...pool.map((q) => ({ ...q, id: `alias-${q.id}` }))];
    const result = buildExamForm({ id: 'alias', blueprint: bp, questions: aliased, context, seed: 'x' });
    expect(result.status).toBe('COMPLETE'); if (result.status === 'INVALID_BLUEPRINT') return;
    expect(result.report.available).toBe(32);
    expect(result.report.exclusions.filter((e) => e.reason === 'DUPLICATE_CONTENT')).toHaveLength(32);
    expect(new Set(result.form?.questions.map(questionContentKey)).size).toBe(8);
  });
});

describe('Form integrity: partial vs complete', () => {
  it('relabelling a partial form as COMPLETE (even with a re-sealed fingerprint) is rejected', () => {
    const partial = buildExamForm({ id: 'p', blueprint: blueprint({ total_questions: 6, family_targets: { GAP_FILL: 6 } }), questions: initialQuestions, context: controlled(), allow_partial: true }).form!;
    const forged = reseal(partial, { quality: 'COMPLETE' });
    expect(() => simulation({ form: forged })).toThrow('family targets');
    const practice = completed({ form: partial, mode: 'PRACTICE_SIMULATION' });
    const result = qualifyExamSimulation({ ...practice, definition: { ...practice.definition, form: forged } }, 202_000);
    expect(result.tier).toBe('NOT_ELIGIBLE'); expect(result.reasons).toEqual(['INVALID_EXECUTION']);
  });
  it('answer key tampering is rejected with or without re-sealing', () => {
    const t = completed(), q = t.definition.form.questions[0]!, other = q.options.find((o) => o.id !== q.correct_option)!.id;
    const questions = [{ ...q, correct_option: other }, ...t.definition.form.questions.slice(1)];
    const unsealed = { ...t.definition.form, questions } as ExamForm;
    expect(qualifyExamSimulation({ ...t, definition: { ...t.definition, form: unsealed } }, 202_000).tier).toBe('NOT_ELIGIBLE');
    expect(qualifyExamSimulation({ ...t, definition: { ...t.definition, form: reseal(t.definition.form, { questions }) } }, 202_000).tier).toBe('NOT_ELIGIBLE');
  });
  it('a forged UNSEEN label without references cannot enter a form', () => {
    const f = form(blueprint(), context);
    const exposure = Object.fromEntries(f.question_ids.map((id) => [id, { state: 'UNSEEN' as const, references: [] }]));
    expect(() => simulation({ form: reseal(f, { exposure }) })).toThrow('novelty');
  });
  it('stored qualification claims and extra fields are not trusted', () => {
    const t = completed();
    expect(qualifyExamSimulation({ ...t, definition: { ...t.definition, qualified: true } } as unknown as ExamSimulationTranscript, 202_000).tier).toBe('NOT_ELIGIBLE');
    expect(qualifyExamSimulation({ ...t, events: t.events.map((e) => ({ ...e, qualified: true })) } as unknown as ExamSimulationTranscript, 202_000).tier).toBe('NOT_ELIGIBLE');
  });
});

describe('Practice vs strict, timing policy', () => {
  it('identical clean execution: strict calibrates, practice is PRACTICE_ONLY for that reason alone', () => {
    expect(qualifyExamSimulation(completed(), 202_000).tier).toBe('PARTIAL_CALIBRATION');
    const practice = qualifyExamSimulation(completed({ mode: 'PRACTICE_SIMULATION' }), 202_000);
    expect(practice.tier).toBe('PRACTICE_ONLY'); expect(practice.reasons).toEqual(['PRACTICE_MODE']); expect(practice.evidence).toBeNull();
  });
  it('practice tolerates overrun (TIMED_OUT, answers kept); strict refuses the same late submissions', () => {
    const tight = form(blueprint({ time_limit_ms: 150_000 }));
    const practice = completed({ form: tight, mode: 'PRACTICE_SIMULATION' });
    expect(projectExamSimulation(practice, 202_000).status).toBe('TIMED_OUT');
    const q = qualifyExamSimulation(practice, 202_000);
    expect(q.question_count).toBe(5); expect(q.reasons).toContain('TIME_LIMIT'); expect(q.timing_valid).toBe(false);
    expect(() => completed({ form: tight })).toThrow('deadline');
  });
  it('strict extension enables completion but forfeits calibration and timing validity', () => {
    const t = execute(simulation({ form: form(blueprint({ time_limit_ms: 150_000 })) }), [{ type: 'EXTEND_TIME', additional_ms: 100_000 }]);
    const state = projectExamSimulation(t, 202_000);
    expect(state.status).toBe('COMPLETED'); expect(state.time_limit_ms).toBe(250_000);
    const q = qualifyExamSimulation(t, 202_000);
    expect(q.qualified).toBe(false); expect(q.completion_valid).toBe(true); expect(q.timing_valid).toBe(false);
    expect(q.reasons).toEqual(expect.arrayContaining(['TIME_EXTENDED', 'TIME_LIMIT']));
  });
  it.each([0, -1, 1.5])('rejects a non-positive or fractional extension (%d)', (additional_ms) => {
    expect(() => append(append(simulation(), { type: 'START' }, 2_000), { type: 'EXTEND_TIME', additional_ms }, 2_000)).toThrow();
  });
  it('strict pause keeps answers and completion but invalidates timing', () => {
    const q = qualifyExamSimulation(beforeCompletion(completed(), [{ type: 'PAUSE' }, { type: 'RESUME' }]), 202_000);
    expect(q.completion_valid).toBe(true); expect(q.timing_valid).toBe(false); expect(q.evidence).toBeNull();
  });
  it('disengaged pulse blocks submission until re-engagement', () => {
    let t = append(simulation(), { type: 'START' }, 2_000); t = append(t, { type: 'PULSE', engaged: false }, 10_000);
    expect(() => append(t, { type: 'SUBMIT', attempt: actual(t.definition.form.questions[0]!, 'x', 30_000), replaces_attempt_id: null }, 30_000)).toThrow('inactive');
  });
  it('events after completion and a still-ACTIVE strict run cannot calibrate', () => {
    const t = completed();
    expect(() => append(t, { type: 'PULSE', engaged: true }, 202_000)).toThrow('not active');
    const open: ExamSimulationTranscript = { ...t, events: t.events.slice(0, -1) };
    const q = qualifyExamSimulation(open, 202_000); expect(q.reasons).toContain('INCOMPLETE'); expect(q.evidence).toBeNull();
  });
});

describe('Assistance observability and answer policy', () => {
  const def = (monitoring: { assistance: 'COMPLETE' | 'UNKNOWN'; interruptions: 'COMPLETE' | 'UNKNOWN'; reference: string | null }) =>
    createExamSimulation({ id: 'mon', form: form(), mode: 'STRICT_SIMULATION', created_at: 2_000, source: { kind: 'USER_EXECUTION', reference: 'u' }, monitoring });
  it('claiming complete monitoring without provenance is rejected', () => {
    expect(() => def({ assistance: 'COMPLETE', interruptions: 'COMPLETE', reference: null })).toThrow('provenance');
  });
  it.each([['COMPLETE', 'UNKNOWN'], ['UNKNOWN', 'COMPLETE']] as const)('partially observed monitoring (%s/%s) is not help-free evidence', (assistance, interruptions) => {
    const q = qualifyExamSimulation(execute(def({ assistance, interruptions, reference: 'instrumentation' })), 202_000);
    expect(q.reasons).toContain('MONITORING_UNKNOWN'); expect(q.qualified).toBe(false);
    if (assistance === 'UNKNOWN') expect(q.assistance_valid).toBe(false);
  });
  it('strict: a different answer for an answered item is refused even without a replacement link', () => {
    const t = completed(), q = t.definition.form.questions[0]!;
    expect(() => append({ ...t, events: t.events.slice(0, -1) }, { type: 'SUBMIT', attempt: actual(q, 'second', 202_000, false), replaces_attempt_id: null }, 202_000)).toThrow('immutable');
  });
  it('practice: replacement must link the current answer; linked revision keeps both attempts and the latest final', () => {
    const t = completed({ mode: 'PRACTICE_SIMULATION' }), q = t.definition.form.questions[0]!, open = { ...t, events: t.events.slice(0, -1) };
    const second = actual(q, 'second', 202_000, false);
    expect(() => append(open, { type: 'SUBMIT', attempt: second, replaces_attempt_id: null }, 202_000)).toThrow('replacement');
    expect(() => append(open, { type: 'SUBMIT', attempt: second, replaces_attempt_id: 'missing' }, 202_000)).toThrow('replacement');
    const revised = append(append(open, { type: 'SUBMIT', attempt: second, replaces_attempt_id: `${t.definition.id}-a0` }, 202_000), { type: 'COMPLETE' }, 202_000);
    const state = projectExamSimulation(revised, 202_000);
    expect(state.submitted_attempt_ids).toHaveLength(6); expect(state.answers).toHaveLength(5);
    expect(state.answers[0]?.id).toBe('second'); expect(state.conditions).toContain('ANSWER_REVISION');
  });
  it('study-session attempts or items outside the form cannot be submitted', () => {
    const t = append(append(simulation(), { type: 'START' }, 2_000), { type: 'PULSE', engaged: true }, 20_000);
    const q = t.definition.form.questions[0]!, a = actual(q, 'x', 40_000);
    expect(() => append(t, { type: 'SUBMIT', attempt: { ...a, session_id: 'study' }, replaces_attempt_id: null }, 40_000)).toThrow('linkage');
    const outside = initialQuestions.find((x) => !t.definition.form.question_ids.includes(x.id))!;
    expect(() => append(t, { type: 'SUBMIT', attempt: actual(outside, 'y', 40_000), replaces_attempt_id: null }, 40_000)).toThrow('outside');
    expect(() => append(t, { type: 'SUBMIT', attempt: actual(q, 'z', 40_000, true, 0, 60_000), replaces_attempt_id: null }, 40_000)).toThrow('timing');
  });
});

describe('Exposure handling', () => {
  const q = initialQuestions[0]!;
  it('recorded SEEN exposure without any attempt marks SEEN and outranks an UNSEEN inventory', () => {
    const ctx = { ...controlled(), exposures: [...controlled().exposures, { question_id: q.id, state: 'SEEN' as const, observed_at: 900, method: 'RECORDED_EXPOSURE' as const, reference: 'viewer-log:1' }] };
    const result = analyzeExamPool(blueprint({ reuse_policy: 'ALLOW_REUSE' }), initialQuestions, ctx);
    if (result.status === 'INVALID_BLUEPRINT') throw new Error('blueprint');
    expect(result.report.novelty).toEqual({ UNSEEN: 4, SEEN: 1, UNKNOWN: 0 });
    const f = form(blueprint(), ctx);
    expect(f.exposure[q.id]).toEqual({ state: 'SEEN', references: ['fixture-controlled-inventory:' + q.id, 'viewer-log:1'] });
    expect(qualifyExamSimulation(completed({ form: f }), 202_000).reasons).toEqual(['SEEN_QUESTIONS']);
  });
  it('EXCLUDE_SEEN keeps UNKNOWN items available (unknown is not seen), UNSEEN_ONLY does not', () => {
    const ctx = { ...context, prior_attempts: [actual(q, 'prior', 500)] };
    const exclude = analyzeExamPool(blueprint({ reuse_policy: 'EXCLUDE_SEEN', total_questions: 4, family_targets: { GAP_FILL: 4 } }), initialQuestions, ctx);
    expect(exclude.status).toBe('ADEQUATE'); if (exclude.status !== 'INVALID_BLUEPRINT') expect(exclude.report.novelty).toEqual({ UNSEEN: 0, SEEN: 1, UNKNOWN: 4 });
    expect(analyzeExamPool(blueprint({ reuse_policy: 'UNSEEN_ONLY', total_questions: 4, family_targets: { GAP_FILL: 4 } }), initialQuestions, ctx).status).toBe('INSUFFICIENT_POOL');
  });
});

describe('Calibration tier matrix and full-calibration guards', () => {
  it.each([
    ['INTERNAL MINI', 'PARTIAL_CALIBRATION', blueprint()],
    ['OFFICIAL_VERIFIED MINI', 'PARTIAL_CALIBRATION', blueprint({ source: officialFixture })],
    ['UNVERIFIED MINI', 'PRACTICE_ONLY', blueprint({ source: { verification: 'UNVERIFIED', reference: 'draft' } })],
  ] as const)('%s → %s; evidence present iff qualified', (_label, tier, bp) => {
    const q = qualifyExamSimulation(completed({ form: form(bp) }), 202_000);
    expect(q.tier).toBe(tier); expect(q.qualified).toBe(q.evidence !== null); expect(q.qualified).toBe(q.reasons.length === 0);
    if (q.evidence) { expect(q.evidence.tier).toBe(tier); expect(q.evidence.official_exam).toBe(false); expect(q.evidence.official_score_mapping).toBeNull(); }
  });
  const pool = syntheticPool();
  it('UNVERIFIED FULL with a complete pool and clean strict run is never full (or any) calibration', () => {
    const q = qualifyExamSimulation(completed({ form: form(configuredFull(), controlled(pool), pool) }), 3_202_000);
    expect(q.tier).toBe('PRACTICE_ONLY'); expect(q.reasons).toEqual(['UNVERIFIED_BLUEPRINT']); expect(q.evidence).toBeNull();
  });
  it('OFFICIAL_VERIFIED FULL: abandoned or corrupted runs never produce full calibration', () => {
    const t = completed({ form: form(configuredFull(officialFixture), controlled(pool), pool) });
    expect(qualifyExamSimulation(t, 3_202_000).tier).toBe('FULL_CALIBRATION');
    const abandoned = append({ ...t, events: t.events.slice(0, 41) }, { type: 'ABANDON' }, t.events[40]!.at);
    const a = qualifyExamSimulation(abandoned, 3_202_000);
    expect(a.tier).toBe('PRACTICE_ONLY'); expect(a.reasons).toContain('INCOMPLETE'); expect(a.evidence).toBeNull();
    const gap: ExamSimulationTranscript = { ...t, events: t.events.filter((e) => e.sequence !== 10) };
    expect(qualifyExamSimulation(gap, 3_202_000).tier).toBe('NOT_ELIGIBLE');
  });
});

describe('Phase 6 adapter edges', () => {
  it('mixed batch: corrupt transcript rejected as INVALID_EXECUTION, clean one consumed', () => {
    const clean = completed(), bad = completed({ id: 'bad' });
    const corrupt: ExamSimulationTranscript = { ...bad, events: bad.events.map((e) => (e.sequence === 3 ? { ...e, at: 1 } : e)) };
    const r = selectCalibrationPerformanceEvidence([corrupt, clean], 202_000);
    expect(r.rejected).toEqual([{ simulation_id: 'bad', reasons: ['INVALID_EXECUTION'] }]);
    expect(r.evidence.records).toHaveLength(5); expect(r.evidence.integrity).toBe('VALID');
    expect(r.evidence.records.every((x) => x.block_id === 'simulation/exam' && x.exam_like_transfer === false)).toBe(true);
  });
  it('events after as_of cannot be consumed', () => {
    const r = selectCalibrationPerformanceEvidence([completed()], 100_000);
    expect(r.evidence.records).toHaveLength(0); expect(r.rejected[0]?.reasons).toEqual(['INVALID_EXECUTION']);
  });
  it('the same content under another question ID in a second calibration is counted once', () => {
    const renamed = initialQuestions.map((q) => ({ ...q, id: `alias-${q.id}` }));
    const other = completed({ id: 'other', form: form(blueprint(), controlled(renamed), renamed, 'form-b') });
    const r = selectCalibrationPerformanceEvidence([completed(), other], 202_000);
    expect(r.evidence.records).toHaveLength(5); expect(r.evidence.exclusions).toHaveLength(5);
    expect(r.evidence.exclusions.every((e) => e.reason === 'DUPLICATE')).toBe(true); expect(r.calibration_references).toHaveLength(1);
  });
  it('adapter output never exposes an exam range or score mapping', () => {
    const r = selectCalibrationPerformanceEvidence([completed()], 202_000);
    expect(r.exam_range).toBeNull(); expect(r.scope).toBe('CALIBRATION_OBSERVATION'); expect(Object.isFrozen(r)).toBe(true);
  });
});
