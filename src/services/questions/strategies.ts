import type { AnchorChain, CheckCriterion, GapFillSubclass, OptionAnalysis, OptionId, Question, QuestionFamily, SemanticRoleMap, TacticalCheck, TriageExplanation } from '../../types/question';

export interface TriageResult extends TriageExplanation {
  readonly question_id: string;
  readonly family: QuestionFamily;
  readonly subclass?: GapFillSubclass | undefined;
  readonly context: readonly string[];
}
export interface SolverContext { readonly eliminated_options: readonly OptionId[] }
export interface VerificationResult {
  readonly candidate: OptionId;
  readonly verdict: 'SUPPORTED' | 'REJECTED' | 'INSUFFICIENT';
  readonly checks: readonly TacticalCheck[];
  readonly evidence: readonly string[];
  readonly summary: string;
}
export interface TacticalSolver {
  triage(question: Question): TriageResult;
  analyzeOptions(question: Question, triage: TriageResult): readonly OptionAnalysis[];
  verify(question: Question, candidate: OptionId, context: SolverContext): VerificationResult;
}
const relationLabels = { CONTRAST: 'karşıtlık', CONCESSION: 'ödünleme', CAUSE: 'neden', RESULT: 'sonuç', CONDITION: 'koşul', ADDITION: 'ekleme' };
const gapChecks: Readonly<Record<GapFillSubclass, readonly CheckCriterion[]>> = {
  VOCAB: ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB'],
  GRAMMAR: ['TENSE_ASPECT', 'VOICE', 'REDUCTION', 'MODALITY', 'CLAUSE_RELATION', 'TEMPORAL_CONTEXT'],
  PREPOSITION: ['COLLOCATION', 'CLAUSE_COMPATIBILITY'],
  CONNECTOR: ['DISCOURSE_RELATION', 'CLAUSE_COMPATIBILITY'],
  STRUCTURE: ['REDUCTION', 'CLAUSE_COMPATIBILITY'],
};

