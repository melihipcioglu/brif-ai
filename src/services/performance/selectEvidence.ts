import { z } from 'zod';
import type { PerformanceEvidence, PerformanceEvidenceSet, PerformanceExclusion, PerformanceSnapshot, PerformanceSource } from '../../types/performance';
import type { QuestionAttempt } from '../../types/question';
import { canonicalEvidence, evidenceRunSchema, skillEvidenceSchema } from '../evidence/validation';
import { extractSkillEvidence } from '../evidence/extractEvidence';
import { primaryQuestionSkill } from '../evidence/mapping';
import { deepFreeze } from '../questions/attempts';
import { questionAttemptSchema, questionSchema, validateAttemptForQuestion } from '../questions/validation';
import { lexicalAttemptSchema, timestampSchema } from '../validation';
import { projectAdaptiveSession } from '../session/execution';
import { deriveTimedBlockResult, extractPacingBlockEvidence, pacingBlockEvidenceSchema } from '../session/pacing';
import { sessionEventSchema, sessionPlanSchema } from '../session/validation';
import { PERFORMANCE_V1 } from './calibration';

export const performanceSourceSchema: z.ZodType<PerformanceSource> = z.strictObject({
  kind: z.enum(['USER_EXECUTION', 'IMPORTED_USER_EXECUTION', 'DEMO', 'SYNTHETIC', 'UNKNOWN']), reference: z.string().min(1).max(500),
});
const compare = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;
const normalized = (s: string): string => s.normalize('NFKC').toLowerCase().replace(/\s+/gu, ' ').trim();

