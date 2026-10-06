import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { LexicalRecord } from '../../types/lexical';
import { OPTION_IDS } from '../../types/question';
import type { OptionId, Question, QuestionAttempt, QuestionFamily } from '../../types/question';
import { createAttemptDraft, deepFreeze, submitQuestionAttempt, updateDraft } from '../../services/questions/attempts';
import type { DraftAction } from '../../services/questions/attempts';
import { persistQuestionAttempt } from '../../services/questions/db';
import { questionSchema } from '../../services/questions/validation';
import { QuestionStem } from './QuestionStem';
import { QuestionOptions } from './QuestionOptions';
import { ConfidenceSelector } from './ConfidenceSelector';
import { PostAnswerAnalysis } from './PostAnswerAnalysis';
import './questions.css';

const familyLabels: Readonly<Record<QuestionFamily, string>> = {
  GAP_FILL: 'Boşluk doldurma', CLOZE_TEST: 'Paragrafta boşluk doldurma', SENTENCE_COMPLETION: 'Cümle tamamlama',
  TRANSLATION_ENG_TR: 'İngilizceden Türkçeye çeviri', TRANSLATION_TR_ENG: 'Türkçeden İngilizceye çeviri',
  PARAGRAPH_COMPLETION: 'Paragraf tamamlama', IRRELEVANT_SENTENCE: 'Anlam bütünlüğünü bozan cümle', READING_COMPREHENSION: 'Okuduğunu anlama',
};
export interface QuestionSolverProps {
  readonly question: Question;
  readonly words?: readonly LexicalRecord[];
  readonly sessionId?: string | null;
  /** Resolve only after durable commit. Rejection keeps the same immutable attempt for retry. */
  readonly saveAttempt?: (attempt: QuestionAttempt, question: Question) => Promise<void>;
}
export function QuestionSolver(props: QuestionSolverProps) {
  return <QuestionRun key={`${props.question.id}:${props.sessionId ?? ''}`} {...props} />;
}
function QuestionRun(props: QuestionSolverProps) {
  const [run, setRun] = useState(0);
  return <QuestionSession key={run} {...props} onRetry={() => setRun((value) => value + 1)} />;
}
function QuestionSession({ question: input, words = [], sessionId = null, saveAttempt = persistQuestionAttempt, onRetry }: QuestionSolverProps & { readonly onRetry: () => void }) {
  // Snapshot the question as well as the response: rerenders cannot silently change the answer key.
  const [question] = useState(() => deepFreeze(questionSchema.parse(input)));
  const [attemptId] = useState(() => crypto.randomUUID());
  const [startedAt] = useState(() => performance.now());
  const [draft, setDraft] = useState(createAttemptDraft);
  const draftRef = useRef(draft);
  const attemptRef = useRef<QuestionAttempt | null>(null);
  const [attempt, setAttempt] = useState<QuestionAttempt | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const savingRef = useRef(false);
  const mountedRef = useRef(true);
  const [notice, setNotice] = useState('');
  const heading = useId();
  const group = useId();
  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);
  useEffect(() => {
    if (attempt !== null) return;
    const timer = setInterval(() => setElapsed(Math.max(0, Math.round(performance.now() - startedAt))), 1_000);
    return () => clearInterval(timer);
  }, [attempt, startedAt]);
  const dispatch = (action: DraftAction): void => {
    if (attemptRef.current !== null) return;
    const next = updateDraft(draftRef.current, action);
    draftRef.current = next;
    setDraft(next);
  };
  const save = async (record: QuestionAttempt): Promise<void> => {
    if (savingRef.current) return;
    savingRef.current = true;
    setSaveState('saving');
    try {
      await saveAttempt(record, question);
      if (mountedRef.current) setSaveState('saved');
    } catch {
      if (mountedRef.current) setSaveState('error');
    } finally { savingRef.current = false; }
  };
  const submit = (): void => {
    if (attemptRef.current !== null) return;
    if (draftRef.current.selected_option === null) { setNotice('Göndermek için bir yanıt seçin.'); return; }
    const response_time_ms = Math.max(0, Math.round(performance.now() - startedAt));
    const record = submitQuestionAttempt(question, draftRef.current, { id: attemptId, session_id: sessionId, response_time_ms, attempted_at: Date.now() });
    attemptRef.current = record;
    setAttempt(record);
    setElapsed(response_time_ms);
    setNotice('');
    void save(record);
  };
  const keyboard = (event: KeyboardEvent<HTMLElement>): void => {
    if (attemptRef.current !== null || event.defaultPrevented || event.nativeEvent.isComposing || event.ctrlKey || event.metaKey) return;
    const target = event.target;
    if (target instanceof Element && target.closest('[data-question-word], [role="dialog"], textarea, select, input:not([type="radio"]), [contenteditable="true"]')) return;
    const key = event.key.toUpperCase();
    if (!OPTION_IDS.includes(key as OptionId)) return;
    event.preventDefault();
    dispatch({ type: event.altKey ? 'eliminate' : 'select', option: key as OptionId });
  };
  const benchmark = question.personal_benchmark_ms ?? question.global_benchmark_ms;
  return <article className="question-solver" lang="tr" aria-labelledby={heading} onKeyDown={keyboard}>
    <header className="question-header"><div><p className="question-eyebrow">Özgün fen alıştırması</p><h1 id={heading}>{familyLabels[question.family]}</h1></div>
      <output aria-label="Geçen süre" aria-live="off" className="question-timer">{Math.floor(elapsed / 60_000)}:{String(Math.floor(elapsed / 1_000) % 60).padStart(2, '0')}</output>
    </header>
    {benchmark !== undefined && <p className="question-muted">{question.personal_benchmark_ms !== undefined ? 'Kişisel' : 'Genel'} referans süre: {Math.round(benchmark / 1_000)} sn. Öncelik doğru yanıtta.</p>}
    <QuestionStem question={question} words={words} attemptId={attemptId} onWord={(word_id) => dispatch({ type: 'word', word_id })} onHint={() => dispatch({ type: 'hint' })} />
    <QuestionOptions question={question} draft={draft} group={group} locked={attempt !== null}
      onSelect={(option) => dispatch({ type: 'select', option })} onEliminate={(option) => dispatch({ type: 'eliminate', option })} onFlag={(option) => dispatch({ type: 'flag', option })} />
    <p className="question-muted">A–E: yanıt seç · Alt + A–E: eleme işareti · Bayrak: tuzak şüphesi</p>
    <ConfidenceSelector value={draft.confidence_level} locked={attempt !== null} onChange={(confidence) => dispatch({ type: 'confidence', confidence })} />
    {attempt === null && <button type="button" className="question-submit" onClick={submit}>Yanıtı gönder</button>}
    {notice !== '' && <p role="alert">{notice}</p>}
    {attempt !== null && <>
      <p role="status">{saveState === 'saved' ? 'Yanıt kaydedildi.' : saveState === 'saving' ? 'Yanıt kaydediliyor…' : ''}</p>
      {saveState === 'error' && <div role="alert"><p>Yanıt kaydedilemedi. Bu ekranı kapatmadan kaydı yeniden deneyin.</p><button type="button" onClick={() => void save(attempt)}>Kaydı yeniden dene</button></div>}
      <PostAnswerAnalysis question={question} attempt={attempt} />
      {saveState === 'saved' && <button type="button" onClick={onRetry}>Yeni deneme başlat</button>}
    </>}
  </article>;
}
