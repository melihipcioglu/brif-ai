import type { DailySession, ProgressBackup } from '../types/progress';
import type { LexicalEntry, LexicalRecord } from '../types/lexical';
import { DEFAULT_MASTERY_REQUIREMENTS, FAMILIAR_DELAY_DAYS } from '../types/lexical';
import { SKILL_IDS } from '../types/learner';
import { initialVocabEntries } from '../data/initialVocab';
import { calculateMasteryEvidence, calculateReviewPriority } from './lexicalScheduler';
import {
  dailySessionSchema, legacyDailySessionV1Schema, legacyLexicalRecordV1Schema,
  legacyProgressBackupV1Schema, lexicalRecordSchema, progressBackupSchema,
} from './validation';

/** Conservative, deterministic conversion. Exposure IDs never become success IDs. */
export function migrateLexicalRecordV1(input: unknown): LexicalRecord {
  const legacy = legacyLexicalRecordV1Schema.parse(input);
  const entry: LexicalEntry | undefined = initialVocabEntries.find((item) =>
    item.word_id === legacy.word_id && item.lemma === legacy.lemma);
  const { delayed_unaided_correct_count: delayed14, ...retainedEvidence } = legacy.evidence;
  // V1 kept the maximum unaided delay but not a 3-day count. Recover only a proven lower bound:
  // every 14-day recall is also a 3-day recall; max >= 3 proves at least one such recall.
  const delayed3 = Math.max(delayed14, Number(legacy.unaided_correct_count > 0 &&
    legacy.evidence.max_unaided_delay_days >= FAMILIAR_DELAY_DAYS));
  const draft: LexicalRecord = {
    ...legacy,
    unaided_success_contexts: [],
    mastery_requirements: { ...(entry?.mastery_requirements ?? DEFAULT_MASTERY_REQUIREMENTS) },
    evidence: {
      ...retainedEvidence,
      delayed_unaided_correct_count_3d: delayed3,
      delayed_unaided_correct_count_14d: delayed14,
    },
  };
  const mes = calculateMasteryEvidence(draft);
  // Requalify legacy promoted states against actual evidence, never against elapsed time.
  // There are no verified context IDs in v1, so MASTERED cannot be carried into v2.
  const lexicalState = legacy.lexical_state === 'FAMILIAR' || legacy.lexical_state === 'MASTERED'
    ? mes.eligible_for_familiar ? 'FAMILIAR' : 'LEARNING'
    : legacy.lexical_state;
  const scored: LexicalRecord = { ...draft, mastery_score: mes.total, lexical_state: lexicalState };
  return lexicalRecordSchema.parse({
    ...scored,
    // Use the last known clock, making repeated imports of the same v1 snapshot identical.
    review_priority: calculateReviewPriority(scored, scored.last_seen_at ?? 0),
  });
}

export function migrateDailySessionV1(input: unknown): DailySession {
  const legacy = legacyDailySessionV1Schema.parse(input);
  const skills = { ...legacy.skills };
  for (const skill of SKILL_IDS) {
    // Always convert by the declared version, including v1 values such as 0.8 -> 0.008.
    // A magnitude heuristic would silently corrupt small percentages.
    skills[skill] = { ...legacy.skills[skill], mastery: legacy.skills[skill].mastery / 100 };
  }
  return dailySessionSchema.parse({ ...legacy, skills });
}

export function migrateProgressV1ToV2(input: unknown): ProgressBackup {
  const legacy = legacyProgressBackupV1Schema.parse(input);
  return progressBackupSchema.parse({
    ...legacy,
    schema_version: 2,
    lexical_store: legacy.lexical_store.map(migrateLexicalRecordV1),
    daily_sessions: legacy.daily_sessions.map(migrateDailySessionV1),
  });
}

export interface ParsedProgressBackup {
  readonly backup: ProgressBackup;
  readonly migrated_from: 1 | null;
}

export function parseProgressBackup(input: unknown): ParsedProgressBackup {
  if (input !== null && typeof input === 'object' && 'schema_version' in input && input.schema_version === 1) {
    return { backup: migrateProgressV1ToV2(input), migrated_from: 1 };
  }
  return { backup: progressBackupSchema.parse(input), migrated_from: null };
}
