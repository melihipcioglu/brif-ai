import type { ConfidenceLevel, OptionId, Question, QuestionAttempt } from '../../types/question';
import { attributeQuestionError } from './attribution';
import { questionSchema, validateAttemptForQuestion } from './validation';

export function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object') {
    Object.values(value).forEach((child: unknown) => deepFreeze(child));
    Object.freeze(value);
  }
  return value;
}
export interface AttemptDraft {
  readonly selected_option: OptionId | null;
  readonly confidence_level: ConfidenceLevel | null;
  readonly eliminated_options: readonly OptionId[];
  readonly distractor_flagged: readonly OptionId[];
  readonly words_clicked: readonly string[];
  readonly hints_used_count: number;
  readonly option_change_count: number;
}
export const createAttemptDraft = (): AttemptDraft => ({ selected_option: null, confidence_level: null, eliminated_options: [], distractor_flagged: [], words_clicked: [], hints_used_count: 0, option_change_count: 0 });
export type DraftAction =
  | { readonly type: 'select'; readonly option: OptionId }
  | { readonly type: 'eliminate' | 'flag'; readonly option: OptionId }
  | { readonly type: 'confidence'; readonly confidence: ConfidenceLevel | null }
  | { readonly type: 'word'; readonly word_id: string }
  | { readonly type: 'hint' };
const toggle = (values: readonly OptionId[], value: OptionId): readonly OptionId[] => values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
export function updateDraft(draft: AttemptDraft, action: DraftAction): AttemptDraft {
  switch (action.type) {
    case 'select': return { ...draft, selected_option: action.option, option_change_count: draft.option_change_count + Number(draft.selected_option !== null && draft.selected_option !== action.option) };
    case 'eliminate': return { ...draft, eliminated_options: toggle(draft.eliminated_options, action.option) };
    case 'flag': return { ...draft, distractor_flagged: toggle(draft.distractor_flagged, action.option) };
    case 'confidence': return { ...draft, confidence_level: action.confidence };
    case 'word': return { ...draft, words_clicked: [...new Set([...draft.words_clicked, action.word_id])] };
    case 'hint': return { ...draft, hints_used_count: draft.hints_used_count + 1 };
  }
}
export function submitQuestionAttempt(question: Question, draft: AttemptDraft, meta: {
  readonly id: string; readonly session_id: string | null; readonly response_time_ms: number; readonly attempted_at: number;
}): QuestionAttempt {
  const q = questionSchema.parse(question);
  if (draft.selected_option === null) throw new RangeError('Select an answer first');
  const base = { ...draft, ...meta, question_id: q.id, family: q.family,
    ...(q.tactical.kind === 'GAP_FILL' ? { subclass: q.tactical.focus } : {}),
    selected_option: draft.selected_option, is_correct: draft.selected_option === q.correct_option };
  return deepFreeze(validateAttemptForQuestion({ ...base, error_attribution: attributeQuestionError(q, base) }, q));
}
