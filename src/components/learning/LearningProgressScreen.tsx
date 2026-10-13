import type { LearnerProfile } from '../../types/learning';
import { academicVocabBank } from '../../data/learning/academicVocabBank';

export interface LearningProgressScreenProps {
  readonly profile: LearnerProfile;
  readonly onReturnHome: () => void;
}

export function LearningProgressScreen({
  profile,
  onReturnHome
}: LearningProgressScreenProps) {
  const words = Object.values(profile.wordRecords);

  const stateCounts = {
    NOT_STARTED: words.filter((w) => w.state === 'NOT_STARTED').length,
    LEARNING: words.filter((w) => w.state === 'LEARNING').length,
    REVIEW_DUE: profile.wordsReviewDueCount,
    RETAINED: words.filter((w) => w.state === 'RETAINED').length,
    MASTERED: words.filter((w) => w.state === 'MASTERED').length
  };

  return (
    <div className="learn-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <span className="learn-pill learn-pill-teal">V1.1 ADAPTIVE PROGRESS</span>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 800, margin: '8px 0 0 0' }}>
            Öğrenme ve Kalıcılık Gelişim Paneli
          </h1>
        </div>
        <button type="button" className="learn-btn learn-btn-secondary" onClick={onReturnHome}>
          ← Ana Ekrana Dön
        </button>
      </div>

      {/* Retention Stages Grid */}
      <h2 className="learn-section-title">📊 Kelime Kalıcılık Evreleri (Spaced Repetition)</h2>
      <div className="learn-stats-grid" style={{ marginBottom: 24 }}>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #16a34a' }}>
          <span className="learn-stat-val" style={{ color: '#16a34a' }}>{stateCounts.MASTERED}</span>
          <span className="learn-stat-label">MASTERED (Kalıcı Ustalık)</span>
        </div>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #0284c7' }}>
          <span className="learn-stat-val" style={{ color: '#0284c7' }}>{stateCounts.RETAINED}</span>
          <span className="learn-stat-label">RETAINED (Hatırlanıyor)</span>
        </div>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #d97706' }}>
          <span className="learn-stat-val" style={{ color: '#d97706' }}>{stateCounts.LEARNING}</span>
          <span className="learn-stat-label">LEARNING (Öğreniliyor)</span>
        </div>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #dc2626' }}>
          <span className="learn-stat-val" style={{ color: '#dc2626' }}>{stateCounts.REVIEW_DUE}</span>
          <span className="learn-stat-label">REVIEW_DUE (Tekrar Bekleyen)</span>
        </div>
      </div>

      {/* 3D Mastery Tracking */}
      <h2 className="learn-section-title">🎯 3 Boyutlu Kelime Ustalığı Takibi</h2>
      <div className="learn-stats-grid" style={{ marginBottom: 32 }}>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #0f766e' }}>
          <span className="learn-stat-val" style={{ color: '#0f766e' }}>
            {words.filter((w) => w.recognitionMastered).length}
          </span>
          <span className="learn-stat-label">1. Tanıma (Recognition)</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 4 }}>
            Anlam ve telaffuzu doğrudan tanıma
          </span>
        </div>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #0284c7' }}>
          <span className="learn-stat-val" style={{ color: '#0284c7' }}>
            {words.filter((w) => w.comprehensionMastered).length}
          </span>
          <span className="learn-stat-label">2. Cümlede Anlama (Comprehension)</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 4 }}>
            Akademik cümlede işlevini kavrama
          </span>
        </div>
        <div className="learn-stat-card" style={{ borderTop: '4px solid #9333ea' }}>
          <span className="learn-stat-val" style={{ color: '#9333ea' }}>
            {words.filter((w) => w.transferMastered).length}
          </span>
          <span className="learn-stat-label">3. Yeni Bağlamda Kullanma (Transfer)</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 4 }}>
            Soru ve yeni metinde bağımsız kullanma
          </span>
        </div>
      </div>

      {/* Reading Comprehension Skills Scaffolding Grid */}
      <h2 className="learn-section-title">📖 Akademik Okuma Becerileri ve İskele Düzeyi</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14, marginBottom: 32 }}>
        {Object.entries(profile.readingMastery).map(([topic, stat]) => {
          let scaffoldColor = 'learn-pill-blue';
          let scaffoldTr = 'Sistem Modeli';
          if (stat.scaffoldLevel === 'GUIDED_PROMPT') {
            scaffoldColor = 'learn-pill-amber';
            scaffoldTr = 'Yönlendirmeli';
          } else if (stat.scaffoldLevel === 'INDEPENDENT') {
            scaffoldColor = 'learn-pill-green';
            scaffoldTr = 'Bağımsız Ustalık';
          }

          return (
            <div
              key={topic}
              style={{
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderRadius: 10,
                padding: '14px 18px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <strong style={{ fontSize: '0.9rem', color: '#0f172a' }}>{topic}</strong>
                  <span className={`learn-pill ${scaffoldColor}`}>{scaffoldTr}</span>
                </div>
                <div style={{ fontSize: '0.8125rem', color: '#64748b' }}>
                  Çözülen Alıştırma: {stat.encounters}
                </div>
              </div>
              <div style={{ marginTop: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontWeight: 600, marginBottom: 4 }}>
                  <span>Başarı Oranı</span>
                  <span>%{Math.round(stat.accuracy * 100)}</span>
                </div>
                <div style={{ background: '#e2e8f0', borderRadius: 9999, height: 6, overflow: 'hidden' }}>
                  <div
                    style={{
                      background: 'var(--learn-primary)',
                      width: `${Math.round(stat.accuracy * 100)}%`,
                      height: '100%'
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Vocabulary Log */}
      <h2 className="learn-section-title">📚 Çalışılan Kelimeler ve Durumları</h2>
      <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 12, padding: '16px 20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
          {academicVocabBank.map((word) => {
            const rec = profile.wordRecords[word.word_id];
            const state = rec?.state ?? 'NOT_STARTED';

            let pillClass = 'learn-pill-blue';
            if (state === 'MASTERED') pillClass = 'learn-pill-green';
            else if (state === 'RETAINED') pillClass = 'learn-pill-teal';
            else if (state === 'LEARNING') pillClass = 'learn-pill-amber';

            return (
              <div
                key={word.word_id}
                style={{
                  border: '1px solid #f1f5f9',
                  background: '#f8fafc',
                  padding: '8px 12px',
                  borderRadius: 8,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <strong style={{ fontSize: '0.9rem', color: '#1e293b' }}>{word.lemma}</strong>
                  <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{word.meaning_tr.slice(0, 22)}...</div>
                </div>
                <span className={`learn-pill ${pillClass}`} style={{ fontSize: '0.7rem' }}>
                  {state}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
