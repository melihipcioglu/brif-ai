import type { ConfidenceLevel } from '../../types/question';
const labels: Readonly<Record<ConfidenceLevel, string>> = { HIGH: 'Kesinim', MEDIUM: 'Tereddütlüyüm', LOW: 'Salladım' };
export function ConfidenceSelector({ value, locked, onChange }: {
  readonly value: ConfidenceLevel | null; readonly locked: boolean; readonly onChange: (value: ConfidenceLevel | null) => void;
}) {
  return <fieldset className="question-confidence"><legend>Yanıt güveni <span>(isteğe bağlı)</span></legend>
    {(Object.keys(labels) as ConfidenceLevel[]).map((level) => <button key={level} type="button" aria-pressed={value === level} disabled={locked} onClick={() => onChange(value === level ? null : level)}>{labels[level]}</button>)}
  </fieldset>;
}
