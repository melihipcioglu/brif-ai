import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createInitialVocab } from '../../src/data/initialVocab';
import { FROST_DURATION_MS, POPOVER_OPEN_DELAY_MS, WordPopover } from '../../src/components/WordPopover';
import type { LexicalRecord } from '../../src/types/lexical';

const word = (): LexicalRecord => {
  const entry = createInitialVocab(0)[0];
  if (entry === undefined) throw new Error('Missing fixture');
  return entry;
};
const trigger = (): HTMLElement => screen.getByRole('button', { name: 'inhibit: kelime desteği' });
beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe('non-blocking adaptive popover', () => {
  const choiceOrder = (): string[] => within(screen.getByRole('dialog')).getAllByRole('button')
    .map((button) => button.textContent ?? '').filter((text) => /^[AB]\./.test(text));
  it('opens within 150 ms on hover, in a portal without changing document scrolling', () => {
    const before = document.body.style.overflow;
    const { container } = render(<WordPopover word={word()} />);
    fireEvent.pointerEnter(trigger());
    act(() => { vi.advanceTimersByTime(POPOVER_OPEN_DELAY_MS - 1); });
    expect(screen.queryByRole('dialog')).toBeNull();
    act(() => { vi.advanceTimersByTime(1); });
    const dialog = screen.getByRole('dialog');
    expect(POPOVER_OPEN_DELAY_MS).toBeLessThanOrEqual(150);
    expect(container.contains(dialog)).toBe(false);
    expect(dialog.getAttribute('aria-modal')).toBe('false');
    expect(document.body.style.overflow).toBe(before);
    expect(within(dialog).getByText(word().exam_meaning_tr)).toBeTruthy();
  });
  it('cancels opening when the pointer leaves early and clears timers on unmount', () => {
    const { unmount } = render(<WordPopover word={word()} />);
    fireEvent.pointerEnter(trigger());
    fireEvent.pointerLeave(trigger());
    act(() => { vi.advanceTimersByTime(200); });
    expect(screen.queryByRole('dialog')).toBeNull();
    fireEvent.pointerEnter(trigger());
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
  it('keeps a hover-opened panel open on click and does not reopen after restoring focus', () => {
    render(<WordPopover word={word()} />);
    fireEvent.pointerEnter(trigger());
    act(() => { vi.advanceTimersByTime(POPOVER_OPEN_DELAY_MS); });
    fireEvent.click(trigger());
    expect(screen.getByRole('dialog')).toBeTruthy();
    const closeButton = screen.getByRole('button', { name: 'Kelime desteğini kapat' });
    act(() => { closeButton.focus(); });
    fireEvent.click(closeButton);
    act(() => { vi.advanceTimersByTime(300); });
    expect(screen.queryByRole('dialog')).toBeNull();
  });
  it('shows meaning automatically after two seconds, and allows immediate reveal', () => {
    const onAssistance = vi.fn();
    render(<WordPopover word={word()} frictionLevel={2} onAssistance={onAssistance} />);
    fireEvent.click(trigger());
    expect(screen.getByText(word().exam_meaning_tr).getAttribute('aria-hidden')).toBe('true');
    act(() => { vi.advanceTimersByTime(FROST_DURATION_MS - 1); });
    expect(onAssistance).not.toHaveBeenCalled();
    act(() => { vi.advanceTimersByTime(1); });
    expect(onAssistance).toHaveBeenCalledWith({ word_id: 'inhibit', kind: 'meaning' });
    expect(screen.queryByRole('button', { name: 'Anlamı göster' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Kelime desteğini kapat' }));
    fireEvent.click(trigger());
    fireEvent.click(screen.getByRole('button', { name: 'Anlamı göster' }));
    expect(onAssistance).toHaveBeenCalledTimes(2);
  });
  it('cancels frost timeout after closing', () => {
    const onAssistance = vi.fn();
    render(<WordPopover word={word()} frictionLevel={2} onAssistance={onAssistance} />);
    fireEvent.click(trigger());
    fireEvent.click(screen.getByRole('button', { name: 'Kelime desteğini kapat' }));
    act(() => { vi.advanceTimersByTime(3_000); });
    expect(onAssistance).not.toHaveBeenCalled();
  });
  it('offers a two-choice micro-test and marks success assisted, never unaided', () => {
    const onMicroTestResult = vi.fn();
    const onAssistance = vi.fn();
    render(<WordPopover word={word()} frictionLevel={3} onMicroTestResult={onMicroTestResult} onAssistance={onAssistance} />);
    fireEvent.click(trigger());
    const dialog = screen.getByRole('dialog');
    const choices = within(dialog).getAllByRole('button').filter((button) => /^[AB]\./.test(button.textContent ?? ''));
    expect(choices).toHaveLength(2);
    const correct = choices.find((button) => button.textContent?.includes(word().exam_meaning_tr));
    if (correct === undefined) throw new Error('Missing correct choice');
    fireEvent.click(correct);
    expect(onMicroTestResult).toHaveBeenCalledWith(expect.objectContaining({ correct: true, outcome: 'assisted' }));
    expect(onAssistance).toHaveBeenCalledWith({ word_id: 'inhibit', kind: 'micro-test' });
    expect(screen.getByRole('status').textContent).toContain('Doğru');
  });
  it('reports a wrong micro-test and still permits revealing the meaning', () => {
    const onMicroTestResult = vi.fn();
    render(<WordPopover word={word()} frictionLevel={3} onMicroTestResult={onMicroTestResult} />);
    fireEvent.click(trigger());
    fireEvent.click(screen.getByRole('button', { name: /bir yerde yaşamak/ }));
    expect(onMicroTestResult).toHaveBeenCalledWith(expect.objectContaining({ correct: false, outcome: 'incorrect' }));
    expect(screen.getByText(word().exam_meaning_tr)).toBeTruthy();
  });
  it('shows polarity/antonym hints at level four and provides a bypass', () => {
    render(<WordPopover word={word()} frictionLevel={4} />);
    fireEvent.click(trigger());
    expect(screen.getByText('↓')).toBeTruthy();
    expect(screen.getByText(/Zıt anlam ipucu: promote/)).toBeTruthy();
    expect(screen.queryByText(word().exam_meaning_tr)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Anlamı göster' }));
    expect(screen.getByText(word().exam_meaning_tr)).toBeTruthy();
  });
  it('allows underlying question buttons to receive the same outside click', () => {
    const answer = vi.fn();
    render(<><WordPopover word={word()} /><button type="button" onClick={answer}>Cevap B</button></>);
    fireEvent.click(trigger());
    const questionButton = screen.getByRole('button', { name: 'Cevap B' });
    expect(questionButton.hasAttribute('disabled')).toBe(false);
    fireEvent.pointerDown(questionButton);
    fireEvent.click(questionButton);
    expect(answer).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('dialog')).toBeNull();
  });
  it('supports keyboard entry, Escape and focus restoration without scrolling', () => {
    const nativeFocus = HTMLElement.prototype.focus;
    vi.spyOn(HTMLElement.prototype, 'focus').mockImplementation(function (this: HTMLElement, options?: FocusOptions) {
      if (this.closest<HTMLElement>('[role="dialog"]')?.style.visibility === 'hidden') return;
      nativeFocus.call(this, options);
    });
    render(<WordPopover word={word()} />);
    fireEvent.keyDown(trigger(), { key: 'ArrowDown' });
    expect(screen.getByRole('dialog').contains(document.activeElement)).toBe(true);
    fireEvent.keyDown(document.activeElement ?? document, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(document.activeElement).toBe(trigger());
  });
  it('resets a previous word’s revealed meaning when the record changes', () => {
    const { rerender } = render(<WordPopover word={word()} frictionLevel={2} />);
    fireEvent.click(trigger());
    fireEvent.click(screen.getByRole('button', { name: 'Anlamı göster' }));
    const other = createInitialVocab(0)[1];
    if (other === undefined) throw new Error('Missing fixture');
    rerender(<WordPopover word={other} frictionLevel={2} />);
    expect(screen.queryByRole('dialog')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'accelerate: kelime desteği' }));
    expect(screen.getByText(other.exam_meaning_tr).getAttribute('aria-hidden')).toBe('true');
  });
  it('keeps A/B order stable throughout one open micro-test including seed changes and rerenders', () => {
    const { rerender } = render(<WordPopover word={word()} frictionLevel={3} choiceSeed="attempt-1" />);
    fireEvent.click(trigger());
    const originalOrder = choiceOrder();
    rerender(<WordPopover word={{ ...word(), encounter_count: 9 }} frictionLevel={3} choiceSeed="attempt-2" />);
    expect(choiceOrder()).toEqual(originalOrder);
    fireEvent.click(trigger());
    expect(choiceOrder()).toEqual(originalOrder);
    act(() => { vi.advanceTimersByTime(500); });
    expect(choiceOrder()).toEqual(originalOrder);
  });
  it('distributes the same word across both A/B positions for different seeded encounters', () => {
    const positions: number[] = [];
    for (let index = 0; index < 10; index += 1) {
      const { unmount } = render(<WordPopover word={word()} frictionLevel={3} choiceSeed={`attempt-${index}`} />);
      fireEvent.click(trigger());
      positions.push(choiceOrder().findIndex((text) => text.includes(word().exam_meaning_tr)));
      unmount();
    }
    expect(positions.filter((position) => position === 0)).toHaveLength(5);
    expect(positions.filter((position) => position === 1)).toHaveLength(5);
  });
  it('reproduces explicit seed ordering and varies unseeded reopened encounters without render randomness', () => {
    const explicit = render(<WordPopover word={word()} frictionLevel={3} choiceSeed="session-1:review-9" />);
    fireEvent.click(trigger());
    const first = choiceOrder();
    explicit.unmount();
    const sameSeed = render(<WordPopover word={word()} frictionLevel={3} choiceSeed="session-1:review-9" />);
    fireEvent.click(trigger());
    expect(choiceOrder()).toEqual(first);
    sameSeed.unmount();
    render(<WordPopover word={word()} frictionLevel={3} />);
    fireEvent.click(trigger());
    const openingOne = choiceOrder();
    fireEvent.click(screen.getByRole('button', { name: 'Kelime desteğini kapat' }));
    fireEvent.click(trigger());
    expect(choiceOrder()).not.toEqual(openingOne);
  });
  it('full reveal includes compact POS, synonyms, antonyms, distractor, family and exam sentence', () => {
    render(<WordPopover word={word()} frictionLevel={1} />);
    fireEvent.click(trigger());
    const dialog = within(screen.getByRole('dialog'));
    expect(dialog.getByText('verb')).toBeTruthy();
    expect(dialog.getByText('suppress')).toBeTruthy();
    expect(dialog.getByText('promote')).toBeTruthy();
    expect(dialog.getByText('inhabit')).toBeTruthy();
    expect(dialog.getByText(/inhibition \(noun\).*inhibitor \(noun\)/)).toBeTruthy();
    expect(dialog.getByText(word().exam_sentence)).toBeTruthy();
    expect(dialog.queryByText(/inhibit the formation of/)).toBeNull();
  });
  it.each([3, 4] as const)('level %i withholds answer-revealing details until full reveal and allows bypass', (level) => {
    render(<WordPopover word={word()} frictionLevel={level} />);
    fireEvent.click(trigger());
    expect(screen.queryByText(word().exam_sentence)).toBeNull();
    expect(screen.queryByText('suppress')).toBeNull();
    expect(screen.queryByText(/inhibition \(noun\)/)).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Anlamı göster' }));
    expect(screen.getByText(word().exam_meaning_tr)).toBeTruthy();
    expect(screen.getByText(word().exam_sentence)).toBeTruthy();
  });
});
