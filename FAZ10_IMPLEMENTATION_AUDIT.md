# FAZ 10 IMPLEMENTATION AUDIT: MULTI-FORM CAPACITY & EXPOSURE-SAFE EXAM BANK

## A. STARTING CHECKPOINT
- **Verified Commit:** `9ae8a1d471989cf66a6817e4bbc3c8f20021cdb3`
- **Commit Message:** `checkpoint: phase 9 controlled question bank expansion verified`
- **Baseline State:**
  - Tests: 539/539 PASS
  - TypeScript: PASS
  - Production Build: PASS
  - Frozen 63 Files: 63/63 unchanged
  - Production Bank: 80 questions (22 existing + 58 newly authored)
  - `productionEligible`: 80
  - `canBuildOneForm`: true

---

## B. PRODUCTION BANK AUDIT
Audited directly from `src/data/productionBank.ts` and validated via `validateQuestionBank`:
- **Total Questions:** 80
- **Production Eligible:** 80
- **Rejected:** 0
- **Exact Duplicates:** 0
- **Family Distribution (8 Families, exactly 10 questions each):**
  - `GAP_FILL`: 10
  - `CLOZE_TEST`: 10
  - `SENTENCE_COMPLETION`: 10
  - `TRANSLATION_ENG_TR`: 10
  - `TRANSLATION_TR_ENG`: 10
  - `PARAGRAPH_COMPLETION`: 10
  - `IRRELEVANT_SENTENCE`: 10
  - `READING_COMPREHENSION`: 10
- **Primary Content Skill Distribution (12 skills):**
  - `VOCAB_CONTEXT`: 2
  - `COLLOCATION_PREPOSITION`: 2
  - `TENSE_ASPECT`: 2
  - `VOICE_REDUCTION`: 2
  - `CONNECTOR_DISCOURSE`: 12 (2 GAP_FILL + 10 CLOZE_TEST)
  - `SENTENCE_COMPLETION`: 10
  - `TRANSLATION_SEMANTICS`: 20 (10 ENG_TR + 10 TR_ENG)
  - `PARAGRAPH_COMPLETION`: 10
  - `COHESION_COHERENCE`: 12 (10 IRRELEVANT_SENTENCE + 2 READING)
  - `READING_DETAIL`: 4
  - `READING_INFERENCE`: 2
  - `MAIN_IDEA`: 2
  - `PACING_STAMINA`: 0 (Content skill only)

---

## C. BLUEPRINT AUDIT
- **Target Blueprint:** `INTERNAL_FULL_BLUEPRINT_80` (`src/data/internalBlueprint.ts`)
- **Scope:** `FULL`
- **Total Questions:** 80
- **Time Limit:** 10,800,000 ms (180 minutes)
- **Family Targets (exact sum = 80):**
  - `GAP_FILL`: 10
  - `CLOZE_TEST`: 10
  - `SENTENCE_COMPLETION`: 10
  - `TRANSLATION_ENG_TR`: 10
  - `TRANSLATION_TR_ENG`: 10
  - `PARAGRAPH_COMPLETION`: 10
  - `IRRELEVANT_SENTENCE`: 10
  - `READING_COMPREHENSION`: 10
- **Skill Minimums:** `{}` (empty map; no artificial skill quota invented)
- **Source Verification:** `UNVERIFIED` (explicitly internal practice distribution, never official exam score claim)

---

## D. EXPOSURE SEMANTICS
Strict adherence to Phase 7 exposure invariants:
- `question exists ≠ question is production eligible`
- `production eligible ≠ question is fresh for learner`
- `absence of attempt record ≠ UNSEEN`
- Absence of record produces `UNKNOWN_EXPOSURE`, which is never counted as `VERIFIED_FRESH`.
- `UNKNOWN` exposure questions are admitted under `EXCLUDE_SEEN` ('FRESH_OR_UNKNOWN') policy, but rejected under `UNSEEN_ONLY` ('VERIFIED_FRESH') strict policy.
- A controlled inventory observation (`CONTROLLED_INVENTORY`) is required to prove `UNSEEN` state, and must be contemporary (`observed_at === context.as_of`); stale inventory degrades to `UNKNOWN`.
- Learner attempts (`prior_attempts`) make question immediately `KNOWN_SEEN`.

---

## E. CAPACITY MODEL
Three explicit capacity tiers implemented in `analyzeFormCapacity`:
1. **RAW Capacity (`ALLOW_REUSE` exposure policy):**
   - Disregards learner exposure; measures inherent bank content capacity against blueprint quotas.
   - For current bank: eligible = 80, upper bound = 1, verified disjoint full forms = 1.
