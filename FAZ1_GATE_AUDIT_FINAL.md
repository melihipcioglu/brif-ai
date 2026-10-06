# FAZ 1 GATE AUDIT — FINAL

Bu belge önceki gate auditinin sonuçlarını korur. Son MES accuracy formülü,
güncel sayısal örnekler ve 99 testlik doğrulama için
[FINAL MES EVIDENCE AUDIT](FINAL_MES_EVIDENCE_AUDIT.md) ve
[README](README.yokdil-phase1.md) esas alınmalıdır.

BLOCKER 1 — Skill mastery scale  
Status: **FIXED**  
Files: `src/types/learner.ts`, `src/services/validation.ts`, `src/services/progressMigration.ts`  
Tests: `gateAudit.test.ts` accepts 0.8, rejects 80 and other invalid values;
`migration.test.ts` converts all v1 skill percentages exactly once.

BLOCKER 2 — Passive contexts contaminating MES  
Status: **FIXED**  
Files: `src/types/lexical.ts`, `src/services/lexicalScheduler.ts`, `src/services/validation.ts`  
Tests: passive, assisted and incorrect contexts earn no transfer points;
three distinct unaided success contexts earn 25 points; subset and uniqueness are validated.

BLOCKER 3 — Familiar delayed recall gate  
Status: **FIXED**  
Files: `src/types/lexical.ts`, `src/services/lexicalScheduler.ts`, `src/services/validation.ts`  
Tests: ten same-day correct answers with MES 70 stay LEARNING;
exactly three delayed unaided days permit FAMILIAR; 2.999 days and intervening exposure do not.

FIX — State demotion  
Status: **FIXED** — MASTERED → FAMILIAR → LEARNING; ordinary errors never force LEARNING → SEEN.
Time alone never changes state. The 30-day inactivity regression passes.

FIX — Collocation/mastery requirements  
Status: **FIXED** — explicit requirements independently gate MASTERED, even at MES 100.
Defaults: collocation not required, distractor evidence required. `susceptible to` explicitly requires collocation evidence.
The vocabulary change is one metadata line; words, examples and other content are preserved.

FIX — MES accuracy normalization  
Status: **FIXED** — `weightedCorrect = 2.5*unaided + assisted`;
`weightedPossible = weightedCorrect + 2.5*incorrect`; zero denominator gives zero.
The accuracy component retains its 20% weight. Tests cover seven concrete distributions;
the README documents old/new results and the effect on the unchanged 15% speed component.
Five targeted tests failed before the fix and pass afterward.

FIX — A/B option randomization  
Status: **FIXED** — word ID + optional choiceSeed + opening sequence determine option order on opening.
The order remains stable while open, including rerenders and mid-quiz seed changes.
Ten seeded encounters split the correct answer 5/5 across A/B in regression tests.
No render-time randomness is used.

FIX — QuestionAttempt future compatibility  
Status: **FIXED** — entity renamed to `LexicalAttempt`; `QuestionAttempt` has no compatibility alias.
The existing `question_attempts` IndexedDB store and JSON key are preserved.

FIX — Popover information hierarchy  
Status: **FIXED** — full reveal shows lemma/POS, meaning, at most two collocations,
one synonym and antonym, one distractor, two family forms and one exam sentence.
Levels 3/4 withhold answer-revealing details before reveal. Bypass, focus, Escape,
outside clicks and non-blocking question controls remain covered by tests.

MIGRATION:  
schema v1 → v2: **IMPLEMENTED**

- A shared explicit conversion handles JSON import and Dexie version upgrades.
- `contexts_seen` is preserved and `unaided_success_contexts` starts empty.
- The old 14-day count is retained; the new 3-day count is a proven conservative lower bound.
- v1 skill percentages are divided by 100; v2 fractions are never converted twice.
- MES and legacy promoted states are requalified from recoverable evidence.
  An old MASTERED becomes FAMILIAR if its new familiar gates hold, otherwise LEARNING.
  This is a one-time schema correction, not time-based demotion.
- IDs, attempts, exposure history, counters, stability and dates are retained.
- Import reports `migrated_from`; defaults still reject conflicting local rows.
- A failed native upgrade preserves the old database version and original rows.

REGRESSION ACCEPTANCE:

| # | Requested case | Result |
| --- | --- | --- |
| 1 | Three passive contexts, no recall → zero context MES | PASS |
| 2 | Three assisted contexts → zero mastery contexts | PASS |
| 3 | Three unaided contexts → three mastery contexts | PASS |
| 4 | MES >60 without three-day delayed unaided recall → not FAMILIAR | PASS |
| 5 | MES ≥60 with three-day delayed unaided recall → FAMILIAR | PASS |
| 6 | Cached MES ≥85 with only exposure contexts → not MASTERED | PASS |
| 7 | Fourteen-day recall, three successful contexts and requirements → MASTERED | PASS |
| 8 | MASTERED + one lexical error → FAMILIAR | PASS |
| 9 | FAMILIAR + one error → LEARNING | PASS |
| 10 | LEARNING + ordinary error → LEARNING | PASS |
| 11 | Thirty days inactive → state preserved, priority increased | PASS |
| 12 | Level 4 always allows meaning reveal | PASS |
| 13 | A/B stable within a quiz, variable across seeded encounters | PASS |
| 14 | v1 exposure contexts never become mastery contexts | PASS |
| 15 | v2 round trip preserves new evidence fields | PASS |
| 16 | mastery 0.8 accepted, 80 rejected | PASS |

VALIDATION:  
TypeScript: **PASS** — `npm run typecheck`  
Tests: **PASS — 89/89**, five test files, no skipped tests  
Production build: **PASS** — `npm run build`

The original 41 scenarios remain; changed field names and demotion expectations
were updated to the audited contract. Forty-eight regression cases were added.
Tests use jsdom and fake-indexeddb; the database tests execute Dexie's actual
version-upgrade and transaction logic against the test IndexedDB implementation.
MES weights, scheduler multipliers, personal-factor bounds, thirteen skills,
four popover levels, and the Vite/strict TypeScript setup are preserved.
No Phase 2 implementation or UI redesign was performed.

FINAL:  
**FAZ 1 = PASS**

🔒 FAZ 1 = FROZEN / READY FOR PHASE 2
