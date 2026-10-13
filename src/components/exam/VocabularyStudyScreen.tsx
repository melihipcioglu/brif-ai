import { useState } from 'react';
import { createInitialVocab } from '../../data/initialVocab';
import type { LexicalRecord } from '../../types/lexical';

type TierFilter = 'ALL' | 1 | 2 | 3;

export function VocabularyStudyScreen() {
  const [vocab] = useState<readonly LexicalRecord[]>(() => createInitialVocab());
  const [tierFilter, setTierFilter] = useState<TierFilter>('ALL');
  const [search, setSearch] = useState('');

  const filtered = vocab.filter((w) => {
    if (tierFilter !== 'ALL' && w.tier !== tierFilter) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      const matchLemma = w.lemma.toLowerCase().includes(q);
      const matchTr = w.exam_meaning_tr.toLowerCase().includes(q);
      if (!matchLemma && !matchTr) return false;
    }
    return true;
  });

  return (
    <div className="exam-card">
      <h1 className="exam-card-title">YÖKDİL Fen Bilimleri Kelime Çalışması</h1>
      <p className="exam-card-desc">
        Sınavda en sık karşılaşılan akademik fen terimleri, bağlam odaklı eş anlamlılar ve Türkçe karşılıkları:
      </p>

      {/* Filter and Search Bar */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '20px' }}>
        <input
          type="search"
          placeholder="Kelime veya Türkçe anlam ara..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            padding: '8px 14px',
            border: '1px solid var(--yokdil-border)',
            borderRadius: 'var(--yokdil-radius)',
            fontSize: '0.875rem',
            minWidth: '220px',
            flex: 1
          }}
        />

        <div style={{ display: 'flex', gap: '6px' }}>
          {(['ALL', 1, 2, 3] as const).map((t) => (
            <button
              key={String(t)}
              type="button"
              className={`exam-btn exam-btn-sm ${tierFilter === t ? 'exam-btn-primary' : 'exam-btn-secondary'}`}
              onClick={() => setTierFilter(t)}
            >
              {t === 'ALL' ? 'Tümü' : `Tier ${t}`}
            </button>
          ))}
        </div>
      </div>

      <p style={{ fontSize: '0.8125rem', color: 'var(--yokdil-text-muted)', marginBottom: '16px' }}>
        Toplam <strong>{filtered.length}</strong> akademik kelime listeleniyor.
      </p>

      {/* Word Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
        {filtered.map((item) => (
          <div
            key={item.word_id}
            style={{
              border: '1px solid var(--yokdil-border)',
              borderRadius: 'var(--yokdil-radius)',
              padding: '16px',
              backgroundColor: '#ffffff'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '6px' }}>
              <span style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--yokdil-primary)' }}>
                {item.lemma}
              </span>
              <span className="exam-brand-badge">Tier {item.tier}</span>
            </div>

            <div style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
              {item.exam_meaning_tr}
            </div>

            {item.critical_collocations && item.critical_collocations.length > 0 && (
              <div style={{ fontSize: '0.75rem', color: 'var(--yokdil-text-muted)', marginBottom: '4px' }}>
                <strong>Kalıplar:</strong> {item.critical_collocations.map((c) => c.phrase).join(' · ')}
              </div>
            )}

            {item.exam_sentence && (
              <div style={{ fontSize: '0.75rem', color: '#475569', fontStyle: 'italic', marginTop: '6px', borderTop: '1px dashed var(--yokdil-border)', paddingTop: '6px' }}>
                "{item.exam_sentence}"
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
