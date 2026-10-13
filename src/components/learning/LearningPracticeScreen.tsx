import { useState } from 'react';
import type { LearningPracticeQuestion, LearnerProfile } from '../../types/learning';
import { learningQuestionsBank } from '../../data/learning/learningQuestionsBank';
import { recordPracticeQuestionCompletion } from '../../services/learning/learningProfileService';

export interface LearningPracticeScreenProps {
  readonly profile: LearnerProfile;
  readonly questionIds: readonly string[];
  readonly onFinish: (updatedProfile: LearnerProfile) => void;
  readonly onCancel: () => void;
}

export function LearningPracticeScreen({
  profile,
  questionIds,
  onFinish,
  onCancel
}: LearningPracticeScreenProps) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState<'A' | 'B' | 'C' | 'D' | 'E' | null>(null);
  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [currentProfile, setCurrentProfile] = useState<LearnerProfile>(profile);

  const questions = questionIds
    .map((id) => learningQuestionsBank.find((q) => q.id === id))
    .filter((q): q is LearningPracticeQuestion => q !== undefined);

  if (questions.length === 0) {
    return (
      <div className="learn-container">
        <div className="vocab-card-box" style={{ textAlign: 'center' }}>
          <h2>Soru Bulunamadı</h2>
          <button type="button" className="learn-btn learn-btn-primary" onClick={onCancel}>
            ← Geri Dön
          </button>
        </div>
      </div>
    );
  }

  const q = questions[currentIdx]!;
  const isCorrect = selectedOption === q.correct_option;

  const handleSelect = (optId: 'A' | 'B' | 'C' | 'D' | 'E') => {
    if (hasSubmitted && isCorrect) return; // locked if already correct
    setSelectedOption(optId);
  };

  const handleSubmit = () => {
    if (!selectedOption) return;
    setHasSubmitted(true);

    if (selectedOption === q.correct_option) {
      const updated = recordPracticeQuestionCompletion(currentProfile);
      setCurrentProfile(updated);
    }
  };

  const handleRetry = () => {
    setSelectedOption(null);
    setHasSubmitted(false);
  };

  const handleNext = () => {
    setSelectedOption(null);
    setHasSubmitted(false);

    if (currentIdx < questions.length - 1) {
      setCurrentIdx(currentIdx + 1);
    } else {
      onFinish(currentProfile);
    }
  };

  return (
    <div className="learn-container">
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <span className="learn-pill learn-pill-teal">
            ÖĞRENME ALIŞTIRMASI • {currentIdx + 1} / {questions.length}
          </span>
          <span className="learn-pill learn-pill-blue" style={{ marginLeft: 8 }}>
            {q.family}
          </span>
          <span className="learn-pill learn-pill-amber" style={{ marginLeft: 8 }}>
            Hedef: {q.target_word_ids.join(', ')}
          </span>
        </div>
        <button type="button" className="learn-btn learn-btn-secondary" onClick={onCancel}>
          Oturumdan Çık
        </button>
      </div>

      <div className="vocab-card-box">
        {/* Banner informing learner that this is learning practice */}
        <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.85rem', color: '#166534' }}>
          🛡️ <strong>Öğretim Havuzu:</strong> Bu sorular öğrendiğiniz kelimeleri pekiştirmek için tasarlanmıştır. Bağımsız deneme sınav havuzunu tüketmez.
        </div>

        {/* Reading passage if relevant */}
        {q.passage && (
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              borderRadius: 10,
              padding: '16px 20px',
              fontSize: '1.05rem',
              lineHeight: 1.7,
              marginBottom: 16,
              color: '#1e293b'
            }}
          >
            {q.passage}
          </div>
        )}

        {/* Stem */}
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, lineHeight: 1.5, margin: '0 0 20px 0' }}>
          {q.stem}
        </h2>

        {/* Options */}
        <div style={{ display: 'grid', gap: 10, marginBottom: 24 }}>
          {q.options.map((opt) => {
            const isSelected = selectedOption === opt.id;
            let bg = '#ffffff';
            let borderColor = 'var(--learn-border)';

            if (hasSubmitted) {
              if (opt.id === q.correct_option) {
                bg = '#f0fdf4';
                borderColor = 'var(--learn-success)';
              } else if (isSelected) {
                bg = '#fef2f2';
                borderColor = 'var(--learn-danger)';
              }
            } else if (isSelected) {
              bg = 'var(--learn-primary-light)';
              borderColor = 'var(--learn-primary)';
            }

            return (
              <button
                key={opt.id}
                type="button"
                style={{
                  background: bg,
                  border: `2px solid ${borderColor}`,
                  borderRadius: 10,
                  padding: '14px 18px',
                  textAlign: 'left',
                  fontSize: '1rem',
                  cursor: hasSubmitted && isCorrect ? 'default' : 'pointer',
                  fontWeight: isSelected ? 700 : 500,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12
                }}
                onClick={() => handleSelect(opt.id)}
              >
                <span
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    background: isSelected ? 'var(--learn-primary)' : '#e2e8f0',
                    color: isSelected ? '#ffffff' : '#334155',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 700,
                    fontSize: '0.9rem',
                    flexShrink: 0
                  }}
                >
                  {opt.id}
                </span>
                <span style={{ flex: 1 }}>{opt.text}</span>
                {hasSubmitted && opt.id === q.correct_option && (
                  <span style={{ color: 'var(--learn-success)', fontWeight: 700 }}>✓ Doğru Cevap</span>
                )}
                {hasSubmitted && isSelected && !isCorrect && (
                  <span style={{ color: 'var(--learn-danger)', fontWeight: 700 }}>✗ Yanıtınız</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Feedback & Pedagogical Explanations */}
        {hasSubmitted && (
          <div style={{ marginBottom: 24 }}>
            <div
              style={{
                background: isCorrect ? '#f0fdf4' : '#fef2f2',
                border: `1.5px solid ${isCorrect ? '#bbf7d0' : '#fecaca'}`,
                padding: '16px 20px',
                borderRadius: 10,
                marginBottom: 16
              }}
            >
              <h3 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', color: isCorrect ? '#166534' : '#991b1b' }}>
                {isCorrect ? 'Tebrikler! Doğru Seçenek.' : 'Yanlış Cevap — Analizi İnceleyin:'}
              </h3>
              <p style={{ margin: '0 0 8px 0', fontSize: '0.92rem', color: '#334155', lineHeight: 1.5 }}>
                {q.pedagogical_explanation.triage_tr}
              </p>
              <div style={{ background: '#ffffff', padding: '10px 14px', borderRadius: 8, border: '1px solid #e2e8f0', fontSize: '0.875rem' }}>
                <strong>Kelime Analizi:</strong> {q.pedagogical_explanation.target_word_insight_tr}
              </div>
            </div>

            {/* Distractor Breakdown */}
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '14px 18px' }}>
              <strong style={{ fontSize: '0.9rem', color: 'var(--learn-text-muted)' }}>
                ÇELDİRİCİ ANALİZLERİ (Neden Yanlış?):
              </strong>
              <div style={{ marginTop: 8, display: 'grid', gap: 6, fontSize: '0.85rem' }}>
                {Object.entries(q.pedagogical_explanation.distractor_breakdowns).map(([optKey, reason]) => (
                  <div key={optKey}>
                    <strong>{optKey}:</strong> <span style={{ color: '#475569' }}>{reason}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          {!hasSubmitted ? (
            <button
              type="button"
              className="learn-btn learn-btn-primary"
              disabled={!selectedOption}
              onClick={handleSubmit}
            >
              Cevabı Kontrol Et →
            </button>
          ) : !isCorrect ? (
            <button
              type="button"
              className="learn-btn learn-btn-outline"
              onClick={handleRetry}
            >
              ↻ Tekrar Dene
            </button>
          ) : (
            <button
              type="button"
              className="learn-btn learn-btn-primary"
              onClick={handleNext}
            >
              {currentIdx < questions.length - 1 ? 'Sonraki Soruya Geç →' : 'Alıştırmayı Tamamla ✓'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
