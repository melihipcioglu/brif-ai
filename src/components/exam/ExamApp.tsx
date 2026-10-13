import { useState, useEffect } from 'react';
import type { OptionId } from '../../types/question';
import type { ActiveExamSession, ExamResultReport, ExamSessionMode } from '../../types/examSession';
import {
  startExamSession,
  loadActiveExamSession,
  saveActiveExamSession,
  finishExamSession,
  getExposureSummary,
  clearActiveExamSession
} from '../../services/exam/examSessionService';
import { ExamStartScreen } from './ExamStartScreen';
import { ExamActiveScreen } from './ExamActiveScreen';
import { ExamResultsScreen } from './ExamResultsScreen';
import { ExamHistoryScreen } from './ExamHistoryScreen';
import { PerformanceDashboard } from './PerformanceDashboard';
import { VocabularyStudyScreen } from './VocabularyStudyScreen';
import './exam.css';
import '../learning/learning.css';

import type { LearnerProfile, DailyStudySessionMode, DiagnosticResult } from '../../types/learning';
import { loadLearnerProfile, saveLearnerProfile } from '../../services/learning/learningProfileService';
import { TodayStudyDashboard } from '../learning/TodayStudyDashboard';
import { VocabTrainerScreen } from '../learning/VocabTrainerScreen';
import { ReadingTutorScreen } from '../learning/ReadingTutorScreen';
import { LearningPracticeScreen } from '../learning/LearningPracticeScreen';
import { LearningProgressScreen } from '../learning/LearningProgressScreen';
import { DiagnosticScreen } from '../learning/DiagnosticScreen';
import { InteractiveDecomposerScreen } from '../learning/InteractiveDecomposerScreen';

export type AppTab =
  | 'TODAY'
  | 'HOME'
  | 'SETUP'
  | 'ACTIVE'
  | 'RESULTS'
  | 'HISTORY'
  | 'PERFORMANCE'
  | 'VOCABULARY'
  | 'LEARN_VOCAB'
  | 'LEARN_READING'
  | 'LEARN_PRACTICE'
  | 'LEARN_PROGRESS'
  | 'DIAGNOSTIC'
  | 'DECOMPOSER';

