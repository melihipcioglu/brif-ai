import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DIAGNOSTIC_QUESTIONS_BANK } from '../../../src/data/learning/diagnosticBank';
import { DiagnosticScreen } from '../../../src/components/learning/DiagnosticScreen';
import type { DiagnosticResult } from '../../../src/types/learning';

describe('Diagnostic Assessment Module', () => {
  it('contains comprehensive diagnostic questions covering vocab, syntax and connectors', () => {
    expect(DIAGNOSTIC_QUESTIONS_BANK.length).toBe(9);

    const vocabQuestions = DIAGNOSTIC_QUESTIONS_BANK.filter((q) => q.type === 'VOCAB_RECOGNITION');
    const syntaxQuestions = DIAGNOSTIC_QUESTIONS_BANK.filter((q) => q.type === 'SYNTAX_IDENTIFICATION');
    const connectorQuestions = DIAGNOSTIC_QUESTIONS_BANK.filter((q) => q.type === 'CONNECTOR_DIRECTION');

    expect(vocabQuestions.length).toBe(4);
    expect(syntaxQuestions.length).toBe(3);
    expect(connectorQuestions.length).toBe(2);

    DIAGNOSTIC_QUESTIONS_BANK.forEach((q) => {
      expect(q.prompt.length).toBeGreaterThan(10);
      expect(q.options.length).toBeGreaterThanOrEqual(4);
      const correctOptions = q.options.filter((o) => o.isCorrect);
      expect(correctOptions.length).toBe(1);
      q.options.forEach((opt) => {
        expect(opt.feedback.length).toBeGreaterThan(5);
      });
      expect(q.scaffoldTip.length).toBeGreaterThan(5);
    });
  });

  it('renders DiagnosticScreen, allows answering, and completes calibration', () => {
    let capturedResult: DiagnosticResult | null = null;
    const handleComplete = (result: DiagnosticResult) => {
      capturedResult = result;
    };

    render(<DiagnosticScreen onComplete={handleComplete} />);

    // Check first question
    expect(screen.getByText(/1\. ADIM: KELİME TANIMA/i)).toBeDefined();
    expect(screen.getByText(/prevent/i)).toBeDefined();

    // Advance through all questions
    for (let i = 0; i < DIAGNOSTIC_QUESTIONS_BANK.length; i++) {
      // Find option A button
      const allButtons = screen.getAllByRole('button');
      const optA = allButtons.find((btn) => btn.textContent?.includes('A)'));
      expect(optA).toBeDefined();
      if (optA) fireEvent.click(optA);

      // Confirm answer
      const confirmBtn = screen.getByText(/Cevabı Onayla →/i);
      fireEvent.click(confirmBtn);

      // Next button or finish button
      if (i + 1 < DIAGNOSTIC_QUESTIONS_BANK.length) {
        const nextBtn = screen.getByText(/Sonraki Soruya Geç →/i);
        fireEvent.click(nextBtn);
      } else {
        const finishBtn = screen.getByText(/Sonucu Gör ve Öğrenmeye Başla →/i);
        fireEvent.click(finishBtn);
      }
    }

    // Should render completion summary
    expect(screen.getByText('BAŞLANGIÇ KALİBRASYONU TAMAMLANDI')).toBeDefined();
    expect(screen.getByText('Bugünkü Öğrenme Yolculuğuma Başla →')).toBeDefined();

    // Click start journey
    fireEvent.click(screen.getByText('Bugünkü Öğrenme Yolculuğuma Başla →'));
    expect(capturedResult).not.toBeNull();
    const finalRes = capturedResult as unknown as DiagnosticResult;
    expect(finalRes.total).toBe(9);
    expect(finalRes.assignedLevel).toBeDefined();
  });
});
