import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  startExamSession,
  finishExamSession,
  loadActiveExamSession,
  clearActiveExamSession,
  getStoredLearnerExposures,
  clearStoredLearnerExposures,
  clearExamHistory,
  getExamHistory
} from '../../../src/services/exam/examSessionService';

describe('Phase 12: Security, Clock Tampering & Edge Cases', () => {
  beforeEach(() => {
    localStorage.clear();
    clearActiveExamSession();
    clearStoredLearnerExposures();
    clearExamHistory();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    clearActiveExamSession();
  });

  it('detects and flags backward client-side clock tampering fail-closed', async () => {
    const session = await startExamSession('SHORT_EXAM_QUICK');

    // Simulate clock jump backwards (completedAt < startedAt)
    const tamperedSession = {
      ...session,
      startedAt: Date.now() + 500000 // future start time relative to current Date.now()
    };

    const report = await finishExamSession(tamperedSession);

    // Tampering detected!
    expect(report.isClockTampered).toBe(true);
    // Elapsed time clamped to 0 rather than negative
    expect(report.totalTimeMs).toBe(0);
  });

  it('handles corrupted localStorage session state safely and recovers', () => {
    // Write invalid JSON
    localStorage.setItem('arcbrief_active_exam_session_v1', '{ invalid json ...');
    const loaded = loadActiveExamSession();
    expect(loaded).toBeNull();

    // Write empty or incomplete object
    localStorage.setItem('arcbrief_active_exam_session_v1', JSON.stringify({ id: 'bad' }));
    const badLoad = loadActiveExamSession();
    expect(badLoad).toBeNull();
  });

  it('records exposures accurately so subsequent forms track seen questions', async () => {
    const session1 = await startExamSession('FULL_EXAM');
    expect(session1.form.questions.length).toBe(80);

    // Finish session 1
    await finishExamSession(session1);

    // Exposures must contain all 80 questions from Form 1
    const exposures = getStoredLearnerExposures();
    expect(Object.keys(exposures).length).toBe(80);
    for (const q of session1.form.questions) {
      expect(exposures[q.id]?.count).toBe(1);
    }

    // Start session 2 - it should build second disjoint form from remaining 80 questions!
    const session2 = await startExamSession('FULL_EXAM');
    expect(session2.form.questions.length).toBe(80);

    // Verify 0 overlap between Form 1 and Form 2 questions
    const form1Ids = new Set(session1.form.questions.map((q) => q.id));
    const form2Ids = new Set(session2.form.questions.map((q) => q.id));

    let overlap = 0;
    for (const id of form2Ids) {
      if (form1Ids.has(id)) overlap++;
    }
    expect(overlap).toBe(0);
  });

  it('stores and retrieves exam history entries without corruption', async () => {
    const session = await startExamSession('SHORT_EXAM_QUICK');
    // Answer all questions correctly
    for (const q of session.form.questions) {
      session.answers[q.id] = q.correct_option;
    }
    const report = await finishExamSession(session);

    expect(report.correctCount).toBe(session.form.questions.length);
    expect(report.yokdilScore).toBe(100);
    expect(report.target80Met).toBe(true);

    const history = getExamHistory();
    expect(history.length).toBe(1);
    expect(history[0]!.yokdilScore).toBe(100);
    expect(history[0]!.totalQuestions).toBe(session.form.questions.length);
  });
});
