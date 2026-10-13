import type { InteractiveDecompositionTask } from '../../types/learning';

export const INTERACTIVE_DECOMPOSITION_TASKS: readonly InteractiveDecompositionTask[] = [
  // 1. I DO (ÖĞRETMEN MODELİ: Sistem Gösterir ve İnteraktif Ayrıştırır)
  {
    id: 'DECOMP_01_I_DO',
    mode: 'I_DO',
    sentence: 'Although the central nervous system possesses neuroplasticity, neural tissues become susceptible to oxidative stress.',
    prompt: 'ÖĞRETMEN MODELİ (I DO): Cümlenin ögelerine tıklayarak sözdizimi rollerini ve aralarındaki anlam bağını inceleyin.',
    targetRole: 'VERB',
    correctTokenIndices: [5], // "become"
    tokens: [
      { text: 'Although', role: 'CONNECTOR', explanation_tr: 'Zıtlık / Ödün Bağlacı: "Her ne kadar ... olsa da" anlamı katar.' },
      { text: 'the central nervous system', role: 'SUBORDINATE', explanation_tr: 'Yan Cümle Öznesi: Merkezi sinir sistemi' },
      { text: 'possesses', role: 'SUBORDINATE', explanation_tr: 'Yan Cümle Fiili: Sahiptir (Although bağlacına bağlıdır)' },
      { text: 'neuroplasticity,', role: 'SUBORDINATE', explanation_tr: 'Yan Cümle Nesnesi: Nöroplastisiteye' },
      { text: 'neural tissues', role: 'SUBJECT', explanation_tr: 'ANA CÜMLE ÖZNESİ: Sinir dokuları (Asıl eylemi yapan)' },
      { text: 'become', role: 'VERB', explanation_tr: 'ANA CÜMLE FİİLİ (Temel Yüklem): Hale gelir / dönüşür' },
      { text: 'susceptible', role: 'MODIFIER', explanation_tr: 'Sıfat / Yüklem Tamamlayıcısı: Savunmasız, duyarlı' },
      { text: 'to oxidative stress.', role: 'OBJECT', explanation_tr: 'Edat Öbeği / Tamamlayıcı: Oksidatif strese karşı' }
    ],
    pedagogicalRationale: 'Uzun YÖKDİL cümlelerini okurken ilk refleksiniz: Bağlaçla başlayan yan cümleyi (possesses) ana cümlenin asıl yükleminden (become) ayırmaktır.',
    tokenExplanations: {
      0: 'Although zıtlık bağlacıdır; virgüle kadar olan kısmı ana cümlenin zıddı bir bağlama oturtur.',
      4: 'neural tissues ana cümlenin gerçek öznesidir.',
      5: 'become cümlenin ana yüklemidir (asıl mesaj sinir dokularının savunmasız hale gelmesidir).'
    }
  },

  // 2. WE DO (BİRLİKTE YAPIYORUZ: Yönlendirmeli İskele)
  {
    id: 'DECOMP_02_WE_DO',
    mode: 'WE_DO',
    sentence: 'Enzymes that catalyze metabolic reactions accelerate cellular energy production.',
    prompt: 'BİRLİKTE ÇÖZÜMLEME (WE DO): Bu cümlenin ANA FİİLİNE (yüklemine) tıklayın. Sıfat cümleciği (that...) tuzağına dikkat edin!',
    targetRole: 'VERB',
    correctTokenIndices: [4], // "accelerate"
    tokens: [
      { text: 'Enzymes', role: 'SUBJECT', explanation_tr: 'Ana Özne: Enzimler' },
      { text: 'that', role: 'SUBORDINATE', explanation_tr: 'İlgi Zamiri (Relative Pronoun): Enzimleri niteleyen sıfat cümleciğini başlatır' },
      { text: 'catalyze', role: 'SUBORDINATE', explanation_tr: 'Sıfat Cümleciği Fiili: Katalizleyen' },
      { text: 'metabolic reactions', role: 'SUBORDINATE', explanation_tr: 'Sıfat Cümleciği Nesnesi: Metabolik reaksiyonları' },
      { text: 'accelerate', role: 'VERB', explanation_tr: 'ANA CÜMLE FİİLİ: Hızlandırır (Enzimlerin asıl yaptığı iş)' },
      { text: 'cellular energy production.', role: 'OBJECT', explanation_tr: 'Ana Cümle Nesnesi: Hücresel enerji üretimini' }
    ],
    pedagogicalRationale: 'Sınavda en çok düşülen tuzak: "that catalyze" içindeki fiili ana fiil sanmaktır. Oysa "that catalyze metabolic reactions" sadece enzimleri niteleyen bir sıfattır.',
    tokenExplanations: {
      0: 'Enzymes cümlenin öznesidir, aradığımız eylem (fiil) değildir.',
      1: '"that", sıfat cümleciğini açan bağlaçtır.',
      2: 'TUZAK! "catalyze" bir fiildir fakat "that" sıfat cümleciğinin içindedir. Cümlenin asıl yüklemi değildir!',
      3: 'metabolic reactions sıfat cümleciğinin nesnesidir.',
      4: 'DOĞRU! "accelerate" (hızlandırır) tüm cümlenin ana yüklemidir.',
      5: 'cellular energy production eylemden etkilenen nesnedir.'
    }
  },

  // 3. YOU DO (SEN ÇÖZÜYORSUN: Bağımsız Çözümleme)
  {
    id: 'DECOMP_03_YOU_DO',
    mode: 'YOU_DO',
    sentence: 'Because global temperatures increase continuously, polar ice caps melt at an unprecedented rate.',
    prompt: 'BAĞIMSIZ ÇÖZÜMLEME (YOU DO): Ana cümlenin temel eylemini bildiren ANA FİİLE (yükleme) tıklayın.',
    targetRole: 'VERB',
    correctTokenIndices: [5], // "melt"
    tokens: [
      { text: 'Because', role: 'CONNECTOR', explanation_tr: 'Sebep Bağlacı: -dığı için' },
      { text: 'global temperatures', role: 'SUBORDINATE', explanation_tr: 'Yan Cümle Öznesi' },
      { text: 'increase', role: 'SUBORDINATE', explanation_tr: 'Yan Cümle Fiili (Sebep)' },
      { text: 'continuously,', role: 'SUBORDINATE', explanation_tr: 'Zarf' },
      { text: 'polar ice caps', role: 'SUBJECT', explanation_tr: 'ANA CÜMLE ÖZNESİ: Kutup buzulları' },
      { text: 'melt', role: 'VERB', explanation_tr: 'ANA CÜMLE FİİLİ: Erir (Asıl sonuç eylemi)' },
      { text: 'at an unprecedented rate.', role: 'MODIFIER', explanation_tr: 'Zarf Öbeği: Benzeri görülmemiş bir hızla' }
    ],
    pedagogicalRationale: 'Because yan cümlesindeki "increase" sebebi bildirir; ana cümlenin asıl mesajı ise kutup buzullarının "melt" (erimesi) eylemidir.',
    tokenExplanations: {
      0: 'Because sebep bağlacıdır.',
      1: 'global temperatures yan cümlenin öznesidir.',
      2: 'DİKKAT: "increase" sebep cümlesinin fiilidir, ana cümlenin asıl yüklemi değildir!',
      4: 'polar ice caps ana cümlenin öznesidir.',
      5: 'TEBRİKLER! "melt" (erimek) ana cümlenin temel yüklemidir.',
      6: 'at an unprecedented rate niteleyici öbektir.'
    }
  }
];
