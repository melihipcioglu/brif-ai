import type { AdaptiveStudySession, SessionBlock, SessionEvent, SessionPlan } from '../../types/session';
import { deepFreeze } from '../questions/attempts';
import { canonicalEvidence } from '../evidence/validation';
import { sessionEventSchema, sessionPlanSchema } from './validation';

type Mutable<T> = { -readonly [K in keyof T]: T[K] };
/** Replayable state machine. It never turns planned content or completion clicks into learning evidence. */
export function projectAdaptiveSession(planInput: SessionPlan, eventInputs: readonly SessionEvent[]): AdaptiveStudySession {
  const plan = sessionPlanSchema.parse(planInput);
  const events = eventInputs.map((e) => sessionEventSchema.parse(e)).sort((a, b) => a.sequence - b.sequence);
  const emptyActual = () => ({ completed_question_ids: [] as string[], completed_lexical_ids: [] as string[], question_attempt_ids: [] as string[], lexical_attempt_ids: [] as string[] });
  const blocks: Mutable<SessionBlock>[] = plan.blocks.map((b) => ({ ...b, ...emptyActual(), status: 'PLANNED', started_at: null, completed_at: null, actual_duration_ms: null }));
  const state: Mutable<AdaptiveStudySession> = { id: plan.session_id, mode: plan.mode, planned_minutes: plan.planned_minutes,
    total_budget_minutes: plan.planned_minutes, started_at: null, ended_at: null, status: 'PLANNED', blocks,
    actual_active_ms: 0, pause_ms: 0, wall_clock_ms: 0, questions_attempted: 0, lexical_reviews_completed: 0,
    engaged: false, last_event_at: plan.created_at, revision: 0 };
  const eventIds = new Set<string>(), attemptRefs = new Set<string>(), planIds = new Set([plan.id]);
  const recorded: { block_id: string; kind: 'QUESTION' | 'LEXICAL'; item_id: string; attempt_id: string }[] = [];
  function fail(message: string): never { throw new RangeError(message); }
  for (const event of events) {
    if (event.session_id !== state.id || event.sequence !== state.revision + 1 || event.at < state.last_event_at || eventIds.has(event.id)) fail('Invalid event order or session');
    const cmd = event.command;
    const active = blocks.find((b) => b.status === 'ACTIVE');
    const delta = state.started_at === null ? 0 : event.at - state.last_event_at;
    if (state.status === 'ACTIVE' || cmd.type === 'EXTEND' && state.status === 'COMPLETED') {
      const credited = state.status === 'ACTIVE' && state.engaged && delta <= plan.config.idle_lease_ms ? delta : 0;
      state.actual_active_ms += credited; state.pause_ms += delta - credited; state.wall_clock_ms += delta;
      if (active) active.actual_duration_ms = (active.actual_duration_ms ?? 0) + credited;
    }
    const block = 'block_id' in cmd ? blocks.find((b) => b.id === cmd.block_id) : undefined;
    if ('block_id' in cmd && block === undefined) fail('Unknown block');
    if (cmd.type !== 'START' && cmd.type !== 'EXTEND' && state.status !== 'ACTIVE') fail('Session is not active');
    switch (cmd.type) {
      case 'START':
        if (state.status !== 'PLANNED') fail('Session already started');
        state.status = 'ACTIVE'; state.started_at = event.at; state.engaged = true; break;
      case 'PAUSE': state.engaged = false; break;
      case 'RESUME': state.engaged = true; break;
      case 'PULSE': state.engaged = cmd.engaged; break;
      case 'START_BLOCK':
        if (active || block?.status !== 'PLANNED') fail('Another block is active or block already executed');
        block.status = 'ACTIVE'; block.started_at = event.at; block.actual_duration_ms = 0; state.engaged = true; break;
      case 'QUESTION': case 'LEXICAL': {
        if (block?.status !== 'ACTIVE') fail('Actual result requires an active block');
        const expected = cmd.type === 'QUESTION' ? block.question_ids : block.lexical_ids;
        if (!expected.includes(cmd.item_id)) fail('Actual item is outside block');
        const ref = `${cmd.type}:${cmd.attempt_id}`;
        if (event.attempt_ref !== ref || attemptRefs.has(ref)) fail('Repeated or invalid attempt reference');
        const previous = [...recorded].reverse().find((r) => r.kind === cmd.type && r.item_id === cmd.item_id);
        if (previous ? cmd.retry_of !== previous.attempt_id : cmd.retry_of !== null) fail('Repeated item requires explicit retry linkage');
        attemptRefs.add(ref); recorded.push({ block_id: block.id, kind: cmd.type, item_id: cmd.item_id, attempt_id: cmd.attempt_id });
        if (cmd.type === 'QUESTION') {
          state.questions_attempted += 1; block.question_attempt_ids = [...block.question_attempt_ids, cmd.attempt_id];
          block.completed_question_ids = [...new Set([...block.completed_question_ids, cmd.item_id])];
        } else {
          state.lexical_reviews_completed += 1; block.lexical_attempt_ids = [...block.lexical_attempt_ids, cmd.attempt_id];
          block.completed_lexical_ids = [...new Set([...block.completed_lexical_ids, cmd.item_id])];
        }
        break;
      }
      case 'COMPLETE_BLOCK': {
        if (block?.status !== 'ACTIVE') fail('Only active blocks can complete');
        const done = recorded.filter((r) => r.block_id === block.id);
        if (block.type !== 'TIMED_BLOCK' && (block.question_ids.some((id) => !done.some((r) => r.kind === 'QUESTION' && r.item_id === id)) ||
          block.lexical_ids.some((id) => !done.some((r) => r.kind === 'LEXICAL' && r.item_id === id)))) fail('Actual content is not completed');
        block.status = 'COMPLETED'; block.completed_at = event.at; break;
      }
      case 'SKIP_BLOCK':
        if (block?.status !== 'PLANNED' && block?.status !== 'ACTIVE') fail('Block already finalized');
        if (cmd.reason === 'ADAPTATION' && active) fail('Adaptation requires a block boundary');
        block.status = 'SKIPPED'; block.completed_at = event.at; block.actual_duration_ms ??= 0; break;
      case 'FINISH':
        if (blocks.some((b) => b.status === 'ACTIVE' || b.status === 'PLANNED')) fail('Unfinished blocks remain');
        state.status = 'COMPLETED'; state.ended_at = event.at; state.engaged = false; break;
      case 'ABANDON':
        for (const b of blocks) if (b.status === 'PLANNED' || b.status === 'ACTIVE') { b.status = 'SKIPPED'; b.completed_at = event.at; b.actual_duration_ms ??= 0; }
        state.status = 'ABANDONED'; state.ended_at = event.at; state.engaged = false; break;
      case 'EXTEND': {
        if (active || !['ACTIVE', 'COMPLETED'].includes(state.status)) fail('Extension/adaptation requires a block boundary');
        const extension = cmd.plan;
        if (extension.session_id !== plan.session_id || extension.mode !== plan.mode || extension.created_at !== event.at || planIds.has(extension.id) ||
          canonicalEvidence(extension.config) !== canonicalEvidence(plan.config)) fail('Invalid extension identity or configuration');
        const occupied = new Set(blocks.flatMap((b) => [...b.candidate_ids.map((id) => `c:${id}`), ...b.question_ids.map((id) => `q:${id}`), ...b.lexical_ids.map((id) => `l:${id}`), `b:${b.id}`]));
        for (const b of extension.blocks) {
          if ([...b.candidate_ids.map((id) => `c:${id}`), ...b.question_ids.map((id) => `q:${id}`), ...b.lexical_ids.map((id) => `l:${id}`), `b:${b.id}`].some((key) => occupied.has(key))) fail('Extension repeats session content');
          blocks.push({ ...b, ...emptyActual(), status: 'PLANNED', started_at: null, completed_at: null, actual_duration_ms: null });
        }
        planIds.add(extension.id); state.total_budget_minutes += extension.planned_minutes;
        state.status = 'ACTIVE'; state.ended_at = null; state.engaged = false; break;
      }
    }
    if (!['QUESTION', 'LEXICAL'].includes(cmd.type) && event.attempt_ref !== undefined) fail('Unexpected attempt reference');
    state.last_event_at = event.at; state.revision = event.sequence; eventIds.add(event.id);
  }
  return deepFreeze(state);
}
