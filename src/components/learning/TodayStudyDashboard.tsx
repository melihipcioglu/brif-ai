import type { LearnerProfile, DailyStudySessionMode } from '../../types/learning';
import { SESSION_MODE_CONFIGS } from '../../services/learning/learningProfileService';

export interface TodayStudyDashboardProps {
  readonly profile: LearnerProfile;
  readonly onStartVocabTrainer: () => void;
  readonly onStartReadingTutor: () => void;
  readonly onStartPracticeQuestions: () => void;
  readonly onStartSession: (mode: DailyStudySessionMode) => void;
  readonly onOpenFullExam: () => void;
  readonly onOpenVocabularyCatalog: () => void;
  readonly onStartDiagnostic?: () => void;
}

export function TodayStudyDashboard({
  profile,
  onStartVocabTrainer,
  onStartReadingTutor,
  onStartPracticeQuestions,
  onStartSession,
  onOpenFullExam,
  onOpenVocabularyCatalog,
  onStartDiagnostic
}: TodayStudyDashboardProps) {
  const plan = profile.todayPlan;

  // Calculate overall day progress percentage
  const totalStepUnits =
    plan.newWordIds.length +
    1 + // reading
    plan.practiceQuestionIds.length;

  const completedUnits =
    plan.completedSteps.vocabLearned +
    (plan.completedSteps.readingCompleted ? 1 : 0) +
    plan.completedSteps.practiceQuestionsCompleted;

  const progressPercent = Math.min(100, Math.round((completedUnits / Math.max(1, totalStepUnits)) * 100));

  const isVocabComplete = plan.completedSteps.vocabLearned >= plan.newWordIds.length;
  const isReadingComplete = plan.completedSteps.readingCompleted;
  const isQuestionsComplete = plan.completedSteps.practiceQuestionsCompleted >= plan.practiceQuestionIds.length;

  return (
    <div className="learn-container">
      {/* Hero Card */}
      <section className="learn-hero-card" aria-label="Bugünkü çalışma özeti">
        <div className="learn-hero-badge">
          <span>📅 GÜN {plan.dayNumber}</span>
          <span>•</span>
          <span>🔥 {profile.streakDays} GÜNLÜK SERİ</span>
        </div>

        <h1 className="learn-hero-title">
          Bugünkü Kişiselleştirilmiş Öğrenme Rotanız
        </h1>
        <p className="learn-hero-subtitle">
          Akademik fen kelimelerini öğrenin, karmaşık cümle yapılarını çözümleyin ve öğrenilen kavramlarla alıştırma yapın.
        </p>

        {/* Daily Progress Bar */}
        <div style={{ marginBottom: 6, display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', fontWeight: 600 }}>
          <span>GÜNLÜK İLERLEME</span>
          <span>%{progressPercent} Tamamlandı</span>
        </div>
        <div className="learn-progress-wrapper" role="progressbar" aria-valuenow={progressPercent} aria-valuemin={0} aria-valuemax={100}>
          <div className="learn-progress-bar" style={{ width: `${progressPercent}%` }} />
        </div>
      </section>

      {/* Diagnostic Prompt or Status Banner */}
      {!profile.diagnosticResult ? (
        <div
          style={{
            background: 'linear-gradient(135deg, #eff6ff, #dbeafe)',
            border: '2px solid #3b82f6',
            borderRadius: 12,
            padding: '18px 24px',
            marginBottom: 24,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12
          }}
        >
          <div>
            <span style={{ background: '#2563eb', color: '#ffffff', padding: '3px 10px', borderRadius: 20, fontSize: '0.75rem', fontWeight: 800 }}>
              ÖNERİLEN İLK ADIM (3 DAKİKA)
            </span>
            <h3 style={{ margin: '8px 0 4px', fontSize: '1.15rem', color: '#1e3a8a', fontWeight: 800 }}>
              🎯 Başlangıç Seviye Tanılama Çalışması
            </h3>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#1e40af' }}>
              Hiçbir ön bilgi varsaymadan, size en uygun öğretim iskele düzeyini belirleyin.
            </p>
          </div>
          {onStartDiagnostic && (
            <button
              type="button"
              className="exam-btn exam-btn-primary"
              style={{ padding: '10px 20px', fontSize: '0.95rem' }}
              onClick={onStartDiagnostic}
            >
              Tanılamayı Başlat →
            </button>
          )}
        </div>
      ) : (
        <div
          style={{
            background: '#f8fafc',
            border: '1px solid #cbd5e1',
            borderRadius: 10,
            padding: '12px 18px',
            marginBottom: 20,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.875rem'
          }}
        >
          <div>
            <span style={{ color: '#0f766e', fontWeight: 700 }}>✓ Seviye Kalibrasyonu:</span>{' '}
            <strong>{profile.learnerLevel || profile.diagnosticResult.assignedLevel}</strong> ({profile.diagnosticResult.score}/9 Puan)
          </div>
          {onStartDiagnostic && (
            <button
              type="button"
              style={{ background: 'none', border: 'none', color: '#0284c7', cursor: 'pointer', fontSize: '0.8rem', textDecoration: 'underline' }}
              onClick={onStartDiagnostic}
            >
              Tanılamayı Tekrarla
            </button>
          )}
        </div>
      )}

      {/* Stats Summary Bar */}
      <section className="learn-stats-grid" aria-label="Öğrenme istatistikleri">
        <div className="learn-stat-card">
          <span className="learn-stat-val">{plan.newWordIds.length}</span>
          <span className="learn-stat-label">Bugünün Yeni Kelimesi</span>
        </div>
        <div className="learn-stat-card">
          <span className="learn-stat-val">{plan.reviewWordIds.length}</span>
          <span className="learn-stat-label">Bugünkü Tekrar Kelimesi</span>
        </div>
        <div className="learn-stat-card">
          <span className="learn-stat-val">{profile.totalWordsLearned}</span>
          <span className="learn-stat-label">Öğrenilen Toplam Kelime</span>
        </div>
        <div className="learn-stat-card">
          <span className="learn-stat-val" style={{ color: profile.wordsReviewDueCount > 0 ? 'var(--learn-warning)' : 'var(--learn-success)' }}>
            {profile.wordsReviewDueCount}
          </span>
          <span className="learn-stat-label">Tekrar Bekleyen Kelime</span>
        </div>
      </section>

      {/* 3-Step Guided Roadmap */}
      <h2 className="learn-section-title">
        <span>🚀 3 Adımlı Günlük Öğrenme Akışı</span>
        <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--learn-text-muted)' }}>
          {plan.isCompleted ? '✓ Günlük Hedef Tamamlandı!' : `${3 - (isVocabComplete ? 1 : 0) - (isReadingComplete ? 1 : 0) - (isQuestionsComplete ? 1 : 0)} Adım Kaldı`}
        </span>
      </h2>

      <div className="learn-stepper-grid">
        {/* STEP 1: VOCABULARY */}
        <div className={`learn-step-card ${isVocabComplete ? 'is-completed' : ''}`}>
          <div>
            <div className="learn-step-header">
              <div className="learn-step-number">{isVocabComplete ? '✓' : '1'}</div>
              <h3 className="learn-step-title">Akademik Kelimeleri Öğren</h3>
            </div>
            <p className="learn-step-desc">
              Fen bilimleri bağlamında kelime ailesi, eş dizimler (collocations), telaffuz ve hafıza ipuçlarıyla aktif öğrenme.
            </p>
            <div className="learn-badge-row">
              <span className="learn-pill learn-pill-teal">
                {plan.newWordIds.length} Yeni Kelime
              </span>
              {plan.reviewWordIds.length > 0 && (
                <span className="learn-pill learn-pill-amber">
                  {plan.reviewWordIds.length} Tekrar
                </span>
              )}
              {plan.relapsingWordIds.length > 0 && (
                <span className="learn-pill learn-pill-blue">
                  {plan.relapsingWordIds.length} Pekiştirme
                </span>
              )}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--learn-text-muted)', marginBottom: 12 }}>
              İlerleme: {plan.completedSteps.vocabLearned} / {plan.newWordIds.length} Kelime
            </div>
            <button
              type="button"
              className={`learn-btn ${isVocabComplete ? 'learn-btn-secondary' : 'learn-btn-primary'}`}
              style={{ width: '100%' }}
              onClick={onStartVocabTrainer}
            >
              {isVocabComplete ? 'Kelimeleri Tekrar İncele' : 'Kelimeleri Çalışmaya Başla →'}
            </button>
          </div>
        </div>

        {/* STEP 2: READING COMPREHENSION */}
        <div className={`learn-step-card ${isReadingComplete ? 'is-completed' : ''}`}>
          <div>
            <div className="learn-step-header">
              <div className="learn-step-number">{isReadingComplete ? '✓' : '2'}</div>
              <h3 className="learn-step-title">Akademik Cümle & Paragraf Oku</h3>
            </div>
            <p className="learn-step-desc">
              Cümlenin öznesini, ana fiilini ve bağlaçlarını renkli sözdizimi ayrıştırması ile adım adım çözümleyin.
            </p>
            <div className="learn-badge-row">
              <span className="learn-pill learn-pill-blue">
                {plan.readingSkillTopic}
              </span>
              <span className="learn-pill learn-pill-teal">
                İnteraktif Çözümleme
              </span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--learn-text-muted)', marginBottom: 12 }}>
              Durum: {isReadingComplete ? '✓ Okuma ve analiz tamamlandı' : '○ İnteraktif analiz bekleniyor'}
            </div>
            <button
              type="button"
              className={`learn-btn ${isReadingComplete ? 'learn-btn-secondary' : 'learn-btn-primary'}`}
              style={{ width: '100%' }}
              onClick={onStartReadingTutor}
            >
              {isReadingComplete ? 'Metni Tekrar İncele' : 'Okuma Öğretimini Başlat →'}
            </button>
          </div>
        </div>

        {/* STEP 3: PRACTICE QUESTIONS */}
        <div className={`learn-step-card ${isQuestionsComplete ? 'is-completed' : ''}`}>
          <div>
            <div className="learn-step-header">
              <div className="learn-step-number">{isQuestionsComplete ? '✓' : '3'}</div>
              <h3 className="learn-step-title">Öğrenilen Kelimelerle Soru Çöz</h3>
            </div>
            <p className="learn-step-desc">
              Günün hedef kelimelerini içeren YÖKDİL tipi alıştırma sorularıyla kavramları pekiştirin. Sınav havuzunu tüketmez.
            </p>
            <div className="learn-badge-row">
              <span className="learn-pill learn-pill-teal">
                {plan.practiceQuestionIds.length} Soru
              </span>
              <span className="learn-pill learn-pill-green">
                Açıklamalı & Tekrar Çözülebilir
              </span>
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.8125rem', color: 'var(--learn-text-muted)', marginBottom: 12 }}>
              İlerleme: {plan.completedSteps.practiceQuestionsCompleted} / {plan.practiceQuestionIds.length} Soru
            </div>
            <button
              type="button"
              className={`learn-btn ${isQuestionsComplete ? 'learn-btn-secondary' : 'learn-btn-primary'}`}
              style={{ width: '100%' }}
              onClick={onStartPracticeQuestions}
            >
              {isQuestionsComplete ? 'Soruları Yeniden Çöz' : 'Alıştırma Sorularını Başlat →'}
            </button>
          </div>
        </div>
      </div>

      {/* Focused Timed Study Sessions */}
      <h2 className="learn-section-title">
        ⏱️ Zaman Kısıtınıza Uygun Çalışma Seansları
      </h2>

      <div className="learn-session-grid">
        {(Object.entries(SESSION_MODE_CONFIGS) as [DailyStudySessionMode, typeof SESSION_MODE_CONFIGS[DailyStudySessionMode]][]).map(
          ([modeKey, cfg]) => (
            <div
              key={modeKey}
              className="learn-session-card"
              onClick={() => onStartSession(modeKey)}
              role="button"
              tabIndex={0}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span className="learn-pill learn-pill-teal">{cfg.badge}</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--learn-primary)' }}>
                    {cfg.durationMinutes} Dk
                  </span>
                </div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '0 0 6px 0' }}>{cfg.title}</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--learn-text-muted)', margin: 0, lineHeight: 1.45 }}>
                  {cfg.description}
                </p>
              </div>
              <div style={{ marginTop: 14 }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--learn-primary)' }}>
                  Seansı Başlat →
                </span>
              </div>
            </div>
          )
        )}
      </div>

      {/* Prominent Full Exam & Vocabulary Catalog Access */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 16 }}>
        <div style={{ background: '#f8fafc', border: '2px solid #cbd5e1', borderRadius: 14, padding: '22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <span className="learn-pill learn-pill-amber">GERÇEK SINAV SİMÜLASYONU</span>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: '10px 0 6px 0' }}>
              80 Soruluk Tam Deneme Sınavı
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--learn-text-muted)', margin: '0 0 16px 0', lineHeight: 1.5 }}>
              180 dakika, 8 soru ailesi ve katı exposure kontrolleriyle resmi formattaki bağımsız sınav havuzunu deneyimleyin.
            </p>
          </div>
          <button
            type="button"
            className="learn-btn learn-btn-accent"
            onClick={onOpenFullExam}
          >
            Tam Deneme Başlat (80 Soru) →
          </button>
        </div>

        <div style={{ background: '#f8fafc', border: '2px solid #cbd5e1', borderRadius: 14, padding: '22px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <span className="learn-pill learn-pill-blue">AKADEMİK REFERANS</span>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800, margin: '10px 0 6px 0' }}>
              Akademik Fen Terimleri Sözlüğü
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--learn-text-muted)', margin: '0 0 16px 0', lineHeight: 1.5 }}>
              Tüm fen bilimleri kelimelerini inceleyin, eş anlamlıları karşılaştırın ve Tier seviyelerine göre filtreleyin.
            </p>
          </div>
          <button
            type="button"
            className="learn-btn learn-btn-secondary"
            onClick={onOpenVocabularyCatalog}
          >
            Kelime Sözlüğünü İncele →
          </button>
        </div>
      </div>
    </div>
  );
}
