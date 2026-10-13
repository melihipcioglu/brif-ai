import { useState } from 'react';
import type { ExamResultReport } from '../../types/examSession';
import { QUESTION_FAMILIES } from '../../types/question';

export interface ExamResultsScreenProps {
  readonly result: ExamResultReport;
  readonly onReturnHome: () => void;
  readonly onNewExam: () => void;
}

type ReviewFilter = 'ALL' | 'INCORRECT' | 'BLANK' | 'CORRECT';

export function ExamResultsScreen({
  result,
  onReturnHome,
  onNewExam
}: ExamResultsScreenProps) {
  const [reviewFilter, setReviewFilter] = useState<ReviewFilter>('INCORRECT');

  const minutes = Math.floor(result.totalTimeMs / (60 * 1000));
  const seconds = Math.floor((result.totalTimeMs % (60 * 1000)) / 1000);
  const avgSec = Math.floor(result.averageTimePerQuestionMs / 1000);

  const filteredItems = result.items.filter((item) => {
    if (reviewFilter === 'ALL') return true;
    if (reviewFilter === 'INCORRECT') return !item.isCorrect && !item.isBlank;
    if (reviewFilter === 'BLANK') return item.isBlank;
    if (reviewFilter === 'CORRECT') return item.isCorrect;
    return true;
  });

  return (
    <div className="exam-main-content" style={{ padding: '24px 0' }}>
      {/* Top Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <button
          type="button"
          className="exam-btn exam-btn-secondary exam-btn-sm"
          onClick={onReturnHome}
        >
          ← Ana Sayfaya Dön
        </button>
        <button
          type="button"
          className="exam-btn exam-btn-primary exam-btn-sm"
          onClick={onNewExam}
        >
          Yeni Sınav Başlat
        </button>
      </div>

      {/* Score Banner */}
      <div className="results-score-banner">
        <div>
          <div style={{ fontSize: '0.875rem', textTransform: 'uppercase', letterSpacing: '0.05em', opacity: 0.9 }}>
            YÖKDİL Fen Bilimleri Simülasyon Puanı
          </div>
          <div className="results-score-val">
            {result.yokdilScore.toFixed(1)}
            <span style={{ fontSize: '1.5rem', fontWeight: 500, opacity: 0.8 }}> / 100</span>
          </div>
          <div className={`results-score-target ${result.target80Met ? 'results-target-success' : 'results-target-warning'}`}>
            {result.target80Met
              ? '🎯 80+ Başarı Hedefi Yakalandı!'
              : `🎯 80+ Hedefine Kalan: ${(80 - result.yokdilScore).toFixed(1)} Puan`}
          </div>
        </div>

        <div className="results-metrics-grid">
          <div className="results-metric-card">
            <div className="results-metric-val" style={{ color: '#86efac' }}>{result.correctCount}</div>
            <div className="results-metric-lbl">Doğru</div>
          </div>
          <div className="results-metric-card">
            <div className="results-metric-val" style={{ color: '#fca5a5' }}>{result.incorrectCount}</div>
            <div className="results-metric-lbl">Yanlış</div>
          </div>
          <div className="results-metric-card">
            <div className="results-metric-val" style={{ color: '#cbd5e1' }}>{result.blankCount}</div>
            <div className="results-metric-lbl">Boş</div>
          </div>
          <div className="results-metric-card">
            <div className="results-metric-val">{minutes}m {seconds}s</div>
            <div className="results-metric-lbl">Toplam Süre</div>
          </div>
          <div className="results-metric-card">
            <div className="results-metric-val">{avgSec} sn</div>
            <div className="results-metric-lbl">Ort. / Soru</div>
          </div>
        </div>
      </div>

      {result.isClockTampered && (
        <div style={{ background: '#fef2f2', border: '1px solid #f87171', borderRadius: 'var(--yokdil-radius)', padding: '12px 16px', marginBottom: '16px', fontSize: '0.875rem', color: '#991b1b' }}>
          ⚠️ <strong>Süre Uyarısı:</strong> İstemci sistem saati manipülasyonu veya saat geriye kayması algılandı. Süre ölçümü güvenilmez kabul edildi.
        </div>
      )}

      {/* Psychometric Disclaimer Box */}
      <div style={{ background: '#f1f5f9', border: '1px solid var(--yokdil-border)', borderRadius: 'var(--yokdil-radius)', padding: '16px 20px', marginBottom: '24px', fontSize: '0.875rem', color: '#475569' }}>
        <strong>Psikometrik Bilgilendirme:</strong> Bu puan, YÖKDİL Fen soru ailesi kotalarına ve madde standartlarına göre hesaplanan pratik simülasyon puanıdır. Resmî ÖSYM sınav puanı değildir; madde güçlüğü ve ayırt edicilik parametreleri öğrenci kitlesi üzerinden standartlaştırılmamıştır.
      </div>

      {/* Question Families Performance */}
      <div className="exam-card">
        <h2 className="exam-card-title">Soru Ailesi Bazında Performans</h2>
        <p className="exam-card-desc">8 farklı YÖKDİL soru tipindeki güçlü ve zayıf yönleriniz:</p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
          {QUESTION_FAMILIES.map((family) => {
            const stat = result.familyStats[family];
            if (!stat || stat.total === 0) return null;

            return (
              <div
                key={family}
                style={{
                  border: '1px solid var(--yokdil-border)',
                  borderRadius: 'var(--yokdil-radius)',
                  padding: '14px',
                  background: '#ffffff'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{family}</span>
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: '0.875rem',
                      color: stat.accuracy >= 70 ? 'var(--yokdil-success)' : stat.accuracy >= 50 ? 'var(--yokdil-warning)' : 'var(--yokdil-danger)'
                    }}
                  >
                    %{stat.accuracy}
                  </span>
                </div>

                {/* Progress bar */}
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden', marginBottom: '8px' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${stat.accuracy}%`,
                      background: stat.accuracy >= 70 ? 'var(--yokdil-success)' : stat.accuracy >= 50 ? 'var(--yokdil-warning)' : 'var(--yokdil-danger)'
                    }}
                  />
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--yokdil-text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>{stat.correct} Doğru</span>
                  <span>{stat.incorrect} Yanlış</span>
                  <span>{stat.blank} Boş</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Weak Skills Alert */}
      {result.weakSkills.length > 0 && (
        <div className="exam-card" style={{ borderLeft: '4px solid var(--yokdil-warning)' }}>
          <h2 className="exam-card-title" style={{ color: '#b45309' }}>
            ⚠️ Geliştirilmesi Gereken Zayıf Beceriler
          </h2>
          <p className="exam-card-desc">
            Aşağıdaki fen bilimleri dil becerilerinde doğruluk oranı %60'ın altında kalmıştır. Bu alanlara öncelik vermeniz tavsiye edilir:
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {result.weakSkills.map((sk) => (
              <span
                key={sk}
                style={{
                  background: 'var(--yokdil-warning-light)',
                  color: '#92400e',
                  border: '1px solid #fde68a',
                  padding: '6px 12px',
                  borderRadius: 'var(--yokdil-radius)',
                  fontWeight: 600,
                  fontSize: '0.8125rem'
                }}
              >
                {sk} ({result.skillStats[sk]?.accuracy ?? 0}%)
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Question Review Section */}
      <div className="exam-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div>
            <h2 className="exam-card-title" style={{ margin: 0 }}>Soru İnceleme ve Çözümler</h2>
            <p className="exam-card-desc" style={{ margin: 0 }}>Soruları, işaretlediğiniz şıkları ve Türkçe çözüm gerekçelerini inceleyin:</p>
          </div>

          {/* Filter buttons */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              className={`exam-btn exam-btn-sm ${reviewFilter === 'ALL' ? 'exam-btn-primary' : 'exam-btn-secondary'}`}
              onClick={() => setReviewFilter('ALL')}
            >
              Tümü ({result.totalQuestions})
            </button>
            <button
              type="button"
              className={`exam-btn exam-btn-sm ${reviewFilter === 'INCORRECT' ? 'exam-btn-primary' : 'exam-btn-secondary'}`}
              onClick={() => setReviewFilter('INCORRECT')}
            >
              Yanlışlar ({result.incorrectCount})
            </button>
            <button
              type="button"
              className={`exam-btn exam-btn-sm ${reviewFilter === 'BLANK' ? 'exam-btn-primary' : 'exam-btn-secondary'}`}
              onClick={() => setReviewFilter('BLANK')}
            >
              Boşlar ({result.blankCount})
            </button>
            <button
              type="button"
              className={`exam-btn exam-btn-sm ${reviewFilter === 'CORRECT' ? 'exam-btn-primary' : 'exam-btn-secondary'}`}
              onClick={() => setReviewFilter('CORRECT')}
            >
              Doğrular ({result.correctCount})
            </button>
          </div>
        </div>

        {/* Filtered Question Cards */}
        {filteredItems.length === 0 ? (
          <p style={{ textAlign: 'center', padding: '32px', color: 'var(--yokdil-text-muted)' }}>
            Bu filtrede gösterilecek soru bulunmamaktadır.
          </p>
        ) : (
          <div>
            {filteredItems.map((item) => {
              const q = item.question;
              const cardClass = item.isCorrect ? 'is-correct' : item.isBlank ? 'is-blank' : 'is-incorrect';

              return (
                <article key={q.id} className={`review-item-card ${cardClass}`}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 700, fontSize: '1rem' }}>Soru {item.index}</span>
                      <span className="exam-family-pill">{q.family}</span>
                    </div>

                    <div>
                      {item.isCorrect && (
                        <span style={{ color: 'var(--yokdil-success)', fontWeight: 700, fontSize: '0.875rem' }}>
                          ✓ Doğru (+1.25 Puan)
                        </span>
                      )}
                      {!item.isCorrect && !item.isBlank && (
                        <span style={{ color: 'var(--yokdil-danger)', fontWeight: 700, fontSize: '0.875rem' }}>
                          ✗ Yanlış (0 Puan)
                        </span>
                      )}
                      {item.isBlank && (
                        <span style={{ color: 'var(--yokdil-text-muted)', fontWeight: 600, fontSize: '0.875rem' }}>
                          ○ Boş Bırakıldı
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Passage if present */}
                  {q.passage && (
                    <div className="exam-passage-box" style={{ maxHeight: '200px', marginBottom: '16px', fontSize: '0.9375rem' }}>
                      {q.passage}
                    </div>
                  )}

                  <p style={{ fontWeight: 600, marginBottom: '16px', fontSize: '1rem' }}>
                    {q.stem}
                  </p>

                  {/* Options with answer indicators */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                    {q.options.map((opt) => {
                      const isStudentChoice = item.selectedOption === opt.id;
                      const isCorrectChoice = q.correct_option === opt.id;

                      let optBorder = '1px solid var(--yokdil-border)';
                      let optBg = '#ffffff';
                      let label = null;

                      if (isCorrectChoice) {
                        optBorder = '2px solid var(--yokdil-success)';
                        optBg = 'var(--yokdil-success-light)';
                        label = <span style={{ color: 'var(--yokdil-success)', fontWeight: 700, fontSize: '0.75rem' }}>[DOĞRU CEVAP]</span>;
                      }

                      if (isStudentChoice && !isCorrectChoice) {
                        optBorder = '2px solid var(--yokdil-danger)';
                        optBg = 'var(--yokdil-danger-light)';
                        label = <span style={{ color: 'var(--yokdil-danger)', fontWeight: 700, fontSize: '0.75rem' }}>[SİZİN YANITINIZ]</span>;
                      }

                      return (
                        <div
                          key={opt.id}
                          style={{
                            padding: '8px 12px',
                            borderRadius: 'var(--yokdil-radius)',
                            border: optBorder,
                            backgroundColor: optBg,
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            fontSize: '0.875rem'
                          }}
                        >
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'baseline' }}>
                            <strong>{opt.id})</strong>
                            <span>{opt.text}</span>
                          </div>
                          {label}
                        </div>
                      );
                    })}
                  </div>

                  {/* Turkish Triage Explanation */}
                  <div className="review-triage-panel">
                    <h4 style={{ margin: '0 0 6px', fontSize: '0.875rem', fontWeight: 700, color: 'var(--yokdil-primary)' }}>
                      💡 Soru Çözümü ve Gerekçe (Triage):
                    </h4>
                    <p style={{ margin: '0 0 8px', lineHeight: 1.5 }}>{q.explanation?.triage?.summary}</p>
                    {q.explanation?.triage?.checks && q.explanation.triage.checks.length > 0 && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--yokdil-text-muted)' }}>
                        <strong>Bilişsel Denetimler:</strong> {q.explanation.triage.checks.join(' · ')}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      {/* Bottom Action Footer */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginTop: '24px' }}>
        <button
          type="button"
          className="exam-btn exam-btn-secondary"
          onClick={onReturnHome}
        >
          ← Ana Menüye Dön
        </button>
        <button
          type="button"
          className="exam-btn exam-btn-primary"
          onClick={onNewExam}
        >
          Yeni Sınav Başlat →
        </button>
      </div>
    </div>
  );
}
