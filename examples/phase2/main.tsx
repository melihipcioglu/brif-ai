import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createInitialVocab } from '../../src/data/initialVocab';
import { initialQuestions, QuestionSolver, persistQuestionAttempt, QuestionDatabase } from '../../src/questions';
import { seedInitialVocabulary } from '../../src/services/db';
import type { LexicalRecord } from '../../src/types/lexical';

const demoDatabase = new QuestionDatabase('yokdil-fen-phase2-demo');

function Demo({ words }: { readonly words: readonly LexicalRecord[] }) {
  const [index, setIndex] = useState(0);
  const question = initialQuestions[index];
  if (question === undefined) return <p>Alıştırma bulunamadı.</p>;
  return <main style={{ padding: '24px 12px' }}>
    <nav aria-label="Alıştırma seçimi" style={{ maxWidth: 850, margin: '0 auto 16px', fontFamily: 'system-ui' }}>
      <label>Özgün alıştırma: <select style={{ display: 'block', width: '100%', padding: 10 }} value={index} onChange={(event) => setIndex(Number(event.target.value))}>
        {initialQuestions.map((q, i) => <option key={q.id} value={i}>{i + 1} · {q.science_domain} · {q.stem.slice(0, 65)}</option>)}
      </select></label>
    </nav>
    <QuestionSolver question={question} words={words} saveAttempt={(attempt, q) => persistQuestionAttempt(attempt, q, demoDatabase)} />
  </main>;
}
const root = document.getElementById('root');
if (root === null) throw new Error('Missing application root');
const app = createRoot(root);
async function start(): Promise<void> {
  try {
    await seedInitialVocabulary(demoDatabase);
    app.render(<Demo words={await demoDatabase.lexical_store.toArray()} />);
  } catch {
    // Solving stays available; the component reports any failed attempt persistence.
    app.render(<Demo words={createInitialVocab()} />);
  }
}
void start();
