import type { Question } from '../../types/question';
import { canonicalEvidence } from '../evidence/validation';

export const compareText = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;
const normalized = (s: string): string => s.normalize('NFKC').toLowerCase().replace(/\s+/gu, ' ').trim();
export function questionContentKey(q: Question): string {
  return canonicalEvidence({ stem: normalized(q.stem), passage: normalized(q.passage ?? ''), options: q.options.map((o) => normalized(o.text)).sort(compareText) });
}
/** Stable consistency fingerprint, NOT a cryptographic proof of source authenticity. */
export function fingerprint(value: unknown): string {
  const text = canonicalEvidence(value); let a = 2166136261, b = 2246822507;
  for (let i = 0; i < text.length; i++) { const n = text.charCodeAt(i); a = Math.imul(a ^ n, 16777619); b = Math.imul(b ^ n, 3266489909); }
  return `${(a >>> 0).toString(16).padStart(8, '0')}${(b >>> 0).toString(16).padStart(8, '0')}`;
}
