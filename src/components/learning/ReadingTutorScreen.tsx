import { useState } from 'react';
import type {
  LearnerProfile,
  SentenceSyntacticToken
} from '../../types/learning';
import { academicReadingBank } from '../../data/learning/academicReadingBank';
import { recordReadingCompletion } from '../../services/learning/learningProfileService';
import { getRecommendedScaffoldLevel } from '../../services/learning/readingTutor';

export interface ReadingTutorScreenProps {
  readonly profile: LearnerProfile;
  readonly passageId: string;
  readonly onFinish: (updatedProfile: LearnerProfile) => void;
  readonly onCancel: () => void;
}

export function ReadingTutorScreen({
  profile,
  passageId,
  onFinish,
  onCancel
}: ReadingTutorScreenProps) {
  const passage =
    academicReadingBank.find((p) => p.id === passageId) ?? academicReadingBank[0]!;

  const [activeStep, setActiveStep] = useState<'SENTENCES' | 'PASSAGE_REVIEW'>('SENTENCES');
  const [currentSentenceIdx, setCurrentSentenceIdx] = useState(0);
  const [selectedToken, setSelectedToken] = useState<SentenceSyntacticToken | null>(null);
  const [sentenceQuizAnswer, setSentenceQuizAnswer] = useState<number | null>(null);
  const [passageQuizAnswers, setPassageQuizAnswers] = useState<Record<number, number>>({});

  const currentSentence = passage.sentences[currentSentenceIdx]!;
  const scaffoldLevel = getRecommendedScaffoldLevel(currentSentence.pedagogical_focus, profile);

  const handleSelectToken = (token: SentenceSyntacticToken) => {
    setSelectedToken(token);
  };

  const handleSentenceQuizChoice = (idx: number) => {
    if (sentenceQuizAnswer !== null) return;
    setSentenceQuizAnswer(idx);
  };

  const handleNextSentence = () => {
    setSelectedToken(null);
    setSentenceQuizAnswer(null);

    if (currentSentenceIdx < passage.sentences.length - 1) {
      setCurrentSentenceIdx(currentSentenceIdx + 1);
    } else {
      setActiveStep('PASSAGE_REVIEW');
    }
  };

  const handlePassageQuizChoice = (qIdx: number, optIdx: number) => {
    setPassageQuizAnswers((prev) => ({ ...prev, [qIdx]: optIdx }));
  };

  const handleFinishReading = () => {
    // Calculate accuracy across scaffold questions
    let correctCount = 0;
    passage.scaffold_questions.forEach((q, idx) => {
      if (passageQuizAnswers[idx] === q.correct_index) correctCount++;
    });
    const accuracy = passage.scaffold_questions.length > 0
      ? correctCount / passage.scaffold_questions.length
      : 1.0;

    const updated = recordReadingCompletion(
      profile,
      profile.todayPlan.readingSkillTopic,
      accuracy
    );
    onFinish(updated);
  };

  return (
    <div className="learn-container">
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <span className="learn-pill learn-pill-teal">
            AKADEMİK OKUMA ÖĞRETİMİ • {passage.science_domain.toUpperCase()}
          </span>
          <span style={{ marginLeft: 12, fontSize: '0.875rem', color: 'var(--learn-text-muted)' }}>
            İskele Düzeyi: <strong>{scaffoldLevel}</strong>
          </span>
        </div>
        <button type="button" className="learn-btn learn-btn-secondary" onClick={onCancel}>
          Oturumdan Çık
        </button>
      </div>

      {activeStep === 'SENTENCES' ? (
        /* STEP 1: SENTENCE-BY-SENTENCE DECOMPOSITION */
        <div className="vocab-card-box">
          <div style={{ marginBottom: 16 }}>
            <span className="learn-pill learn-pill-blue">
              CÜMLE {currentSentenceIdx + 1} / {passage.sentences.length}
            </span>
            <span className="learn-pill learn-pill-amber" style={{ marginLeft: 8 }}>
              Odak Becerisi: {currentSentence.pedagogical_focus}
            </span>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, margin: '12px 0 6px 0' }}>
              {passage.title}
            </h2>
          </div>

          {/* Interactive Syntactic Sentence Box */}
          <div
            style={{
              background: '#f8fafc',
              border: '2px solid #cbd5e1',
              borderRadius: 12,
              padding: '20px 24px',
              fontSize: '1.25rem',
              lineHeight: 1.9,
              marginBottom: 16
            }}
          >
            {currentSentence.tokens.map((token, i) => {
              const roleClass = `syntax-role-${token.role}`;
              const isSelected = selectedToken?.text === token.text;

              return (
                <span
                  key={i}
                  className={`syntax-token ${roleClass}`}
                  style={{
                    outline: isSelected ? '2px solid #0f766e' : 'none',
                    transform: isSelected ? 'scale(1.05)' : 'none'
                  }}
                  onClick={() => handleSelectToken(token)}
                  title="Görevi görmek için tıklayın"
                  role="button"
                  tabIndex={0}
                >
                  {token.text}
                </span>
              );
            })}
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--learn-text-muted)', marginBottom: 20 }}>
            👆 <em>İpucu: Cümlenin ögelerine tıklayarak özne, yüklem, bağlaç ve niteleyicilerin görevlerini inceleyin.</em>
          </p>

          {/* Token explanation on click */}
          {selectedToken && (
            <div
              style={{
                background: '#f0fdfa',
                border: '1.5px solid #99f6e4',
                borderRadius: 10,
                padding: '12px 18px',
                marginBottom: 20,
                animation: 'fadeIn 0.2s ease'
              }}
            >
              <strong style={{ color: 'var(--learn-primary)' }}>
                Seçilen Öge: "{selectedToken.text}" [{selectedToken.role}]
              </strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.92rem', color: '#134e4a' }}>
                {selectedToken.explanation_tr}
              </p>
            </div>
          )}

          {/* Syntactic Structure Decomposition Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 14, marginBottom: 20 }}>
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '14px 18px' }}>
              <span className="learn-pill learn-pill-blue">ANA CÜMLE (Main Clause)</span>
              <div style={{ marginTop: 8, fontSize: '0.9rem', lineHeight: 1.6 }}>
                <div><strong>Özne:</strong> {currentSentence.main_clause.subject}</div>
                <div><strong>Yüklem:</strong> <span style={{ color: '#b45309', fontWeight: 700 }}>{currentSentence.main_clause.verb}</span></div>
                {currentSentence.main_clause.object && (
                  <div><strong>Nesne:</strong> {currentSentence.main_clause.object}</div>
                )}
              </div>
            </div>

            {currentSentence.subordinate_clause && (
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10, padding: '14px 18px' }}>
                <span className="learn-pill learn-pill-amber">YAN CÜMLE (Subordinate Clause)</span>
                <div style={{ marginTop: 8, fontSize: '0.9rem', lineHeight: 1.6 }}>
                  <div><strong>Bağlaç:</strong> <span style={{ color: '#15803d', fontWeight: 700 }}>{currentSentence.subordinate_clause.connector}</span></div>
                  <div><strong>Yan Cümlecik:</strong> {currentSentence.subordinate_clause.clause}</div>
                  <div style={{ color: '#64748b', fontSize: '0.85rem', marginTop: 4 }}>
                    {currentSentence.subordinate_clause.function_tr}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Pedagogical Strategy Tip */}
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, padding: '14px 18px', marginBottom: 20 }}>
            <strong style={{ color: '#166534' }}>💡 AKADEMİK OKUMA İPUCU:</strong>
            <p style={{ margin: '6px 0 0 0', fontSize: '0.92rem', color: '#14532d', lineHeight: 1.5 }}>
              {currentSentence.pedagogical_tip_tr}
            </p>
          </div>

          {/* Interactive Check Question if available */}
          {currentSentence.interactive_question && (
            <div style={{ background: '#fdf4ff', border: '1px solid #f5d0fe', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
              <strong style={{ color: '#86198f', fontSize: '0.95rem' }}>
                🎯 CÜMLE ANALİZİ SORUSU:
              </strong>
              <p style={{ margin: '8px 0 12px 0', fontWeight: 600, color: '#3b0764' }}>
                {currentSentence.interactive_question.prompt}
              </p>

              <div style={{ display: 'grid', gap: 8 }}>
                {currentSentence.interactive_question.options.map((opt, i) => {
                  const isSelected = sentenceQuizAnswer === i;
                  const isCorrect = i === currentSentence.interactive_question!.correct_index;

                  let optBg = '#ffffff';
                  let optBorder = '#e9d5ff';

                  if (sentenceQuizAnswer !== null) {
                    if (isCorrect) {
                      optBg = '#f0fdf4';
                      optBorder = 'var(--learn-success)';
                    } else if (isSelected) {
                      optBg = '#fef2f2';
                      optBorder = 'var(--learn-danger)';
                    }
                  }

                  return (
                    <button
                      key={i}
                      type="button"
                      style={{
                        background: optBg,
                        border: `1.5px solid ${optBorder}`,
                        borderRadius: 8,
                        padding: '10px 14px',
                        textAlign: 'left',
                        cursor: sentenceQuizAnswer === null ? 'pointer' : 'default',
                        fontWeight: isSelected ? 700 : 500,
                        fontSize: '0.92rem'
                      }}
                      onClick={() => handleSentenceQuizChoice(i)}
                    >
                      {opt} {sentenceQuizAnswer !== null && (isCorrect ? '✓' : isSelected ? '✗' : '')}
                    </button>
                  );
                })}
              </div>

              {sentenceQuizAnswer !== null && (
                <div style={{ marginTop: 12, fontSize: '0.875rem', color: '#4a044e' }}>
                  <strong>Açıklama:</strong> {currentSentence.interactive_question.rationale_tr}
                </div>
              )}
            </div>
          )}

          {/* Sentence Translation */}
          <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 14, marginBottom: 20 }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--learn-text-muted)' }}>
              TÜRKÇE ÇEVİRİ:
            </span>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.95rem', color: '#334155' }}>
              {currentSentence.translation_tr}
            </p>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="learn-btn learn-btn-primary"
              onClick={handleNextSentence}
            >
              {currentSentenceIdx < passage.sentences.length - 1
                ? 'Sonraki Cümleye Geç →'
                : 'Tüm Paragrafı ve Soruları İncele →'}
            </button>
          </div>
        </div>
      ) : (
        /* STEP 2: FULL PASSAGE REVIEW & COMPREHENSION */
        <div className="vocab-card-box">
          <span className="learn-pill learn-pill-teal">PARAGRAF BÜTÜNLÜĞÜ VE ANLAMA</span>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 800, margin: '12px 0 16px 0' }}>
            {passage.title}
          </h2>

          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              borderRadius: 12,
              padding: '20px 24px',
              fontSize: '1.1rem',
              lineHeight: 1.8,
              color: '#1e293b',
              marginBottom: 20
            }}
          >
            {passage.paragraph_text}
          </div>

          <div style={{ background: '#f0fdf4', padding: '14px 18px', borderRadius: 10, marginBottom: 24, border: '1px solid #bbf7d0' }}>
            <strong style={{ color: '#166534' }}>📌 PARAGRAFIN ANA FİKRİ (Main Idea):</strong>
            <p style={{ margin: '6px 0 0 0', fontSize: '0.95rem', color: '#14532d' }}>
              {passage.main_idea_tr}
            </p>
          </div>

          {/* Scaffold Questions */}
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: 16 }}>
            Paragraf Anlama Soruları
          </h3>

          <div style={{ display: 'grid', gap: 20, marginBottom: 28 }}>
            {passage.scaffold_questions.map((q, qIdx) => {
              const selectedOpt = passageQuizAnswers[qIdx];
              const isAnswered = selectedOpt !== undefined;

              return (
                <div key={qIdx} style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 10, padding: '18px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <span className="learn-pill learn-pill-blue">{q.type}</span>
                    <strong style={{ fontSize: '1rem', color: '#0f172a' }}>{q.prompt}</strong>
                  </div>

                  <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
                    {q.options.map((opt, optIdx) => {
                      const isSelected = selectedOpt === optIdx;
                      const isCorrect = optIdx === q.correct_index;

                      let bg = '#ffffff';
                      let bColor = '#cbd5e1';

                      if (isAnswered) {
                        if (isCorrect) {
                          bg = '#f0fdf4';
                          bColor = 'var(--learn-success)';
                        } else if (isSelected) {
                          bg = '#fef2f2';
                          bColor = 'var(--learn-danger)';
                        }
                      }

                      return (
                        <button
                          key={optIdx}
                          type="button"
                          style={{
                            background: bg,
                            border: `1.5px solid ${bColor}`,
                            borderRadius: 8,
                            padding: '10px 14px',
                            textAlign: 'left',
                            fontSize: '0.92rem',
                            cursor: isAnswered ? 'default' : 'pointer',
                            fontWeight: isSelected ? 700 : 500
                          }}
                          onClick={() => handlePassageQuizChoice(qIdx, optIdx)}
                        >
                          {opt} {isAnswered && (isCorrect ? '✓ Doğru' : isSelected ? '✗ Yanlış' : '')}
                        </button>
                      );
                    })}
                  </div>

                  {isAnswered && (
                    <div style={{ marginTop: 12, fontSize: '0.875rem', color: '#334155', background: '#f1f5f9', padding: '10px 14px', borderRadius: 6 }}>
                      <strong>Çözüm Gerekçesi:</strong> {q.explanation_tr}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <button
              type="button"
              className="learn-btn learn-btn-primary"
              onClick={handleFinishReading}
            >
              Okuma Öğretimini Tamamla ✓
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
