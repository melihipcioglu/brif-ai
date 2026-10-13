import { useState, useEffect } from 'react';
import type { ExamHistoryEntry, ExamResultReport } from '../../types/examSession';
import { getExamHistory, EXAM_MODE_INFOS } from '../../services/exam/examSessionService';

export interface ExamHistoryScreenProps {
  readonly onViewResult: (result: ExamResultReport) => void;
  readonly onNewExam: () => void;
}

export function ExamHistoryScreen({
  onViewResult,
  onNewExam
}: ExamHistoryScreenProps) {
  const [history, setHistory] = useState<readonly ExamHistoryEntry[]>([]);

  useEffect(() => {
    setHistory(getExamHistory());
  }, []);

  return (
    <div className="exam-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h1 className="exam-card-title" style={{ margin: 0 }}>Önceki Sınavlarım ve Geçmiş</h1>
          <p className="exam-card-desc" style={{ margin: '4px 0 0' }}>
            Tamamladığınız deneme sınavları ve çalışma oturumlarının geçmiş kayıtları:
          </p>
        </div>
        <button
          type="button"
          className="exam-btn exam-btn-primary exam-btn-sm"
          onClick={onNewExam}
        >
          Yeni Sınav Başlat +
        </button>
      </div>

      {history.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 16px', background: '#f8fafc', borderRadius: 'var(--yokdil-radius)', border: '1px dashed var(--yokdil-border)' }}>
          <p style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--yokdil-text)', marginBottom: '8px' }}>
            Henüz tamamlanmış bir sınav kaydı bulunmuyor.
          </p>
          <p style={{ color: 'var(--yokdil-text-muted)', fontSize: '0.875rem', marginBottom: '20px' }}>
            Bilginizi sınamak ve gelişim raporunuzu oluşturmak için ilk denemenizi başlatın.
          </p>
          <button
            type="button"
            className="exam-btn exam-btn-primary"
            onClick={onNewExam}
          >
            İlk Denemeyi Başlat →
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {[...history].reverse().map((entry) => {
            const dateStr = new Date(entry.completedAt).toLocaleDateString('tr-TR', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            });
            const modeInfo = EXAM_MODE_INFOS[entry.mode];
            const durationMin = Math.round(entry.totalDurationMs / (60 * 1000));

            return (
              <div
                key={entry.id}
                style={{
                  border: '1px solid var(--yokdil-border)',
                  borderRadius: 'var(--yokdil-radius)',
                  padding: '16px 20px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '16px',
                  backgroundColor: '#ffffff'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.0625rem' }}>
                      {modeInfo?.title ?? entry.mode}
                    </span>
                    <span className="exam-brand-badge">{dateStr}</span>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--yokdil-text-muted)', display: 'flex', gap: '12px' }}>
                    <span>{entry.totalQuestions} Soru</span>
                    <span>•</span>
                    <span style={{ color: 'var(--yokdil-success)', fontWeight: 600 }}>{entry.correctCount} Doğru</span>
                    <span>•</span>
                    <span style={{ color: 'var(--yokdil-danger)', fontWeight: 600 }}>{entry.incorrectCount} Yanlış</span>
                    <span>•</span>
                    <span>{entry.blankCount} Boş</span>
                    <span>•</span>
                    <span>⏱ {durationMin} Dk</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--yokdil-primary)' }}>
                      {entry.yokdilScore.toFixed(1)}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--yokdil-text-muted)', fontWeight: 600 }}>
                      {entry.yokdilScore >= 80 ? '🎯 80+ Başarı' : 'Hedef: 80'}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="exam-btn exam-btn-secondary exam-btn-sm"
                    onClick={() => onViewResult(entry.result)}
                  >
                    Raporu İncele →
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
