/**
 * BRIF.AI — Demo Intent Parser & Text Normalizer (v5.1 Engine)
 *
 * Provides robust Turkish text normalization and state-aware intent parsing.
 */

class DemoIntentParser {
  constructor() {
    // Intent definitions with pattern arrays
    this.masterBathInitialPatterns = [
      /ebeveyn banyos/i,
      /banyoyu kuzey/i,
      /banyo kuzey/i,
      /banyoyu taş/i,
      /banyonun yerini değ/i
    ];

    this.masterBathReasonPatterns = {
      visibility: [
        /yataktan gör/i,
        /yataktan bak/i,
        /yatağın karşıs/i,
        /görünmesin/i,
        /görünmesini istem/i,
        /görmek istem/i
      ],
      dressing: [
        /giyinme/i,
        /giyinmeden/i,
        /giyinme odas/i,
        /giyinme alan/i
      ],
      privacy: [
        /mahrem/i,
        /gizli/i,
        /izole/i,
        /özel kal/i
      ],
      service_facade: [
        /kuzey cephe/i,
        /servis alan/i,
        /kuzey taraf/i
      ]
    };
  }

  normalizeText(text) {
    if (!text) return '';
    let str = text.toLowerCase().trim();
    // Turkish char replacement for soft matching
    str = str.replace(/ı/g, 'i')
             .replace(/ğ/g, 'g')
             .replace(/ü/g, 'u')
             .replace(/ş/g, 's')
             .replace(/ö/g, 'o')
             .replace(/ç/g, 'c');
    return str;
  }

  isMasterBathInitial(text) {
    const norm = this.normalizeText(text);
    return this.masterBathInitialPatterns.some(p => p.test(text) || p.test(norm));
  }

  parseMasterBathReason(text) {
    const norm = this.normalizeText(text);

    for (const p of this.masterBathReasonPatterns.visibility) {
      if (p.test(text) || p.test(norm)) return 'visibility';
    }
    for (const p of this.masterBathReasonPatterns.dressing) {
      if (p.test(text) || p.test(norm)) return 'dressing';
    }
    for (const p of this.masterBathReasonPatterns.privacy) {
      if (p.test(text) || p.test(norm)) return 'privacy';
    }
    for (const p of this.masterBathReasonPatterns.service_facade) {
      if (p.test(text) || p.test(norm)) return 'service_facade';
    }

    // Default reason fallback if reason matched generally
    return 'privacy';
  }
}

// Global Export
window.DemoIntentParser = DemoIntentParser;
