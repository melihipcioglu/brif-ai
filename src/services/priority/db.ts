import type { Question } from '../../types/question';
import type { NextBestActionPlan, PriorityContext, PriorityModelConfig, TrainingAction } from '../../types/priority';
import { evidenceDb, type EvidenceDatabase, loadLearnerSkillVector } from '../evidence/db';
import { PRIORITY_V1 } from './calibration';
import { deriveEvidenceCoverage } from './coverage';
import { planNextBestAction } from './nextBestAction';

export interface DatabasePlanningRequest {
  readonly questions: readonly Question[];
  readonly actions: readonly TrainingAction[];
  readonly as_of: number;
  readonly available_minutes: number;
  readonly profiles?: PriorityContext['profiles'];
}

/** Read-only v4 adapter. Model and coverage share one audited snapshot; no new schema or cached scores. */
export async function loadNextBestActionPlan(
  request: DatabasePlanningRequest,
  database: EvidenceDatabase = evidenceDb,
  config: PriorityModelConfig = PRIORITY_V1,
): Promise<NextBestActionPlan> {
  return database.transaction('r', database.tables, async () => {
    const learner = await loadLearnerSkillVector(request.questions, database, request.as_of);
    const coverage = deriveEvidenceCoverage(await database.skill_evidence.toArray());
    return planNextBestAction(learner, request.actions, {
      as_of: request.as_of, coverage, profiles: request.profiles,
    }, request.available_minutes, config);
  });
}
