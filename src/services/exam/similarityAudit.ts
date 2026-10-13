import type { Question } from '../../types/question';
import type { ExamForm } from '../../types/exam';
import { questionContentKey } from './provenance';
import type {
  SimilarityPair,
  PassageLeakage,
  DistractorLeakage,
  FormSetSimilarityAudit,
  BankSimilarityAudit
} from '../../types/similarity';

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9ğüşıöç]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length > 2)
  );
}

function calculateJaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 1;
  const intersection = new Set([...a].filter((x) => b.has(x)));
  const union = new Set([...a, ...b]);
  return intersection.size / union.size;
}

function normalizeSnippet(text: string): string {
  return text.trim().replace(/\s+/g, ' ').toLowerCase();
}

/**
 * Returns the full semantic text of a question, incorporating passage when present.
 */
export function getSemanticContent(q: Question): string {
  if (q.passage && q.passage.trim().length > 0) {
    return `${q.passage.trim()} ${q.stem.trim()}`;
  }
  return q.stem.trim();
}

/**
 * Audits a question bank for internal exact duplicates, semantic near duplicates, and shared passages.
 */
export function auditBankSimilarity(questions: readonly Question[]): BankSimilarityAudit {
  const exactDuplicates: SimilarityPair[] = [];
  const nearDuplicates: SimilarityPair[] = [];
  const passageMap = new Map<string, string[]>();

  const tokenCache = questions.map((q) => tokenize(getSemanticContent(q)));
  const contentKeyCache = questions.map((q) => questionContentKey(q));

  for (let i = 0; i < questions.length; i++) {
    const qA = questions[i]!;
    if (qA.passage && qA.passage.trim().length > 20) {
      const normP = normalizeSnippet(qA.passage);
      if (!passageMap.has(normP)) passageMap.set(normP, []);
      passageMap.get(normP)!.push(qA.id);
    }

    for (let j = i + 1; j < questions.length; j++) {
      const qB = questions[j]!;

      // Check exact canonical content key match
      if (contentKeyCache[i] === contentKeyCache[j]) {
        exactDuplicates.push({
          questionIdA: qA.id,
          questionIdB: qB.id,
          similarityScore: 1.0,
          kind: 'EXACT_STEM',
          details: `Exact matching content: "${qA.id}" vs "${qB.id}"`
        });
        continue;
      }

      // Check lexical similarity (Jaccard) over semantic content
      const sim = calculateJaccard(tokenCache[i]!, tokenCache[j]!);
      if (sim >= 0.75) {
        nearDuplicates.push({
          questionIdA: qA.id,
          questionIdB: qB.id,
          similarityScore: Math.round(sim * 1000) / 1000,
          kind: 'NEAR_STEM',
          details: `Semantic token similarity ${Math.round(sim * 100)}% between questions`
        });
      }
    }
  }

  const sharedPassageGroups = [...passageMap.entries()]
    .filter(([_, ids]) => ids.length > 1)
    .map(([normP, ids]) => ({ snippet: normP.slice(0, 80), questionIds: ids }));

  const pass = exactDuplicates.length === 0 && nearDuplicates.length === 0;

  return {
    totalQuestions: questions.length,
    exactDuplicates,
    nearDuplicates,
    sharedPassageGroups,
    pass
  };
}

/**
 * Audits a set of built exam forms (e.g. Form 1 and Form 2) for:
 * 1. Disjointness (shared question IDs)
 * 2. Cross-form passage leakage
 * 3. Cross-form near duplicates (semantic)
 * 4. Distractor / verbatim answer leakage
 */
export function auditFormSetSimilarityAndLeakage(forms: readonly ExamForm[]): FormSetSimilarityAudit {
  const sharedQuestionIds: string[] = [];
  const crossFormPassageLeakages: PassageLeakage[] = [];
  const crossFormNearDuplicates: SimilarityPair[] = [];
  const distractorLeakages: DistractorLeakage[] = [];

  const allItemIds = new Set<string>();
  let totalItems = 0;

  for (const f of forms) {
    for (const q of f.questions) {
      totalItems++;
      if (allItemIds.has(q.id)) {
        if (!sharedQuestionIds.includes(q.id)) sharedQuestionIds.push(q.id);
      } else {
        allItemIds.add(q.id);
      }
    }
  }

  // Cross-form pairwise checks
  for (let i = 0; i < forms.length; i++) {
    const fA = forms[i]!;
    for (let j = i + 1; j < forms.length; j++) {
      const fB = forms[j]!;

      for (const qA of fA.questions) {
        for (const qB of fB.questions) {
          // Check passage leakage
          if (qA.passage && qB.passage) {
            const pA = normalizeSnippet(qA.passage);
            const pB = normalizeSnippet(qB.passage);
            if (pA === pB) {
              crossFormPassageLeakages.push({
                formIdA: fA.id,
                formIdB: fB.id,
                questionIdA: qA.id,
                questionIdB: qB.id,
                passageSnippet: qA.passage.slice(0, 60),
                overlapScore: 1.0
              });
            } else {
              const tokA = tokenize(qA.passage);
              const tokB = tokenize(qB.passage);
              const sim = calculateJaccard(tokA, tokB);
              if (sim > 0.75) {
                crossFormPassageLeakages.push({
                  formIdA: fA.id,
                  formIdB: fB.id,
                  questionIdA: qA.id,
                  questionIdB: qB.id,
                  passageSnippet: qA.passage.slice(0, 60),
                  overlapScore: Math.round(sim * 1000) / 1000
                });
              }
            }
          }

          // Check semantic near duplicate
          const simSemantic = calculateJaccard(
            tokenize(getSemanticContent(qA)),
            tokenize(getSemanticContent(qB))
          );
          if (simSemantic >= 0.75) {
            crossFormNearDuplicates.push({
              questionIdA: qA.id,
              questionIdB: qB.id,
              similarityScore: Math.round(simSemantic * 1000) / 1000,
              kind: 'NEAR_STEM',
              details: `Cross-form semantic similarity ${Math.round(simSemantic * 100)}%`
            });
          }

          // Distractor / answer leakage
          const correctB = qB.options.find((o) => o.id === qB.correct_option);
          if (correctB && correctB.text.length > 30) {
            const normCB = normalizeSnippet(correctB.text);
            if (normalizeSnippet(getSemanticContent(qA)).includes(normCB)) {
              distractorLeakages.push({
                questionIdA: qA.id,
                questionIdB: qB.id,
                leakedText: correctB.text,
                details: `Question ${qA.id} content contains verbatim correct option of ${qB.id}`
              });
            }
          }
        }
      }
    }
  }

  const allPairwiseDisjoint = sharedQuestionIds.length === 0;
  const pass =
    allPairwiseDisjoint &&
    crossFormPassageLeakages.length === 0 &&
    crossFormNearDuplicates.length === 0 &&
    distractorLeakages.length === 0;

  return {
    formCount: forms.length,
    allPairwiseDisjoint,
    sharedQuestionIds,
    crossFormPassageLeakages,
    crossFormNearDuplicates,
    distractorLeakages,
    pass,
    summary: {
      totalItems,
      distinctItems: allItemIds.size,
      crossFormLeakageCount: crossFormPassageLeakages.length,
      crossFormNearDuplicateCount: crossFormNearDuplicates.length
    }
  };
}
