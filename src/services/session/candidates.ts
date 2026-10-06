import type { LexicalRecord } from '../../types/lexical';
import type { Question, QuestionAttempt } from '../../types/question';
import type { SessionCandidate, SessionConfig } from '../../types/session';
import { deepFreeze } from '../questions/attempts';
import { questionSchema, validateAttemptForQuestion } from '../questions/validation';
import { mapQuestionSkills } from '../evidence/mapping';
import { lexicalRecordSchema, timestampSchema } from '../validation';
import { PACING_V1, SESSION_V1 } from './calibration';
import { sessionCandidateSchema, sessionConfigSchema } from './validation';

export interface SessionContent {
  readonly questions: readonly Question[];
  readonly lexical_records: readonly LexicalRecord[];
  readonly attempts: readonly QuestionAttempt[];
}
export function validateSessionContent(input: SessionContent): SessionContent {
  const questions = input.questions.map((q) => questionSchema.parse(q));
  const words = input.lexical_records.map((w) => lexicalRecordSchema.parse(w));
  const bank = new Map(questions.map((q) => [q.id, q]));
  if (bank.size !== questions.length || new Set(words.map((w) => w.word_id)).size !== words.length || new Set(input.attempts.map((a) => a.id)).size !== input.attempts.length) throw new RangeError('Duplicate catalog IDs');
  const attempts = input.attempts.map((a) => {
    const q = bank.get(a.question_id); if (q === undefined) throw new RangeError('Unknown attempt question');
    return validateAttemptForQuestion(a, q);
  });
  return { questions, lexical_records: words, attempts };
}
function estimateQuestion(q: Question, attempts: readonly QuestionAttempt[], config: SessionConfig): number {
  const direct = attempts.filter((a) => a.question_id === q.id && a.response_time_ms > 0);
  const family = attempts.filter((a) => a.family === q.family && a.response_time_ms > 0);
  const sample = direct.length >= config.speed_min_samples ? direct : family;
  if (sample.length >= config.speed_min_samples) {
    const times = sample.map((a) => a.response_time_ms).sort((a, b) => a - b);
    return Math.max(1, Math.min(10, (times[Math.floor(times.length / 2)] ?? 120_000) / 60_000));
  }
  return Math.max(1, Math.min(10, (q.personal_benchmark_ms ?? q.global_benchmark_ms ?? config.question_default_minutes * 60_000) / 60_000));
}

/** Concrete resources only. Per-question variants share resource IDs and cannot all enter one plan. */
export function buildSessionCandidatePool(content: SessionContent, asOf: number, timedEnabled = false, config: SessionConfig = SESSION_V1): readonly SessionCandidate[] {
  timestampSchema.parse(asOf); const c = sessionConfigSchema.parse(config); const source = validateSessionContent(content);
  if (source.attempts.some((a) => a.attempted_at > asOf)) throw new RangeError('Future attempt in speed history');
  const rows: SessionCandidate[] = [];
  const ordered = [...source.questions].sort((a, b) => a.id < b.id ? -1 : 1);
  ordered.forEach((q, index) => {
    const heavy = ['READING_COMPREHENSION', 'TRANSLATION_ENG_TR', 'TRANSLATION_TR_ENG', 'PARAGRAPH_COMPLETION'].includes(q.family);
    const types = ['DIAGNOSTIC', 'TARGETED_PRACTICE', ...(source.attempts.some((a) => a.question_id === q.id) ? ['RETENTION_REVIEW' as const] : [])] as const;
    for (const type of types) rows.push({ id: `question-${index}-${type}`, type, available: true,
      expected_minutes: estimateQuestion(q, source.attempts, c), cognitive_load: heavy ? 'HIGH' : 'MEDIUM',
      targets: mapQuestionSkills(q).map((m) => ({ skill_id: m.skill_id, weight: m.weight })), question_ids: [q.id], lexical_ids: [], timed_enabled: false });
  });
  [...source.lexical_records].sort((a, b) => a.word_id < b.word_id ? -1 : 1).forEach((word, index) => {
    if (word.next_review_date > asOf || word.encounter_count === 0) return;
    rows.push({ id: `lexical-${index}`, type: 'LEXICAL_REVIEW', available: true,
      expected_minutes: word.response_time_avg_ms > 0 ? Math.max(1 / 6, Math.min(2, word.response_time_avg_ms / 60_000)) : c.lexical_default_minutes,
      cognitive_load: 'LOW', targets: [{ skill_id: 'VOCAB_CONTEXT', weight: 1 }], question_ids: [], lexical_ids: [word.word_id], timed_enabled: false });
  });
  if (timedEnabled) {
    // Minimum block qualification is not a session question-count quota.
    for (let offset = 0; offset + PACING_V1.min_questions <= ordered.length; offset += PACING_V1.min_questions) {
      const group = ordered.slice(offset, offset + PACING_V1.min_questions);
      rows.push({ id: `timed-${offset}`, type: 'TIMED_BLOCK', available: true, cognitive_load: 'HIGH',
        expected_minutes: group.reduce((sum, q) => sum + estimateQuestion(q, source.attempts, c), 0),
        targets: [{ skill_id: 'PACING_STAMINA', weight: 1 }], question_ids: group.map((q) => q.id), lexical_ids: [], timed_enabled: true });
    }
  }
  return deepFreeze(rows.map((r) => sessionCandidateSchema.parse(r)));
}