export function ExamApp() {
  const [activeTab, setActiveTab] = useState<AppTab>('TODAY');
  const [activeSession, setActiveSession] = useState<ActiveExamSession | null>(null);
  const [currentResult, setCurrentResult] = useState<ExamResultReport | null>(null);
  const [setupMode, setSetupMode] = useState<ExamSessionMode>('FULL_EXAM');
  const [exposureSummary, setExposureSummary] = useState(getExposureSummary);
  const [learnerProfile, setLearnerProfile] = useState<LearnerProfile>(loadLearnerProfile);

  // Restore ongoing exam session on mount
  useEffect(() => {
    const existing = loadActiveExamSession();
    if (existing) {
      setActiveSession(existing);
      setActiveTab('ACTIVE');
    }
  }, []);

  const handleStartExam = (mode: ExamSessionMode) => {
    const session = startExamSession(mode);
    setActiveSession(session);
    setActiveTab('ACTIVE');
  };

  const handleAnswer = (questionId: string, option: OptionId | null) => {
    if (!activeSession) return;
    const nextAnswers = { ...activeSession.answers, [questionId]: option };
    const nextSession: ActiveExamSession = {
      ...activeSession,
      answers: nextAnswers
    };
    setActiveSession(nextSession);
    saveActiveExamSession(nextSession);
  };

  const handleToggleFlag = (questionId: string) => {
    if (!activeSession) return;
    const isFlagged = activeSession.flaggedQuestionIds.includes(questionId);
    const nextFlags = isFlagged
      ? activeSession.flaggedQuestionIds.filter((id) => id !== questionId)
      : [...activeSession.flaggedQuestionIds, questionId];
    const nextSession: ActiveExamSession = {
      ...activeSession,
      flaggedQuestionIds: nextFlags
    };
    setActiveSession(nextSession);
    saveActiveExamSession(nextSession);
  };

  const handleToggleEliminate = (questionId: string, option: OptionId) => {
    if (!activeSession) return;
    const currentElim = activeSession.eliminatedOptions[questionId] ?? [];
    const isElim = currentElim.includes(option);
    const nextElim = isElim
      ? currentElim.filter((o) => o !== option)
      : [...currentElim, option];
    const nextElimMap = { ...activeSession.eliminatedOptions, [questionId]: nextElim };
    const nextSession: ActiveExamSession = {
      ...activeSession,
      eliminatedOptions: nextElimMap
    };
    setActiveSession(nextSession);
    saveActiveExamSession(nextSession);
  };

  const handleNavigate = (index: number) => {
    if (!activeSession) return;
    if (index < 0 || index >= activeSession.form.questions.length) return;
    const nextSession: ActiveExamSession = {
      ...activeSession,
      currentIndex: index
    };
    setActiveSession(nextSession);
    saveActiveExamSession(nextSession);
  };

  const handleFinish = async () => {
    if (!activeSession) return;
    const report = await finishExamSession(activeSession);
    setCurrentResult(report);
    setActiveSession(null);
    clearActiveExamSession();
    setExposureSummary(getExposureSummary());
    setActiveTab('RESULTS');
  };

  const openSetup = (mode: ExamSessionMode) => {
    setSetupMode(mode);
    setActiveTab('SETUP');
  };

  const handleStartStudySession = (mode: DailyStudySessionMode) => {
    if (mode === 'SHORT_15') {
      setActiveTab('DECOMPOSER');
    } else {
      setActiveTab('LEARN_VOCAB');
    }
  };

  const handleDiagnosticComplete = (result: DiagnosticResult) => {
    const updated: LearnerProfile = {
      ...learnerProfile,
      diagnosticResult: result,
      learnerLevel: result.assignedLevel
    };
    setLearnerProfile(updated);
    saveLearnerProfile(updated);
    setActiveTab('TODAY');
  };

  // If in active exam mode, show dedicated runner
  if (activeTab === 'ACTIVE' && activeSession) {
    return (
      <ExamActiveScreen
        session={activeSession}
        onAnswer={handleAnswer}
        onToggleFlag={handleToggleFlag}
        onToggleEliminate={handleToggleEliminate}
        onNavigate={handleNavigate}
        onFinish={handleFinish}
      />
    );
  }

  // If viewing results report
  if (activeTab === 'RESULTS' && currentResult) {
    return (
      <div className="exam-app-container">
        <header className="exam-app-header">
          <div className="exam-brand">
            <h1 className="exam-brand-title">YÖKDİL Fen Bilimleri</h1>
            <span className="exam-brand-badge">Sınav Raporu</span>
          </div>
        </header>
        <ExamResultsScreen
          result={currentResult}
          onReturnHome={() => setActiveTab('TODAY')}
          onNewExam={() => openSetup('FULL_EXAM')}
        />
      </div>
    );
  }

  return (
    <div className="exam-app-container">
      {/* Top Navigation Bar */}
      <header className="exam-app-header">
        <div className="exam-brand">
          <h1 className="exam-brand-title">ARCBRIEF / YÖKDİL FEN</h1>
          <span className="exam-brand-badge">80+ Hedef</span>
        </div>

        <nav aria-label="Ana menü">
          <ul className="exam-nav-tabs">
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'TODAY' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('TODAY')}
              >
                Bugünkü Çalışmam
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'SETUP' && setupMode === 'FULL_EXAM' ? 'is-active' : ''}`}
                onClick={() => openSetup('FULL_EXAM')}
              >
                Tam Deneme
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'SETUP' && setupMode !== 'FULL_EXAM' ? 'is-active' : ''}`}
                onClick={() => openSetup('SHORT_EXAM_STANDARD')}
              >
                Kısa Çalışma
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'VOCABULARY' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('VOCABULARY')}
              >
                Kelimeler
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'LEARN_PROGRESS' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('LEARN_PROGRESS')}
              >
                Öğrenme Gelişimi
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'HISTORY' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('HISTORY')}
              >
                Geçmişim
              </button>
            </li>
            <li>
              <button
                type="button"
                className={`exam-nav-button ${activeTab === 'PERFORMANCE' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('PERFORMANCE')}
              >
                Performans
              </button>
            </li>
          </ul>
        </nav>
      </header>

      {/* Main Tab Content */}
      <main className="exam-main-content">
        {activeTab === 'TODAY' && (
          <TodayStudyDashboard
            profile={learnerProfile}
            onStartVocabTrainer={() => setActiveTab('LEARN_VOCAB')}
            onStartReadingTutor={() => setActiveTab('DECOMPOSER')}
            onStartPracticeQuestions={() => setActiveTab('LEARN_PRACTICE')}
            onStartSession={handleStartStudySession}
            onOpenFullExam={() => openSetup('FULL_EXAM')}
            onOpenVocabularyCatalog={() => setActiveTab('VOCABULARY')}
            onStartDiagnostic={() => setActiveTab('DIAGNOSTIC')}
          />
        )}

        {activeTab === 'DIAGNOSTIC' && (
          <DiagnosticScreen
            onComplete={handleDiagnosticComplete}
            onSkip={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'DECOMPOSER' && (
          <InteractiveDecomposerScreen
            profile={learnerProfile}
            onFinish={(updated) => {
              setLearnerProfile(updated);
              setActiveTab('TODAY');
            }}
            onCancel={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'LEARN_VOCAB' && (
          <VocabTrainerScreen
            profile={learnerProfile}
            targetWordIds={[
              ...learnerProfile.todayPlan.newWordIds,
              ...learnerProfile.todayPlan.reviewWordIds,
              ...learnerProfile.todayPlan.relapsingWordIds
            ]}
            onFinish={(updated) => {
              setLearnerProfile(updated);
              setActiveTab('TODAY');
            }}
            onCancel={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'LEARN_READING' && (
          <ReadingTutorScreen
            profile={learnerProfile}
            passageId={learnerProfile.todayPlan.readingPassageId}
            onFinish={(updated) => {
              setLearnerProfile(updated);
              setActiveTab('TODAY');
            }}
            onCancel={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'LEARN_PRACTICE' && (
          <LearningPracticeScreen
            profile={learnerProfile}
            questionIds={learnerProfile.todayPlan.practiceQuestionIds}
            onFinish={(updated) => {
              setLearnerProfile(updated);
              setActiveTab('TODAY');
            }}
            onCancel={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'LEARN_PROGRESS' && (
          <LearningProgressScreen
            profile={learnerProfile}
            onReturnHome={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'HOME' && (
          <div>
            {/* Active session resume alert if exists */}
            {activeSession && (
              <div
                style={{
                  background: 'var(--yokdil-warning-light)',
                  border: '1px solid #fde68a',
                  padding: '16px 20px',
                  borderRadius: 'var(--yokdil-radius)',
                  marginBottom: '24px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <strong style={{ color: '#92400e', fontSize: '1rem' }}>
                    ⚠️ Devam Eden Bir Sınav Oturumunuz Bulunuyor
                  </strong>
                  <p style={{ margin: '4px 0 0', fontSize: '0.875rem', color: '#b45309' }}>
                    {activeSession.form.questions.length} soruluk oturumunuz kaldığı yerden devam ettirilebilir.
                  </p>
                </div>
                <button
                  type="button"
                  className="exam-btn exam-btn-primary"
                  onClick={() => setActiveTab('ACTIVE')}
                >
                  Sınava Devam Et →
                </button>
              </div>
            )}

            {/* Hero Welcome */}
            <div className="exam-card" style={{ background: 'linear-gradient(135deg, #0f766e, #134e4a)', color: '#ffffff' }}>
              <div style={{ maxWidth: '650px' }}>
                <span style={{ background: 'rgba(255,255,255,0.2)', padding: '4px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase' }}>
                  YÖKDİL Fen Bilimleri Sınav Hazırlık
                </span>
                <h1 style={{ fontSize: '2rem', fontWeight: 800, margin: '12px 0 8px', letterSpacing: '-0.02em' }}>
                  80+ Hedefli Tam Deneme & Performans Analizi
                </h1>
                <p style={{ opacity: 0.9, fontSize: '1rem', lineHeight: 1.6, margin: '0 0 24px' }}>
                  160 üretim-uygun fen sorusu, 8 sınav ailesi, katı süre kuralı ve 12 analitik beceri haritasıyla gerçek sınav koşullarını deneyimleyin.
                </p>

                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="exam-btn"
                    style={{ background: '#ffffff', color: '#0f766e', fontWeight: 700 }}
                    onClick={() => openSetup('FULL_EXAM')}
                  >
                    Tam Deneme Başlat (80 Soru) →
                  </button>
                  <button
                    type="button"
                    className="exam-btn"
                    style={{ background: 'rgba(255,255,255,0.15)', color: '#ffffff', border: '1px solid rgba(255,255,255,0.3)' }}
                    onClick={() => openSetup('SHORT_EXAM_STANDARD')}
                  >
                    Kısa Çalışma (15 Soru)
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Actions Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', marginBottom: '24px' }}>
              <div
                className="exam-card"
                style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onClick={() => openSetup('FULL_EXAM')}
                role="button"
                tabIndex={0}
              >
                <div style={{ fontSize: '1.75rem', marginBottom: '12px' }}>📝</div>
                <h2 className="exam-card-title">80 Soruluk Tam Deneme</h2>
                <p className="exam-card-desc">
                  180 dakika, 8 soru ailesi (10 soru x 8). Yanlışlar doğruyu götürmez. Gerçek sınav simülasyonu.
                </p>
                <span style={{ color: 'var(--yokdil-primary)', fontWeight: 600, fontSize: '0.875rem' }}>
                  Denemeyi Başlat →
                </span>
              </div>

              <div
                className="exam-card"
                style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onClick={() => openSetup('SHORT_EXAM_STANDARD')}
                role="button"
                tabIndex={0}
              >
                <div style={{ fontSize: '1.75rem', marginBottom: '12px' }}>⏱️</div>
                <h2 className="exam-card-title">Kısa Çalışma Seansları</h2>
                <p className="exam-card-desc">
                  Acil (10 dk · 5 soru), Normal (25 dk · 15 soru) veya Yoğun (50 dk · 30 soru) odaklı çalışma.
                </p>
                <span style={{ color: 'var(--yokdil-primary)', fontWeight: 600, fontSize: '0.875rem' }}>
                  Seans Seç →
                </span>
              </div>

              <div
                className="exam-card"
                style={{ cursor: 'pointer', transition: 'transform 0.15s ease' }}
                onClick={() => setActiveTab('VOCABULARY')}
                role="button"
                tabIndex={0}
              >
                <div style={{ fontSize: '1.75rem', marginBottom: '12px' }}>📚</div>
                <h2 className="exam-card-title">Akademik Fen Kelimeleri</h2>
                <p className="exam-card-desc">
                  Sık çıkan akademik fen terimleri, bağlam odaklı eş anlamlılar ve Türkçe karşılıkları.
                </p>
                <span style={{ color: 'var(--yokdil-primary)', fontWeight: 600, fontSize: '0.875rem' }}>
                  Kelimeleri İncele →
                </span>
              </div>
            </div>

            {/* Question Pool & Capacity Status Card */}
            <div className="exam-card">
              <h2 className="exam-card-title">Soru Bankası ve Tazelik Durumu</h2>
              <p className="exam-card-desc">
                FAZ 10–11 kapasite motoru ve exposure kayıtlarına göre güncel durum:
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Toplam Üretim Havuzu</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>160 Soru</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Taze Soru Sayısı</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--yokdil-success)' }}>
                    {exposureSummary.freshCount} Soru
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Çözülmüş / Görülen</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--yokdil-text-muted)' }}>
                    {exposureSummary.seenCount} Soru
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)' }}>Ayrık Tam Deneme Kapasitesi</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--yokdil-primary)' }}>
                    {Math.floor(exposureSummary.freshCount / 80)} Taze Form
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'SETUP' && (
          <ExamStartScreen
            initialMode={setupMode}
            onStartExam={handleStartExam}
            onCancel={() => setActiveTab('TODAY')}
          />
        )}

        {activeTab === 'HISTORY' && (
          <ExamHistoryScreen
            onViewResult={(res) => {
              setCurrentResult(res);
              setActiveTab('RESULTS');
            }}
            onNewExam={() => openSetup('FULL_EXAM')}
          />
        )}

        {activeTab === 'PERFORMANCE' && <PerformanceDashboard />}

        {activeTab === 'VOCABULARY' && <VocabularyStudyScreen />}
      </main>
    </div>
  );
}
