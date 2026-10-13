# FINDINGS & ARCHITECTURAL DISCOVERIES: V1.1 ADAPTIVE & INTERACTIVE LEARNING SYSTEM

## 1. Frozen Baseline Invariants
- 63 core baseline files from FAZ 5 were verified and 100% untouched (`tmp/phase5-baseline/frozen-hashes.json`: 63 passed, 0 failed).
- `src/data/initialVocab.ts` is among the 63 frozen files (contains 12 baseline starter words). All expanded academic vocabulary and learning models were safely placed in `src/data/learning/` and `src/services/learning/`.
- `src/data/productionBank.ts` contains 160 production-eligible questions for FAZ 10-11 exam construction. It supports 2 full disjoint 80-question exams. Learning practice questions were isolated in `src/data/learning/learningQuestionsBank.ts` and never touch or deplete the exam bank.

## 2. Audio Pronunciation Support
- Web Speech API (`window.speechSynthesis`) is supported natively in modern desktop and mobile browsers (Chrome, Edge, Safari, Firefox) without external network dependencies or external audio assets.
- Providing an audio button utilizing `SpeechSynthesisUtterance(word)` with `lang = 'en-US'` delivers immediate, reliable English audio pronunciation.

## 3. Storage Separation & Backward Compatibility
- Existing exam session keys:
  - `yokdil_active_exam_session_v1`
  - `yokdil_exam_history_v1`
  - `yokdil_learner_exposures_v1`
- Learning system storage uses dedicated keys to avoid polluting exam psychometrics and exposure:
  - `yokdil_learning_profile_v1` (retention stage, word history, streak, current day plan, diagnostic results, 3D mastery)
  - `yokdil_active_study_session_v1` (in-progress daily study session state)
  - `yokdil_reading_progress_v1` (reading skill mastery and scaffolding levels)

## 4. World-Class Pedagogical Framework Integration
- **Zero-Assumption Diagnostic:** 9 questions assessing vocabulary recognition, sentence syntax, and logical connectors, allowing personalized calibration without shaming or high cognitive load.
- **Atomik Basamaklama (Atomic Sentence Expansion):** Starting with a 3-word sentence skeleton (Basamak 0), adding modifiers (Basamak 1), logical clauses (Basamak 2), and scaling to full YÖKDİL exam sentences (Basamak 3) with custom teacher tips for each level.
- **Tuzak Aşısı (Trap Inoculation):** Directly pairing high-frequency distractors (inhabit vs inhibit, exhibit vs inhibit) with root mnemonics.
- **Interactive Decomposer (Cümle Çözümleme Atölyesi):** Gradual release of responsibility:
  - `I DO`: Student clicks tokens to inspect teacher model and syntactic roles.
  - `WE DO`: Student locates main verbs; clicking common traps (e.g., verbs inside relative clauses like `that catalyze`) provides specific pedagogical feedback explaining *why* it's a trap, blocking advance until the true main verb is selected.
  - `YOU DO`: Completely independent analysis of target structures.
- **3D Mastery Guardrails:** Tracking Recognition, Sentence Comprehension, and Transfer & Application independently. Strict rule: A word **cannot become MASTERED on the same day**; requires tested retention across $\ge 2$ distinct days.
