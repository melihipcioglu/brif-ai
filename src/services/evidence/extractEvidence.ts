import type { EvidenceContext, SkillEvidence } from '../../types/evidence';
import type { Question, QuestionAttempt } from '../../types/question';
import { deepFreeze } from '../questions/attempts';
import { tacticalSolvers } from '../questions/strategies';
import { questionSchema, validateAttemptForQuestion } from '../questions/validation';
import { CONFIDENCE_QUALITY_V1, EVIDENCE_DAY_MS, EVIDENCE_V1 as C } from './calibration';
import { allocateAttribution, mapQuestionSkills, primaryQuestionSkill } from './mapping';
import { evidenceContextSchema, evidenceId, skillEvidenceSchema } from './validation';

/** Pure extraction: explicit telemetry only. The v1 attribution distribution is a weighting signal. */
export function extractSkillEvidence(question: Question, attempt: QuestionAttempt, context: EvidenceContext = {}): readonly SkillEvidence[] {
  const q = questionSchema.parse(question);
  const a = validateAttemptForQuestion(attempt, q);
  const ctx = evidenceContextSchema.parse(context);
  if (ctx.identified_relation !== undefined && ctx.identified_relation.recorded_at > a.attempted_at) throw new RangeError('Relation response must precede submission');
  if (ctx.transfer !== undefined && ctx.transfer.prior_practice_at > a.attempted_at) throw new RangeError('Prior practice cannot be in the future');
  const assisted = a.hints_used_count > 0 || a.words_clicked.length > 0;
  const transfer = !assisted && ctx.transfer?.unseen === true && ctx.transfer.exam_like &&
    a.attempted_at - ctx.transfer.prior_practice_at >= C.transfer_delay_days * EVIDENCE_DAY_MS;
  const mapping = mapQuestionSkills(q);
  const attribution = allocateAttribution(q, mapping, a.error_attribution?.probabilities ?? {});
  const solver = tacticalSolvers[q.family];
  const validEliminations = a.eliminated_options.filter((o) => o !== q.correct_option && o !== a.selected_option &&
    solver.verify(q, o, { eliminated_options: [] }).verdict === 'REJECTED').length;
  const eliminatesCorrect = a.eliminated_options.includes(q.correct_option);
  const eliminationQuality = eliminatesCorrect ? 0 : validEliminations / 4;
  const benchmark = q.personal_benchmark_ms ?? q.global_benchmark_ms;
  const timing = benchmark === undefined || a.response_time_ms <= benchmark ? 1 : Math.max(C.slow_floor, benchmark / a.response_time_ms);
  const assistance = assisted ? C.assisted_factor : 1;
  const process = assistance / (1 + C.hint_penalty * a.hints_used_count) /
    (1 + C.word_penalty * a.words_clicked.length) / (1 + C.change_penalty * a.option_change_count);
  const positive = C.correct_base * process * (C.difficulty_floor + C.difficulty_range * (q.difficulty ?? C.default_difficulty)) *
    timing * CONFIDENCE_QUALITY_V1[a.confidence_level ?? 'UNSET'] * (C.elimination_floor + (1 - C.elimination_floor) * eliminationQuality);
  const common = {
    extractor_version: 'v1' as const, attempt_id: a.id, question_id: a.question_id, session_id: a.session_id,
    question_family: a.family, evidence_kind: transfer ? 'TRANSFER' as const : 'PRACTICE' as const,
    transfer_level: transfer ? 1 : 0, assisted, outcome_correct: a.is_correct,
    ...(q.difficulty === undefined ? {} : { difficulty: q.difficulty }),
    ...(transfer ? { transfer_context: ctx.transfer } : {}), created_at: a.attempted_at,
  };
  const reliability = transfer ? C.transfer_reliability : C.practice_reliability;
  const rows: SkillEvidence[] = mapping.map((m) => {
    const weight = a.is_correct ? 0 : attribution.get(m.skill_id) ?? 0;
    return {
      ...common, id: evidenceId(a.id, m.skill_id, 'QUESTION_RESULT'), skill_id: m.skill_id,
      source: 'QUESTION_RESULT', mapping_weight: m.weight, attribution_weight: weight,
      direction: a.is_correct ? 'POSITIVE' : weight > 0 ? 'NEGATIVE' : 'NEUTRAL',
      strength: a.is_correct ? positive * m.weight : C.incorrect_base * assistance * weight * m.weight,
      reliability: a.is_correct ? reliability : reliability * (C.attribution_reliability_floor + C.attribution_reliability_range * (a.error_attribution?.confidence ?? 0)),
    };
  });
  const tactical = new Map<SkillEvidence['skill_id'], number>();
  // Strikeouts alone do not establish a specific reasoning skill. Award only weak primary-task evidence.
  if (!eliminatesCorrect && validEliminations >= 3) tactical.set(primaryQuestionSkill(q), C.elimination_strength);
  if (ctx.identified_relation !== undefined && 'relation' in q.tactical && ctx.identified_relation.relation === q.tactical.relation) {
    tactical.set('CONNECTOR_DISCOURSE', C.relation_strength);
  }
  for (const [skill_id, strength] of tactical) {
    const weight = mapping.find((m) => m.skill_id === skill_id)?.weight;
    if (weight === undefined) continue;
    rows.push({ ...common, id: evidenceId(a.id, skill_id, 'TACTICAL_DECISION'), skill_id, source: 'TACTICAL_DECISION',
      direction: 'POSITIVE', mapping_weight: weight, strength: strength * weight * process,
      reliability: C.tactical_reliability * (transfer ? C.transfer_reliability / C.practice_reliability : 1) });
  }
  return deepFreeze(rows.map((row) => skillEvidenceSchema.parse(row)));
}
