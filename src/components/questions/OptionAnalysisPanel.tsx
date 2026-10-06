import type { OptionAnalysis } from '../../types/question';
const labels = { CORRECT: 'Uygun', ELIMINATE: 'Elenir', POSSIBLE: 'Kanıt yetersiz' };
export function OptionAnalysisPanel({ analyses }: { readonly analyses: readonly OptionAnalysis[] }) {
  return <section aria-label="Şık eleme analizi"><h3>2. Şık eleme analizi</h3><ol>
    {analyses.map((a) => <li key={a.option_id}><strong>{a.option_id} — {labels[a.verdict]}</strong><ul>
      {[...new Set(a.reasons)].map((reason, index) => <li key={index}>{reason}</li>)}
    </ul></li>)}
  </ol></section>;
}