/** Authored semantic evidence, not surface-word heuristics or a general NLP parser. */
abstract class EvidenceSolver implements TacticalSolver {
  protected abstract criteria(question: Question): readonly CheckCriterion[];
  protected context(question: Question): readonly string[] { return [question.passage ?? question.stem]; }
  triage(question: Question): TriageResult {
    return { ...question.explanation.triage, question_id: question.id, family: question.family,
      ...(question.tactical.kind === 'GAP_FILL' ? { subclass: question.tactical.focus } : {}), context: this.context(question) };
  }
  protected checks(question: Question, candidate: OptionId): readonly TacticalCheck[] {
    return this.criteria(question).map((criterion) => {
      const check = question.option_evidence[candidate].find((c) => c.criterion === criterion) ??
        { criterion, matches: null, evidence: 'Bu kontrol için yeterli bağlam kanıtı kaydedilmemiş.' };
      const metadata = question.tactical;
      if (criterion === 'DISCOURSE_RELATION' && 'candidate_relations' in metadata) {
        const candidateRelation = metadata.candidate_relations[candidate];
        const matches = check.matches === false ? false : candidateRelation === null ? null : candidateRelation === metadata.relation;
        return { ...check, matches, evidence: `${check.evidence} Beklenen ilişki: ${relationLabels[metadata.relation]}; aday: ${candidateRelation === null ? 'belirsiz' : relationLabels[candidateRelation]}.` };
      }
      return check;
    });
  }
  verify(question: Question, candidate: OptionId, context: SolverContext): VerificationResult {
    const checks = this.checks(question, candidate);
    const verdict = checks.some((c) => c.matches === false) ? 'REJECTED' :
      checks.length > 0 && checks.every((c) => c.matches === true) ? 'SUPPORTED' : 'INSUFFICIENT';
    return { candidate, verdict, checks,
      evidence: [...checks.map((c) => c.evidence), ...(context.eliminated_options.includes(candidate) ? ['Bu şıkkı elemiştiniz; işaretiniz doğruluk kanıtı değildir.'] : [])],
      summary: verdict === 'SUPPORTED' ? 'Seçenek bağlam ve anlam kontrollerini karşılıyor.' :
        verdict === 'REJECTED' ? 'Seçenek en az bir bağlamsal kontrolle çelişiyor.' : 'Kesin hüküm için kanıt yetersiz.' };
  }
  analyzeOptions(question: Question, triage: TriageResult): readonly OptionAnalysis[] {
    if (triage.question_id !== question.id || triage.family !== question.family) throw new RangeError('Triage belongs to another question');
    return question.options.map(({ id }) => {
      const verification = this.verify(question, id, { eliminated_options: [] });
      const authored = question.explanation.option_analysis.find((a) => a.option_id === id);
      return { option_id: id, verdict: verification.verdict === 'SUPPORTED' ? 'CORRECT' : verification.verdict === 'REJECTED' ? 'ELIMINATE' : 'POSSIBLE',
        reasons: [...(authored?.reasons ?? []), ...verification.evidence], patterns: authored?.patterns ?? [] };
    });
  }
}
export class GapFillSolver extends EvidenceSolver {
  protected criteria(q: Question): readonly CheckCriterion[] {
    if (q.tactical.kind !== 'GAP_FILL') throw new TypeError('Expected gap fill');
    return gapChecks[q.tactical.focus];
  }
  protected override context(q: Question): readonly string[] {
    if (q.tactical.kind !== 'GAP_FILL') throw new TypeError('Expected gap fill');
    const t = q.tactical.temporal;
    return t ? [q.stem, t.temporal_anchor, t.event_order, t.tense_aspect, t.context] : [q.stem];
  }
}
export class ClozeSolver extends EvidenceSolver {
  protected criteria(): readonly CheckCriterion[] { return ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT']; }
  protected override context(q: Question): readonly string[] {
    if (q.tactical.kind !== 'CLOZE_TEST') throw new TypeError('Expected cloze');
    return [q.tactical.previous_sentence, q.tactical.target_sentence, q.tactical.next_sentence, q.tactical.macro_context, q.passage ?? '', `İlişki: ${relationLabels[q.tactical.relation]}`];
  }
}
export class SentenceCompletionSolver extends EvidenceSolver {
  protected criteria(): readonly CheckCriterion[] { return ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE']; }
  protected override context(q: Question): readonly string[] {
    if (q.tactical.kind !== 'SENTENCE_COMPLETION') throw new TypeError('Expected sentence completion');
    return [`İlişki: ${relationLabels[q.tactical.relation]}`, q.stem];
  }
}
/** Canonical roles let reordered translations preserve meaning without matching tokens. */
export function compareSemanticRoles(source: SemanticRoleMap, candidate: SemanticRoleMap): readonly string[] {
  const differences: string[] = [];
  const fields = ['agent', 'action', 'patient', 'voice', 'modality', 'polarity', 'time', 'condition', 'degree'] as const;
  const labels = { agent: 'eyleyen', action: 'eylem', patient: 'etkilenen', voice: 'çatı', modality: 'kip / olasılık', polarity: 'olumluluk', time: 'zaman', condition: 'koşul', degree: 'derece / zarf' };
  for (const field of fields) if (source[field] !== candidate[field]) differences.push(`Anlam eşleşmiyor: ${labels[field]}.`);
  const expected = new Set(source.propositions);
  const actual = new Set(candidate.propositions);
  if (expected.size !== actual.size || [...expected].some((p) => !actual.has(p))) differences.push('Anlamsal önerme eklenmiş veya çıkarılmış.');
  return differences;
}
export class TranslationSolver extends EvidenceSolver {
  protected criteria(): readonly CheckCriterion[] { return ['SEMANTIC_EQUIVALENCE']; }
  protected override checks(q: Question, id: OptionId): readonly TacticalCheck[] {
    if (q.tactical.kind !== 'TRANSLATION') throw new TypeError('Expected translation');
    const differences = compareSemanticRoles(q.tactical.source, q.tactical.candidates[id]);
    return [{ criterion: 'SEMANTIC_EQUIVALENCE', matches: differences.length === 0,
      evidence: differences.length === 0 ? 'Sözcük sırası değişse de eyleyen, eylem, çatı, kip, zaman, koşul ve kapsam korunuyor.' : differences.join(' ') }];
  }
}
/** Editorial continuity score; not a learner score or a predicted exam gain. */
export function scoreAnchorChain(chain: AnchorChain): number {
  return (chain.referent + chain.topic_continuity + chain.connector + chain.tense_aspect + chain.cause_effect + chain.lexical_chain) / 6;
}
/** Editorial continuity threshold for authored anchors, not a learner calibration. */
export const ANCHOR_CHAIN_MIN = 0.65;
export class ParagraphCompletionSolver extends EvidenceSolver {
  protected criteria(): readonly CheckCriterion[] { return ['DISCOURSE_RELATION', 'CONTINUATION']; }
  protected override checks(q: Question, id: OptionId): readonly TacticalCheck[] {
    if (q.tactical.kind !== 'PARAGRAPH_COMPLETION') throw new TypeError('Expected paragraph completion');
    const chain = q.tactical.anchors[id];
    const score = scoreAnchorChain(chain);
    return [...super.checks(q, id), { criterion: 'REFERENT', matches: score >= ANCHOR_CHAIN_MIN,
      evidence: `Gönderim, konu, bağlaç, zaman, neden-sonuç ve sözcük zinciri birlikte değerlendirildi; anlamsal bağlantı ${score >= ANCHOR_CHAIN_MIN ? 'yeterli' : 'zayıf'}.` }];
  }
}
export class IrrelevantSentenceSolver extends EvidenceSolver {
  protected criteria(): readonly CheckCriterion[] { return ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY']; }
  protected override context(q: Question): readonly string[] {
    if (q.tactical.kind !== 'IRRELEVANT_SENTENCE') throw new TypeError('Expected irrelevant sentence');
    return [q.tactical.topic, q.tactical.discourse_function, q.passage ?? ''];
  }
}
export class ReadingComprehensionSolver extends EvidenceSolver {
  protected criteria(q: Question): readonly CheckCriterion[] {
    if (q.tactical.kind !== 'READING_COMPREHENSION') throw new TypeError('Expected reading');
    const base: readonly CheckCriterion[] = ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'];
    switch (q.tactical.subtype) {
      case 'REFERENCE': return ['REFERENT', ...base];
      case 'PURPOSE': return ['DISCOURSE_FUNCTION', ...base];
      case 'MAIN_IDEA': return ['TOPIC', ...base];
      case 'INFERENCE': return ['CONTINUATION', ...base];
      case 'DETAIL': return base;
    }
  }
  protected override context(q: Question): readonly string[] {
    if (q.tactical.kind !== 'READING_COMPREHENSION') throw new TypeError('Expected reading');
    const labels = { DETAIL: 'Ayrıntı', INFERENCE: 'Çıkarım', MAIN_IDEA: 'Ana düşünce', REFERENCE: 'Gönderim', PURPOSE: 'Yazarın amacı' };
    return [labels[q.tactical.subtype], q.passage ?? '', 'Kesinlik bildiren sözcükler risk sinyalidir; hüküm metin kanıtıyla verilir.'];
  }
}
const translation = new TranslationSolver();
export const tacticalSolvers: Readonly<Record<QuestionFamily, TacticalSolver>> = Object.freeze({
  GAP_FILL: new GapFillSolver(), CLOZE_TEST: new ClozeSolver(), SENTENCE_COMPLETION: new SentenceCompletionSolver(),
  TRANSLATION_ENG_TR: translation, TRANSLATION_TR_ENG: translation, PARAGRAPH_COMPLETION: new ParagraphCompletionSolver(),
  IRRELEVANT_SENTENCE: new IrrelevantSentenceSolver(), READING_COMPREHENSION: new ReadingComprehensionSolver(),
});
