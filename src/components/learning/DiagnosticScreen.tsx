import React, { useState } from 'react';
import type { DiagnosticQuestion, DiagnosticResult, LearnerLevel } from '../../types/learning';
import { DIAGNOSTIC_QUESTIONS_BANK } from '../../data/learning/diagnosticBank';

interface DiagnosticScreenProps {
  onComplete: (result: DiagnosticResult) => void;
  onSkip?: () => void;
}

export const DiagnosticScreen: React.FC<DiagnosticScreenProps> = ({ onComplete, onSkip }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const currentQ: DiagnosticQuestion = DIAGNOSTIC_QUESTIONS_BANK[currentIndex]!;
  const totalQuestions = DIAGNOSTIC_QUESTIONS_BANK.length;

  const handleSelectOption = (optionId: string) => {
    if (isSubmitted) return;
    setSelectedOptionId(optionId);
  };

  const handleConfirmAnswer = () => {
    if (!selectedOptionId) return;
    setAnswers((prev) => ({ ...prev, [currentQ.id]: selectedOptionId }));
    setIsSubmitted(true);
  };

  const handleNext = () => {
    if (currentIndex + 1 < totalQuestions) {
      setCurrentIndex((prev) => prev + 1);
      setSelectedOptionId(null);
      setIsSubmitted(false);
    } else {
      calculateAndFinish();
    }
  };

  const calculateAndFinish = () => {
    let vocabScore = 0;
    let syntaxScore = 0;
    let connectorScore = 0;

    DIAGNOSTIC_QUESTIONS_BANK.forEach((q) => {
      const chosenId = answers[q.id] || selectedOptionId;
      const isCorrect = q.options.find((o) => o.id === chosenId)?.isCorrect ?? false;
      if (isCorrect) {
        if (q.type === 'VOCAB_RECOGNITION') vocabScore++;
        if (q.type === 'SYNTAX_IDENTIFICATION') syntaxScore++;
        if (q.type === 'CONNECTOR_DIRECTION') connectorScore++;
      }
    });

    const totalScore = vocabScore + syntaxScore + connectorScore;
    let assignedLevel: LearnerLevel = 'FOUNDATIONAL';
    if (totalScore >= 8) {
      assignedLevel = 'ADVANCED';
    } else if (totalScore >= 5) {
      assignedLevel = 'INTERMEDIATE';
    } else {
      assignedLevel = 'FOUNDATIONAL';
    }

    const result: DiagnosticResult = {
      score: totalScore,
      total: totalQuestions,
      vocabScore,
      syntaxScore,
      connectorScore,
      assignedLevel,
      completedAt: Date.now()
    };

    setIsFinished(true);
    // Also pass to parent when user clicks finish
    setFinalResult(result);
  };

  const [finalResult, setFinalResult] = useState<DiagnosticResult | null>(null);

  if (isFinished && finalResult) {
    return (
      <div className="learning-screen-container">
        <div className="learning-card" style={{ maxWidth: '680px', margin: '40px auto', textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🎯</div>
          <span className="learning-badge learning-badge-success" style={{ fontSize: '0.875rem' }}>
            BAŞLANGIÇ KALİBRASYONU TAMAMLANDI
          </span>
          <h1 style={{ fontSize: '1.75rem', margin: '16px 0 8px', color: '#0f172a' }}>
            Kişiselleştirilmiş Öğretim Seviyeniz Belirlendi
          </h1>
          <p style={{ color: '#64748b', fontSize: '1rem', marginBottom: '24px' }}>
            Hiçbir ön bilgi varsaymadan, öğrenme hızınıza ve eksiklerinize tam uyum sağlayan özel iskele düzeyi oluşturuldu.
          </p>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '12px',
              background: '#f8fafc',
              padding: '20px',
              borderRadius: '12px',
              marginBottom: '24px',
              textAlign: 'center'
            }}
          >
            <div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>KELİME BİLGİSİ</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0f766e' }}>
                {finalResult.vocabScore} / 4
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>CÜMLE İSKELETİ</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#0284c7' }}>
                {finalResult.syntaxScore} / 3
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>BAĞLAÇ & YÖN</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#8b5cf6' }}>
                {finalResult.connectorScore} / 2
              </div>
            </div>
          </div>

          <div
            style={{
              background:
                finalResult.assignedLevel === 'FOUNDATIONAL'
                  ? '#eff6ff'
                  : finalResult.assignedLevel === 'INTERMEDIATE'
                  ? '#f0fdf4'
                  : '#faf5ff',
              border: '1px solid #cbd5e1',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '24px',
              textAlign: 'left'
            }}
          >
            <strong style={{ color: '#1e293b', fontSize: '1.05rem', display: 'block', marginBottom: '6px' }}>
              Öğretim Modu: {finalResult.assignedLevel} (
              {finalResult.assignedLevel === 'FOUNDATIONAL'
                ? 'Temel İskele — Sıfır Varsayım'
                : finalResult.assignedLevel === 'INTERMEDIATE'
                ? 'Standart Kademeli İskele'
                : 'İleri Seviye Hızlı Basamaklama'}
              )
            </strong>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#475569', lineHeight: 1.5 }}>
              {finalResult.assignedLevel === 'FOUNDATIONAL' &&
                'Kelimeler sıfır gürültülü basit cümlelerle tanıtılacak; cümlenin öznesi ve ana fiili adım adım gösterilecek; açıklamalar en anlaşılır dille sunulacaktır.'}
              {finalResult.assignedLevel === 'INTERMEDIATE' &&
                'Temel kavramlar pekiştirilecek, bağlaçların düşünce akışındaki rolü vurgulanacak ve akademik cümle genişletmelerine kademeli olarak geçilecektir.'}
              {finalResult.assignedLevel === 'ADVANCED' &&
                'Kelime ailesi ve çeldirici tuzaklar hızla analiz edilecek; doğrudan karmaşık sınav şablonlarına ve soru çözüm taktiklerine odaklanılacaktır.'}
            </p>
          </div>

          <button
            type="button"
            className="exam-btn exam-btn-primary"
            style={{ width: '100%', padding: '14px', fontSize: '1.05rem' }}
            onClick={() => onComplete(finalResult)}
          >
            Bugünkü Öğrenme Yolculuğuma Başla →
          </button>
        </div>
      </div>
    );
  }

  const selectedOpt = currentQ.options.find((o) => o.id === selectedOptionId);

  return (
    <div className="learning-screen-container">
      <div className="learning-card" style={{ maxWidth: '720px', margin: '30px auto' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <span className="learning-badge learning-badge-tier">
              {currentQ.type === 'VOCAB_RECOGNITION' && '1. ADIM: KELİME TANIMA'}
              {currentQ.type === 'SYNTAX_IDENTIFICATION' && '2. ADIM: CÜMLE İSKELETİ'}
              {currentQ.type === 'CONNECTOR_DIRECTION' && '3. ADIM: BAĞLAÇ & YÖN'}
            </span>
            <span style={{ marginLeft: '8px', fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>
              Soru {currentIndex + 1} / {totalQuestions}
            </span>
          </div>
          {onSkip && (
            <button
              type="button"
              className="exam-btn"
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              onClick={onSkip}
            >
              Atla ve Başla
            </button>
          )}
        </div>

        {/* Reassurance Banner on First Question */}
        {currentIndex === 0 && (
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              padding: '10px 14px',
              borderRadius: '8px',
              marginBottom: '16px',
              fontSize: '0.85rem',
              color: '#475569'
            }}
          >
            💡 <strong>Sıfır Ön Bilgi Kalibrasyonu:</strong> Bu bir sınav değildir; puanınızı kırmaz. Sadece size en uygun öğretim hızını ve iskele desteğini ayarlamak içindir.
          </div>
        )}

        {/* Question sentence if any */}
        {currentQ.sentence && (
          <div
            style={{
              background: '#f1f5f9',
              padding: '16px',
              borderRadius: '8px',
              fontSize: '1.05rem',
              fontWeight: 600,
              color: '#1e293b',
              marginBottom: '16px',
              fontFamily: 'serif',
              borderLeft: '4px solid #0284c7'
            }}
          >
            {currentQ.sentence}
          </div>
        )}

        {/* Prompt */}
        <h2 style={{ fontSize: '1.15rem', color: '#0f172a', marginBottom: '20px', fontWeight: 700 }}>
          {currentQ.prompt}
        </h2>

        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
          {currentQ.options.map((opt) => {
            const isSelected = selectedOptionId === opt.id;
            let btnStyle: React.CSSProperties = {
              textAlign: 'left',
              padding: '14px 18px',
              borderRadius: '8px',
              border: '1.5px solid #cbd5e1',
              background: '#ffffff',
              fontSize: '0.95rem',
              cursor: isSubmitted ? 'default' : 'pointer',
              transition: 'all 0.15s ease'
            };

            if (isSelected) {
              btnStyle.border = '2px solid #0284c7';
              btnStyle.background = '#f0f9ff';
              btnStyle.fontWeight = 600;
            }

            if (isSubmitted) {
              if (opt.isCorrect) {
                btnStyle.border = '2px solid #16a34a';
                btnStyle.background = '#f0fdf4';
                btnStyle.color = '#15803d';
              } else if (isSelected && !opt.isCorrect) {
                btnStyle.border = '2px solid #dc2626';
                btnStyle.background = '#fef2f2';
                btnStyle.color = '#b91c1c';
              }
            }

            return (
              <button
                key={opt.id}
                type="button"
                style={btnStyle}
                onClick={() => handleSelectOption(opt.id)}
                disabled={isSubmitted}
              >
                <span style={{ fontWeight: 700, marginRight: '8px' }}>{opt.id})</span> {opt.text}
                {isSubmitted && opt.isCorrect && ' ✓ Doğru'}
                {isSubmitted && isSelected && !opt.isCorrect && ' ✗'}
              </button>
            );
          })}
        </div>

        {/* Pedagogical Feedback after submission */}
        {isSubmitted && selectedOpt && (
          <div
            style={{
              background: selectedOpt.isCorrect ? '#f0fdf4' : '#fffbeb',
              border: `1px solid ${selectedOpt.isCorrect ? '#86efac' : '#fde68a'}`,
              borderRadius: '8px',
              padding: '14px 18px',
              marginBottom: '20px'
            }}
          >
            <div style={{ fontWeight: 700, color: selectedOpt.isCorrect ? '#166534' : '#92400e', marginBottom: '4px' }}>
              {selectedOpt.isCorrect ? '👏 Tebrikler!' : '💡 Öğretmen Açıklaması:'}
            </div>
            <p style={{ margin: 0, fontSize: '0.9rem', color: '#334155', lineHeight: 1.5 }}>
              {selectedOpt.feedback}
            </p>
            <div style={{ marginTop: '8px', fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>
              📌 İpucu: {currentQ.scaffoldTip}
            </div>
          </div>
        )}

        {/* Action Button */}
        <div>
          {!isSubmitted ? (
            <button
              type="button"
              className="exam-btn exam-btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '1rem' }}
              disabled={!selectedOptionId}
              onClick={handleConfirmAnswer}
            >
              Cevabı Onayla →
            </button>
          ) : (
            <button
              type="button"
              className="exam-btn exam-btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '1rem' }}
              onClick={handleNext}
            >
              {currentIndex + 1 < totalQuestions ? 'Sonraki Soruya Geç →' : 'Sonucu Gör ve Öğrenmeye Başla →'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
