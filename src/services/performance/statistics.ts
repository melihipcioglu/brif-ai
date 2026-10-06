import type { PerformanceRange } from '../../types/performance';
import { DEFAULT_CONFIDENCE_LEVEL, WILSON_Z_95 } from './calibration';

/** Two-sided Wilson score interval. NIST handbook PRC 7.2.4.1; no Wald approximation. */
export function wilsonInterval(correct: number, sampleSize: number): PerformanceRange | null {
  if (!Number.isSafeInteger(correct) || !Number.isSafeInteger(sampleSize) || correct < 0 || sampleSize < 0 || correct > sampleSize) {
    throw new RangeError('Counts must be nonnegative safe integers with correct <= sample size');
  }
  if (sampleSize === 0) return null;
  const p = correct / sampleSize, z2 = WILSON_Z_95 ** 2, adjustment = z2 / sampleSize;
  const denominator = 1 + adjustment;
  const center = (p + adjustment / 2) / denominator;
  const halfWidth = WILSON_Z_95 * Math.sqrt((p * (1 - p) + adjustment / 4) / sampleSize) / denominator;
  return Object.freeze({ lower_bound: correct === 0 ? 0 : Math.max(0, center - halfWidth),
    upper_bound: correct === sampleSize ? 1 : Math.min(1, center + halfWidth),
    confidence_level: DEFAULT_CONFIDENCE_LEVEL, sample_size: sampleSize, method: 'WILSON', unit: 'CORRECT_RESPONSE_PROPORTION' });
}
/** Display only: outward whole percentages, explicitly NOT exam points. */
export function outwardPercentRange(range: PerformanceRange): { readonly lower_percent: number; readonly upper_percent: number; readonly unit: 'CORRECT_RESPONSE_PERCENT' } {
  if (!Number.isFinite(range.lower_bound) || !Number.isFinite(range.upper_bound) || range.lower_bound < 0 || range.upper_bound > 1 || range.lower_bound > range.upper_bound) throw new RangeError('Invalid range bounds');
  return Object.freeze({ lower_percent: Math.floor(range.lower_bound * 100), upper_percent: Math.ceil(range.upper_bound * 100), unit: 'CORRECT_RESPONSE_PERCENT' });
}
