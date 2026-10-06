import { describe, expect, it } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import type { Question } from '../../../src/types/question';
import { compareSemanticRoles, scoreAnchorChain, tacticalSolvers } from '../../../src/services/questions/strategies';

function get(id: string): Question {
  const q = initialQuestions.find((entry) => entry.id === id);
  if (!q) throw new Error('Missing question');
  return q;
}
describe('Evidence-driven family strategies', () => {
  it.each(initialQuestions.map((q) => [q.id, q] as const))('%s has one context-supported answer', (_, q) => {
    const solver = tacticalSolvers[q.family];
    const analyses = solver.analyzeOptions(q, solver.triage(q));
    expect(analyses.filter((a) => a.verdict === 'CORRECT').map((a) => a.option_id)).toEqual([q.correct_option]);
  });
  it('uses dynamic gap subclasses independently of question ID or position', () => {
    for (const q of initialQuestions.filter((item) => item.family === 'GAP_FILL')) {
      expect(tacticalSolvers.GAP_FILL.triage({ ...q, id: 'question-1' }).subclass).toBe(q.subclass);
    }
  });
  it('does not eliminate from a temporal mismatch label alone', () => {
    const q = get('gap-grammar');
    const changed = { ...q, explanation: { ...q.explanation, option_analysis: q.explanation.option_analysis.map((a) => ({ ...a, patterns: ['TEMPORAL_MISMATCH' as const] })) } };
    expect(tacticalSolvers.GAP_FILL.verify(changed, 'D', { eliminated_options: [] }).verdict).toBe('SUPPORTED');
    expect(tacticalSolvers.GAP_FILL.triage(q).context).toHaveLength(5);
  });
  it('retains local and macro cloze context across unrelated science passages', () => {
    for (const id of ['cloze-biology', 'cloze-astronomy']) {
      const q = get(id);
      if (q.tactical.kind !== 'CLOZE_TEST') throw new Error('Wrong fixture');
      const context = tacticalSolvers.CLOZE_TEST.triage(q).context;
      expect(context).toContain(q.tactical.previous_sentence);
      expect(context).toContain(q.tactical.target_sentence);
      expect(context).toContain(q.tactical.next_sentence);
      expect(context).toContain(q.passage);
      expect(context).toContain(q.tactical.macro_context);
    }
  });
  it('puts discourse relation first and ignores polarity as a standalone verdict', () => {
    const q = get('sentence-concession');
    const changed = { ...q, explanation: { ...q.explanation, option_analysis: q.explanation.option_analysis.map((a) => ({ ...a, patterns: ['POLARITY_INVERSION' as const] })) } };
    expect(tacticalSolvers.SENTENCE_COMPLETION.triage(q).context[0]).toBe('İlişki: ödünleme');
    const result = tacticalSolvers.SENTENCE_COMPLETION.verify(changed, 'A', { eliminated_options: [] });
    expect(result.checks[0]?.criterion).toBe('DISCOURSE_RELATION');
    expect(result.verdict).toBe('SUPPORTED');
    if (q.tactical.kind !== 'SENTENCE_COMPLETION') throw new Error('Wrong fixture');
    const wrongRelation: Question = { ...q, tactical: { ...q.tactical, relation: 'CAUSE' } };
    expect(tacticalSolvers.SENTENCE_COMPLETION.verify(wrongRelation, 'A', { eliminated_options: [] }).verdict).toBe('REJECTED');
    const contradictory: Question = { ...q, option_evidence: { ...q.option_evidence, A: q.option_evidence.A.map((c) => c.criterion === 'DISCOURSE_RELATION' ? { ...c, matches: false } : c) } };
    expect(tacticalSolvers.SENTENCE_COMPLETION.verify(contradictory, 'A', { eliminated_options: [] }).verdict).toBe('REJECTED');
  });
  it('accepts equivalent translation roles regardless of word order; rejects voice, modality and additions', () => {
    const q = get('translation-eng-tr-sensor');
    if (q.tactical.kind !== 'TRANSLATION') throw new Error('Wrong fixture');
    expect(tacticalSolvers.TRANSLATION_ENG_TR.verify(q, 'B', { eliminated_options: [] }).verdict).toBe('SUPPORTED');
    const roles = q.tactical.source;
    expect(compareSemanticRoles(roles, { ...roles, propositions: [...roles.propositions].reverse() })).toEqual([]);
    expect(compareSemanticRoles(roles, { ...roles, voice: 'PASSIVE' })).toContain('Anlam eşleşmiyor: çatı.');
    expect(compareSemanticRoles(roles, { ...roles, modality: 'must' })).toContain('Anlam eşleşmiyor: kip / olasılık.');
    expect(compareSemanticRoles(roles, { ...roles, propositions: [...roles.propositions, 'invented'] })).not.toEqual([]);
  });
  it('uses semantic anchors, not the first/last words of neighboring sentences', () => {
    const q = get('paragraph-glacier');
    if (q.tactical.kind !== 'PARAGRAPH_COMPLETION') throw new Error('Wrong fixture');
    const solver = tacticalSolvers.PARAGRAPH_COMPLETION;
    const changed = { ...q, passage: 'Different surface wording; same authored semantic links.' };
    expect(solver.verify(changed, 'D', { eliminated_options: [] }).verdict).toBe('SUPPORTED');
    const weak = q.tactical.anchors.A;
    expect(scoreAnchorChain(weak)).toBeLessThan(0.65);
    const weakened: Question = { ...q, tactical: { ...q.tactical, anchors: { ...q.tactical.anchors, D: weak } } };
    expect(solver.verify(weakened, 'D', { eliminated_options: [] }).verdict).toBe('REJECTED');
  });
  it('treats extreme qualifiers and lexical overlap as signals requiring semantic support', () => {
    const q = get('reading-detail');
    const solver = tacticalSolvers.READING_COMPREHENSION;
    expect(q.options.find((o) => o.id === 'B')?.text).toContain('only');
    expect(solver.verify(q, 'B', { eliminated_options: [] }).verdict).toBe('SUPPORTED');
    expect(solver.verify(q, 'A', { eliminated_options: [] }).verdict).toBe('REJECTED');
    const surfaceOnly = { ...q, options: q.options.map((o) => ({ ...o, text: q.passage ?? '' })) };
    expect(solver.verify(surfaceOnly, 'A', { eliminated_options: [] }).verdict).toBe('REJECTED');
    expect(solver.verify(surfaceOnly, 'B', { eliminated_options: [] }).verdict).toBe('SUPPORTED');
  });
  it('returns insufficient rather than inventing missing evidence', () => {
    const q = get('reading-detail');
    const incomplete = { ...q, option_evidence: { ...q.option_evidence, B: [] } };
    expect(tacticalSolvers.READING_COMPREHENSION.verify(incomplete, 'B', { eliminated_options: [] }).verdict).toBe('INSUFFICIENT');
  });
});
