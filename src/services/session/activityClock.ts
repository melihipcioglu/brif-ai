import type { Question } from '../../types/question';
import type { AdaptiveStudySession } from '../../types/session';
import { executeSessionCommand, restoreAdaptiveSession, sessionDb, type SessionDatabase } from './db';
import { sessionPlanSchema } from './validation';

export function isSessionEngaged(visible: boolean, focused: boolean, lastInteractionAt: number, now: number, inactivityMs: number): boolean {
  if (![lastInteractionAt, now, inactivityMs].every(Number.isFinite) || inactivityMs <= 0 || now < lastInteractionAt) return false;
  return visible && focused && now - lastInteractionAt < inactivityMs;
}

/** Optional browser integration: visibility/focus and an idle timestamp only; no keys, coordinates or content are captured.
 * Call stop() on unmount/navigation. A missing heartbeat after a crash is handled by the journal lease.
 */
export async function attachSessionActivityClock(sessionId: string, questions: readonly Question[], options: {
  readonly onError: (error: unknown) => void;
  readonly onState?: (state: AdaptiveStudySession) => void;
}, database: SessionDatabase = sessionDb): Promise<{ readonly stop: () => Promise<void> }> {
  if (typeof window === 'undefined' || typeof document === 'undefined') throw new Error('Activity clock requires a browser');
  const plan = sessionPlanSchema.parse(await database.adaptive_sessions.get(sessionId));
  let stopped = false; let queue: Promise<void> = Promise.resolve();
  let lastInteractionAt = Date.now();
  const pulse = (engaged: boolean): void => {
    const at = Date.now();
    queue = queue.then(async () => {
      const state = await restoreAdaptiveSession(sessionId, database);
      if (state.status !== 'ACTIVE') return;
      const next = await executeSessionCommand({ id: crypto.randomUUID(), session_id: sessionId, at: Math.max(at, state.last_event_at),
        command: { type: 'PULSE', engaged } }, state.revision, questions, database);
      options.onState?.(next);
    }).catch((error: unknown) => { options.onError(error); });
  };
  const activity = (): void => { if (!stopped) pulse(isSessionEngaged(document.visibilityState === 'visible', document.hasFocus(), lastInteractionAt, Date.now(), plan.config.inactivity_ms)); };
  const interaction = (): void => { lastInteractionAt = Date.now(); };
  const focused = (): void => { interaction(); activity(); };
  const interval = window.setInterval(activity, Math.min(10_000, Math.floor(plan.config.idle_lease_ms / 3)));
  document.addEventListener('visibilitychange', activity); window.addEventListener('focus', focused); window.addEventListener('blur', activity);
  window.addEventListener('pointerdown', interaction, { passive: true }); window.addEventListener('keydown', interaction); activity();
  return { stop: async () => {
    if (stopped) return queue; stopped = true; window.clearInterval(interval);
    document.removeEventListener('visibilitychange', activity); window.removeEventListener('focus', focused); window.removeEventListener('blur', activity);
    window.removeEventListener('pointerdown', interaction); window.removeEventListener('keydown', interaction);
    pulse(false); await queue;
  } };
}
