import { useState } from 'react';
import type { AcademicVocabEntry, LearnerProfile } from '../../types/learning';
import { academicVocabBank, playPronunciation, getWordProgression, getTrapWords } from '../../data/learning/academicVocabBank';
import { recordWordPracticeResult } from '../../services/learning/learningProfileService';

export interface VocabTrainerScreenProps {
  readonly profile: LearnerProfile;
  readonly targetWordIds: readonly string[];
  readonly onFinish: (updatedProfile: LearnerProfile) => void;
  readonly onCancel: () => void;
}

export function VocabTrainerScreen({
  profile,
  targetWordIds,
  onFinish,
  onCancel
}: VocabTrainerScreenProps) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [progressionIdx, setProgressionIdx] = useState(0);
  const [mode, setMode] = useState<'CARD' | 'QUIZ'>('CARD');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ isCorrect: boolean; explanation: string } | null>(null);
  const [currentProfile, setCurrentProfile] = useState<LearnerProfile>(profile);

  const words = targetWordIds
    .map((id) => academicVocabBank.find((w) => w.word_id === id))
    .filter((w): w is AcademicVocabEntry => w !== undefined);

  if (words.length === 0) {
    return (
      <div className="learn-container">
        <div className="vocab-card-box" style={{ textAlign: 'center' }}>
          <h2>Çalışılacak Kelime Bulunamadı</h2>
          <p>Tüm kelimeler başarıyla tamamlandı veya liste boş.</p>
          <button type="button" className="learn-btn learn-btn-primary" onClick={onCancel}>
            ← Ana Ekrana Dön
          </button>
        </div>
      </div>
    );
  }

  const currentWord = words[currentIdx]!;
  const wordRecord = currentProfile.wordRecords[currentWord.word_id];

  // Distractors for active recall test
  const quizOptions = [
    { text: currentWord.meaning_tr, isCorrect: true, explanation: 'Doğru anlam.' },
    ...currentWord.distractors.map((d) => ({
      text: d.meaning_tr,
      isCorrect: false,
      explanation: d.explanation_tr
    }))
  ].slice(0, 4);

  // Pseudo-randomize consistently based on word_id length
  const randomizedOptions = [...quizOptions].sort((a, b) => a.text.localeCompare(b.text));

  const handleSpeak = () => {
    playPronunciation(currentWord.lemma);
  };

  const handleSelectQuizOption = (opt: { text: string; isCorrect: boolean; explanation: string }) => {
    if (selectedOption !== null) return;
    setSelectedOption(opt.text);
    setFeedback({
      isCorrect: opt.isCorrect,
      explanation: opt.explanation
    });

    const updated = recordWordPracticeResult(
      currentProfile,
      currentWord.word_id,
      'PREDICTION',
      opt.isCorrect
    );
    setCurrentProfile(updated);
  };

  const handleNext = () => {
    setSelectedOption(null);
    setFeedback(null);
    setMode('CARD');

    if (currentIdx < words.length - 1) {
      setCurrentIdx(currentIdx + 1);
    } else {
      onFinish(currentProfile);
    }
  };

  return (
    <div className="learn-container">
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <span className="learn-pill learn-pill-teal">
            KELİME ÖĞRETİMİ • {currentIdx + 1} / {words.length}
          </span>
          <span style={{ marginLeft: 12, fontSize: '0.875rem', color: 'var(--learn-text-muted)' }}>
            Durum: <strong>{wordRecord?.state ?? 'NOT_STARTED'}</strong>
          </span>
        </div>
        <button type="button" className="learn-btn learn-btn-secondary" onClick={onCancel}>
          Oturumdan Çık
        </button>
      </div>

      {mode === 'CARD' ? (
        /* CARD MODE: Teach step with full rich linguistic properties */
        <div className="vocab-card-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <h1 style={{ fontSize: '2.25rem', fontWeight: 800, margin: 0, color: 'var(--learn-primary)' }}>
                  {currentWord.lemma}
                </h1>
                <button
                  type="button"
                  className="vocab-audio-btn"
                  onClick={handleSpeak}
                  title="İngilizce Telaffuzu Dinle"
                  aria-label="Telaffuz dinle"
                >
                  🔊
                </button>
                <span className="learn-pill learn-pill-blue">
                  {currentWord.pos.toUpperCase()}
                </span>
                {currentWord.polarity_symbol && (
                  <span className="learn-pill learn-pill-amber" title="Anlamsal Yön">
                    {currentWord.polarity_symbol} Yön
                  </span>
                )}
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#334155', marginTop: 8 }}>
                {currentWord.meaning_tr}
              </h3>
            </div>
            <div style={{ textAlign: 'right' }}>
              <span className="learn-pill learn-pill-teal">Tier {currentWord.tier}</span>
              <div style={{ fontSize: '0.75rem', color: 'var(--learn-text-muted)', marginTop: 4 }}>
                Öncelik: {currentWord.priority_score}/100
              </div>
            </div>
          </div>

          {/* Atomik Cümle Büyütücü (Micro-Stepping Progression) */}
          {(() => {
            const progressionSteps = getWordProgression(currentWord);
            const currentProgStep = progressionSteps[progressionIdx] || progressionSteps[0];
            const trapWords = getTrapWords(currentWord);
            if (!currentProgStep) return null;

            return (
              <>
                <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
                    <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#0369a1', fontWeight: 700 }}>
                      🔬 ATOMİK CÜMLE BÜYÜTÜCÜ (Basitten Sınav Seviyesine):
                    </h4>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {progressionSteps.map((_step, idx) => (
                        <button
                          key={idx}
                          type="button"
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            borderRadius: 20,
                            border: 'none',
                            cursor: 'pointer',
                            background: progressionIdx === idx ? '#0284c7' : '#e0f2fe',
                            color: progressionIdx === idx ? '#ffffff' : '#0369a1'
                          }}
                          onClick={() => setProgressionIdx(idx)}
                        >
                          Basamak {idx}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div style={{ background: '#ffffff', padding: '14px 16px', borderRadius: 8, border: '1px solid #e0f2fe' }}>
                    <div style={{ fontSize: '0.8rem', color: '#0284c7', fontWeight: 700, textTransform: 'uppercase' }}>
                      {currentProgStep.title}
                    </div>
                    <div style={{ fontSize: '1.15rem', fontWeight: 600, color: '#0f172a', margin: '8px 0', fontFamily: 'serif' }}>
                      "{currentProgStep.englishText}"
                    </div>
                    <div style={{ fontSize: '0.95rem', color: '#475569', marginBottom: 10 }}>
                      {currentProgStep.turkishTranslation}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#0f766e', background: '#f0fdfa', padding: '6px 12px', borderRadius: 6 }}>
                      🎯 <strong>Öğretmen İpucu:</strong> {currentProgStep.focusPoint}
                    </div>
                  </div>
                </div>

                {/* Tuzak Aşısı (Error Inoculation) */}
                {trapWords.length > 0 && (
                  <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: '14px 18px', marginBottom: 20 }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: '#991b1b', display: 'flex', alignItems: 'center', gap: 6 }}>
                      ⚠️ TUZAK AŞISI (Sınavda En Çok Düşülen Benzer Kelimeler):
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
                      {trapWords.map((tw, idx) => (
                        <div key={idx} style={{ background: '#ffffff', padding: '10px 14px', borderRadius: 8, border: '1px solid #fee2e2' }}>
                          <div style={{ fontWeight: 700, color: '#dc2626', fontSize: '0.95rem' }}>
                            ❌ {tw.trapWord} = {tw.trapMeaning}
                          </div>
                          <div style={{ fontSize: '0.825rem', color: '#4b5563', marginTop: 4 }}>
                            {tw.confusionReason}
                          </div>
                          <div style={{ fontSize: '0.825rem', color: '#16a34a', fontWeight: 600, marginTop: 4 }}>
                            💡 {tw.memoryHook}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            );
          })()}

          {/* Collocations */}
          <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: 10, marginBottom: 16 }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', color: 'var(--learn-text-muted)' }}>
              YAYGIN AKADEMİK COLLOCATIONS (Eş Dizimler):
            </h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {currentWord.critical_collocations.map((c, idx) => (
                <div key={idx} style={{ background: '#ffffff', border: '1px solid #cbd5e1', padding: '4px 10px', borderRadius: 6, fontSize: '0.875rem' }}>
                  <strong>{c.phrase}</strong>: <span style={{ color: '#475569' }}>{c.meaning_tr}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Example Science Sentence */}
          <div style={{ borderLeft: '4px solid var(--learn-primary)', paddingLeft: 16, marginBottom: 20 }}>
            <p style={{ fontSize: '1.05rem', fontStyle: 'italic', margin: '0 0 6px 0', color: '#1e293b' }}>
              "{currentWord.exam_sentence}"
            </p>
            <p style={{ fontSize: '0.92rem', color: '#64748b', margin: 0 }}>
              {currentWord.exam_sentence_tr}
            </p>
          </div>

          {/* Word Family & Mnemonics */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginBottom: 24 }}>
            <div style={{ background: '#f0fdf4', padding: '12px 16px', borderRadius: 8, border: '1px solid #bbf7d0' }}>
              <strong style={{ fontSize: '0.85rem', color: '#166534' }}>SÖZCÜK AİLESİ:</strong>
              <div style={{ marginTop: 6, fontSize: '0.875rem' }}>
                {currentWord.word_family.map((f, i) => (
                  <div key={i} style={{ margin: '2px 0' }}>
                    <span style={{ color: '#15803d', fontWeight: 600 }}>{f.form}</span> ({f.pos}): {f.meaning_tr}
                  </div>
                ))}
              </div>
            </div>

            <div style={{ background: '#fffbeb', padding: '12px 16px', borderRadius: 8, border: '1px solid #fde68a' }}>
              <strong style={{ fontSize: '0.85rem', color: '#92400e' }}>💡 HATIRLAMA İPUCU (Mnemonic):</strong>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.875rem', color: '#78350f', lineHeight: 1.5 }}>
                {currentWord.mnemonic_hint}
              </p>
            </div>
          </div>

          {/* Action button to switch to active recall test */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <button
              type="button"
              className="learn-btn learn-btn-primary"
              onClick={() => setMode('QUIZ')}
            >
              Aktif Hatırlama Alıştırması Yap →
            </button>
          </div>
        </div>
      ) : (
        /* QUIZ MODE: Active recall verification */
        <div className="vocab-card-box">
          <div style={{ marginBottom: 20 }}>
            <span className="learn-pill learn-pill-amber">AKTİF HATIRLAMA</span>
            <h2 style={{ fontSize: '1.5rem', fontWeight: 800, margin: '12px 0 6px 0' }}>
              "{currentWord.lemma}" kelimesinin akademik fen bağlamındaki doğru anlamı nedir?
            </h2>
            <p style={{ color: 'var(--learn-text-muted)', margin: 0, fontSize: '0.9rem' }}>
              Çeldiricilere dikkat ederek doğru Türkçe karşılığı seçin:
            </p>
          </div>

          <div style={{ display: 'grid', gap: 10, marginBottom: 20 }}>
            {randomizedOptions.map((opt, i) => {
              const isSelected = selectedOption === opt.text;
              let bg = '#ffffff';
              let borderColor = 'var(--learn-border)';

              if (selectedOption !== null) {
                if (opt.isCorrect) {
                  bg = '#f0fdf4';
                  borderColor = 'var(--learn-success)';
                } else if (isSelected) {
                  bg = '#fef2f2';
                  borderColor = 'var(--learn-danger)';
                }
              }

              return (
                <button
                  key={i}
                  type="button"
                  style={{
                    background: bg,
                    border: `2px solid ${borderColor}`,
                    padding: '14px 18px',
                    borderRadius: 10,
                    textAlign: 'left',
                    fontSize: '1rem',
                    cursor: selectedOption === null ? 'pointer' : 'default',
                    fontWeight: isSelected ? 700 : 500,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                  onClick={() => handleSelectQuizOption(opt)}
                >
                  <span>{opt.text}</span>
                  {selectedOption !== null && (
                    <span>{opt.isCorrect ? '✓ Doğru' : isSelected ? '✗ Yanlış' : ''}</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Feedback banner */}
          {feedback && (
            <div
              style={{
                background: feedback.isCorrect ? '#f0fdf4' : '#fef2f2',
                border: `1px solid ${feedback.isCorrect ? '#bbf7d0' : '#fecaca'}`,
                padding: '14px 18px',
                borderRadius: 10,
                marginBottom: 20
              }}
            >
              <strong style={{ color: feedback.isCorrect ? '#166534' : '#991b1b' }}>
                {feedback.isCorrect ? 'Tebrikler! Doğru cevap.' : 'Dikkat! Yanlış seçenek.'}
              </strong>
              <p style={{ margin: '6px 0 0 0', fontSize: '0.875rem', color: '#334155' }}>
                {feedback.explanation}
              </p>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            {selectedOption !== null && (
              <button
                type="button"
                className="learn-btn learn-btn-primary"
                onClick={handleNext}
              >
                {currentIdx < words.length - 1 ? 'Sonraki Kelimeye Geç →' : 'Kelime Çalışmasını Tamamla ✓'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
