import { describe, expect, it } from 'vitest';
import { wilsonInterval, outwardPercentRange } from '../../../src/services/performance/statistics';

describe('Phase 6 Wilson contract', () => {
  it('empty evidence has no interval', () => { expect(wilsonInterval(0, 0)).toBeNull(); });
  it('matches the published Wilson expression for 50/100', () => {
    const range = wilsonInterval(50, 100)!;
    expect(range.lower_bound).toBeCloseTo(0.4038315304, 9);
    expect(range.upper_bound).toBeCloseTo(0.5961684696, 9);
    expect(range.confidence_level).toBe(.95);
  });
  it.each([[0, 1], [1, 1], [0, 100], [100, 100], [500_000, 1_000_000]])('is bounded for %i/%i', (correct, n) => {
    const range = wilsonInterval(correct, n)!;
    expect(range.lower_bound).toBeGreaterThanOrEqual(0);
    expect(range.upper_bound).toBeLessThanOrEqual(1);
    expect(range.lower_bound).toBeLessThanOrEqual(range.upper_bound);
    expect(range.sample_size).toBe(n);
  });
  it('does not become certain after a single correct answer', () => {
    expect(wilsonInterval(1, 1)!.lower_bound).toBeLessThan(.21);
    expect(wilsonInterval(0, 1)!.upper_bound).toBeGreaterThan(.79);
  });
  it('narrows with more evidence at the same observed rate', () => {
    const small = wilsonInterval(5, 10)!, large = wilsonInterval(50, 100)!;
    expect(large.upper_bound - large.lower_bound).toBeLessThan(small.upper_bound - small.lower_bound);
  });
  it.each([[-1, 5], [6, 5], [1.5, 5], [1, -1], [NaN, 1], [1, Infinity], [1, Number.MAX_SAFE_INTEGER + 1]])('rejects invalid counts %s/%s', (c, n) => {
    expect(() => wilsonInterval(c, n)).toThrow();
  });
  it('rounds display bounds outwards; percentage is explicitly not exam points', () => {
    expect(outwardPercentRange(wilsonInterval(50, 100)!)).toEqual({ lower_percent: 40, upper_percent: 60, unit: 'CORRECT_RESPONSE_PERCENT' });
  });
});
