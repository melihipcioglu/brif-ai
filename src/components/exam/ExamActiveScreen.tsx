import { useState, useEffect, useRef, useId } from 'react';
import type { OptionId, QuestionFamily } from '../../types/question';
import { OPTION_IDS } from '../../types/question';
import type { ActiveExamSession } from '../../types/examSession';
import { QuestionPalette } from './QuestionPalette';

const familyTurkishLabels: Record<QuestionFamily, string> = {
  GAP_FILL: 'Boşluk Doldurma',
  CLOZE_TEST: 'Paragrafta Boşluk Doldurma',
  SENTENCE_COMPLETION: 'Cümle Tamamlama',
  TRANSLATION_ENG_TR: 'İngilizceden Türkçeye Çeviri',
  TRANSLATION_TR_ENG: 'Türkçeden İngilizceye Çeviri',
  PARAGRAPH_COMPLETION: 'Paragraf Tamamlama',
  IRRELEVANT_SENTENCE: 'Anlam Bütünlüğünü Bozan Cümle',
  READING_COMPREHENSION: 'Okuduğunu Anlama'
};

export interface ExamActiveScreenProps {
  readonly session: ActiveExamSession;
  readonly onAnswer: (questionId: string, option: OptionId | null) => void;
  readonly onToggleFlag: (questionId: string) => void;
  readonly onToggleEliminate: (questionId: string, option: OptionId) => void;
  readonly onNavigate: (index: number) => void;
  readonly onFinish: () => void;
}