/** Replays Phase 5; never accepts a detached qualified=true flag, score, or learner snapshot. */
export function selectPerformanceEvidence(input: PerformanceSnapshot): PerformanceEvidenceSet {
  const source = performanceSourceSchema.parse(input.source);
  timestampSchema.parse(input.as_of);
  const exclusions: PerformanceExclusion[] = [];
  const exclude = (kind: PerformanceExclusion['kind'], id: string, reason: PerformanceExclusion['reason']): void => { exclusions.push({ kind, id, reason }); };
  const finish = (records: readonly PerformanceEvidence[], integrity: PerformanceEvidenceSet['integrity']): PerformanceEvidenceSet => deepFreeze({
    records: [...records].sort((a, b) => a.attempted_at - b.attempted_at || compare(a.attempt_id, b.attempt_id)), integrity,
    exclusions: [...new Map(exclusions.map((e) => [canonicalEvidence(e), e])).values()].sort((a, b) => compare(canonicalEvidence(a), canonicalEvidence(b))),
  });
  for (const id of input.lexical_attempt_ids) exclude('ATTEMPT', id, 'LEXICAL_ATTEMPT');
  if (source.kind !== 'USER_EXECUTION' && source.kind !== 'IMPORTED_USER_EXECUTION') {
    exclude('SOURCE', source.reference, 'UNTRUSTED_SOURCE'); return finish([], 'VALID');
  }
  // Conflicting or malformed source history fails closed as a whole: dropping bad answers could bias accuracy.
  try {
    function unique<T>(rows: readonly unknown[], parse: (row: unknown) => T, key: (row: T) => string): Map<string, T> {
      const map = new Map<string, T>();
      for (const raw of rows) {
        const row = parse(raw), id = key(row), previous = map.get(id);
        if (previous !== undefined) {
          if (canonicalEvidence(previous) !== canonicalEvidence(row)) throw new RangeError('Conflicting duplicate record');
          exclude('RECORD', id, 'DUPLICATE');
        } else map.set(id, row);
      }
      return map;
    }
    const questions = unique(input.questions, (q) => questionSchema.parse(q), (q) => q.id);
    const questionInputs = input.attempts.filter((raw) => {
      const lexical = lexicalAttemptSchema.safeParse(raw);
      if (!lexical.success) return true;
      exclude('ATTEMPT', lexical.data.id, 'LEXICAL_ATTEMPT'); return false;
    });
    const attempts = unique(questionInputs, (raw) => {
      const a = questionAttemptSchema.parse(raw), q = questions.get(a.question_id);
      if (!q || a.attempted_at > input.as_of) throw new RangeError('Missing catalog or future attempt');
      return validateAttemptForQuestion(a, q);
    }, (a) => a.id);
    const plans = unique(input.plans, (p) => sessionPlanSchema.parse(p), (p) => p.session_id);
    const events = unique(input.events, (e) => sessionEventSchema.parse(e), (e) => e.id);
    const results = unique(input.timed_results, (r) => { z.object({ block_id: z.string() }).parse(r); return r; }, (r) => z.object({ block_id: z.string() }).parse(r).block_id);
    const pacing = unique(input.pacing_evidence, (e) => pacingBlockEvidenceSchema.parse(e), (e) => e.id);
    const runs = unique(input.evidence_runs, (r) => evidenceRunSchema.parse(r), (r) => r.attempt_id);
    const evidence = unique(input.skill_evidence, (e) => skillEvidenceSchema.parse(e), (e) => e.id);
    const expectedEvidenceIds = new Set<string>();
    const transferAttempts = new Set<string>();
    for (const run of runs.values()) {
      const a = attempts.get(run.attempt_id), q = questions.get(run.question_id);
      if (!a || !q) throw new RangeError('Unknown evidence reference');
      const generated = extractSkillEvidence(q, a, run.context);
      const expectedRun = { attempt_id: a.id, question_id: q.id, extractor_version: 'v1', context: run.context, evidence_ids: generated.map((e) => e.id), created_at: a.attempted_at };
      if (canonicalEvidence(expectedRun) !== canonicalEvidence(run)) throw new RangeError('Evidence receipt mismatch');
      for (const e of generated) {
        if (canonicalEvidence(e) !== canonicalEvidence(evidence.get(e.id))) throw new RangeError('Derived evidence mismatch');
        expectedEvidenceIds.add(e.id);
        if (e.evidence_kind === 'TRANSFER') transferAttempts.add(a.id);
      }
    }
    if (expectedEvidenceIds.size !== evidence.size) throw new RangeError('Orphan skill evidence');
    const contentKeys = new Map([...questions].map(([id, q]) => [id, canonicalEvidence({ stem: normalized(q.stem), passage: normalized(q.passage ?? ''), options: q.options.map((o) => normalized(o.text)).sort(compare) })]));
    const history = new Map<string, QuestionAttempt[]>();
    for (const a of attempts.values()) {
      const key = contentKeys.get(a.question_id)!;
      const group = history.get(key) ?? []; group.push(a); history.set(key, group);
    }
    for (const group of history.values()) group.sort((a, b) => a.attempted_at - b.attempted_at || compare(a.id, b.id));
    const linked = new Set<string>(), seenBlocks = new Set<string>(), expectedResults = new Set<string>(), expectedPacing = new Set<string>();
    for (const event of events.values()) {
      if (!plans.has(event.session_id) || event.at > input.as_of) throw new RangeError('Orphan or future event');
      if (event.command.type === 'QUESTION') {
        if (linked.has(event.command.attempt_id)) throw new RangeError('Attempt reused across blocks');
        linked.add(event.command.attempt_id);
      }
    }
    const records: PerformanceEvidence[] = [];
    for (const plan of [...plans.values()].sort((a, b) => compare(a.session_id, b.session_id))) {
      if (plan.created_at > input.as_of) throw new RangeError('Future plan');
      const local = [...events.values()].filter((e) => e.session_id === plan.session_id);
      const state = projectAdaptiveSession(plan, local);
      for (const e of local) if (e.command.type === 'QUESTION') {
        const a = attempts.get(e.command.attempt_id);
        if (!a || a.question_id !== e.command.item_id || a.attempted_at !== e.at || a.session_id !== null || !runs.has(a.id)) throw new RangeError('Invalid actual question linkage');
      }
      for (const block of state.blocks) {
        if (seenBlocks.has(block.id) || block.question_ids.some((id) => !questions.has(id))) throw new RangeError('Invalid block identity or content');
        seenBlocks.add(block.id);
        if (block.type !== 'TIMED_BLOCK') { exclude('BLOCK', block.id, 'NOT_TIMED'); continue; }
        if (block.status !== 'COMPLETED') { exclude('BLOCK', block.id, 'INCOMPLETE'); continue; }
        const derived = deriveTimedBlockResult(state.id, block, local, [...attempts.values()]);
        if (canonicalEvidence(derived) !== canonicalEvidence(results.get(block.id))) throw new RangeError('Forged or missing timed result');
        expectedResults.add(block.id);
        const pe = extractPacingBlockEvidence(derived, [...attempts.values()]);
        if (pe !== null) {
          if (canonicalEvidence(pe) !== canonicalEvidence(pacing.get(pe.id))) throw new RangeError('Forged or missing pacing evidence');
          expectedPacing.add(pe.id);
        }
        if (!derived.qualified) {
          exclude('BLOCK', block.id, derived.disqualification_reasons.some((r) => ['INSUFFICIENT_ACTIVE_DURATION', 'INCONSISTENT_ACTIVE_TIME'].includes(r)) ? 'INSUFFICIENT_TIME' : 'NOT_QUALIFIED'); continue;
        }
        for (const id of derived.attempt_ids) {
          const a = attempts.get(id)!, q = questions.get(a.question_id)!;
          if (a.hints_used_count > 0 || a.words_clicked.length > 0) { exclude('ATTEMPT', id, 'ASSISTED'); continue; }
          const group = history.get(contentKeys.get(q.id)!)!;
          if (group[0]?.id !== id || group[1]?.attempted_at === a.attempted_at) { exclude('ATTEMPT', id, 'REPEATED_QUESTION'); continue; }
          if (input.as_of - a.attempted_at > PERFORMANCE_V1.max_age_ms) { exclude('ATTEMPT', id, 'OUTSIDE_WINDOW'); continue; }
          const skill = primaryQuestionSkill(q);
          if (skill === 'PACING_STAMINA') throw new RangeError('Pacing is not a content question class');
          const transfer = transferAttempts.has(id);
          if (!transfer) exclude('ATTEMPT', id, 'NOT_EXAM_LIKE_TRANSFER');
          records.push({ attempt_id: id, question_id: q.id, block_id: block.id, session_id: state.id, family: q.family,
            primary_skill: skill, correct: a.is_correct, attempted_at: a.attempted_at, exam_like_transfer: transfer });
        }
      }
    }
    if (expectedResults.size !== results.size || expectedPacing.size !== pacing.size) throw new RangeError('Orphan derived block record');
    const included = new Set(records.map((r) => r.attempt_id));
    for (const id of attempts.keys()) if (!included.has(id) && !exclusions.some((e) => e.kind === 'ATTEMPT' && e.id === id)) exclude('ATTEMPT', id, 'NO_QUALIFIED_BLOCK');
    return finish(records, 'VALID');
  } catch (error) {
    if (!(error instanceof z.ZodError) && !(error instanceof RangeError)) throw error;
    // Stable reason rather than order-sensitive parser text; no partial statistics from corrupted history.
    exclusions.length = 0;
    for (const id of input.lexical_attempt_ids) exclude('ATTEMPT', id, 'LEXICAL_ATTEMPT');
    exclude('SOURCE', source.reference, 'INVALID_RECORD');
    return finish([], 'INVALID');
  }
}
