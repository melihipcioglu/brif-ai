import type { Question } from '../../types/question';
import type { AttemptDraft } from '../../services/questions/attempts';
import { OptionRow } from './OptionRow';
import type { OptionRowProps } from './OptionRow';

export function QuestionOptions({ question, draft, group, locked, onSelect, onEliminate, onFlag }: {
  readonly question: Question; readonly draft: AttemptDraft; readonly group: string; readonly locked: boolean;
} & Pick<OptionRowProps, 'onSelect' | 'onEliminate' | 'onFlag'>) {
  return <fieldset className="question-options"><legend>Yanıt seçenekleri</legend>
    {question.options.map((option) => <OptionRow key={option.id} option={option} group={group} locked={locked}
      selected={draft.selected_option === option.id} eliminated={draft.eliminated_options.includes(option.id)} flagged={draft.distractor_flagged.includes(option.id)}
      onSelect={onSelect} onEliminate={onEliminate} onFlag={onFlag} />)}
  </fieldset>;
}
