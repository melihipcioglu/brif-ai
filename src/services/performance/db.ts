import { z } from 'zod';
import type { Question } from '../../types/question';
import type { PerformanceEstimateResult, PerformanceSnapshot, PerformanceSource } from '../../types/performance';
import { loadSessionLearnerSnapshot, sessionDb, type SessionDatabase } from '../session/db';
import { estimatePerformance } from './estimate';
import { performanceSourceSchema } from './selectEvidence';
import { timestampSchema } from '../validation';

/** One consistent read-only v5 transaction. No migration, cached score or progress writes. */
export async function loadPerformanceEstimate(questions: readonly Question[], asOf: number, source: PerformanceSource, database: SessionDatabase = sessionDb): Promise<PerformanceEstimateResult> {
  timestampSchema.parse(asOf); performanceSourceSchema.parse(source);
  const origin: PerformanceSource = database.name === 'yokdil-fen-phase2-demo' ? { kind: 'DEMO', reference: database.name } : source;
  let captured: PerformanceSnapshot | undefined;
  try { return await database.transaction('r', database.tables, async () => {
    const snapshot: PerformanceSnapshot = { source: origin, as_of: asOf, questions,
      plans: await database.adaptive_sessions.toArray(), events: await database.session_events.toArray(),
      attempts: await database.solver_attempts.toArray(), timed_results: await database.timed_block_results.toArray(),
      pacing_evidence: await database.pacing_evidence.toArray(), evidence_runs: await database.evidence_runs.toArray(),
      skill_evidence: await database.skill_evidence.toArray(), lexical_attempt_ids: (await database.question_attempts.toArray()).map((a) => a.id) };
    captured = snapshot;
    if (origin.kind === 'DEMO' || origin.kind === 'SYNTHETIC' || origin.kind === 'UNKNOWN') return estimatePerformance(snapshot);
    // Reuse authoritative Phase 3/5 audits; the returned mastery/priority values are NOT estimator inputs.
    await loadSessionLearnerSnapshot(questions, asOf, database);
    return estimatePerformance(snapshot);
  }); } catch (error) {
    // Catch outside the transaction: nested Dexie validation failures abort their parent transaction.
    if (captured === undefined || !(error instanceof z.ZodError) && !(error instanceof RangeError)) throw error;
    return estimatePerformance({ ...captured, plans: [{}] });
  }
}
