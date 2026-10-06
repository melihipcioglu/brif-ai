import type { ExamBlueprint } from '../../types/exam';
import { QUESTION_FAMILIES } from '../../types/question';
import { PERFORMANCE_CONTENT_SKILLS } from '../performance/calibration';

export const cellKey = (family: string, skill: string): string => `${family}|${skill}`;
interface Edge { to: number; capacity: number; reverse: number; initial: number }
/** Exact bipartite max-flow for primary-skill minima under family quotas; at most 22 nodes. */
export function allocateMinimums(blueprint: ExamBlueprint, capacities: ReadonlyMap<string, number>): { readonly cells: ReadonlyMap<string, number>; readonly shortfall: number } {
  const skills = PERFORMANCE_CONTENT_SKILLS, families = QUESTION_FAMILIES;
  const sink = 1 + skills.length + families.length, graph: Edge[][] = Array.from({ length: sink + 1 }, () => []);
  function edge(from: number, to: number, capacity: number): Edge {
    const a: Edge = { to, capacity, initial: capacity, reverse: graph[to]!.length };
    const b: Edge = { to: from, capacity: 0, initial: 0, reverse: graph[from]!.length };
    graph[from]!.push(a); graph[to]!.push(b); return a;
  }
  const tracked = new Map<string, Edge>(); let required = 0;
  skills.forEach((s, i) => {
    const n = blueprint.skill_minimums[s] ?? 0; required += n; edge(0, 1 + i, n);
    families.forEach((f, j) => { const key = cellKey(f, s); tracked.set(key, edge(1 + i, 1 + skills.length + j, capacities.get(key) ?? 0)); });
  });
  families.forEach((f, j) => edge(1 + skills.length + j, sink, blueprint.family_targets[f] ?? 0));
  let flow = 0;
  while (true) {
    const parent = new Map<number, { from: number; edge: Edge }>(), queue = [0]; parent.set(0, { from: 0, edge: { to: 0, capacity: 0, reverse: 0, initial: 0 } });
    for (let at = 0; at < queue.length && !parent.has(sink); at++) {
      const from = queue[at]!;
      for (const e of graph[from]!) if (e.capacity > 0 && !parent.has(e.to)) { parent.set(e.to, { from, edge: e }); queue.push(e.to); }
    }
    if (!parent.has(sink)) break;
    let amount = Number.MAX_SAFE_INTEGER;
    for (let v = sink; v !== 0;) { const p = parent.get(v)!; amount = Math.min(amount, p.edge.capacity); v = p.from; }
    for (let v = sink; v !== 0;) { const p = parent.get(v)!; p.edge.capacity -= amount; graph[v]![p.edge.reverse]!.capacity += amount; v = p.from; }
    flow += amount;
  }
  return { cells: new Map([...tracked].map(([key, e]) => [key, e.initial - e.capacity])), shortfall: required - flow };
}
