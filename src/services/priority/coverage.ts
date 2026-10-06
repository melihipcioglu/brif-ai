import type { SkillEvidence } from '../../types/evidence';
import { SKILL_IDS, type SkillId } from '../../types/learner';
import type { SkillEvidenceCoverage } from '../../types/priority';
import { uniqueEvidence } from '../evidence/validation';
import { deepFreeze } from '../questions/attempts';
import { skillEvidenceCoverageSchema } from './validation';

/** Supply complete, already audited Phase 3 history. Exact retries never increase coverage.
 * Neutral/zero-reliability events do not support a claim of skill coverage.
 */
export function deriveEvidenceCoverage(history: readonly SkillEvidence[]): Readonly<Record<SkillId, SkillEvidenceCoverage>> {
  const rows = uniqueEvidence(history);
  const entries = SKILL_IDS.map((skill) => {
    const relevant = rows.filter((e) => e.skill_id === skill && e.strength > 0 && e.reliability > 0);
    const coverage = skillEvidenceCoverageSchema.parse({
      informative_attempt_count: new Set(relevant.map((e) => e.attempt_id)).size,
      question_count: new Set(relevant.map((e) => e.question_id)).size,
      family_count: new Set(relevant.map((e) => e.question_family)).size,
      unaided_attempt_count: new Set(relevant.filter((e) => !e.assisted).map((e) => e.attempt_id)).size,
      transfer_attempt_count: new Set(relevant.filter((e) => e.evidence_kind === 'TRANSFER').map((e) => e.attempt_id)).size,
      last_informative_at: relevant.reduce<number | null>((time, e) => Math.max(time ?? 0, e.created_at), null),
    });
    return [skill, coverage] as const;
  });
  // The entries above are constructed from the complete closed SkillId tuple.
  return deepFreeze(Object.fromEntries(entries) as Record<SkillId, SkillEvidenceCoverage>);
}
