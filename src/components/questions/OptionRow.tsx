import { Flag, Strikethrough } from 'lucide-react';
import type { OptionId } from '../../types/question';

export interface OptionRowProps {
  readonly option: { readonly id: OptionId; readonly text: string };
  readonly group: string;
  readonly selected: boolean;
  readonly eliminated: boolean;
  readonly flagged: boolean;
  readonly locked: boolean;
  readonly onSelect: (id: OptionId) => void;
  readonly onEliminate: (id: OptionId) => void;
  readonly onFlag: (id: OptionId) => void;
}
export function OptionRow({ option, group, selected, eliminated, flagged, locked, onSelect, onEliminate, onFlag }: OptionRowProps) {
  return <div className={`question-option${selected ? ' is-selected' : ''}`}>
    <label className="question-option-label">
      <input type="radio" name={group} value={option.id} checked={selected} disabled={locked} onChange={() => onSelect(option.id)} />
      <span className="question-option-letter">{option.id}</span>
      <span className={eliminated ? 'question-option-text is-eliminated' : 'question-option-text'}>{option.text}</span>
      <span className="question-sr-only">{eliminated ? ' (eleme işaretli)' : ''}</span>
    </label>
    <button type="button" aria-label={`${option.id} şıkkını eleme işareti`} aria-pressed={eliminated} disabled={locked} onClick={() => onEliminate(option.id)} title="Eleme işaretini değiştir">
      <Strikethrough size={18} aria-hidden="true" />
    </button>
    <button type="button" aria-label={`${option.id} şıkkı tuzak şüphesi`} aria-pressed={flagged} disabled={locked} onClick={() => onFlag(option.id)} title="Tuzak şüphesini değiştir">
      <Flag size={18} aria-hidden="true" />
    </button>
  </div>;
}
