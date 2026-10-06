import { describe, expect, it } from 'vitest';
import { validateQuestionBank } from '../../../src/questionBank';
import { initialQuestions } from '../../../src/data/initialQuestions';
import { analyzeExamPool } from '../../../src/services/exam/poolAnalysis';

describe('Phase 8 <-> Phase 7 Integration', () => {
  it('feeds only productionEligible questions to FAZ 7 pool analyzer', () => {
    // 1. Run the FAZ 8 validator on mixed/raw inputs
    const badQuestion = { ...initialQuestions[0], id: 'bad-question-id', stem: '' }; // Invalid
    const mixedPool = [...initialQuestions, badQuestion];
    
    const bankResult = validateQuestionBank(mixedPool);
    
    // 2. The adapter step: filter only production eligible questions
    const eligibleIds = new Set(bankResult.results.filter(r => r.productionEligible).map(r => r.questionId));
    const eligibleQuestions = mixedPool.filter((q: any) => eligibleIds.has(q.id));
    
    expect(eligibleQuestions.length).toBe(22); // badQuestion is dropped
    
    // 3. Feed to FAZ 7 analyzer
    const blueprint = {
      id: 'test', version: '1', scope: 'MINI', total_questions: 5,
      time_limit_ms: 1000, family_targets: { GAP_FILL: 5 }, skill_minimums: {},
      reuse_policy: 'ALLOW_REUSE', source: { verification: 'UNVERIFIED', reference: null }
    };
    const context = { as_of: Date.now(), prior_attempts: [], exposures: [] };
    
    const analysis = analyzeExamPool(blueprint, eligibleQuestions, context);
    if (analysis.status !== 'INSUFFICIENT_POOL' && analysis.status !== 'ADEQUATE') {
      throw new Error('Unexpected analysis status');
    }
    // The FAZ 7 analyzer sees exactly the clean 22 questions
    expect(analysis.report.available).toBe(22);
  });
});
