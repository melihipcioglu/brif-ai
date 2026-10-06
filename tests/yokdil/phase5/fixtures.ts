import { initialQuestions } from '../../../src/data/initialQuestions';
import { createInitialVocab } from '../../../src/data/initialVocab';
import { recordEncounter } from '../../../src/services/lexicalScheduler';
import { createAttemptDraft, submitQuestionAttempt } from '../../../src/services/questions/attempts';
import type { Question } from '../../../src/types/question';
import type { SessionCandidate, SessionPlan } from '../../../src/types/session';
import { SESSION_V1 } from '../../../src/services/session/calibration';

export const NOW = 10_000_000;
export function q(index = 0): Question { const value = initialQuestions[index]; if (!value) throw new Error('Missing fixture'); return value; }
export const dueWords = () => createInitialVocab(0).map((w) => recordEncounter(w, 'initial-context', 1));
export function candidate(id: string, question: Question, skill: SessionCandidate['targets'][number]['skill_id'], type: SessionCandidate['type'] = 'TARGETED_PRACTICE', minutes = 2): SessionCandidate {
  return { id, type, available: true, expected_minutes: minutes, cognitive_load: 'MEDIUM', targets: [{ skill_id: skill, weight: 1 }], question_ids: [question.id], lexical_ids: [], timed_enabled: false };
}
export function simplePlan(type: SessionPlan['blocks'][number]['type'] = 'TARGETED_PRACTICE', count = 1, id = 'session'): SessionPlan {
  return { id, session_id: id, mode: 'NORMAL', created_at: 0, planned_minutes: 10, allocated_minutes: 5,
    config: SESSION_V1, notes: [], blocks: [{ id: `${id}/b`, type, planned_minutes: 5, target_skills: type === 'TIMED_BLOCK' ? ['PACING_STAMINA'] : ['VOCAB_CONTEXT'], candidate_ids: ['c'],
      question_ids: type === 'REFLECTION' || type === 'LEXICAL_REVIEW' ? [] : initialQuestions.slice(0, count).map((x) => x.id),
      lexical_ids: type === 'LEXICAL_REVIEW' ? ['inhibit'] : [], cognitive_load: 'MEDIUM', timed_enabled: type === 'TIMED_BLOCK', explanation: 'Çalışma etkinliği.' }] };
}
export function actual(question: Question, id: string, at: number, correct = true, hints = 0, response = 20_000) {
  const wrong = question.options.find((x) => x.id !== question.correct_option);
  if (!wrong) throw new Error('Missing distractor');
  return submitQuestionAttempt(question, { ...createAttemptDraft(), selected_option: correct ? question.correct_option : wrong.id, hints_used_count: hints },
    { id, session_id: null, attempted_at: at, response_time_ms: response });
}
