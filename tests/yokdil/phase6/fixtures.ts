import { initialQuestions } from '../../../src/data/initialQuestions';
import { extractSkillEvidence } from '../../../src/services/evidence/extractEvidence';
import { projectAdaptiveSession } from '../../../src/services/session/execution';
import { deriveTimedBlockResult, extractPacingBlockEvidence } from '../../../src/services/session/pacing';
import { SESSION_V1 } from '../../../src/services/session/calibration';
import { actual } from '../phase5/fixtures';
import type { PerformanceSnapshot } from '../../../src/types/performance';
import type { EvidenceContext, EvidenceRun, SkillEvidence } from '../../../src/types/evidence';
import type { Question, QuestionAttempt } from '../../../src/types/question';
import type { SessionEvent, SessionPlan, TimedBlockResult, PacingBlockEvidence } from '../../../src/types/session';

export function fixture(options: { count?: number; correct?: boolean; assisted?: boolean; transfer?: boolean; familyOnly?: boolean; alternating?: boolean; blockSize?: number; noOptional?: boolean } = {}): PerformanceSnapshot {
  const count = options.count ?? 5;
  const questions: Question[] = Array.from({ length: count }, (_, i) => {
    const seed = initialQuestions[options.familyOnly ? 0 : i % initialQuestions.length]!;
    // Test-only expanded catalog; never inserted into the production question bank.
    const item = { ...seed, id: `p6-q-${i}`, stem: `${seed.stem} [fixture ${i}]`,
      ...(seed.passage === undefined ? {} : { passage: `${seed.passage} [fixture ${i}]` }) };
    if (options.noOptional) {
      const { difficulty: _d, global_benchmark_ms: _g, personal_benchmark_ms: _p, science_domain: _s, ...rest } = item;
      return rest;
    }
    return item;
  });
  const plans: SessionPlan[] = [], events: SessionEvent[] = [], attempts: QuestionAttempt[] = [];
  const results: TimedBlockResult[] = [], pacing: PacingBlockEvidence[] = [], runs: EvidenceRun[] = [], evidence: SkillEvidence[] = [];
  for (let offset = 0; offset < count;) {
    const length = options.blockSize === undefined ? count - offset < 10 ? count - offset : 5 : Math.min(count - offset, options.blockSize);
    const group = questions.slice(offset, offset + length), id = `p6-s-${offset}`;
    const start = 1_300_000_000 + offset * 300_000;
    const plan: SessionPlan = { id, session_id: id, mode: 'NORMAL', created_at: start, planned_minutes: 10, allocated_minutes: 6,
      config: SESSION_V1, notes: [], blocks: [{ id: `${id}/b`, type: 'TIMED_BLOCK', target_skills: ['PACING_STAMINA'], planned_minutes: 6,
        candidate_ids: [`${id}/candidate`], question_ids: group.map((q) => q.id), lexical_ids: [], cognitive_load: 'HIGH', timed_enabled: true, explanation: 'Test execution' }] };
    const local: SessionEvent[] = [];
    const add = (command: SessionEvent['command'], at: number) => local.push({ id: `${id}/e${local.length}`, session_id: id, at, sequence: local.length + 1, command,
      ...(command.type === 'QUESTION' ? { attempt_ref: `QUESTION:${command.attempt_id}` } : {}) });
    add({ type: 'START' }, start); add({ type: 'START_BLOCK', block_id: `${id}/b` }, start);
    for (const [index, q] of group.entries()) {
      const at = start + (index + 1) * 40_000;
      add({ type: 'PULSE', engaged: true }, at - 20_000);
      const a = actual(q, `${id}/a${index}`, at, options.alternating ? (offset + index) % 2 === 0 : options.correct ?? true, options.assisted && index === 0 ? 1 : 0, 40_000);
      const context: EvidenceContext = options.transfer === false ? {} : { transfer: { unseen: true, exam_like: true, prior_practice_at: 1 } };
      const rows = extractSkillEvidence(q, a, context);
      attempts.push(a); evidence.push(...rows);
      runs.push({ attempt_id: a.id, question_id: q.id, extractor_version: 'v1', context, evidence_ids: rows.map((e) => e.id), created_at: a.attempted_at });
      add({ type: 'QUESTION', block_id: `${id}/b`, item_id: q.id, attempt_id: a.id, retry_of: null }, at);
    }
    const end = start + group.length * 40_000;
    add({ type: 'COMPLETE_BLOCK', block_id: `${id}/b` }, end); add({ type: 'FINISH' }, end);
    const state = projectAdaptiveSession(plan, local);
    const result = deriveTimedBlockResult(id, state.blocks[0]!, local, attempts);
    const pe = extractPacingBlockEvidence(result, attempts);
    plans.push(plan); events.push(...local); results.push(result); if (pe) pacing.push(pe);
    offset += length;
  }
  return { source: { kind: 'USER_EXECUTION', reference: 'test-harness-user-stream' }, as_of: 2_000_000_000,
    questions, plans, events, attempts, timed_results: results, pacing_evidence: pacing, evidence_runs: runs, skill_evidence: evidence, lexical_attempt_ids: [] };
}
