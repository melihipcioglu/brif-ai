import { useId } from 'react';
import type { DistractorPattern, Question, QuestionAttempt } from '../../types/question';
import { tacticalSolvers } from '../../services/questions/strategies';
import { TriagePanel } from './TriagePanel';
import { OptionAnalysisPanel } from './OptionAnalysisPanel';
const patternLabels: Readonly<Record<DistractorPattern, string>> = {
  POLARITY_INVERSION: 'Anlam yönünü ters çevirme', EXTREME_QUALIFIER: 'Kesinlik ifadesi: metin kanıtıyla kontrol edin', FALSE_FRIEND: 'Benzer görünen sözcük veya kalıp',
  SCOPE_DRIFT: 'Kapsamı değiştirme', TEMPORAL_MISMATCH: 'Zaman ilişkisini değiştirme', REFERENCE_MISMATCH: 'Gönderimi karıştırma',
  CAUSE_EFFECT_REVERSAL: 'Neden ve sonucu ters çevirme', PARTIAL_TRUTH: 'Doğru bilginin yalnız bir kısmı', UNSUPPORTED_DETAIL: 'Metinde desteklenmeyen ayrıntı', SEMANTIC_ROLE_SWAP: 'Eyleyen ve etkilenen rollerini değiştirme',
};
export function PostAnswerAnalysis({ question, attempt }: { readonly question: Question; readonly attempt: QuestionAttempt }) {
  const id = useId();
  const solver = tacticalSolvers[question.family];
  const triage = solver.triage(question);
  const analyses = solver.analyzeOptions(question, triage);
  const verification = solver.verify(question, question.correct_option, { eliminated_options: attempt.eliminated_options });
  return <section className="question-analysis" aria-labelledby={id}>
    <h2 id={id}>Cevap sonrası taktik analiz</h2>
    <p role="status">{attempt.is_correct ? 'Doğru yanıt.' : 'Yanıtınız doğru değil.'} Seçiminiz: {attempt.selected_option}. Doğru cevap: {question.correct_option}.</p>
    <TriagePanel triage={triage} /><OptionAnalysisPanel analyses={analyses} />
    <section aria-label="Doğrulama"><h3>3. Doğrulama</h3><p>{question.explanation.verification.summary}</p>
      <ul>{[...new Set([...question.explanation.verification.evidence, ...verification.evidence])].map((item, i) => <li key={i}>{item}</li>)}</ul>
    </section>
    <section aria-label="Çeldirici çözümlemesi"><h3>4. Çeldirici çözümlemesi</h3>
      {analyses.filter((a) => a.patterns.length > 0).map((a) => <p key={a.option_id}><strong>{a.option_id}:</strong> {a.patterns.map((pattern) => patternLabels[pattern]).join(' · ')}</p>)}
      {attempt.error_attribution !== null && <p>Hatanın nedeni tek bir işaretten kesinleştirilemez; olası etkenler belirsizlikleriyle kaydedildi.</p>}
    </section>
  </section>;
}
