# V1.1 Adaptive & Interactive Learning System Implementation Plan

> **Goal:** Build the complete, interactive pedagogical learning system for YÖKDİL Fen: Diagnostic Assessment, Atomic Sentence Expansion, Interactive Syntax Decomposition (I DO -> WE DO -> YOU DO), 3-Dimensional Mastery Tracking, and Cumulative Spiraling Practice, fully integrated into the working web app without touching the 63 frozen baseline files or 160-question exam bank.

**Architecture:** A teacher-like digital scaffolding system built on React + TypeScript. Diagnostic calibrates scaffolding level; Word Progression trains vocabulary from clear basic sentence to full academic sentence; Interactive Sentence Decomposer allows clicking tokens for Subject/Verb/Clause with detailed feedback on misconceptions; Spaced repetition enforces 3D mastery across days.

**Tech Stack:** React 19, TypeScript, Vitest, Vite, Web Speech API.

## Global Constraints
- Preserve all 63 baseline files from FAZ 5 untouched (exact SHA-256 matches in `tmp/phase5-baseline/frozen-hashes.json`).
- Preserve the 160-question `productionBank.ts` exam bank and its 2-form disjoint capacity 100% intact.
- Separate `LEARNING_PRACTICE` and diagnostic attempts from exam exposure tracking (`yokdil_learner_exposures_v1`).
- Zero TypeScript errors (`npm run typecheck`).
- 100% test pass rate across all existing 598 tests + new learning tests.

---

### Task 1: Diagnostic Assessment Module (`DiagnosticScreen.tsx` & Data Models)
**Files:**
- Modify: `src/types/learning.ts`
- Create: `src/data/learning/diagnosticBank.ts`
- Create: `src/components/learning/DiagnosticScreen.tsx`
- Test: `tests/yokdil/learning/diagnostic.test.ts`

- [x] Step 1: Define `DiagnosticQuestion`, `DiagnosticResult`, and `LearnerLevel` types in `src/types/learning.ts`.
- [x] Step 2: Implement authentic diagnostic questions (4 vocab + 3 syntax + 2 connectors) in `src/data/learning/diagnosticBank.ts`.
- [x] Step 3: Implement `DiagnosticScreen.tsx` with zero-assumption introductory guidance and level calibration.
- [x] Step 4: Write and run unit tests in `tests/yokdil/learning/diagnostic.test.ts`.

---

### Task 2: Atomic Sentence Expansion & Word Progression Engine
**Files:**
- Modify: `src/types/learning.ts`
- Modify: `src/data/learning/academicVocabBank.ts`
- Modify: `src/components/learning/VocabTrainerScreen.tsx`
- Test: `tests/yokdil/learning/wordProgression.test.ts`

- [x] Step 1: Add `WordProgressionStep` and `TrapWordPair` types to `src/types/learning.ts`.
- [x] Step 2: Enrich academic vocabulary in `src/data/learning/academicVocabBank.ts` with progression steps (Level 0 Anchor -> Level 1 Basic Sentence -> Level 2 Expanded -> Level 3 Academic Pattern).
- [x] Step 3: Update `VocabTrainerScreen.tsx` with step-by-step progressive sentence reveal and trap word comparisons (*inhibit* vs *inhabit* vs *exhibit*).
- [x] Step 4: Write and run unit tests in `tests/yokdil/learning/wordProgression.test.ts`.

---

### Task 3: Interactive Syntax Decomposition Workshop (I DO -> WE DO -> YOU DO)
**Files:**
- Modify: `src/types/learning.ts`
- Modify: `src/data/learning/academicReadingBank.ts`
- Create: `src/components/learning/InteractiveDecomposerScreen.tsx`
- Test: `tests/yokdil/learning/interactiveDecomposer.test.ts`

- [x] Step 1: Define `InteractiveDecompositionTask` with token-based selection, roles, and tailored error rationale.
- [x] Step 2: Build interactive workbench allowing learner to click tokens for Subject, Verb, Object, Connector, Subordinate.
- [x] Step 3: Implement pedagogical feedback when learner clicks wrong tokens (explaining why they thought that and how to approach it).
- [x] Step 4: Write and run unit tests in `tests/yokdil/learning/interactiveDecomposer.test.ts`.

---

### Task 4: 3-Dimensional Mastery & Fail-Closed Spaced Repetition
**Files:**
- Modify: `src/types/learning.ts`
- Modify: `src/services/learning/spacedRepetition.ts`
- Modify: `src/components/learning/LearningProgressScreen.tsx`
- Test: `tests/yokdil/learning/spacedRepetition.test.ts`

- [x] Step 1: Track `recognitionScore`, `comprehensionScore`, and `transferScore` separately.
- [x] Step 2: Ensure a word CANNOT transition to `MASTERED` on the same day; require spaced recall on subsequent sessions.
- [x] Step 3: Update `LearningProgressScreen.tsx` to visualize 3D mastery breakdown.
- [x] Step 4: Update and run unit tests in `tests/yokdil/learning/spacedRepetition.test.ts`.

---

### Task 5: App Wiring & Seamless First-Day Journey
**Files:**
- Modify: `src/components/learning/TodayStudyDashboard.tsx`
- Modify: `src/components/exam/ExamApp.tsx`
- Test: `tests/yokdil/learning/learningApp.test.tsx`

- [x] Step 1: Wire Diagnostic trigger into `TodayStudyDashboard.tsx` and `ExamApp.tsx`.
- [x] Step 2: Wire `InteractiveDecomposerScreen` into reading learning tab.
- [x] Step 3: Verify first-day journey in automated tests.
- [x] Step 4: Verify in live browser via Chrome DevTools MCP.

---

### Task 6: Comprehensive Verification & Audit Report
**Files:**
- Run: `npm run typecheck`
- Run: `npx vitest run`
- Run: `npx vite build --config vite.app.config.ts`
- Verify: 63 frozen baseline files hashes against `tmp/phase5-baseline/frozen-hashes.json`
- Update: `V1_1_LEARNING_IMPLEMENTATION_AUDIT.md`
