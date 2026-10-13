import { useState } from 'react';
import type { ExamSessionMode } from '../../types/examSession';
import { EXAM_MODE_INFOS, getExposureSummary } from '../../services/exam/examSessionService';

export interface ExamStartScreenProps {
  readonly initialMode?: ExamSessionMode;
  readonly onStartExam: (mode: ExamSessionMode) => void;
  readonly onCancel: () => void;
}

export function ExamStartScreen({
  initialMode = 'FULL_EXAM',
  onStartExam,
  onCancel
}: ExamStartScreenProps) {
  const [selectedMode, setSelectedMode] = useState<ExamSessionMode>(initialMode);
  const exposure = getExposureSummary();
  const info = EXAM_MODE_INFOS[selectedMode];

  const modes: ExamSessionMode[] = [
    'FULL_EXAM',
    'SHORT_EXAM_QUICK',
    'SHORT_EXAM_STANDARD',
    'SHORT_EXAM_INTENSIVE'
  ];

  return (
    <div className="exam-card" style={{ maxWidth: '800px', margin: '40px auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 className="exam-card-title" style={{ margin: 0, fontSize: '1.5rem' }}>
          Sınav Başlatma ve Hazırlık
        </h1>
        <button
          type="button"
          className="exam-btn exam-btn-sm exam-btn-secondary"
          onClick={onCancel}
        >
          ← Geri Dön
        </button>
      </div>

      <p className="exam-card-desc">
        YÖKDİL Fen Bilimleri hedeflerinize uygun çalışma modunu seçin ve sınav kurallarını inceleyin.
      </p>

      {/* Mode Selection Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        {modes.map((m) => {
          const item = EXAM_MODE_INFOS[m];
          const isSelected = selectedMode === m;
          return (
            <div
              key={m}
              onClick={() => setSelectedMode(m)}
              style={{
                border: isSelected ? '2px solid var(--yokdil-primary)' : '1px solid var(--yokdil-border)',
                backgroundColor: isSelected ? 'var(--yokdil-primary-light)' : '#ffffff',
                borderRadius: 'var(--yokdil-radius)',
                padding: '16px',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--yokdil-primary)', textTransform: 'uppercase' }}>
                  {item.tag}
                </span>
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--yokdil-text-muted)' }}>
                  {item.durationMinutes} Dk
                </span>
              </div>
              <h3 style={{ margin: '0 0 6px', fontSize: '1rem', fontWeight: 700, color: 'var(--yokdil-text)' }}>
                {item.title}
              </h3>
              <p style={{ margin: 0, fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)', lineHeight: 1.4 }}>
                {item.totalQuestions} Soru · {item.description}
              </p>
            </div>
          );
        })}
      </div>

      {/* Selected Mode Summary */}
      <div style={{ background: '#f8fafc', border: '1px solid var(--yokdil-border)', borderRadius: 'var(--yokdil-radius)', padding: '20px', marginBottom: '24px' }}>
        <h3 style={{ margin: '0 0 12px', fontSize: '1.0625rem', fontWeight: 700 }}>
          Seçilen Sınav: {info.title}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Soru Sayısı</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{info.totalQuestions} Soru</div>
          </div>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Sınav Süresi</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{info.durationMinutes} Dakika</div>
          </div>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Soru Başına Süre</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              {(info.durationMinutes / info.totalQuestions).toFixed(1)} Dk
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Havuz Durumu</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: exposure.freshCount >= info.totalQuestions ? 'var(--yokdil-success)' : 'var(--yokdil-warning)' }}>
              {exposure.freshCount >= info.totalQuestions ? '✓ Taze Sorular Hazır' : '↻ Tekrar / Pekiştirme'}
            </div>
          </div>
        </div>
      </div>

      {/* Exam Rules & Guidelines */}
      <div style={{ borderLeft: '4px solid #0f766e', background: '#f0fdfa', padding: '16px 20px', borderRadius: '4px', marginBottom: '28px' }}>
        <h4 style={{ margin: '0 0 8px', fontSize: '0.9375rem', fontWeight: 700, color: '#0f766e' }}>
          Sınav Kuralları ve Yönerge
        </h4>
        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.875rem', color: '#134e4a', lineHeight: 1.6 }}>
          <li>Her soru 5 seçeneklidir ve tek bir doğru cevabı vardır.</li>
          <li><strong>Yanlış cevaplar doğruyu götürmez;</strong> boş bırakmak yerine en olası şıkkı işaretlemeniz önerilir.</li>
          <li>Sınav esnasında sorular arasında dilediğiniz gibi ileri-geri gezinebilir, soru paletinden istediğiniz soruya doğrudan geçebilirsiniz.</li>
          <li>Cevabından emin olmadığınız soruları işaretleyip (flag) daha sonra tekrar kontrol edebilirsiniz.</li>
          <li>Gerçek sınav koşullarını simüle etmek amacıyla sınav süresince doğru/yanlış bildirimleri verilmez; teslim sonrasında kapsamlı analiz raporu üretilir.</li>
        </ul>
      </div>

      {/* Start Actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
        <button
          type="button"
          className="exam-btn exam-btn-secondary"
          onClick={onCancel}
        >
          Vazgeç
        </button>
        <button
          type="button"
          className="exam-btn exam-btn-primary"
          onClick={() => onStartExam(selectedMode)}
          style={{ padding: '12px 28px', fontSize: '1rem' }}
        >
          Sınavı Başlat →
        </button>
      </div>
    </div>
  );
}
