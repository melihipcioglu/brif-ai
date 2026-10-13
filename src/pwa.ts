declare const __PWA_ENABLED__: boolean | undefined;

/** Registers the offline service worker (production builds served over HTTPS or localhost only). */
export function registerServiceWorker(): void {
  if (typeof __PWA_ENABLED__ === 'undefined' || !__PWA_ENABLED__) return;
  if (!('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {
      /* offline mode is an enhancement; the app works without it */
    });
  });
}
