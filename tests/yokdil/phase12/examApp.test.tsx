import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExamApp } from '../../../src/components/exam/ExamApp';
import {
  clearActiveExamSession,
  getStoredLearnerExposures,
  clearStoredLearnerExposures,
  clearExamHistory,
  calculateYokdilScore
} from '../../../src/services/exam/examSessionService';
import { QUESTION_FAMILIES } from '../../../src/types/question';
import { PERFORMANCE_CONTENT_SKILLS } from '../../../src/services/performance/calibration';

describe('Phase 12: Complete Exam Experience & End-to-End User Journey', () => {
  beforeEach(() => {
    localStorage.clear();
    clearActiveExamSession();
    clearStoredLearnerExposures();
    clearExamHistory();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    clearActiveExamSession();
  });

  it('verifies the full 14-step student exam journey', async () => {
    const user = userEvent.setup();

    // -------------------------------------------------------------
    // Step 1: Student opens the app
    // -------------------------------------------------------------
    const { unmount } = render(<ExamApp />);
    expect(screen.getByText('ARCBRIEF / YÖKDİL FEN')).toBeDefined();
    expect(screen.getByRole('button', { name: 'Tam Deneme' })).toBeDefined();

    // -------------------------------------------------------------
    // Step 2 & 3: Mode selection & Start screen information
    // -------------------------------------------------------------
    const startTabBtn = screen.getByRole('button', { name: 'Tam Deneme' });
    await user.click(startTabBtn);

    // Verify Start screen metadata
    expect(screen.getByText('Sınav Başlatma ve Hazırlık')).toBeDefined();
    expect(screen.getByText('Tam Deneme Sınavı')).toBeDefined();
    expect(screen.getByText('80 Soru')).toBeDefined();
    expect(screen.getByText('180 Dakika')).toBeDefined();
    expect(screen.getByText('✓ Taze Sorular Hazır')).toBeDefined();

    // -------------------------------------------------------------
    // Step 4: Click "Sınavı Başlat" -> Loads 80 questions
    // -------------------------------------------------------------
    const startExamBtn = screen.getByRole('button', { name: /Sınavı Başlat/i });
    await user.click(startExamBtn);

    // Active screen is loaded
    await waitFor(() => {
      expect(screen.getByText(/Soru 1 \/ 80/i)).toBeDefined();
    });

    // -------------------------------------------------------------
    // Step 5: Navigation (Previous / Next)
    // -------------------------------------------------------------
    const nextBtn = screen.getByRole('button', { name: 'Sonraki →' });
    await user.click(nextBtn);
    expect(screen.getByText(/Soru 2 \/ 80/i)).toBeDefined();

    const prevBtn = screen.getByRole('button', { name: '← Önceki' });
    await user.click(prevBtn);
    expect(screen.getByText(/Soru 1 \/ 80/i)).toBeDefined();

    // -------------------------------------------------------------
    // Step 6: Question answering (select option B)
    // -------------------------------------------------------------
    const optionB = screen.getByText('B').closest('.exam-option-item')!;
    await user.click(optionB);
    expect(optionB.getAttribute('aria-pressed')).toBe('true');

    // -------------------------------------------------------------
    // Step 7: Option elimination / Strikeout (eliminate option A)
    // -------------------------------------------------------------
    const strikeoutA = screen.getByRole('button', { name: 'A şıkkını ele' });
    await user.click(strikeoutA);
    expect(strikeoutA.getAttribute('title')).toBe('Elemeyi kaldır');

    // Reversible: click again to restore
    await user.click(strikeoutA);
    expect(strikeoutA.getAttribute('title')).toBe('Şıkkı ele');

    // Re-eliminate option A
    await user.click(strikeoutA);
    expect(strikeoutA.getAttribute('title')).toBe('Elemeyi kaldır');

    // -------------------------------------------------------------
    // Step 8: Flagging question for review
    // -------------------------------------------------------------
    const flagBtn = screen.getByRole('button', { name: /İşaretle/i });
    await user.click(flagBtn);
    expect(screen.getByRole('button', { name: /İşaretlendi/i })).toBeDefined();

    // -------------------------------------------------------------
    // Step 9: Question Palette counts & filtering
    // -------------------------------------------------------------
    expect(screen.getByText(/1 Cevaplandı/i)).toBeDefined();
    expect(screen.getByText(/79 Boş/i)).toBeDefined();

    // Palette filter tabs
    const flaggedFilter = screen.getByRole('button', { name: /İşaretli \(1\)/i });
    await user.click(flaggedFilter);
    expect(screen.getByRole('button', { name: /Soru 1,/i })).toBeDefined();

    const allFilter = screen.getByRole('button', { name: /Tümü \(80\)/i });
    await user.click(allFilter);

    // -------------------------------------------------------------
    // Step 10: Session resume / State recovery on reload
    // -------------------------------------------------------------
    unmount();

    // Remount app (simulating page reload)
    render(<ExamApp />);

    // Should resume active session automatically
    await waitFor(() => {
      expect(screen.getByText(/Soru 1 \/ 80/i)).toBeDefined();
    });
    const resumedOptB = screen.getByText('B').closest('.exam-option-item')!;
    expect(resumedOptB.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: /İşaretlendi/i })).toBeDefined();

    // -------------------------------------------------------------
    // Step 11: Accidental leave protection
    // -------------------------------------------------------------
    const beforeUnloadEvent = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(beforeUnloadEvent);
    expect(beforeUnloadEvent.defaultPrevented).toBe(true);

    // -------------------------------------------------------------
    // Step 12: Finish exam modal & Confirmation
    // -------------------------------------------------------------
    const finishBtn = screen.getByRole('button', { name: 'Sınavı Bitir' });
    await user.click(finishBtn);

    expect(screen.getByText('Sınavı Bitirmek İstiyor Musunuz?')).toBeDefined();
    expect(screen.getByText(/boş sorunuz bulunmaktadır/i)).toBeDefined();

    const confirmFinishBtn = screen.getByRole('button', { name: 'Evet, Sınavı Bitir' });
    await user.click(confirmFinishBtn);

    // -------------------------------------------------------------
    // Step 13: Results Screen & Scoring
    // -------------------------------------------------------------
    await waitFor(() => {
      expect(screen.getByText(/YÖKDİL Fen Bilimleri Simülasyon Puanı/i)).toBeDefined();
    });

    // Score banner calculation
    expect(screen.getByText(/Sınav Raporu/i)).toBeDefined();
    expect(screen.getByText('1')).toBeDefined(); // 1 answered
    expect(screen.getByText('79')).toBeDefined(); // 79 blank

    // 8 Question Families Performance section
    expect(screen.getByText('Soru Ailesi Bazında Performans')).toBeDefined();
    for (const fam of QUESTION_FAMILIES) {
      expect(screen.getAllByText(fam).length).toBeGreaterThan(0);
    }

    // Question Review section
    expect(screen.getByText('Soru İnceleme ve Çözümler')).toBeDefined();

    // Review Mode: Triage explanation & cognitive checks
    await user.click(screen.getByRole('button', { name: /Tümü \(80\)/i }));
    expect(screen.getByText('Soru 1')).toBeDefined();
    expect(screen.getAllByText(/Soru Çözümü ve Gerekçe/i).length).toBeGreaterThan(0);

    // -------------------------------------------------------------
    // Step 14: History & Exposure Update
    // -------------------------------------------------------------
    // Return home first
    const returnHomeBtn = screen.getByRole('button', { name: '← Ana Sayfaya Dön' });
    await user.click(returnHomeBtn);

    // Click "Geçmişim" tab
    const historyTabBtn = screen.getByRole('button', { name: 'Geçmişim' });
    await user.click(historyTabBtn);

    expect(screen.getByText('Önceki Sınavlarım ve Geçmiş')).toBeDefined();
    expect(screen.getByText(/Tam Deneme Sınavı/i)).toBeDefined();

    // Check learner exposures were recorded
    const exposures = getStoredLearnerExposures();
    expect(Object.keys(exposures).length).toBe(80);
  }, 30000);

  it('supports short study modes (Quick 5, Standard 15, Intensive 30)', async () => {
    const user = userEvent.setup();
    render(<ExamApp />);

    // Go to Start Screen via "Tam Deneme" / Setup
    await user.click(screen.getByRole('button', { name: 'Tam Deneme' }));

    // Select Quick mode
    const quickModeCard = screen.getByText(/Acil Çalışma/i);
    await user.click(quickModeCard);
    expect(screen.getByText('5 Soru')).toBeDefined();
    expect(screen.getByText('10 Dakika')).toBeDefined();

    // Start Quick mode
    await user.click(screen.getByRole('button', { name: /Sınavı Başlat/i }));

    await waitFor(() => {
      expect(screen.getByText(/Soru 1 \/ 5/i)).toBeDefined();
    });

    // Answer Q1 with option A
    const optionA = screen.getByText('A').closest('.exam-option-item')!;
    await user.click(optionA);

    // Finish Quick exam
    await user.click(screen.getByRole('button', { name: 'Sınavı Bitir' }));
    await user.click(screen.getByRole('button', { name: 'Evet, Sınavı Bitir' }));

    await waitFor(() => {
      expect(screen.getByText(/YÖKDİL Fen Bilimleri Simülasyon Puanı/i)).toBeDefined();
    });
  });

  it('calculates score according to YÖKDİL formula (1.25 per question)', () => {
    // 80 questions:
    expect(calculateYokdilScore(0, 80)).toBe(0);
    expect(calculateYokdilScore(1, 80)).toBe(1.25);
    expect(calculateYokdilScore(64, 80)).toBe(80);
    expect(calculateYokdilScore(80, 80)).toBe(100);

    // Short mode 5 questions:
    expect(calculateYokdilScore(5, 5)).toBe(100);
    expect(calculateYokdilScore(4, 5)).toBe(80);
  });

  it('renders Performance Dashboard with 12 content skills and Wilson interval', async () => {
    const user = userEvent.setup();
    render(<ExamApp />);

    await user.click(screen.getByRole('button', { name: 'Performans' }));

    expect(screen.getByText('Performans ve Beceri Analizi')).toBeDefined();
    expect(screen.getByText('Wilson %95 Güven Aralığı')).toBeDefined();
    expect(screen.getByText('Ölçüm Hazır Olma Durumu')).toBeDefined();

    for (const skill of PERFORMANCE_CONTENT_SKILLS) {
      expect(screen.getByText(skill)).toBeDefined();
    }
  });

  it('renders Vocabulary Study Screen with search and tier filtering', async () => {
    const user = userEvent.setup();
    render(<ExamApp />);

    await user.click(screen.getByRole('button', { name: 'Kelimeler' }));

    expect(screen.getByText('YÖKDİL Fen Bilimleri Kelime Çalışması')).toBeDefined();

    // Search for 'inhibit'
    const searchInput = screen.getByPlaceholderText('Kelime veya Türkçe anlam ara...');
    await user.type(searchInput, 'inhibit');

    expect(screen.getByText('inhibit')).toBeDefined();
    expect(screen.getByText(/engellemek/i)).toBeDefined();
  });
});