2. **FRESH_OR_UNKNOWN Capacity (`EXCLUDE_SEEN` exposure policy):**
   - Admits fresh and unrecorded questions, strictly excludes known seen questions.
   - For current bank with no prior history: eligible = 80, verified disjoint full forms = 1.
3. **VERIFIED_FRESH Capacity (`UNSEEN_ONLY` exposure policy):**
   - Strictly admits only verified fresh (`UNSEEN` via controlled inventory) questions.
   - With fresh inventory: eligible = 80, verified disjoint full forms = 1.
   - With no inventory (unrecorded): eligible = 0, verified disjoint full forms = 0.

---

## F. REUSE POLICIES
Cross-form reuse inside form-sets (`FormSetReusePolicy`):
1. **`NO_REUSE`:**
   - Strict content disjointness: `Form A ∩ Form B = ∅`.
   - Solved via global max-flow allocation across $N \times \text{target}$, verified by FAZ 7 `buildExamForm`.
2. **`LIMITED_REUSE`:**
   - Overlap strictly bounded by caller parameter: `maxSharedQuestionsPerPair`.
   - If allocation cannot stay within threshold, fails closed with reason `OVERLAP_LIMIT_EXCEEDED`.
3. **`ALLOW_REUSE`:**
   - Sequential least-used allocation. Allows question reuse, but form qualification reports `REUSED_FULL` and `calibrationFresh: false`.

---

## G. OVERLAP MODEL
Audited via `analyzeFormOverlap`:
- Metrics computed: `sharedQuestionCount`, `overlapRatio`, `uniqueToA`, `uniqueToB`, `totalUniqueQuestions`, `totalPlacements`, `reuseCount`, `maxPairwiseShared`, `maxPairwiseOverlapRatio`, `meanPairwiseOverlapRatio`, `orderDistinctForms`, `contentDistinctForms`, `allPairwiseDisjoint`.
- **Critical Acceptance Criterion Verified:**
  - Two forms having the identical 80 questions in different shuffled order have `orderDistinctForms = 2` but `contentDistinctForms = 1`, `allPairwiseDisjoint = false`, and pairwise overlap = 100%. They are NOT independent forms.

---

## H. CURRENT ONE-FORM CAPACITY
- **Raw Disjoint Full Forms:** 1
- **Verified Fresh Full Forms (with clean inventory):** 1
- **Fresh Full Forms (without inventory / unrecorded):** 0 (`UNKNOWN_EXPOSURE` requires `EXCLUDE_SEEN` policy to form 1 `UNKNOWN_EXPOSURE_FULL` form).
- **Bottlenecks:** All 8 families are exact bottlenecks ($10 / 10 = 1.0$).

---

## I. TWO-FORM ANALYSIS (N = 2)
- **NO_REUSE Forms Achievable:** 0 (Insufficient capacity)
- **Status:** `INSUFFICIENT_CAPACITY`
- **Reason:** `FAMILY_CAPACITY`
- **Shortage:** Exactly 80 questions needed:
  - `GAP_FILL`: 10
  - `CLOZE_TEST`: 10
  - `SENTENCE_COMPLETION`: 10
  - `TRANSLATION_ENG_TR`: 10
  - `TRANSLATION_TR_ENG`: 10
  - `PARAGRAPH_COMPLETION`: 10
  - `IRRELEVANT_SENTENCE`: 10
  - `READING_COMPREHENSION`: 10
- **Total Additional Questions Required:** 80

---

## J. THREE-FORM ANALYSIS (N = 3)
- **NO_REUSE Forms Achievable:** 0 (Insufficient capacity)
- **Status:** `INSUFFICIENT_CAPACITY`
- **Reason:** `FAMILY_CAPACITY`
- **Shortage:** Exactly 160 questions needed:
  - 20 per family across all 8 families ($20 \times 8 = 160$).
- **Total Additional Questions Required:** 160

---

## K. EXPOSURE SCENARIOS
Tested under 6 rigorous cases in `tests/yokdil/phase10/capacity.test.ts`:
- **Case A (Zero Seen, Current Controlled Inventory):**
  - Exposure: 80 VERIFIED_FRESH, 0 UNKNOWN, 0 SEEN.
  - Verified Fresh Capacity: 1 form. Form qualification: `FRESH_FULL`.
- **Case B (1 Required-Family Question Seen):**
  - Exposure: 79 VERIFIED_FRESH, 1 KNOWN_SEEN.
  - Raw Capacity: 1 form.
  - Fresh Capacity: 0 forms (GAP_FILL shortfall = 1).
  - Expansion planner detects 1 question required for GAP_FILL.
- **Case C (10 Questions Seen from One Family):**
  - All 10 READING_COMPREHENSION seen.
  - Shortfall for READING_COMPREHENSION = 10. Fresh capacity = 0.
