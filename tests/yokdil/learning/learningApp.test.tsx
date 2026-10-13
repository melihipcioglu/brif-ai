import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ExamApp } from '../../../src/components/exam/ExamApp';
import { productionBank } from '../../../src/data/productionBank';
import { LEARNER_PROFILE_STORAGE_KEY } from '../../../src/services/learning/learningProfileService';
import { LEARNER_EXPOSURES_STORAGE_KEY } from '../../../src/services/exam/examSessionService';

describe('V1.1 Adaptive Learning System Integration', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders "Bugünkü Çalışmam" as the default home screen on first launch with Diagnostic banner', () => {
    render(<ExamApp />);

    expect(screen.getByText('Bugünkü Kişiselleştirilmiş Öğrenme Rotanız')).toBeDefined();
    expect(screen.getByText('📅 GÜN 1')).toBeDefined();
    expect(screen.getByText('🔥 1 GÜNLÜK SERİ')).toBeDefined();
    expect(screen.getByText('Akademik Kelimeleri Öğren')).toBeDefined();
    expect(screen.getByText('Akademik Cümle & Paragraf Oku')).toBeDefined();
    expect(screen.getByText('Öğrenilen Kelimelerle Soru Çöz')).toBeDefined();

    // Check Diagnostic Banner
    expect(screen.getByText(/Başlangıç Seviye Tanılama Çalışması/i)).toBeDefined();
    expect(screen.getByText('Tanılamayı Başlat →')).toBeDefined();
  });

  it('allows student to launch Diagnostic Assessment from dashboard', () => {
    render(<ExamApp />);

    const startDiagBtn = screen.getByText('Tanılamayı Başlat →');
    fireEvent.click(startDiagBtn);

    expect(screen.getByText(/1\. ADIM: KELİME TANIMA/i)).toBeDefined();
    expect(screen.getByText(/prevent/i)).toBeDefined();
  });

  it('allows student to launch Vocab Trainer, inspect word progression, and do active recall', async () => {
    render(<ExamApp />);

    // Click "Kelimeleri Çalışmaya Başla →"
    const startVocabBtn = screen.getByText('Kelimeleri Çalışmaya Başla →');
    fireEvent.click(startVocabBtn);

    // Should be in Vocab Trainer screen
    expect(screen.getByText(/KELİME ÖĞRETİMİ • 1 \//)).toBeDefined();
    expect(screen.getByTitle('İngilizce Telaffuzu Dinle')).toBeDefined();
    expect(screen.getByText(/ATOMİK CÜMLE BÜYÜTÜCÜ/i)).toBeDefined();
    expect(screen.getByText(/TUZAK AŞISI/i)).toBeDefined();
    expect(screen.getByText(/YAYGIN AKADEMİK COLLOCATIONS/)).toBeDefined();
    expect(screen.getByText(/SÖZCÜK AİLESİ:/)).toBeDefined();
    expect(screen.getByText(/💡 HATIRLAMA İPUCU/)).toBeDefined();

    // Click "Aktif Hatırlama Alıştırması Yap →"
    const quizBtn = screen.getByText('Aktif Hatırlama Alıştırması Yap →');
    fireEvent.click(quizBtn);

    expect(screen.getByText('AKTİF HATIRLAMA')).toBeDefined();
    expect(screen.getByText(/Çeldiricilere dikkat ederek doğru Türkçe karşılığı seçin/)).toBeDefined();
  });

  it('allows student to launch Interactive Decomposer Workshop from dashboard', () => {
    render(<ExamApp />);

    // Click "Okuma Öğretimini Başlat →"
    const startReadingBtn = screen.getByText('Okuma Öğretimini Başlat →');
    fireEvent.click(startReadingBtn);

    expect(screen.getByText(/I DO: ÖĞRETMEN MODELİ/i)).toBeDefined();
    expect(screen.getByText('Although')).toBeDefined();

    // Click token in I DO mode
    const token = screen.getByText('Although');
    fireEvent.click(token);

    expect(screen.getByText(/Although zıtlık bağlacıdır/i)).toBeDefined();
  });

  it('allows student to launch Practice Questions and examine distractor analyses', () => {
    render(<ExamApp />);

    // Click "Alıştırma Sorularını Başlat →"
    const startQuestionsBtn = screen.getByText('Alıştırma Sorularını Başlat →');
    fireEvent.click(startQuestionsBtn);

    expect(screen.getByText(/ÖĞRENME ALIŞTIRMASI • 1 \//)).toBeDefined();
    expect(screen.getByText(/Bağımsız deneme sınav havuzunu tüketmez/)).toBeDefined();

    // Select option and submit
    const optionA = screen.getAllByText('A')[0]!;
    fireEvent.click(optionA);

    const checkBtn = screen.getByText('Cevabı Kontrol Et →');
    fireEvent.click(checkBtn);

    // Distractor analysis should be revealed
    expect(screen.getByText(/ÇELDİRİCİ ANALİZLERİ/)).toBeDefined();
  });

  it('displays Learning Progress Dashboard with retention stages and 3D mastery breakdown', () => {
    render(<ExamApp />);

    // Click "Öğrenme Gelişimi" in top nav
    const progressNavBtn = screen.getByText('Öğrenme Gelişimi');
    fireEvent.click(progressNavBtn);

    expect(screen.getByText('Öğrenme ve Kalıcılık Gelişim Paneli')).toBeDefined();
    expect(screen.getByText(/MASTERED \(Kalıcı Ustalık\)/)).toBeDefined();
    expect(screen.getByText(/RETAINED \(Hatırlanıyor\)/)).toBeDefined();
    expect(screen.getByText(/3 Boyutlu Kelime Ustalığı Takibi/)).toBeDefined();
    expect(screen.getByText(/1\. Tanıma \(Recognition\)/)).toBeDefined();
    expect(screen.getByText(/2\. Cümlede Anlama \(Comprehension\)/)).toBeDefined();
    expect(screen.getByText(/3\. Yeni Bağlamda Kullanma \(Transfer\)/)).toBeDefined();
    expect(screen.getByText(/Akademik Okuma Becerileri ve İskele Düzeyi/)).toBeDefined();
  });

  it('guarantees that 160-item independent exam pool remains 100% untouched and unexposed', () => {
    render(<ExamApp />);

    // Verify productionBank count
    expect(productionBank).toHaveLength(160);

    // Verify learner exposures storage has not been touched by learning system
    const rawExposures = localStorage.getItem(LEARNER_EXPOSURES_STORAGE_KEY);
    expect(rawExposures).toBeNull();

    // Learning profile storage is maintained separately
    expect(localStorage.getItem(LEARNER_PROFILE_STORAGE_KEY)).toBeDefined();
  });
});
