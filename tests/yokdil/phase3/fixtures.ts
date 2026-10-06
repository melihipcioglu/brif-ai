import { initialQuestions } from '../../../src/data/initialQuestions';
import { createAttemptDraft, submitQuestionAttempt } from '../../../src/services/questions/attempts';
import type { AttemptDraft } from '../../../src/services/questions/attempts';
import type { Question, QuestionAttempt } from '../../../src/types/question';
import type { SkillEvidence } from '../../../src/types/evidence';
import { EVIDENCE_DAY_MS } from '../../../src/services/evidence/calibration';

export const TIME = 30 * EVIDENCE_DAY_MS;
export function question(id = 'gap-vocab'): Question {
  const q = initialQuestions.find((item) => item.id === id);
  if (q === undefined) throw new Error(`Missing fixture ${id}`);
  return q;
}
export function attempt(id = 'a-1', correct = true, changes: Partial<AttemptDraft> = {}, q: Question = question()): QuestionAttempt {
  const wrong = q.options.find((o) => o.id !== q.correct_option);
  if (wrong === undefined) throw new Error('Missing wrong option');
  return submitQuestionAttempt(q, { ...createAttemptDraft(), confidence_level: 'HIGH', selected_option: correct ? q.correct_option : wrong.id, ...changes },
    { id, session_id: null, response_time_ms: 2_000, attempted_at: TIME });
}
export function fractionalAttempt(id = 'fractional', q: Question = question()): QuestionAttempt {
  return { ...attempt(id, false, {}, q), error_attribution: { probabilities: { VOCABULARY: 0.4, CARELESS: 0.6 }, primary_category: 'CARELESS', confidence: 0.3 } };
}
export function vocab(rows: readonly SkillEvidence[]): SkillEvidence {
  const row = rows.find((e) => e.skill_id === 'VOCAB_CONTEXT' && e.source === 'QUESTION_RESULT');
  if (row === undefined) throw new Error('Missing vocab result');
  return row;
}
