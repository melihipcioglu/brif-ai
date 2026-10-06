import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { createInitialVocab } from '../../../src/data/initialVocab';
import { QuestionSolver } from '../../../src/components/questions/QuestionSolver';
import type { QuestionAttempt } from '../../../src/types/question';

const q = initialQuestions[0];
if (!q) throw new Error('Missing question');
const question = q;
const save = () => vi.fn<(attempt: QuestionAttempt) => Promise<void>>().mockResolvedValue(undefined);
const answer = (id: string) => screen.getByRole('radio', { name: new RegExp(`^${id} `) });

describe('Question focus mode', () => {
  it('hides reasoning and correct answer until submission; confidence starts genuinely null', () => {
    render(<QuestionSolver question={question} saveAttempt={save()} />);
    expect(screen.queryByText(/Doğru cevap:/)).toBeNull();
    expect(screen.queryByRole('region', { name: 'Cevap sonrası taktik analiz' })).toBeNull();
    expect(screen.queryByText(question.explanation.triage.summary)).toBeNull();
    for (const label of ['Kesinim', 'Tereddütlüyüm', 'Salladım']) expect(screen.getByRole('button', { name: label }).getAttribute('aria-pressed')).toBe('false');
  });
  it('strikeout and flags are reversible and do not select or submit an answer', async () => {
    const user = userEvent.setup();
    const persist = save();
    render(<QuestionSolver question={question} saveAttempt={persist} />);
    const strike = screen.getByRole('button', { name: 'B şıkkını eleme işareti' });
    await user.click(strike);
    expect((answer('B') as HTMLInputElement).checked).toBe(false);
    expect(strike.getAttribute('aria-pressed')).toBe('true');
    await user.click(answer('B'));
    await user.click(strike);
    expect(strike.getAttribute('aria-pressed')).toBe('false');
    expect((answer('B') as HTMLInputElement).checked).toBe(true);
    await user.click(screen.getByRole('button', { name: 'D şıkkı tuzak şüphesi' }));
    expect((answer('D') as HTMLInputElement).checked).toBe(false);
    expect(persist).not.toHaveBeenCalled();
  });
  it.each([['Kesinim', 'HIGH'], ['Tereddütlüyüm', 'MEDIUM'], ['Salladım', 'LOW']] as const)('persists %s confidence without a default', async (label, confidence) => {
    const user = userEvent.setup();
    const persist = save();
    render(<QuestionSolver question={question} saveAttempt={persist} />);
    await user.click(answer('B'));
    await user.click(screen.getByRole('button', { name: label }));
    await user.click(screen.getByRole('button', { name: 'Yanıtı gönder' }));
    await waitFor(() => expect(persist).toHaveBeenCalledTimes(1));
    expect(persist.mock.calls[0]?.[0].confidence_level).toBe(confidence);
  });
  it('locks the first submission, counts actual answer changes and retries under a new ID', async () => {
    const user = userEvent.setup();
    const persist = save();
    render(<QuestionSolver question={question} saveAttempt={persist} />);
    await user.click(answer('A'));
    await user.click(answer('A'));
    await user.click(answer('C'));
    await user.click(answer('B'));
    await user.click(screen.getByRole('button', { name: 'B şıkkını eleme işareti' }));
    await user.click(screen.getByRole('button', { name: 'D şıkkı tuzak şüphesi' }));
    await user.dblClick(screen.getByRole('button', { name: 'Yanıtı gönder' }));
    await screen.findByRole('button', { name: 'Yeni deneme başlat' });
    expect(persist).toHaveBeenCalledTimes(1);
    const first = persist.mock.calls[0]?.[0];
    expect(first?.option_change_count).toBe(2);
    expect(first?.selected_option).toBe('B');
    expect(first?.eliminated_options).toEqual(['B']);
    expect(first?.distractor_flagged).toEqual(['D']);
    expect(first?.confidence_level).toBeNull();
    expect(Object.isFrozen(first)).toBe(true);
    expect((answer('A') as HTMLInputElement).disabled).toBe(true);
    const analysis = screen.getByRole('region', { name: 'Cevap sonrası taktik analiz' });
    expect(within(analysis).getByRole('heading', { name: '1. Taktik sınıflandırma' })).toBeTruthy();
    expect(within(analysis).getByRole('heading', { name: '4. Çeldirici çözümlemesi' })).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Yeni deneme başlat' }));
    expect(screen.queryByRole('region', { name: 'Cevap sonrası taktik analiz' })).toBeNull();
    await user.click(answer('A'));
    await user.click(screen.getByRole('button', { name: 'Yanıtı gönder' }));
    await waitFor(() => expect(persist).toHaveBeenCalledTimes(2));
    expect(persist.mock.calls[1]?.[0].id).not.toBe(first?.id);
    expect(first?.selected_option).toBe('B');
  });
  it('records elapsed time without enforcing a deadline', async () => {
    vi.useFakeTimers();
    try {
      const persist = save();
      render(<QuestionSolver question={question} saveAttempt={persist} />);
      await act(async () => { vi.advanceTimersByTime(90_000); });
      fireEvent.click(answer('B'));
      await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Yanıtı gönder' })); });
      expect(persist.mock.calls[0]?.[0].response_time_ms).toBeGreaterThanOrEqual(90_000);
      expect(persist.mock.calls[0]?.[0].is_correct).toBe(true);
    } finally { vi.useRealTimers(); }
  });
  it('retries failed persistence with the same immutable record, not a second attempt', async () => {
    const user = userEvent.setup();
    const persist = save().mockRejectedValueOnce(new Error('quota'));
    render(<QuestionSolver question={question} saveAttempt={persist} />);
    await user.click(answer('B'));
    await user.click(screen.getByRole('button', { name: 'Yanıtı gönder' }));
    const retry = await screen.findByRole('button', { name: 'Kaydı yeniden dene' });
    expect(screen.queryByRole('button', { name: 'Yeni deneme başlat' })).toBeNull();
    await user.click(retry);
    await screen.findByRole('button', { name: 'Yeni deneme başlat' });
    expect(persist.mock.calls[1]?.[0]).toBe(persist.mock.calls[0]?.[0]);
  });
});
describe('Keyboard and frozen WordPopover integration', () => {
  it('supports keyboard selection and independent Alt-letter strikeout, preserving Escape', async () => {
    const user = userEvent.setup();
    render(<QuestionSolver question={question} saveAttempt={save()} />);
    await user.tab();
    expect(document.activeElement).toBe(answer('A'));
    await user.keyboard('b');
    expect((answer('B') as HTMLInputElement).checked).toBe(true);
    await user.keyboard('{Alt>}b{/Alt}');
    expect(screen.getByRole('button', { name: 'B şıkkını eleme işareti' }).getAttribute('aria-pressed')).toBe('true');
    expect((answer('B') as HTMLInputElement).checked).toBe(true);
    await user.keyboard('{Escape}');
    expect((answer('B') as HTMLInputElement).checked).toBe(true);
  });
  it('opens Phase 1 word support without selecting an answer, records help, and never hard-blocks submission', async () => {
    const user = userEvent.setup();
    const persist = save();
    const words = createInitialVocab(0);
    const before = structuredClone(words);
    render(<QuestionSolver question={question} words={words} saveAttempt={persist} />);
    const word = screen.getByRole('button', { name: 'inhibit: kelime desteği' });
    await user.click(word);
    expect(screen.getByRole('dialog')).toBeTruthy();
    expect(screen.getAllByRole('radio').every((node) => !(node as HTMLInputElement).checked)).toBe(true);
    await user.keyboard('b');
    expect((answer('B') as HTMLInputElement).checked).toBe(false);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
    await user.click(word);
    expect((screen.getByRole('button', { name: 'Yanıtı gönder' }) as HTMLButtonElement).disabled).toBe(false);
    await user.click(answer('B'));
    await user.click(screen.getByRole('button', { name: 'Yanıtı gönder' }));
    await waitFor(() => expect(persist).toHaveBeenCalledTimes(1));
    const submitted = persist.mock.calls[0]?.[0];
    expect(submitted?.words_clicked).toEqual(['inhibit']);
    expect(submitted?.hints_used_count).toBeGreaterThan(0);
    expect(submitted?.is_correct).toBe(true);
    expect(submitted?.error_attribution).toBeNull();
    expect(words).toEqual(before);
  });
});
