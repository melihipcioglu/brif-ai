import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Eye, X } from 'lucide-react';
import type { FrictionLevel, LexicalRecord } from '../types/lexical';
import { getFrictionLevel } from '../services/lexicalScheduler';
import './WordPopover.css';

/** Hover target is below 150 ms; click and keyboard activation are immediate. */
export const POPOVER_OPEN_DELAY_MS = 120;
export const FROST_DURATION_MS = 2_000;
const CLOSE_DELAY_MS = 160;
const GAP = 8;

export interface AssistanceEvent {
  readonly word_id: string;
  readonly kind: 'meaning' | 'micro-test' | 'polarity';
}
export interface MicroTestResult {
  readonly word_id: string;
  readonly selected_meaning: string;
  readonly correct: boolean;
  /** Meaning choices are assistance; a micro-test never supplies unaided evidence. */
  readonly outcome: 'assisted' | 'incorrect';
}
export interface WordPopoverProps {
  readonly word: LexicalRecord;
  readonly children?: ReactNode;
  readonly frictionLevel?: FrictionLevel;
  /** Supply an attempt/session+encounter ID for reproducible option ordering. */
  readonly choiceSeed?: string;
  readonly className?: string;
  readonly onOpenChange?: (open: boolean) => void;
  readonly onAssistance?: (event: AssistanceEvent) => void;
  readonly onMicroTestResult?: (result: MicroTestResult) => void;
}

/** The keyed inner component resets timers/quiz state if the word or level changes. */
export function WordPopover(props: WordPopoverProps) {
  const level = props.frictionLevel ?? getFrictionLevel(props.word);
  return <WordPopoverContent key={`${props.word.word_id}:${level}`} {...props} level={level} />;
}