export function ExamActiveScreen({
  session,
  onAnswer,
  onToggleFlag,
  onToggleEliminate,
  onNavigate,
  onFinish
}: ExamActiveScreenProps) {
  const [showPalette, setShowPalette] = useState(true);
  const [showConfirmFinish, setShowConfirmFinish] = useState(false);
  const [remainingMs, setRemainingMs] = useState(() => {
    const elapsed = Date.now() - session.startedAt;
    return Math.max(0, session.timeLimitMs - elapsed);
  });

  const headingId = useId();
  const form = session.form;
  const questions = form.questions;
  const currentQ = questions[session.currentIndex]!;
  const selectedOption = session.answers[currentQ.id] ?? null;
  const eliminated = session.eliminatedOptions[currentQ.id] ?? [];
  const isFlagged = session.flaggedQuestionIds.includes(currentQ.id);

  // Countdown timer
  const onFinishRef = useRef(onFinish);
  onFinishRef.current = onFinish;

  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Date.now() - session.startedAt;
      const left = Math.max(0, session.timeLimitMs - elapsed);
      setRemainingMs(left);
      if (left <= 0) {
        clearInterval(timer);
        onFinishRef.current();
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [session.startedAt, session.timeLimitMs]);

  // Accidental exit protection
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = 'Devam eden bir sınavınız var. Sayfadan ayrılmak istediğinize emin misiniz?';
      return e.returnValue;
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (showConfirmFinish) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      const key = e.key.toUpperCase();
      if (OPTION_IDS.includes(key as OptionId)) {
        e.preventDefault();
        onAnswer(currentQ.id, key as OptionId);
      } else if (['1', '2', '3', '4', '5'].includes(e.key)) {
        e.preventDefault();
        const map: Record<string, OptionId> = { '1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E' };
        onAnswer(currentQ.id, map[e.key]!);
      } else if (e.key === 'ArrowRight' && session.currentIndex < questions.length - 1) {
        e.preventDefault();
        onNavigate(session.currentIndex + 1);
      } else if (e.key === 'ArrowLeft' && session.currentIndex > 0) {
        e.preventDefault();
        onNavigate(session.currentIndex - 1);
      } else if (key === 'F') {
        e.preventDefault();
        onToggleFlag(currentQ.id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentQ.id, session.currentIndex, questions.length, onAnswer, onNavigate, onToggleFlag, showConfirmFinish]);

  // Format timer
  const totalSeconds = Math.floor(remainingMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const formattedTime = hours > 0
    ? `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
    : `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  const isUrgent = remainingMs < 15 * 60 * 1000; // less than 15 mins

  // Stats for confirmation
  const answeredCount = Object.values(session.answers).filter((a) => a !== null).length;
  const blankCount = questions.length - answeredCount;

  return (
    <div className="exam-app-container">
      {/* Top Runner Header */}
      <header className="exam-runner-header">
        <div className="exam-runner-meta">
          <span style={{ fontWeight: 700, fontSize: '1rem' }}>
            Soru {session.currentIndex + 1} / {questions.length}
          </span>
          <span className="exam-family-pill">
            {familyTurkishLabels[currentQ.family] ?? currentQ.family}
          </span>
        </div>

        <div className="exam-runner-center">
          <div
            className={`exam-countdown-timer ${isUrgent ? 'is-urgent' : ''}`}
            aria-label={`Kalan süre: ${formattedTime}`}
          >
            ⏱ Kalan Süre: {formattedTime}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            type="button"
            className={`exam-btn exam-btn-sm ${isFlagged ? 'exam-btn-primary' : 'exam-btn-secondary'}`}
            onClick={() => onToggleFlag(currentQ.id)}
            aria-pressed={isFlagged}
          >
            🚩 {isFlagged ? 'İşaretlendi' : 'İşaretle'}
          </button>
          <button
            type="button"
            className="exam-btn exam-btn-sm exam-btn-danger"
            onClick={() => setShowConfirmFinish(true)}
          >
            Sınavı Bitir
          </button>
        </div>
      </header>

      {/* Main Question Layout */}
      <main className="exam-main-content">
        <div className={`exam-question-layout ${currentQ.passage ? 'has-passage' : ''}`}>
          {/* Passage Section */}
          {currentQ.passage && (
            <section className="exam-passage-box" aria-label="Okuma veya paragraf metni">
              <h2 className="exam-passage-title">Parça / Metin</h2>
              <div style={{ whiteSpace: 'pre-wrap' }}>{currentQ.passage}</div>
            </section>
          )}

          {/* Stem & Options Section */}
          <section className="exam-stem-box" aria-labelledby={headingId}>
            <h1 id={headingId} className="exam-stem-text">
              {session.currentIndex + 1}. {currentQ.stem}
            </h1>

            <fieldset className="exam-options-list" style={{ border: 'none', padding: 0, margin: 0 }}>
              <legend className="exam-sr-only">Cevap Seçenekleri</legend>
              {currentQ.options.map((opt) => {
                const isSelected = selectedOption === opt.id;
                const isEliminated = eliminated.includes(opt.id);

                return (
                  <div
                    key={opt.id}
                    className={`exam-option-item ${isSelected ? 'is-selected' : ''}`}
                    onClick={() => onAnswer(currentQ.id, opt.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onAnswer(currentQ.id, opt.id);
                      }
                    }}
                    aria-pressed={isSelected}
                  >
                    <div className="exam-option-main">
                      <span className="exam-option-letter">{opt.id}</span>
                      <span className={`exam-option-text ${isEliminated ? 'is-eliminated' : ''}`}>
                        {opt.text}
                      </span>
                    </div>

                    <div className="exam-option-actions" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="exam-eliminate-btn"
                        onClick={() => onToggleEliminate(currentQ.id, opt.id)}
                        title={isEliminated ? 'Elemeyi kaldır' : 'Şıkkı ele'}
                        aria-label={`${opt.id} şıkkını ele`}
                      >
                        {isEliminated ? 'Geri Al' : 'Ele'}
                      </button>
                    </div>
                  </div>
                );
              })}
            </fieldset>

            {/* Clear Choice Button */}
            {selectedOption !== null && (
              <div style={{ marginTop: '16px', textAlign: 'right' }}>
                <button
                  type="button"
                  className="exam-btn exam-btn-sm exam-btn-secondary"
                  onClick={() => onAnswer(currentQ.id, null)}
                >
                  Cevabı Temizle
                </button>
              </div>
            )}
          </section>
        </div>

        {/* Question Palette */}
        {showPalette && (
          <QuestionPalette
            totalQuestions={questions.length}
            currentIndex={session.currentIndex}
            answers={session.answers}
            questionIds={form.question_ids}
            flaggedQuestionIds={session.flaggedQuestionIds}
            onSelectQuestion={(idx) => onNavigate(idx)}
          />
        )}
      </main>

      {/* Runner Footer Navigation */}
      <footer className="exam-runner-footer">
        <button
          type="button"
          className="exam-btn exam-btn-secondary"
          onClick={() => onNavigate(session.currentIndex - 1)}
          disabled={session.currentIndex === 0}
        >
          ← Önceki
        </button>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="exam-btn exam-btn-secondary exam-btn-sm"
            onClick={() => setShowPalette(!showPalette)}
          >
            {showPalette ? 'Paleti Gizle' : 'Paleti Göster'}
          </button>
        </div>

        {session.currentIndex < questions.length - 1 ? (
          <button
            type="button"
            className="exam-btn exam-btn-primary"
            onClick={() => onNavigate(session.currentIndex + 1)}
          >
            Sonraki →
          </button>
        ) : (
          <button
            type="button"
            className="exam-btn exam-btn-danger"
            onClick={() => setShowConfirmFinish(true)}
          >
            Sınavı Bitir
          </button>
        )}
      </footer>

      {/* Finish Confirmation Modal */}
      {showConfirmFinish && (
        <div className="exam-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="exam-modal-card">
            <h2 id="modal-title" style={{ marginTop: 0, fontSize: '1.25rem', fontWeight: 700 }}>
              Sınavı Bitirmek İstiyor Musunuz?
            </h2>
            <p style={{ color: 'var(--yokdil-text-muted)', lineHeight: 1.6 }}>
              Toplam <strong>{questions.length}</strong> sorudan{' '}
              <strong style={{ color: 'var(--yokdil-success)' }}>{answeredCount}</strong> tanesini cevapladınız.
              {blankCount > 0 ? (
                <>
                  {' '}Hâlâ <strong style={{ color: 'var(--yokdil-danger)' }}>{blankCount}</strong> boş sorunuz bulunmaktadır.
                </>
              ) : (
                ' Tüm soruları yanıtladınız.'
              )}
            </p>
            <p style={{ fontSize: '0.875rem', color: 'var(--yokdil-text-muted)' }}>
              Sınavı teslim ettikten sonra cevaplarınız kilitlenecek ve detaylı analiz raporunuz oluşturulacaktır.
            </p>
            <div className="exam-modal-actions">
              <button
                type="button"
                className="exam-btn exam-btn-secondary"
                onClick={() => setShowConfirmFinish(false)}
              >
                Sınava Devam Et
              </button>
              <button
                type="button"
                className="exam-btn exam-btn-danger"
                onClick={() => {
                  setShowConfirmFinish(false);
                  onFinish();
                }}
              >
                Evet, Sınavı Bitir
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
