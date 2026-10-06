import type { TriageResult } from '../../services/questions/strategies';
export function TriagePanel({ triage }: { readonly triage: TriageResult }) {
  return <section aria-label="Taktik sınıflandırma"><h3>1. Taktik sınıflandırma</h3><p>{triage.summary}</p>
    <ul>{triage.cues.map((cue, i) => <li key={i}>{cue}</li>)}</ul>
    <details><summary>Kontroller ve bağlam</summary><ul>{[...triage.checks, ...triage.context].map((item, i) => <li key={i}>{item}</li>)}</ul></details>
  </section>;
}