function WordPopoverContent({ word, children, className, level, choiceSeed, onOpenChange, onAssistance, onMicroTestResult }: WordPopoverProps & { readonly level: FrictionLevel }) {
  const id = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const openTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const openRef = useRef(false);
  const focusPanel = useRef(false);
  const restoringFocus = useRef(false);
  const reportedAssistance = useRef(new Set<AssistanceEvent['kind']>());
  const encounterSequence = useRef(0);
  const callbacks = useRef({ onOpenChange, onAssistance, onMicroTestResult });
  const [open, setOpen] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [selected, setSelected] = useState<'correct' | 'distractor' | null>(null);
  const [correctFirst, setCorrectFirst] = useState(true);
  const [position, setPosition] = useState<CSSProperties>({ visibility: 'hidden' });
  useLayoutEffect(() => { callbacks.current = { onOpenChange, onAssistance, onMicroTestResult }; });

  const clearTimers = useCallback(() => {
    if (openTimer.current !== null) clearTimeout(openTimer.current);
    if (closeTimer.current !== null) clearTimeout(closeTimer.current);
    openTimer.current = null;
    closeTimer.current = null;
  }, []);

  const reportAssistance = useCallback((kind: AssistanceEvent['kind']) => {
    if (reportedAssistance.current.has(kind)) return;
    reportedAssistance.current.add(kind);
    callbacks.current.onAssistance?.({ word_id: word.word_id, kind });
  }, [word.word_id]);

  const show = useCallback(() => {
    clearTimers();
    if (openRef.current) return;
    openRef.current = true;
    // Resolve only when opening, never during render/hydration. State fixes the order
    // throughout this quiz even if its props rerender or choiceSeed changes mid-quiz.
    const seed = JSON.stringify([word.word_id, choiceSeed ?? id, encounterSequence.current]);
    let hash = 2_166_136_261;
    for (const character of seed) hash = Math.imul(hash ^ character.charCodeAt(0), 16_777_619);
    setCorrectFirst((hash >>> 0) % 2 === 0);
    encounterSequence.current += 1;
    reportedAssistance.current.clear();
    setSelected(null);
    setRevealed(level === 1);
    setPosition({ visibility: 'hidden' });
    setOpen(true);
    callbacks.current.onOpenChange?.(true);
  }, [clearTimers, level, choiceSeed, id, word.word_id]);

  const close = useCallback((restoreFocus = false) => {
    clearTimers();
    focusPanel.current = false;
    if (!openRef.current) return;
    openRef.current = false;
    setOpen(false);
    callbacks.current.onOpenChange?.(false);
    if (restoreFocus) {
      restoringFocus.current = true;
      trigger.current?.focus({ preventScroll: true });
      restoringFocus.current = false;
    }
  }, [clearTimers]);

  useEffect(() => () => {
    clearTimers();
    if (openRef.current) callbacks.current.onOpenChange?.(false);
  }, [clearTimers]);

  useEffect(() => {
    if (!open) return;
    if (level === 1) reportAssistance('meaning');
    if (level === 3) reportAssistance('micro-test');
    if (level === 4) reportAssistance('polarity');
  }, [open, level, reportAssistance]);

  const reveal = useCallback(() => {
    setRevealed(true);
    reportAssistance('meaning');
  }, [reportAssistance]);

  useEffect(() => {
    if (!open || level !== 2 || revealed) return;
    const timeout = setTimeout(reveal, FROST_DURATION_MS);
    return () => clearTimeout(timeout);
  }, [open, level, revealed, reveal]);

  useLayoutEffect(() => {
    if (!open) return;
    const reposition = (): void => {
      if (trigger.current === null || panel.current === null) return;
      const anchor = trigger.current.getBoundingClientRect();
      const viewport = window.visualViewport;
      const width = viewport?.width ?? window.innerWidth;
      const height = viewport?.height ?? window.innerHeight;
      const offsetLeft = viewport?.offsetLeft ?? 0;
      const offsetTop = viewport?.offsetTop ?? 0;
      const panelWidth = Math.max(1, Math.min(320, width - GAP * 2));
      const box = panel.current.getBoundingClientRect();
      const maxHeight = Math.max(1, height - GAP * 2);
      const panelHeight = Math.min(box.height, maxHeight);
      const above = anchor.top - panelHeight - GAP;
      // Prefer above the word, leaving the question's following answer controls uncovered.
      const proposedTop = above >= offsetTop + GAP ? above : anchor.bottom + GAP;
      setPosition({
        top: Math.max(offsetTop + GAP, Math.min(proposedTop, offsetTop + height - panelHeight - GAP)),
        left: Math.max(offsetLeft + GAP, Math.min(anchor.left, offsetLeft + width - panelWidth - GAP)),
        width: panelWidth, maxHeight, visibility: 'visible',
      });
    };
    reposition();
    const observer = typeof ResizeObserver === 'undefined' ? undefined : new ResizeObserver(reposition);
    if (panel.current !== null) observer?.observe(panel.current);
    if (trigger.current !== null) observer?.observe(trigger.current);
    // Capture also follows nested scrolling containers. Never call scrollIntoView or lock body.
    window.addEventListener('scroll', reposition, true);
    window.addEventListener('resize', reposition);
    window.visualViewport?.addEventListener('resize', reposition);
    window.visualViewport?.addEventListener('scroll', reposition);
    return () => {
      observer?.disconnect();
      window.removeEventListener('scroll', reposition, true);
      window.removeEventListener('resize', reposition);
      window.visualViewport?.removeEventListener('resize', reposition);
      window.visualViewport?.removeEventListener('scroll', reposition);
    };
  }, [open, revealed, selected]);

  useLayoutEffect(() => {
    // Real browsers cannot focus a control until the initially hidden panel is positioned.
    if (open && position.visibility === 'visible' && focusPanel.current) {
      panel.current?.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true });
      focusPanel.current = false;
    }
  }, [open, position.visibility]);

  useEffect(() => {
    if (!open) return;
    const isInside = (target: EventTarget | null): boolean => target instanceof Node &&
      (trigger.current?.contains(target) === true || panel.current?.contains(target) === true);
    const outside = (event: PointerEvent): void => {
      if (!isInside(event.target)) close(); // Do not cancel the underlying question click.
    };
    const keyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') close(isInside(document.activeElement));
    };
    const focusIn = (event: FocusEvent): void => { if (!isInside(event.target)) close(); };
    document.addEventListener('pointerdown', outside, true);
    document.addEventListener('keydown', keyDown);
    document.addEventListener('focusin', focusIn);
    return () => {
      document.removeEventListener('pointerdown', outside, true);
      document.removeEventListener('keydown', keyDown);
      document.removeEventListener('focusin', focusIn);
    };
  }, [open, close]);

  const scheduleOpen = (): void => {
    clearTimers();
    if (!openRef.current) openTimer.current = setTimeout(show, POPOVER_OPEN_DELAY_MS);
  };
  const scheduleClose = (): void => {
    clearTimers();
    closeTimer.current = setTimeout(() => {
      // Keep keyboard users' focused controls mounted while the pointer leaves.
      if (!panel.current?.contains(document.activeElement) && document.activeElement !== trigger.current) close();
    }, CLOSE_DELAY_MS);
  };

  const distractor = word.typical_distractor.find((item) => item.meaning_tr !== word.exam_meaning_tr);
  const correctOption = { key: 'correct' as const, label: word.exam_meaning_tr };
  const wrongOption = { key: 'distractor' as const, label: distractor?.meaning_tr ?? '' };
  const options = correctFirst ? [correctOption, wrongOption] : [wrongOption, correctOption];
  const choose = (key: 'correct' | 'distractor', label: string): void => {
    if (selected !== null) return;
    setSelected(key);
    reveal();
    callbacks.current.onMicroTestResult?.({
      word_id: word.word_id, selected_meaning: label,
      correct: key === 'correct', outcome: key === 'correct' ? 'assisted' : 'incorrect',
    });
  };

  return <>
    <button
      ref={trigger} type="button" className={`yokdil-word-trigger ${className ?? ''}`}
      aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined}
      aria-label={`${word.lemma}: kelime desteği`}
      onPointerEnter={(event) => { if (event.pointerType !== 'touch') scheduleOpen(); }}
      onPointerLeave={scheduleClose}
      onFocus={() => { if (!restoringFocus.current) scheduleOpen(); }}
      onBlur={() => { if (!openRef.current) clearTimers(); }}
      onClick={(event) => { event.stopPropagation(); show(); }}
      onKeyDown={(event) => {
        if (event.key === 'ArrowDown') {
          event.preventDefault();
          focusPanel.current = true;
          if (openRef.current) panel.current?.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true });
          else show();
        }
        if (event.key === 'Escape') { event.stopPropagation(); close(); }
      }}
    >{children ?? word.lemma}</button>
    {open && typeof document !== 'undefined' && createPortal(
      <div
        ref={panel} id={id} role="dialog" aria-modal="false" aria-labelledby={`${id}-title`}
        className="yokdil-word-popover rounded-xl border border-solid border-slate-200 bg-white p-4 text-slate-900 shadow-xl"
        style={position} onPointerEnter={clearTimers} onPointerLeave={scheduleClose}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex items-baseline gap-2">
            <strong id={`${id}-title`}>{word.lemma}</strong>
            <span className="text-xs text-slate-500" lang="en">{word.pos}</span>
          </div>
          <button type="button" aria-label="Kelime desteğini kapat" className="flex rounded border-0 bg-transparent p-1 text-slate-500" onClick={() => close(true)}>
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        {level === 2 && !revealed && <div className="grid gap-2">
          <span className="yokdil-frost" aria-hidden="true">{word.exam_meaning_tr}</span>
          <p className="text-sm text-slate-600">Anlam 2 saniye içinde açılır.</p>
        </div>}
        {level === 3 && selected === null && !revealed && distractor !== undefined && <div className="grid gap-2">
          <p className="text-sm text-slate-600">Bu bağlamda hangi anlam uygun?</p>
          {options.map((option, index) => <button
            key={option.key} type="button"
            className="rounded-lg border border-solid border-slate-200 bg-slate-50 px-3 py-2 text-left hover:bg-slate-100"
            onClick={() => choose(option.key, option.label)}
          ><span className="font-semibold">{index === 0 ? 'A' : 'B'}.</span> {option.label}</button>)}
        </div>}
        {level === 4 && !revealed && <div className="grid gap-2">
          <p><span className="text-2xl font-semibold" aria-label={word.polarity_symbol === '↑' ? 'Artış veya başlatma yönü' : word.polarity_symbol === '↓' ? 'Azalma veya baskılama yönü' : 'Bağlama bağlı yön'}>{word.polarity_symbol}</span></p>
          {word.antonyms[0] !== undefined && <p className="text-sm text-slate-600">Zıt anlam ipucu: {word.antonyms[0]}</p>}
        </div>}
        {selected !== null && <p role="status" className="mb-2 text-sm text-slate-700">
          {selected === 'correct' ? 'Doğru. Bu yanıt yardımlı alıştırma olarak değerlendirilir.' : `Bu seçenek uygun değil. ${distractor?.explanation_tr ?? ''}`}
        </p>}
        {revealed && <div className="grid gap-2" aria-live="polite">
          <p className="font-medium">{word.exam_meaning_tr}</p>
          {word.critical_collocations.slice(0, 2).map((item) => <p key={item.phrase} className="text-sm text-slate-600">
            <span lang="en">{item.phrase}</span> — {item.meaning_tr}
          </p>)}
          {(word.synonyms.length > 0 || word.antonyms.length > 0) && <p className="text-sm text-slate-600">
            {word.synonyms[0] !== undefined && <>Eş: <span lang="en">{word.synonyms[0]}</span></>}
            {word.synonyms.length > 0 && word.antonyms.length > 0 && ' · '}
            {word.antonyms[0] !== undefined && <>Zıt: <span lang="en">{word.antonyms[0]}</span></>}
          </p>}
          {distractor !== undefined && <p className="text-sm text-slate-600">
            Karıştırma: <span lang="en">{distractor.word}</span> — {distractor.meaning_tr}
          </p>}
          <p className="text-sm text-slate-600">
            Aile: <span lang="en">{word.word_family.filter((member) => member.form !== word.lemma)
              .slice(0, 2).map((member) => `${member.form} (${member.pos})`).join(' · ') || word.lemma}</span>
          </p>
          <p className="text-sm italic text-slate-600" lang="en">{word.exam_sentence}</p>
        </div>}
        {!revealed && <button type="button" className="mt-3 flex items-center gap-2 rounded-lg border-0 bg-blue-50 px-3 py-2 text-blue-800 hover:bg-blue-100" onClick={reveal}>
          <Eye size={16} aria-hidden="true" /> Anlamı göster
        </button>}
      </div>, document.body,
    )}
  </>;
}

export default WordPopover;