- **Case D (Mixed 40 Fresh, 5 Seen, 35 Unknown):**
  - VERIFIED_FRESH = 40, KNOWN_SEEN = 5, UNKNOWN = 35.
  - Verified fresh eligible = 40; Fresh or unknown eligible = 75; Raw eligible = 80.
- **Case E (All 80 Seen):**
  - Raw Capacity = 1; Fresh Capacity = 0; Shortfall = 80.
- **Case F (No History / Unavailable):**
  - All 80 are UNKNOWN_EXPOSURE (never fabricated as UNSEEN).
  - Strict UNSEEN_ONLY capacity = 0; EXCLUDE_SEEN capacity = 1 form (`UNKNOWN_EXPOSURE_FULL`).

---

## L. EXPANSION REQUIREMENTS FOR FAZ 11
- **Mathematical Minimum for 2 Disjoint Forms:** 80 questions (10 per family).
- **Mathematical Minimum for 3 Disjoint Forms:** 160 questions (20 per family).
- **Operational Target Formulation:**
  - Built-in operational target calculator `planMultiFormExpansion` with optional `assumedLossRate`.
  - For example, with an explicit 20% candidate loss rate:
    - 2 forms: $\lceil 80 / (1 - 0.20) \rceil = 100$ candidate questions.
    - 3 forms: $\lceil 160 / (1 - 0.20) \rceil = 200$ candidate questions.
  - No default margin is fabricated; assumptions are explicitly documented in `plan.assumptions`.

---

## M. FAZ 7 / 8 / 9 INTEGRATION
- **FAZ 8 Integration:** Only questions passing `validateQuestionBank` with `productionEligible: true` enter the capacity calculation. Malformed or exact duplicate questions are filtered out at the quality gate and never inflate RAW capacity.
- **FAZ 7 Integration:** Disjoint forms partitioned by global allocation are directly submitted to and validated by the immutable Phase 7 `buildExamForm` engine.
- **FAZ 9 Integration:** Uses public `productionBank` via `src/index.ts`. No synthetic parallel banks used in production flow.

---

## N. NEW AND MODIFIED FILES
### New Files:
- `src/types/formCapacity.ts`: Domain types and interfaces for multi-form capacity, overlap reports, reuse policies, and expansion plans.
- `src/services/exam/formCapacity.ts`: Implementation of capacity analyzer, overlap analyzer, form-set builder, and expansion planner.
- `src/data/internalBlueprint.ts`: Canonical 80-question internal practice blueprint constant.
- `src/formCapacity.ts`: Public API export module for capacity services.
- `tests/yokdil/phase10/capacity.test.ts`: 21 comprehensive test cases covering capacity, determinism, overlap, exposure, safety, and constraints.
- `tests/yokdil/phase10/integration.test.ts`: Public entry-point integration test.
- `FAZ10_IMPLEMENTATION_AUDIT.md`: This comprehensive audit report.

### Modified Files:
- `src/index.ts`: Additive export of `export * from './formCapacity';`.

---

## O. TESTS
- **Existing Tests (Phases 1-9):** 539 / 539 PASS
- **New FAZ 10 Tests:** 22 / 22 PASS (21 capacity tests + 1 integration test)
- **Total Suite:** 561 / 561 PASS across 37 test suites.

---

## P. TYPESCRIPT & BUILD
- `npx tsc --noEmit`: 0 errors (strict TypeScript compliance, no `any`, no `@ts-ignore`).
- `npm run build`: Production bundle generated successfully (`dist-yokdil/yokdil-phase-one.js`).

---

## Q. FROZEN VERIFICATION
- `tmp/phase5-baseline/frozen-hashes.json`: 63/63 unchanged (0 changed, 0 missing).
- `tmp/phase7-baseline/all-existing-hashes.json`: 95/96 unchanged, only additive modification in `src/index.ts`.
- Forbidden API scan on exam sources: 0 occurrences of `Math.random`, `Date.now`, `fetch`, `indexedDB`, etc.
- UI files under exam: 0.

---

## R. KNOWN LIMITATIONS
1. **Current Question Bank Size:** With exactly 80 questions and an 80-question blueprint, the maximum disjoint capacity is strictly 1 form. Multiple independent exams without question reuse cannot be served until question authoring expands the bank.
2. **Exposure Tracking Requirement:** In the absence of contemporary controlled inventory records, learner exposure defaults to `UNKNOWN_EXPOSURE`, preventing `FULL_FRESH_CALIBRATION`.
3. **Skill Quota Extensibility:** `INTERNAL_FULL_BLUEPRINT_80` currently defines no skill minimums (`skill_minimums: {}`). When skill minimums are added in the future, bipartite max-flow guarantees global feasibility, but may require slightly more questions than the pure family-sum minimum.
