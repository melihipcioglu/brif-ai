import type { ReactNode } from 'react';
import type { LexicalRecord } from '../../types/lexical';
import type { Question } from '../../types/question';
import { WordPopover } from '../WordPopover';

/** Exact, whole lexical tokens/phrases only; no substring guessing or answer annotation. */
function tokenize(text: string, words: readonly LexicalRecord[]): readonly { text: string; word?: LexicalRecord }[] {
  const matches: { start: number; end: number; word: LexicalRecord }[] = [];
  for (const word of words) {
    const escaped = word.lemma.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`(?<![\\p{L}\\p{N}_])${escaped}(?![\\p{L}\\p{N}_])`, 'giu');
    for (const match of text.matchAll(pattern)) matches.push({ start: match.index, end: match.index + match[0].length, word });
  }
  matches.sort((a, b) => a.start - b.start || b.end - a.end);
  const result: { text: string; word?: LexicalRecord }[] = [];
  let offset = 0;
  for (const match of matches) {
    if (match.start < offset) continue;
    if (match.start > offset) result.push({ text: text.slice(offset, match.start) });
    result.push({ text: text.slice(match.start, match.end), word: match.word });
    offset = match.end;
  }
  if (offset < text.length) result.push({ text: text.slice(offset) });
  return result;
}
export function QuestionStem({ question, words, attemptId, onWord, onHint }: {
  readonly question: Question; readonly words: readonly LexicalRecord[]; readonly attemptId: string;
  readonly onWord: (id: string) => void; readonly onHint: () => void;
}) {
  const available = words.filter((word) => question.lexical_ids?.includes(word.word_id));
  const render = (text: string): ReactNode => tokenize(text, available).map((part, index) => {
    const word = part.word;
    if (word === undefined) return part.text;
    return <span key={index} data-question-word
      onClickCapture={(event) => {
        if (event.target instanceof Element && event.target.closest('.yokdil-word-trigger')) onWord(word.word_id);
      }}
      onKeyDownCapture={(event) => {
        if (event.key === 'ArrowDown' && event.target instanceof Element && event.target.closest('.yokdil-word-trigger')) onWord(word.word_id);
      }}>
      <WordPopover word={word} choiceSeed={attemptId} onAssistance={onHint}>{part.text}</WordPopover>
    </span>;
  });
  return <div className="question-stem">
    {question.passage !== undefined && <div className="question-passage" aria-label="Okuma metni" lang="en">{render(question.passage)}</div>}
    <p lang={question.family === 'TRANSLATION_TR_ENG' ? 'tr' : 'en'}>{render(question.stem)}</p>
  </div>;
}
