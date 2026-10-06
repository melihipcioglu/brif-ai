import type { LearnerSkillVector, SkillId } from '../../types/learner';
import type { PriorityContext, TrainingAction } from '../../types/priority';
import type { PlannedSessionBlock, SessionCandidate, SessionConfig, SessionMode, SessionPlan } from '../../types/session';
import { deepFreeze } from '../questions/attempts';
import { calculateReviewPriority } from '../lexicalScheduler';
import { planNextBestAction } from '../priority/nextBestAction';
import { idSchema } from '../validation';
import { PACING_V1, SESSION_V1 } from './calibration';
import { validateSessionContent, type SessionContent } from './candidates';
import { sessionCandidateSchema, sessionConfigSchema, sessionPlanSchema } from './validation';

export interface SessionPlanningRequest {
  readonly id: string;
  readonly session_id: string;
  readonly mode: SessionMode;
  readonly available_minutes?: number | undefined;
  readonly used_candidate_ids?: readonly string[] | undefined;
  readonly used_question_ids?: readonly string[] | undefined;
  readonly used_lexical_ids?: readonly string[] | undefined;
}
interface Valued { candidate: SessionCandidate; value: number; explanation: string; families: readonly string[] }

/** Deterministic constrained selection: lexical reserve, exploration, family coverage, then guarded value. */
export function planDailySession(request: SessionPlanningRequest, learner: LearnerSkillVector, candidates: readonly SessionCandidate[], content: SessionContent,
  context: PriorityContext, config: SessionConfig = SESSION_V1): SessionPlan {
  idSchema.parse(request.id); idSchema.parse(request.session_id);
  const c = sessionConfigSchema.parse(config);
  const budget = request.available_minutes ?? c.mode_minutes[request.mode];
  if (!Number.isFinite(budget) || budget <= 0 || budget > 180) throw new RangeError('Invalid session time budget');
  const source = validateSessionContent(content);
  const bank = new Map(source.questions.map((q) => [q.id, q]));
  const words = new Map(source.lexical_records.map((w) => [w.word_id, w]));
  const input = candidates.map((candidate) => sessionCandidateSchema.parse(candidate));
  if (new Set(input.map((x) => x.id)).size !== input.length) throw new RangeError('Duplicate candidate IDs');
  const usedCandidates = new Set(request.used_candidate_ids ?? []), usedQuestions = new Set(request.used_question_ids ?? []), usedWords = new Set(request.used_lexical_ids ?? []);
  const real = input.filter((candidate) => candidate.available && !usedCandidates.has(candidate.id) &&
    candidate.question_ids.every((id) => bank.has(id) && !usedQuestions.has(id)) && candidate.lexical_ids.every((id) => {
      const word = words.get(id); return word !== undefined && word.encounter_count > 0 && word.next_review_date <= context.as_of && !usedWords.has(id);
    }) && (candidate.type !== 'TIMED_BLOCK' || candidate.question_ids.length >= PACING_V1.min_questions));
  const questionActions: TrainingAction[] = real.filter((x) => !['LEXICAL_REVIEW', 'REFLECTION'].includes(x.type)).map((x) => ({
    id: x.id, title: x.id, kind: x.type === 'TIMED_BLOCK' ? 'DIAGNOSTIC' : x.type as TrainingAction['kind'],
    format: x.type === 'TIMED_BLOCK' ? 'TIMED_BLOCK' : x.question_ids.length === 1 ? 'SINGLE_QUESTION' : 'QUESTION_SET',
    available: true, expected_minutes: x.expected_minutes, targets: x.targets,
  }));
  const nba = planNextBestAction(learner, questionActions, context, budget);
  const valued = new Map(nba.ranked_actions.map((r) => [r.action.id, r]));
  const pool: Valued[] = real.flatMap((candidate) => {
    const families = [...new Set(candidate.question_ids.map((id) => bank.get(id)?.family ?? ''))];
    if (candidate.type === 'LEXICAL_REVIEW') return [{ candidate, families, value: Math.max(...candidate.lexical_ids.map((id) => calculateReviewPriority(words.get(id)!, context.as_of))), explanation: 'Tekrar zamanı gelen kelime; gerçek hatırlama yanıtı tamamlanınca kaydedilir.' }];
    if (candidate.type === 'REFLECTION') return [{ candidate, families, value: 0.01, explanation: candidate.reflection_prompt ?? 'Kısa değerlendirme.' }];
    const item = valued.get(candidate.id);
    return item === undefined ? [] : [{ candidate, families, value: item.expected_training_value, explanation: item.explanation }];
  });
  pool.sort((a, b) => b.value - a.value || (a.candidate.id < b.candidate.id ? -1 : 1));
  const chosen: Valued[] = []; let spent = 0, lexical = 0, diagnostic = 0;
  const skillMinutes = new Map<SkillId, number>(); const families = new Set<string>(); const notes: string[] = [];
  const diagnosticCap = budget * (Object.values(learner).every((m) => m.evidence_count === 0) ? c.cold_start_diagnostic_fraction : c.diagnostic_fraction);
  const isDiagnostic = (x: Valued): boolean => x.candidate.type === 'DIAGNOSTIC' || x.candidate.type === 'TIMED_BLOCK';
  const fits = (x: Valued): boolean => !usedCandidates.has(x.candidate.id) && spent + x.candidate.expected_minutes <= budget + 1e-9 &&
    !x.candidate.question_ids.some((id) => usedQuestions.has(id)) && !x.candidate.lexical_ids.some((id) => usedWords.has(id)) &&
    (x.candidate.type !== 'LEXICAL_REVIEW' || lexical + x.candidate.expected_minutes <= budget * c.lexical_reserve_fraction + 1e-9) &&
    (!isDiagnostic(x) || diagnostic + x.candidate.expected_minutes <= diagnosticCap + 1e-9);
  const add = (x: Valued): void => {
    chosen.push(x); spent += x.candidate.expected_minutes; usedCandidates.add(x.candidate.id);
    x.candidate.question_ids.forEach((id) => usedQuestions.add(id)); x.candidate.lexical_ids.forEach((id) => usedWords.add(id));
    x.families.forEach((f) => families.add(f));
    if (x.candidate.type === 'LEXICAL_REVIEW') lexical += x.candidate.expected_minutes;
    if (isDiagnostic(x)) diagnostic += x.candidate.expected_minutes;
    for (const t of x.candidate.targets) skillMinutes.set(t.skill_id, (skillMinutes.get(t.skill_id) ?? 0) + x.candidate.expected_minutes * t.weight);
  };
  for (const x of pool.filter((x) => x.candidate.type === 'LEXICAL_REVIEW')) if (fits(x)) add(x);
  const exploratory = pool.find((x) => isDiagnostic(x) && fits(x) && x.candidate.targets.some((t) => {
    const row = nba.score_leak_map.skills.find((r) => r.skill_id === t.skill_id); return row !== undefined && (row.uncertainty >= 0.5 || row.coverage_index < 0.5);
  }));
  if (exploratory) add(exploratory);
  while (families.size < c.family_coverage_floor) {
    const next = pool.find((x) => fits(x) && x.families.some((f) => !families.has(f)));
    if (!next) break; add(next);
  }
  while (true) {
    const possible = pool.filter(fits); if (possible.length === 0) break;
    const diverse = possible.filter((x) => x.candidate.targets.every((t) => (skillMinutes.get(t.skill_id) ?? 0) + x.candidate.expected_minutes * t.weight <= budget * c.max_single_skill_fraction + 1e-9));
    const highCount = chosen.filter((x) => x.candidate.cognitive_load === 'HIGH').length;
    const needsLighter = highCount >= (chosen.length - highCount + 1) * c.max_consecutive_high;
    const lighter = needsLighter ? (diverse.find((x) => x.candidate.cognitive_load !== 'HIGH') ?? possible.find((x) => x.candidate.cognitive_load !== 'HIGH')) : undefined;
    const next = lighter ?? diverse[0] ?? possible[0]; if (next === undefined) break;
    if (diverse.length === 0 && !notes.includes('Uygun alternatif kalmadığı için beceri tekrar sınırı esnetildi.')) notes.push('Uygun alternatif kalmadığı için beceri tekrar sınırı esnetildi.');
    add(next);
  }
  // Order independently of reservation: medium entry, heavy middle with available lighter separators.
  const remaining = [...chosen]; const ordered: Valued[] = []; let highStreak = 0;
  while (remaining.length > 0) {
    const highCount = remaining.filter((x) => x.candidate.cognitive_load === 'HIGH').length;
    const mustStartHeavy = ordered.length === 0 && highCount > (remaining.length - highCount) * c.max_consecutive_high;
    const preference = [...remaining].sort((a, b) => {
      if (c.ordering === 'MEDIUM_FIRST_LIGHT_FINISH') {
        const stage = (x: Valued): number => ordered.length === 0 && x.candidate.cognitive_load === (mustStartHeavy ? 'HIGH' : 'MEDIUM') ? -1 : ['LEXICAL_REVIEW', 'RETENTION_REVIEW', 'REFLECTION'].includes(x.candidate.type) ? 1 : 0;
        const delta = stage(a) - stage(b); if (delta) return delta;
      }
      return b.value - a.value || (a.candidate.id < b.candidate.id ? -1 : 1);
    });
    const next = (highStreak >= c.max_consecutive_high ? preference.find((x) => x.candidate.cognitive_load !== 'HIGH') : undefined) ?? preference[0];
    if (!next) break;
    highStreak = next.candidate.cognitive_load === 'HIGH' ? highStreak + 1 : 0;
    ordered.push(next); remaining.splice(remaining.indexOf(next), 1);
  }
  const blocks: PlannedSessionBlock[] = ordered.map((x, index) => ({ id: `${request.session_id}/${request.id}/block/${index}`, type: x.candidate.type,
    target_skills: x.candidate.targets.map((t) => t.skill_id), planned_minutes: x.candidate.expected_minutes,
    candidate_ids: [x.candidate.id], question_ids: x.candidate.question_ids, lexical_ids: x.candidate.lexical_ids,
    cognitive_load: x.candidate.cognitive_load, timed_enabled: x.candidate.timed_enabled, explanation: x.explanation }));
  if (families.size < c.family_coverage_floor) notes.push('Bütçe ve kullanılabilir içerik içinde hedeflenen aile çeşitliliğine ulaşılamadı.');
  if (spent < budget - 1e-9) notes.push('Uygun içerik ve sınırlar nedeniyle bütçenin bir kısmı boş bırakıldı.');
  return deepFreeze(sessionPlanSchema.parse({ id: request.id, session_id: request.session_id, mode: request.mode, created_at: context.as_of,
    planned_minutes: budget, allocated_minutes: spent, blocks, notes, config: c }));
}
