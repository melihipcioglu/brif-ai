import { useState, useEffect } from 'react';
import { getExamHistory } from '../../services/exam/examSessionService';
import { PERFORMANCE_CONTENT_SKILLS } from '../../services/performance/calibration';
import { wilsonInterval } from '../../services/performance/statistics';

export function PerformanceDashboard() {
  const [totalAttempts, setTotalAttempts] = useState(0);
  const [totalCorrect, setTotalCorrect] = useState(0);
  const [skillCounts, setSkillCounts] = useState<Record<string, { total: number; correct: number }>>({});

  useEffect(() => {
    const history = getExamHistory();
    let attempts = 0;
    let correct = 0;
    const skills: Record<string, { total: number; correct: number }> = {};

    for (const s of PERFORMANCE_CONTENT_SKILLS) {
      skills[s] = { total: 0, correct: 0 };
    }

    for (const entry of history) {
      attempts += entry.totalQuestions - entry.blankCount;
      correct += entry.correctCount;

      for (const [s, stat] of Object.entries(entry.result.skillStats)) {
        if (!skills[s]) skills[s] = { total: 0, correct: 0 };
        skills[s]!.total += stat.total;
        skills[s]!.correct += stat.correct;
      }
    }

    setTotalAttempts(attempts);
    setTotalCorrect(correct);
    setSkillCounts(skills);
  }, []);

  const overallAccuracy = totalAttempts > 0 ? Math.round((totalCorrect / totalAttempts) * 100) : 0;
  const interval = wilsonInterval(totalCorrect, totalAttempts);
  const isReadinessMet = totalAttempts >= 60;

  return (
    <div className="exam-card">
      <h1 className="exam-card-title">Performans ve Beceri Analizi</h1>
      <p className="exam-card-desc">
        Phase 6 Performance Estimator motoru ile 12 fen bilimleri dil becerisinde ölçülen ustalık durumu:
      </p>

      {/* Top Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        <div style={{ background: '#f8fafc', padding: '16px', borderRadius: 'var(--yokdil-radius)', border: '1px solid var(--yokdil-border)' }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Toplam Çözülen Soru</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{totalAttempts}</div>
        </div>
        <div style={{ background: '#f8fafc', padding: '16px', borderRadius: 'var(--yokdil-radius)', border: '1px solid var(--yokdil-border)' }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Genel Doğruluk Oranı</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--yokdil-primary)' }}>%{overallAccuracy}</div>
        </div>
        <div style={{ background: '#f8fafc', padding: '16px', borderRadius: 'var(--yokdil-radius)', border: '1px solid var(--yokdil-border)' }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Wilson %95 Güven Aralığı</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
            {totalAttempts > 0 && interval ? `[%${(interval.lower_bound * 100).toFixed(1)} - %${(interval.upper_bound * 100).toFixed(1)}]` : 'Veri Bekleniyor'}
          </div>
        </div>
        <div style={{ background: '#f8fafc', padding: '16px', borderRadius: 'var(--yokdil-radius)', border: '1px solid var(--yokdil-border)' }}>
          <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Ölçüm Hazır Olma Durumu</div>
          <div style={{ fontSize: '0.9375rem', fontWeight: 700, color: isReadinessMet ? 'var(--yokdil-success)' : 'var(--yokdil-warning)' }}>
            {isReadinessMet ? '✓ READY (Yeterli Kanıt)' : '○ GÖZLEM (≥60 Soru Gerekli)'}
          </div>
        </div>
      </div>

      {/* 12 Content Skills List */}
      <h2 style={{ fontSize: '1.125rem', fontWeight: 700, marginBottom: '16px' }}>
        12 Temel Fen İçerik Becerisi (Content Skills)
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
        {PERFORMANCE_CONTENT_SKILLS.map((skill) => {
          const stat = skillCounts[skill] ?? { total: 0, correct: 0 };
          const acc = stat.total > 0 ? Math.round((stat.correct / stat.total) * 100) : 0;
          const isWeak = stat.total >= 3 && acc < 60;

          return (
            <div
              key={skill}
              style={{
                border: isWeak ? '2px solid #f59e0b' : '1px solid var(--yokdil-border)',
                borderRadius: 'var(--yokdil-radius)',
                padding: '14px',
                backgroundColor: isWeak ? '#fffbeb' : '#ffffff'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>{skill}</span>
                <span style={{ fontWeight: 700, fontSize: '0.875rem', color: stat.total === 0 ? '#94a3b8' : acc >= 70 ? 'var(--yokdil-success)' : acc >= 50 ? 'var(--yokdil-warning)' : 'var(--yokdil-danger)' }}>
                  {stat.total === 0 ? '—' : `%${acc}`}
                </span>
              </div>

              {/* Bar */}
              <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden', marginBottom: '8px' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${acc}%`,
                    background: stat.total === 0 ? 'transparent' : acc >= 70 ? 'var(--yokdil-success)' : acc >= 50 ? 'var(--yokdil-warning)' : 'var(--yokdil-danger)'
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--yokdil-text-muted)' }}>
                <span>{stat.total} Soru Çözüldü</span>
                {isWeak && <span style={{ color: '#b45309', fontWeight: 700 }}>Zayıf Alan</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
