import { useState } from 'react';
import type { LearnerProfile, SentenceSyntacticToken } from '../../types/learning';
import { INTERACTIVE_DECOMPOSITION_TASKS } from '../../data/learning/interactiveDecompositionBank';
import { recordReadingCompletion } from '../../services/learning/learningProfileService';

export interface InteractiveDecomposerScreenProps {
  readonly profile: LearnerProfile;
  readonly onFinish: (updatedProfile: LearnerProfile) => void;
  readonly onCancel: () => void;
}

export function InteractiveDecomposerScreen({
  profile,
  onFinish,
  onCancel
}: InteractiveDecomposerScreenProps) {
  const [taskIndex, setTaskIndex] = useState(0);
  const [selectedTokenIdx, setSelectedTokenIdx] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<{ isCorrect: boolean; message: string } | null>(null);
  const [taskCompleted, setTaskCompleted] = useState(false);
  const [currentProfile, setCurrentProfile] = useState<LearnerProfile>(profile);

  const currentTask = INTERACTIVE_DECOMPOSITION_TASKS[taskIndex];
  const totalTasks = INTERACTIVE_DECOMPOSITION_TASKS.length;

  if (!currentTask) {
    return null;
  }

  const handleTokenClick = (index: number) => {
    setSelectedTokenIdx(index);
    const token = currentTask.tokens[index];
    if (!token) return;

    if (currentTask.mode === 'I_DO') {
      // In I DO mode, any token click explains its syntactic role
      const customExpl = currentTask.tokenExplanations[index] || token.explanation_tr;
      setFeedback({
        isCorrect: true,
        message: `[${token.role}] ${token.text}: ${customExpl}`
      });
      setTaskCompleted(true);
      return;
    }

    // In WE DO and YOU DO modes, evaluate whether selected token matches target
    const isCorrect = currentTask.correctTokenIndices.includes(index);
    const customExpl = currentTask.tokenExplanations[index] || token.explanation_tr;

    setFeedback({
      isCorrect,
      message: customExpl
    });

    if (isCorrect) {
      setTaskCompleted(true);
      // Record progress
      const updated = recordReadingCompletion(
        currentProfile,
        'CLAUSE_DECOMPOSITION',
        1.0
      );
      setCurrentProfile(updated);
    }
  };

  const handleNextTask = () => {
    if (taskIndex + 1 < totalTasks) {
      setTaskIndex((prev) => prev + 1);
      setSelectedTokenIdx(null);
      setFeedback(null);
      setTaskCompleted(false);
    } else {
      onFinish(currentProfile);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'SUBJECT':
        return '#0284c7'; // Blue
      case 'VERB':
        return '#16a34a'; // Green
      case 'OBJECT':
        return '#9333ea'; // Purple
      case 'CONNECTOR':
        return '#ea580c'; // Orange
      case 'SUBORDINATE':
        return '#ca8a04'; // Amber
      default:
        return '#475569';
    }
  };

  return (
    <div className="learn-container">
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <span
            className="learn-pill"
            style={{
              background:
                currentTask.mode === 'I_DO'
                  ? '#eff6ff'
                  : currentTask.mode === 'WE_DO'
                  ? '#f0fdf4'
                  : '#faf5ff',
              color:
                currentTask.mode === 'I_DO'
                  ? '#1d4ed8'
                  : currentTask.mode === 'WE_DO'
                  ? '#15803d'
                  : '#7e22ce',
              fontWeight: 700
            }}
          >
            {currentTask.mode === 'I_DO' && '👩‍🏫 I DO: ÖĞRETMEN MODELİ (İnceleme)'}
            {currentTask.mode === 'WE_DO' && '🤝 WE DO: BİRLİKTE ÇÖZÜMLEME (Rehberli)'}
            {currentTask.mode === 'YOU_DO' && '🎯 YOU DO: BAĞIMSIZ UYGULAMA (Sen Çözüyorsun)'}
          </span>
          <span style={{ marginLeft: 12, fontSize: '0.875rem', color: '#64748b' }}>
            Aşama {taskIndex + 1} / {totalTasks}
          </span>
        </div>
        <button type="button" className="learn-btn learn-btn-secondary" onClick={onCancel}>
          Oturumdan Çık
        </button>
      </div>

      {/* Main Interactive Workbench Card */}
      <div className="vocab-card-box">
        {/* Pedagogical Prompt */}
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', marginBottom: 12 }}>
          {currentTask.prompt}
        </h2>
        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: 20 }}>
          💡 <strong>Strateji:</strong> {currentTask.pedagogicalRationale}
        </p>

        {/* Interactive Sentence Token Stream */}
        <div
          style={{
            background: '#f8fafc',
            border: '2px dashed #cbd5e1',
            borderRadius: 12,
            padding: '24px 20px',
            marginBottom: 24,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 10,
            alignItems: 'center'
          }}
        >
          {currentTask.tokens.map((token: SentenceSyntacticToken, idx: number) => {
            const isSelected = selectedTokenIdx === idx;
            const isTarget = currentTask.correctTokenIndices.includes(idx);
            let chipBg = '#ffffff';
            let chipBorder = '1.5px solid #cbd5e1';
            let chipColor = '#1e293b';

            if (isSelected) {
              if (currentTask.mode === 'I_DO') {
                chipBg = '#e0f2fe';
                chipBorder = '2px solid #0284c7';
                chipColor = '#0369a1';
              } else if (feedback?.isCorrect) {
                chipBg = '#f0fdf4';
                chipBorder = '2px solid #16a34a';
                chipColor = '#15803d';
              } else {
                chipBg = '#fef2f2';
                chipBorder = '2px solid #dc2626';
                chipColor = '#b91c1c';
              }
            } else if (taskCompleted && isTarget) {
              chipBg = '#f0fdf4';
              chipBorder = '2px solid #16a34a';
              chipColor = '#15803d';
            }

            return (
              <button
                key={idx}
                type="button"
                style={{
                  background: chipBg,
                  border: chipBorder,
                  color: chipColor,
                  padding: '10px 16px',
                  borderRadius: 8,
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  fontFamily: 'serif',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4
                }}
                onClick={() => handleTokenClick(idx)}
              >
                <span>{token.text}</span>
                {(isSelected || (taskCompleted && isTarget) || currentTask.mode === 'I_DO') && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 800,
                      color: getRoleBadgeColor(token.role),
                      textTransform: 'uppercase',
                      background: 'rgba(0,0,0,0.05)',
                      padding: '2px 6px',
                      borderRadius: 4
                    }}
                  >
                    {token.role}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Pedagogical Feedback Box */}
        {feedback && (
          <div
            style={{
              background: feedback.isCorrect ? '#f0fdf4' : '#fffbeb',
              border: `1px solid ${feedback.isCorrect ? '#86efac' : '#fde68a'}`,
              borderRadius: 10,
              padding: '16px 20px',
              marginBottom: 24
            }}
          >
            <div
              style={{
                fontWeight: 700,
                fontSize: '1rem',
                color: feedback.isCorrect ? '#166534' : '#92400e',
                marginBottom: 6
              }}
            >
              {feedback.isCorrect ? '✅ Doğru Tespit!' : '⚠️ Dikkat — Neden Yanlış?'}
            </div>
            <p style={{ margin: 0, fontSize: '0.925rem', color: '#334155', lineHeight: 1.6 }}>
              {feedback.message}
            </p>
          </div>
        )}

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            className="learn-btn learn-btn-primary"
            style={{ padding: '12px 24px', fontSize: '1rem' }}
            disabled={!taskCompleted}
            onClick={handleNextTask}
          >
            {taskIndex + 1 < totalTasks ? 'Sonraki Aşamaya Geç →' : 'Çözümleme Çalışmasını Tamamla →'}
          </button>
        </div>
      </div>
    </div>
  );
}
