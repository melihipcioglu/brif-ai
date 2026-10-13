import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { academicVocabBank, getWordProgression, getTrapWords } from '../../../src/data/learning/academicVocabBank';
import { VocabTrainerScreen } from '../../../src/components/learning/VocabTrainerScreen';
import { createInitialLearnerProfile } from '../../../src/services/learning/dailyPlanner';

describe('Word Progression & Sentence Expansion Engine', () => {
  it('provides 4-level progressive sentences for words in bank', () => {
    const inhibitWord = academicVocabBank.find((w) => w.word_id === 'inhibit')!;
    expect(inhibitWord).toBeDefined();

    const steps = getWordProgression(inhibitWord);
    expect(steps.length).toBe(4);
    expect(steps[0]!.level).toBe(0);
    expect(steps[0]!.title).toContain('Atom Cümle');
    expect(steps[0]!.englishText).toBe('Cold inhibits bacteria.');

    expect(steps[1]!.level).toBe(1);
    expect(steps[1]!.title).toContain('1. Basamak Genişletme');

    expect(steps[2]!.level).toBe(2);
    expect(steps[2]!.title).toContain('2. Basamak: Fen Kalıbı');

    expect(steps[3]!.level).toBe(3);
    expect(steps[3]!.title).toContain('3. Basamak: Gerçek YÖKDİL');

    steps.forEach((step) => {
      expect(step.englishText.length).toBeGreaterThan(5);
      expect(step.turkishTranslation.length).toBeGreaterThan(5);
      expect(step.focusPoint.length).toBeGreaterThan(5);
      expect(step.tokens.length).toBeGreaterThan(0);
    });
  });

  it('provides trap word comparisons (inhibit vs inhabit vs exhibit)', () => {
    const inhibitWord = academicVocabBank.find((w) => w.word_id === 'inhibit')!;
    const trapWords = getTrapWords(inhibitWord);

    expect(trapWords.length).toBeGreaterThanOrEqual(2);
    const inhabitTrap = trapWords.find((tw) => tw.trapWord === 'inhabit');
    expect(inhabitTrap).toBeDefined();
    expect(inhabitTrap?.trapMeaning).toContain('yaşamak');
    expect(inhabitTrap?.memoryHook).toContain('Habitat');
  });

  it('renders interactive Sentence Expansion Stepper and Trap Breaker in VocabTrainerScreen', () => {
    const profile = createInitialLearnerProfile();
    const handleFinish = vi.fn();
    const handleCancel = vi.fn();

    render(
      <VocabTrainerScreen
        profile={profile}
        targetWordIds={['inhibit']}
        onFinish={handleFinish}
        onCancel={handleCancel}
      />
    );

    // Should display Atomic Sentence Expansion section
    expect(screen.getByText(/ATOMİK CÜMLE BÜYÜTÜCÜ/i)).toBeDefined();
    expect(screen.getByText(/Cold inhibits bacteria/i)).toBeDefined();

    // Should display Trap Breaker section
    expect(screen.getByText(/TUZAK AŞISI/i)).toBeDefined();
    expect(screen.getAllByText(/inhabit/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/exhibit/i).length).toBeGreaterThan(0);

    // Click "Basamak 1"
    const step1Btn = screen.getByText('Basamak 1');
    fireEvent.click(step1Btn);

    // Should now show expanded sentence
    expect(screen.getByText(/Low temperatures inhibit the growth/i)).toBeDefined();

    // Click "Basamak 2"
    const step2Btn = screen.getByText('Basamak 2');
    fireEvent.click(step2Btn);
    expect(screen.getByText(/Because cold inhibits bacterial growth/i)).toBeDefined();
  });
});
