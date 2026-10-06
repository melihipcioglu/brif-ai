import type { AnchorChain, CheckCriterion, DistractorPattern, OptionId, Question, SemanticRoleMap, TacticalMetadata } from '../types/question';
import { OPTION_IDS } from '../types/question';
import { questionSchema } from '../services/questions/validation';

import { tacticalSolvers } from '../services/questions/strategies';

/** All items are original practice material, not released ÖSYM questions. */
export type Choice = readonly [text: string, reason: string, patterns: readonly DistractorPattern[], failed: readonly CheckCriterion[]];
interface Seed {
  readonly id: string; readonly family: Question['family']; readonly domain: string; readonly stem: string;
  readonly passage?: string; readonly correct: OptionId; readonly choices: readonly [Choice, Choice, Choice, Choice, Choice];
  readonly tactical: TacticalMetadata; readonly checks: readonly CheckCriterion[]; readonly triage: string;
  readonly skills: Question['skill_ids']; readonly lexical?: readonly string[];
}
export function make(seed: Seed): Question {
  const analyses = seed.choices.map((choice, i) => {
    const id = OPTION_IDS[i];
    if (id === undefined) throw new Error('Invalid choice index');
    return { option_id: id, verdict: id === seed.correct ? 'CORRECT' as const : 'ELIMINATE' as const, reasons: [choice[1]], patterns: choice[2] };
  });
  const q = questionSchema.parse({
    id: seed.id, family: seed.family, science_domain: seed.domain, stem: seed.stem,
    ...(seed.passage === undefined ? {} : { passage: seed.passage }),
    ...(seed.tactical.kind === 'GAP_FILL' ? { subclass: seed.tactical.focus } : {}),
    options: seed.choices.map((choice, i) => ({ id: OPTION_IDS[i], text: choice[0] })), correct_option: seed.correct,
    tactical: seed.tactical, option_evidence: Object.fromEntries(seed.choices.map((choice, i) => [OPTION_IDS[i], seed.checks.map((criterion) => ({ criterion, matches: !choice[3].includes(criterion), evidence: choice[1] }))])),
    explanation: {
      triage: { summary: seed.triage, cues: [seed.tactical.kind === 'TRANSLATION' ? 'Eyleyen ve eylemi ayırın; kip ve kapsamı koruyun.' : seed.triage], checks: ['Bağlam kanıtını bulun.', 'Her adayı aynı anlam kontrollerinden geçirin.'] },
      option_analysis: analyses, verification: { summary: 'Doğru adayı cümleye veya metne geri yerleştirerek anlamı doğrulayın.', evidence: analyses.find((a) => a.option_id === seed.correct)?.reasons ?? [] },
      distractor_patterns: [...new Set(analyses.flatMap((a) => a.patterns))],
    },
    lexical_ids: seed.lexical ?? [], skill_ids: seed.skills, difficulty: 0.5, provenance: 'ORIGINAL_PRACTICE',
  });
  const solver = tacticalSolvers[q.family];
  const supported = solver.analyzeOptions(q, solver.triage(q)).filter((a) => a.verdict === 'CORRECT');
  if (supported.length !== 1 || supported[0]?.option_id !== q.correct_option) throw new Error(`Inconsistent authored evidence: ${q.id}`);
  return q;
}
export const sentenceChecks: readonly CheckCriterion[] = ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'];
export const clozeChecks: readonly CheckCriterion[] = ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'];
export const readingChecks: readonly CheckCriterion[] = ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'];
export const irrelevantChecks: readonly CheckCriterion[] = ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'];
export const strong: AnchorChain = { referent: 1, topic_continuity: 1, connector: 1, tense_aspect: 1, cause_effect: 1, lexical_chain: 1 };
export const weak: AnchorChain = { referent: 0.2, topic_continuity: 0.2, connector: 0.3, tense_aspect: 0.8, cause_effect: 0.1, lexical_chain: 0.2 };
export const anchors = (correct: OptionId): Readonly<Record<OptionId, AnchorChain>> => ({ A: correct === 'A' ? strong : weak, B: correct === 'B' ? strong : weak, C: correct === 'C' ? strong : weak, D: correct === 'D' ? strong : weak, E: correct === 'E' ? strong : weak });
export const roles1: SemanticRoleMap = { agent: 'scientists', action: 'detect', patient: 'small-planets', voice: 'ACTIVE', modality: 'may', polarity: 'positive', time: 'present', propositions: ['with-new-sensor'] };
export const roles2: SemanticRoleMap = { agent: 'roots', action: 'absorb', patient: 'water', voice: 'ACTIVE', polarity: 'positive', condition: 'soil-moist', degree: 'more-quickly', propositions: [] };
export const roles3: SemanticRoleMap = { agent: 'researchers', action: 'measure', patient: 'temperature', voice: 'ACTIVE', time: 'past', degree: 'twice', propositions: ['before-reaction'] };
export const roles4: SemanticRoleMap = { agent: 'thick-clouds', action: 'reduce', patient: 'surface-sunlight', voice: 'ACTIVE', modality: 'can', polarity: 'positive', propositions: [] };



