import { useState } from 'react';
import type { OptionId } from '../../types/question';

export interface QuestionPaletteProps {
  readonly totalQuestions: number;
  readonly currentIndex: number;
  readonly answers: Record<string, OptionId | null>;
  readonly questionIds: readonly string[];
  readonly flaggedQuestionIds: readonly string[];
  readonly onSelectQuestion: (index: number) => void;
}

type PaletteFilter = 'ALL' | 'ANSWERED' | 'BLANK' | 'FLAGGED';

export function QuestionPalette({
  totalQuestions,
  currentIndex,
  answers,
  questionIds,
  flaggedQuestionIds,
  onSelectQuestion
}: QuestionPaletteProps) {
  const [filter, setFilter] = useState<PaletteFilter>('ALL');

  const flaggedSet = new Set(flaggedQuestionIds);

  const answeredIndices: number[] = [];
  const blankIndices: number[] = [];
  const flaggedIndices: number[] = [];

  for (let i = 0; i < totalQuestions; i++) {
    const qId = questionIds[i]!;
    const isAnswered = answers[qId] !== null && answers[qId] !== undefined;
    const isFlagged = flaggedSet.has(qId);

    if (isAnswered) answeredIndices.push(i);
    else blankIndices.push(i);

    if (isFlagged) flaggedIndices.push(i);
  }

  const visibleIndices: number[] = [];
  for (let i = 0; i < totalQuestions; i++) {
    const qId = questionIds[i]!;
    const isAnswered = answers[qId] !== null && answers[qId] !== undefined;
    const isFlagged = flaggedSet.has(qId);

    if (filter === 'ALL') visibleIndices.push(i);
    else if (filter === 'ANSWERED' && isAnswered) visibleIndices.push(i);
    else if (filter === 'BLANK' && !isAnswered) visibleIndices.push(i);
    else if (filter === 'FLAGGED' && isFlagged) visibleIndices.push(i);
  }

  return (
    <nav className="palette-container" aria-label="Soru paleti ve gezinme">
      <div className="palette-header">
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', fontSize: '0.875rem' }}>
          <span style={{ fontWeight: 600 }}>Soru Paleti:</span>
          <span style={{ color: 'var(--yokdil-success)' }}>{answeredIndices.length} Cevaplandı</span>
          <span style={{ color: 'var(--yokdil-text-muted)' }}>{blankIndices.length} Boş</span>
          {flaggedIndices.length > 0 && (
            <span style={{ color: 'var(--yokdil-warning)' }}>{flaggedIndices.length} İşaretli</span>
          )}
        </div>

        <div className="palette-filters" role="tablist" aria-label="Filtreleme seçenekleri">
          <button
            type="button"
            className={`palette-filter-btn ${filter === 'ALL' ? 'is-active' : ''}`}
            onClick={() => setFilter('ALL')}
            aria-selected={filter === 'ALL'}
          >
            Tümü ({totalQuestions})
          </button>
          <button
            type="button"
            className={`palette-filter-btn ${filter === 'ANSWERED' ? 'is-active' : ''}`}
            onClick={() => setFilter('ANSWERED')}
            aria-selected={filter === 'ANSWERED'}
          >
            Cevaplanan ({answeredIndices.length})
          </button>
          <button
            type="button"
            className={`palette-filter-btn ${filter === 'BLANK' ? 'is-active' : ''}`}
            onClick={() => setFilter('BLANK')}
            aria-selected={filter === 'BLANK'}
          >
            Boş ({blankIndices.length})
          </button>
          <button
            type="button"
            className={`palette-filter-btn ${filter === 'FLAGGED' ? 'is-active' : ''}`}
            onClick={() => setFilter('FLAGGED')}
            aria-selected={filter === 'FLAGGED'}
          >
            İşaretli ({flaggedIndices.length})
          </button>
        </div>
      </div>

      <div className="palette-grid" role="list">
        {visibleIndices.map((i) => {
          const qId = questionIds[i]!;
          const isCurrent = i === currentIndex;
          const isAnswered = answers[qId] !== null && answers[qId] !== undefined;
          const isFlagged = flaggedSet.has(qId);

          let className = 'palette-item';
          if (isCurrent) className += ' is-current';
          if (isAnswered) className += ' is-answered';
          if (isFlagged) className += ' is-flagged';

          return (
            <button
              key={qId}
              type="button"
              className={className}
              onClick={() => onSelectQuestion(i)}
              aria-label={`Soru ${i + 1}${isAnswered ? ', cevaplandı' : ', boş'}${isFlagged ? ', işaretlendi' : ''}${isCurrent ? ', mevcut' : ''}`}
              aria-current={isCurrent ? 'true' : undefined}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
