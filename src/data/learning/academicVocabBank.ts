import type { AcademicVocabEntry, WordProgressionStep, TrapWordComparison } from '../../types/learning';

/**
 * Curated Academic Science Vocabulary Bank for YÖKDİL Fen preparation.
 * Contains high-yield academic science lemmas across Biology, Chemistry, Physics,
 * Medicine, Environmental Science, and Technology.
 */
export const academicVocabBank: readonly AcademicVocabEntry[] = [
  // --- BIOLOGY & MEDICINE ---
  {
    word_id: 'inhibit',
    lemma: 'inhibit',
    pos: 'verb',
    tier: 1,
    priority_score: 98,
    meaning_tr: 'engellemek; bir süreç veya biyokimyasal reaksiyonu baskılamak',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'verb', form: 'inhibit', meaning_tr: 'engellemek' },
      { pos: 'noun', form: 'inhibition', meaning_tr: 'baskılama; engelleme' },
      { pos: 'noun', form: 'inhibitor', meaning_tr: 'inhibitör; baskılayıcı molekül' },
      { pos: 'adjective', form: 'inhibitory', meaning_tr: 'baskılayıcı' }
    ],
    science_domain: 'biology',
    exam_sentence: 'Specific chemical compounds can inhibit the proliferation of malignant cancer cells without damaging healthy tissues.',
    exam_sentence_tr: 'Belirli kimyasal bileşikler, sağlıklı dokulara zarar vermeden kötü huylu kanser hücrelerinin çoğalmasını baskılayabilir.',
    critical_collocations: [
      { phrase: 'inhibit growth', meaning_tr: 'büyümeyi baskılamak' },
      { phrase: 'inhibit enzyme activity', meaning_tr: 'enzim aktivitesini engellemek' },
      { phrase: 'inhibit the synthesis of', meaning_tr: 'sentezini baskılamak' }
    ],
    synonyms: ['suppress', 'restrain', 'hinder', 'impede'],
    antonyms: ['stimulate', 'promote', 'facilitate', 'trigger'],
    mnemonic_hint: 'Latince "in-habere" (tutmak, alıkoymak). İçeride tutup ilerlemesini "inhibe" etmek / engellemek.',
    distractors: [
      { word: 'inhabit', meaning_tr: 'ikamet etmek; yaşamak', explanation_tr: 'Yazılışı benzerdir fakat bir yerde yaşamayı belirtir.' },
      { word: 'exhibit', meaning_tr: 'sergilemek; göstermek', explanation_tr: 'Bir özelliği ortaya koymaktır; baskılamak değildir.' },
      { word: 'inherit', meaning_tr: 'miras almak; kalıtımla devralmak', explanation_tr: 'Genetik aktarımı anlatır, engelleme değildir.' }
    ],
    trap_words: [
      {
        trapWord: 'inhabit',
        trapMeaning: 'yaşamak, ikamet etmek',
        confusionReason: 'Yazılışı neredeyse aynıdır (h-i vs h-a).',
        memoryHook: 'Habitat (yaşam alanı) kökünden hatırlayın: Inhabit = yaşamak.'
      },
      {
        trapWord: 'exhibit',
        trapMeaning: 'sergilemek, göstermek',
        confusionReason: 'Benzer hece yapısı ve son ek (-hibit).',
        memoryHook: 'Exhibition (sergi) kökünden hatırlayın: Exhibit = sergilemek.'
      }
    ],
    progression: [
      {
        level: 0,
        title: 'Atom Cümle (Temel İskelet)',
        englishText: 'Cold inhibits bacteria.',
        turkishTranslation: 'Soğuk, bakteriyi durdurur / engeller.',
        focusPoint: 'En basit haliyle: [Özne] + INHIBIT + [Nesne]. Eylemin yönü frenlemektir.',
        tokens: [
          { text: 'Cold', role: 'SUBJECT', explanation_tr: 'Özne (Eylemi yapan)' },
          { text: 'inhibits', role: 'VERB', explanation_tr: 'Fiil (Engeller / frenler)', isTargetWord: true },
          { text: 'bacteria.', role: 'OBJECT', explanation_tr: 'Nesne (Etkilenen)' }
        ]
      },
      {
        level: 1,
        title: '1. Basamak Genişletme (Bilinen Kelimelerle)',
        englishText: 'Low temperatures inhibit the growth of bacteria.',
        turkishTranslation: 'Düşük sıcaklıklar bakterilerin büyümesini engeller.',
        focusPoint: 'Cümleye sadece bir tamlama eklendi: "the growth of" (büyümesini).',
        tokens: [
          { text: 'Low temperatures', role: 'SUBJECT', explanation_tr: 'Özne tamlaması' },
          { text: 'inhibit', role: 'VERB', explanation_tr: 'Fiil', isTargetWord: true },
          { text: 'the growth of bacteria.', role: 'OBJECT', explanation_tr: 'Nesne grubu' }
        ]
      },
      {
        level: 2,
        title: '2. Basamak: Fen Kalıbı ve Neden-Sonuç',
        englishText: 'Because cold inhibits bacterial growth, fresh food lasts longer.',
        turkishTranslation: 'Soğuk bakteri gelişimini engellediği için, taze gıdalar daha uzun süre dayanır.',
        focusPoint: 'Because bağlacıyla fen ilişkisi kuruldu: [Neden: engelleme] -> [Sonuç: dayanma].',
        tokens: [
          { text: 'Because', role: 'CONNECTOR', explanation_tr: 'Sebep bağlacı' },
          { text: 'cold', role: 'SUBORDINATE', explanation_tr: 'Yan cümlenin öznesi' },
          { text: 'inhibits', role: 'VERB', explanation_tr: 'Fiil', isTargetWord: true },
          { text: 'bacterial growth,', role: 'SUBORDINATE', explanation_tr: 'Yan cümlenin nesnesi' },
          { text: 'fresh food lasts longer.', role: 'MODIFIER', explanation_tr: 'Ana cümle' }
        ]
      },
      {
        level: 3,
        title: '3. Basamak: Gerçek YÖKDİL Akademik Cümlesi',
        englishText: 'Specific chemical compounds can inhibit the proliferation of malignant cancer cells.',
        turkishTranslation: 'Belirli kimyasal bileşikler, kötü huylu kanser hücrelerinin çoğalmasını baskılayabilir.',
        focusPoint: 'Akademik süsleri çıkarınca aynı atom kalır: [Compounds] + CAN INHIBIT + [Proliferation].',
        tokens: [
          { text: 'Specific chemical compounds', role: 'SUBJECT', explanation_tr: 'Akademik Özne' },
          { text: 'can inhibit', role: 'VERB', explanation_tr: 'Modal + Ana Fiil', isTargetWord: true },
          { text: 'the proliferation of malignant cancer cells.', role: 'OBJECT', explanation_tr: 'Akademik Nesne Grubu' }
        ]
      }
    ]
  },
  {
    word_id: 'proliferate',
    lemma: 'proliferate',
    pos: 'verb',
    tier: 1,
    priority_score: 95,
    meaning_tr: 'hızla çoğalmak; üremek; sayıca artmak',
    polarity_symbol: '↑',
    word_family: [
      { pos: 'verb', form: 'proliferate', meaning_tr: 'hızla çoğalmak' },
      { pos: 'noun', form: 'proliferation', meaning_tr: 'hızlı çoğalma; yayılma' },
      { pos: 'adjective', form: 'proliferative', meaning_tr: 'çoğalan; üreyen' }
    ],
    science_domain: 'biology',
    exam_sentence: 'When nutrients are abundant, phytoplankton proliferate rapidly near the ocean surface.',
    exam_sentence_tr: 'Besin maddeleri bol olduğunda, fitoplanktonlar okyanus yüzeyine yakın yerlerde hızla çoğalır.',
    critical_collocations: [
      { phrase: 'proliferate rapidly', meaning_tr: 'hızla çoğalmak' },
      { phrase: 'cellular proliferation', meaning_tr: 'hücresel çoğalma' },
      { phrase: 'proliferate in response to', meaning_tr: 'yanıt olarak çoğalmak' }
    ],
    synonyms: ['multiply', 'reproduce', 'escalate', 'burgeon'],
    antonyms: ['dwindle', 'diminish', 'decline'],
    mnemonic_hint: '"Pro-life" kökünden aklınıza gelsin: yaşamın hızla çoğalması, filizlenmesi.',
    distractors: [
      { word: 'propagate', meaning_tr: 'yaymak; üretmek', explanation_tr: 'Benzer olsa da proliferate daha çok organizmanın kendi çoğalmasını anlatır.' },
      { word: 'prolong', meaning_tr: 'süresini uzatmak', explanation_tr: 'Zamanı uzatmayı anlatır; sayısal çoğalma değildir.' },
      { word: 'prohibit', meaning_tr: 'yasaklamak', explanation_tr: 'Engellemektir; çoğalmanın zıttıdır.' }
    ]
  },
  {
    word_id: 'susceptible',
    lemma: 'susceptible',
    pos: 'adjective',
    tier: 1,
    priority_score: 96,
    meaning_tr: 'duyarlı; savunmasız; kolay etkilenen (-e yatkın)',
    polarity_symbol: '=',
    word_family: [
      { pos: 'adjective', form: 'susceptible', meaning_tr: 'duyarlı; savunmasız' },
      { pos: 'noun', form: 'susceptibility', meaning_tr: 'duyarlılık; yatkınlık' }
    ],
    science_domain: 'medicine',
    exam_sentence: 'Individuals with compromised immune systems are particularly susceptible to secondary bacterial infections.',
    exam_sentence_tr: 'Bağışıklık sistemi zayıflamış bireyler, ikincil bakteriyel enfeksiyonlara karşı özellikle savunmasızdır.',
    critical_collocations: [
      { phrase: 'susceptible to infection', meaning_tr: 'enfeksiyona duyarlı' },
      { phrase: 'highly susceptible', meaning_tr: 'oldukça duyarlı / savunmasız' },
      { phrase: 'genetically susceptible', meaning_tr: 'genetik olarak yatkın' }
    ],
    synonyms: ['vulnerable', 'prone to', 'predisposed to'],
    antonyms: ['immune', 'resistant', 'impervious'],
    mnemonic_hint: '"Suspect" (şüphe) gibi savunması açık, kolayca etki "kabul eden" (sus-cept).',
    distractors: [
      { word: 'suspicious', meaning_tr: 'şüpheli', explanation_tr: 'Kuşkulu demektir; biyolojik savunmasızlık değildir.' },
      { word: 'sustainable', meaning_tr: 'sürdürülebilir', explanation_tr: 'Devam ettirilebilir demektir.' },
      { word: 'subsequent', meaning_tr: 'ardından gelen', explanation_tr: 'Zaman sıralamasını anlatır.' }
    ]
  },
  {
    word_id: 'deteriorate',
    lemma: 'deteriorate',
    pos: 'verb',
    tier: 1,
    priority_score: 94,
    meaning_tr: 'kötüleşmek; kalitesi bozulmak; dejenere olmak',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'verb', form: 'deteriorate', meaning_tr: 'kötüleşmek' },
      { pos: 'noun', form: 'deterioration', meaning_tr: 'kötüleşme; bozulma' },
      { pos: 'adjective', form: 'deteriorating', meaning_tr: 'kötüleşen' }
    ],
    science_domain: 'environment',
    exam_sentence: 'If atmospheric pollution levels exceed the critical threshold, pulmonary function will deteriorate progressively.',
    exam_sentence_tr: 'Atmosferik kirlilik seviyeleri kritik eşiği aşarsa, akciğer fonksiyonları giderek kötüleşecektir.',
    critical_collocations: [
      { phrase: 'deteriorate rapidly', meaning_tr: 'hızla kötüleşmek' },
      { phrase: 'deteriorate over time', meaning_tr: 'zamanla bozulmak' },
      { phrase: 'environmental deterioration', meaning_tr: 'çevresel bozulma' }
    ],
    synonyms: ['worsen', 'degrade', 'decline', 'degenerate'],
    antonyms: ['improve', 'ameliorate', 'recover'],
    mnemonic_hint: 'De-terior (daha kötüye gitmek). Kalitenin "deforme" olup kötüleşmesi.',
    distractors: [
      { word: 'determine', meaning_tr: 'belirlemek; saptamak', explanation_tr: 'Bir sonuca varmaktır; kötüleşme değildir.' },
      { word: 'detrimental', meaning_tr: 'zararlı', explanation_tr: 'Sıfattır, eylem olan deteriorate ile karıştırılmamalıdır.' },
      { word: 'deter', meaning_tr: 'caydırıcı olmak', explanation_tr: 'Vazgeçirmektir.' }
    ]
  },

  // --- CHEMISTRY & PHYSICS ---
  {
    word_id: 'accelerate',
    lemma: 'accelerate',
    pos: 'verb',
    tier: 1,
    priority_score: 97,
    meaning_tr: 'hızlandırmak; ivme kazandırmak; hızlanmak',
    polarity_symbol: '↑',
    word_family: [
      { pos: 'verb', form: 'accelerate', meaning_tr: 'hızlandırmak' },
      { pos: 'noun', form: 'acceleration', meaning_tr: 'ivme; hızlanma' },
      { pos: 'noun', form: 'accelerator', meaning_tr: 'hızlandırıcı' },
      { pos: 'adjective', form: 'accelerated', meaning_tr: 'hızlandırılmış' }
    ],
    science_domain: 'chemistry',
    exam_sentence: 'Enzymes function as biological catalysts that accelerate essential metabolic reactions without being consumed.',
    exam_sentence_tr: 'Enzimler, tüketilmeden temel metabolik reaksiyonları hızlandıran biyolojik katalizörler olarak işlev görür.',
    critical_collocations: [
      { phrase: 'accelerate the rate of', meaning_tr: 'oranını / hızını artırmak' },
      { phrase: 'accelerate reaction', meaning_tr: 'tepkimeyi hızlandırmak' },
      { phrase: 'accelerate global warming', meaning_tr: 'küresel ısınmayı hızlandırmak' }
    ],
    synonyms: ['hasten', 'expedite', 'quicken', 'speed up'],
    antonyms: ['decelerate', 'retard', 'slow down', 'delay'],
    mnemonic_hint: 'Arabaların gaz pedalına "akseleratör" denir; hızı artıran mekanizma.',
    distractors: [
      { word: 'accumulate', meaning_tr: 'birikmek; toplamak', explanation_tr: 'Miktar artışıdır; hızlanma değildir.' },
      { word: 'accommodate', meaning_tr: 'uyum sağlamak; barındırmak', explanation_tr: 'Hız ile ilgisi yoktur.' },
      { word: 'accentuate', meaning_tr: 'vurgulamak', explanation_tr: 'Ön plana çıkarmaktır.' }
    ]
  },
  {
    word_id: 'diminish',
    lemma: 'diminish',
    pos: 'verb',
    tier: 1,
    priority_score: 95,
    meaning_tr: 'azalmak; eksilmek; hafifletmek',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'verb', form: 'diminish', meaning_tr: 'azalmak' },
      { pos: 'noun', form: 'diminution', meaning_tr: 'azalma' },
      { pos: 'adjective', form: 'diminished', meaning_tr: 'azalmış' }
    ],
    science_domain: 'physics',
    exam_sentence: 'The gravitational attraction between two celestial bodies diminishes proportionally as the square of the distance increases.',
    exam_sentence_tr: 'İki gök cismi arasındaki kütleçekim kuvveti, aralarındaki mesafenin karesi arttıkça orantılı olarak azalır.',
    critical_collocations: [
      { phrase: 'diminish the impact', meaning_tr: 'etkiyi azaltmak' },
      { phrase: 'diminish in size', meaning_tr: 'boyutça küçülmek' },
      { phrase: 'diminish significantly', meaning_tr: 'ciddi ölçüde azalmak' }
    ],
    synonyms: ['decrease', 'lessen', 'shrink', 'subside'],
    antonyms: ['increase', 'augment', 'magnify', 'boost'],
    mnemonic_hint: '"Mini" / "minimum" kökünden: giderek küçülüp minimuma inmek.',
    distractors: [
      { word: 'demolish', meaning_tr: 'yıkmak; imha etmek', explanation_tr: 'Tamamen yıkmaktır; nicel azalma değildir.' },
      { word: 'distinguish', meaning_tr: 'ayırt etmek', explanation_tr: 'Farkı kavramaktır.' },
      { word: 'dismiss', meaning_tr: 'göz ardı etmek; kovmak', explanation_tr: 'Dikkate almamaktır.' }
    ]
  },
  {
    word_id: 'deplete',
    lemma: 'deplete',
    pos: 'verb',
    tier: 1,
    priority_score: 93,
    meaning_tr: 'tüketmek; kaynakları bitirmek; boşaltmak',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'verb', form: 'deplete', meaning_tr: 'tüketmek' },
      { pos: 'noun', form: 'depletion', meaning_tr: 'tükenme; azalma' },
      { pos: 'adjective', form: 'depleted', meaning_tr: 'tükenmiş' }
    ],
    science_domain: 'environment',
    exam_sentence: 'Unregulated groundwater extraction continues to deplete underground aquifers faster than natural precipitation can replenish them.',
    exam_sentence_tr: 'Kontrolsüz yeraltı suyu çekimi, yeraltı akiferlerini doğal yağışın onları yenileyebileceğinden daha hızlı tüketmeye devam ediyor.',
    critical_collocations: [
      { phrase: 'deplete natural resources', meaning_tr: 'doğal kaynakları tüketmek' },
      { phrase: 'ozone depletion', meaning_tr: 'ozon tabakasının incelmesi/tükenmesi' },
      { phrase: 'severely deplete', meaning_tr: 'ciddi şekilde tüketmek' }
    ],
    synonyms: ['exhaust', 'consume', 'drain', 'use up'],
    antonyms: ['replenish', 'restore', 'renew', 'augment'],
    mnemonic_hint: 'De-plete: "Complete" dolu iken, "deplete" içi boşaltılmış, tüketilmiş.',
    distractors: [
      { word: 'deploy', meaning_tr: 'konuşlandırmak; devreye sokmak', explanation_tr: 'Kaynakları sahaya sürmektir.' },
      { word: 'deprive', meaning_tr: 'yoksun bırakmak', explanation_tr: 'Birini bir şeyden mahrum etmektir.' },
      { word: 'deprecate', meaning_tr: 'onaylamamak; kullanım dışı bırakmak', explanation_tr: 'Yazılım ve terminolojide tercih edilmemektir.' }
    ]
  },
  {
    word_id: 'trigger',
    lemma: 'trigger',
    pos: 'verb',
    tier: 1,
    priority_score: 96,
    meaning_tr: 'tetiklemek; başlatmak; bir olaya yol açmak',
    polarity_symbol: '↑',
    word_family: [
      { pos: 'verb', form: 'trigger', meaning_tr: 'tetiklemek' },
      { pos: 'noun', form: 'trigger', meaning_tr: 'tetikleyici unsur' }
    ],
    science_domain: 'medicine',
    exam_sentence: 'Sudden fluctuations in atmospheric pressure can trigger acute migraine episodes in susceptible individuals.',
    exam_sentence_tr: 'Atmosferik basınçtaki ani dalgalanmalar, duyarlı bireylerde akut migren ataklarını tetikleyebilir.',
    critical_collocations: [
      { phrase: 'trigger a chain reaction', meaning_tr: 'zincirleme reaksiyon tetiklemek' },
      { phrase: 'trigger an immune response', meaning_tr: 'bağışıklık yanıtı başlatmak' },
      { phrase: 'trigger mechanism', meaning_tr: 'tetikleyici mekanizma' }
    ],
    synonyms: ['initiate', 'spark', 'provoke', 'induce', 'set off'],
    antonyms: ['halt', 'suppress', 'terminate', 'prevent'],
    mnemonic_hint: 'Silah tetiği (trigger): Basılınca zincirleme bir olayı derhal başlatan unsur.',
    distractors: [
      { word: 'triumph', meaning_tr: 'zafer kazanmak', explanation_tr: 'Başarı elde etmektir.' },
      { word: 'truncate', meaning_tr: 'kısa kesmek; budamak', explanation_tr: 'Bir metni veya veriyi kesmektir.' },
      { word: 'trickle', meaning_tr: 'damlamak; sızmak', explanation_tr: 'Yavaşça akmaktır.' }
    ]
  },

  // --- ENVIRONMENT & TECHNOLOGY ---
  {
    word_id: 'abundant',
    lemma: 'abundant',
    pos: 'adjective',
    tier: 1,
    priority_score: 94,
    meaning_tr: 'bol; çok miktarda bulunan; zengin',
    polarity_symbol: '↑',
    word_family: [
      { pos: 'adjective', form: 'abundant', meaning_tr: 'bol' },
      { pos: 'noun', form: 'abundance', meaning_tr: 'bolluk; çokluk' },
      { pos: 'adverb', form: 'abundantly', meaning_tr: 'bolca; bol miktarda' }
    ],
    science_domain: 'environment',
    exam_sentence: 'Silicon is an abundant element in the Earth’s crust, making it a sustainable raw material for semiconductor fabrication.',
    exam_sentence_tr: 'Silisyum yer kabuğunda bol bulunan bir elementtir ve bu da onu yarı iletken üretimi için sürdürülebilir bir ham madde yapar.',
    critical_collocations: [
      { phrase: 'abundant in nature', meaning_tr: 'doğada bol bulunan' },
      { phrase: 'abundant supply', meaning_tr: 'bol miktarda arz / kaynak' },
      { phrase: 'in great abundance', meaning_tr: 'büyük bir bolluk içinde' }
    ],
    synonyms: ['plentiful', 'copious', 'ample', 'bountiful'],
    antonyms: ['scarce', 'meager', 'deficient', 'sparse'],
    mnemonic_hint: '"A-bundant" -> Bir demet (bundle) dolusu, her yerde bolca var.',
    distractors: [
      { word: 'abandoned', meaning_tr: 'terk edilmiş', explanation_tr: 'Bırakılmış anlamındadır.' },
      { word: 'redundant', meaning_tr: 'gereksiz; lüzumsuz fazlalık', explanation_tr: 'Gereksiz fazlalıktır, bol bulunmak zorunlu olarak lüzumsuzluk değildir.' },
      { word: 'reluctant', meaning_tr: 'isteksiz', explanation_tr: 'Gönülsüz anlamındadır.' }
    ]
  },
  {
    word_id: 'negligible',
    lemma: 'negligible',
    pos: 'adjective',
    tier: 2,
    priority_score: 92,
    meaning_tr: 'ihmal edilebilir; göz ardı edilecek kadar önemsiz/az',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'adjective', form: 'negligible', meaning_tr: 'ihmal edilebilir' },
      { pos: 'verb', form: 'neglect', meaning_tr: 'ihmal etmek' },
      { pos: 'noun', form: 'negligence', meaning_tr: 'ihmalkarlık' },
      { pos: 'adverb', form: 'negligibly', meaning_tr: 'ihmal edilebilir derecede' }
    ],
    science_domain: 'physics',
    exam_sentence: 'When calculating the orbital trajectories of macroscopic spacecraft, the radiation pressure of starlight is virtually negligible.',
    exam_sentence_tr: 'Makroskopik uzay araçlarının yörünge hareketleri hesaplanırken, yıldız ışığının radyasyon basıncı neredeyse ihmal edilebilir düzeydedir.',
    critical_collocations: [
      { phrase: 'negligible amount', meaning_tr: 'ihmal edilebilir miktar' },
      { phrase: 'negligible effect', meaning_tr: 'önemsiz / ihmal edilebilir etki' },
      { phrase: 'virtually negligible', meaning_tr: 'neredeyse ihmal edilebilir' }
    ],
    synonyms: ['insignificant', 'trivial', 'minor', 'imperceptible'],
    antonyms: ['substantial', 'significant', 'considerable', 'momentous'],
    mnemonic_hint: '"Neglect" (ihmal etmek) + "ible" (edilebilir) -> İhmal edilebilir kadar önemsiz.',
    distractors: [
      { word: 'negligent', meaning_tr: 'ihmalkar (insan)', explanation_tr: 'Kişinin dikkatsizliğini belirtir; niceliğin küçüklüğünü değil.' },
      { word: 'negotiable', meaning_tr: 'müzakere edilebilir', explanation_tr: 'Pazarlık yapılabilir demektir.' },
      { word: 'negative', meaning_tr: 'olumsuz', explanation_tr: 'Küçük etki mutlaka negatif etki demek değildir.' }
    ]
  },
  {
    word_id: 'plausible',
    lemma: 'plausible',
    pos: 'adjective',
    tier: 2,
    priority_score: 91,
    meaning_tr: 'akla yatkın; makul; olası (bilimsel olarak savunulabilir)',
    polarity_symbol: '=',
    word_family: [
      { pos: 'adjective', form: 'plausible', meaning_tr: 'akla yatkın' },
      { pos: 'noun', form: 'plausibility', meaning_tr: 'akla yatkınlık; inandırıcılık' },
      { pos: 'adverb', form: 'plausibly', meaning_tr: 'akla yatkın bir şekilde' }
    ],
    science_domain: 'technology',
    exam_sentence: 'Researchers formulated a plausible hypothesis to explain the unexpected thermal anomaly detected in the core reactor.',
    exam_sentence_tr: 'Araştırmacılar, çekirdek reaktöründe saptanan beklenmedik termal anomaliyi açıklamak için akla yatkın bir hipotez formüle ettiler.',
    critical_collocations: [
      { phrase: 'plausible explanation', meaning_tr: 'akla yatkın açıklama' },
      { phrase: 'scientifically plausible', meaning_tr: 'bilimsel olarak akla yatkın' },
      { phrase: 'plausible hypothesis', meaning_tr: 'mantıklı hipotez' }
    ],
    synonyms: ['reasonable', 'credible', 'believable', 'feasible'],
    antonyms: ['implausible', 'unlikely', 'far-fetched', 'absurd'],
    mnemonic_hint: '"Applaud" (alkışlamak) ile aynı kökten: İnsanların onaylayıp alkışlayacağı kadar mantıklı ve akla yatkın.',
    distractors: [
      { word: 'pliable', meaning_tr: 'bükülebilir; esnek', explanation_tr: 'Maddenin fiziksel esnekliğini anlatır.' },
      { word: 'palpable', meaning_tr: 'elle tutulur; somut', explanation_tr: 'Hissedilebilir anlamındadır.' },
      { word: 'permissible', meaning_tr: 'izin verilebilir', explanation_tr: 'Kurallara uygunluktur.' }
    ]
  },
  {
    word_id: 'empirical',
    lemma: 'empirical',
    pos: 'adjective',
    tier: 2,
    priority_score: 93,
    meaning_tr: 'deneysel; gözleme dayalı; ampirik',
    polarity_symbol: '=',
    word_family: [
      { pos: 'adjective', form: 'empirical', meaning_tr: 'deneysel' },
      { pos: 'adverb', form: 'empirically', meaning_tr: 'deneysel yolla' },
      { pos: 'noun', form: 'empiricism', meaning_tr: 'deneycilik' }
    ],
    science_domain: 'physics',
    exam_sentence: 'Theoretical models must always be corroborated by robust empirical data collected through systematic laboratory experimentation.',
    exam_sentence_tr: 'Teorik modeller, sistematik laboratuvar deneyleri yoluyla toplanan sağlam ampirik verilerle her zaman doğrulanmalıdır.',
    critical_collocations: [
      { phrase: 'empirical evidence', meaning_tr: 'deneysel kanıt' },
      { phrase: 'empirical study', meaning_tr: 'ampirik / uygulamalı çalışma' },
      { phrase: 'empirical findings', meaning_tr: 'deneysel bulgular' }
    ],
    synonyms: ['observational', 'experimental', 'evidence-based', 'practical'],
    antonyms: ['theoretical', 'hypothetical', 'speculative'],
    mnemonic_hint: 'Empire (İmparatorluk) değil, "Em-piric" (deneyerek gözlemleyen bilimsel yöntem).',
    distractors: [
      { word: 'imperial', meaning_tr: 'imparatorlukla ilgili', explanation_tr: 'Siyasi bir kavramdır; bilimsel deneyle ilgisizdir.' },
      { word: 'imperative', meaning_tr: 'zorunlu; elzem', explanation_tr: 'Kaçınılmaz gerekliliktir.' },
      { word: 'empirical', meaning_tr: 'deneysel', explanation_tr: 'Doğru seçenektir.' }
    ]
  },

  // --- ADDITIONAL CORE ACADEMIC SCIENCE EXPANSIONS ---
  {
    word_id: 'enhance',
    lemma: 'enhance',
    pos: 'verb',
    tier: 1,
    priority_score: 95,
    meaning_tr: 'geliştirmek; kalitesini / verimini artırmak',
    polarity_symbol: '↑',
    word_family: [
      { pos: 'verb', form: 'enhance', meaning_tr: 'geliştirmek; artırmak' },
      { pos: 'noun', form: 'enhancement', meaning_tr: 'iyileştirme; artış' },
      { pos: 'adjective', form: 'enhanced', meaning_tr: 'geliştirilmiş' }
    ],
    science_domain: 'technology',
    exam_sentence: 'Doping silicon with phosphorus enhances its electrical conductivity by introducing additional free electrons.',
    exam_sentence_tr: 'Silisyumun fosfor ile katkılanması, ilave serbest elektronlar sağlayarak elektriksel iletkenliğini artırır.',
    critical_collocations: [
      { phrase: 'enhance efficiency', meaning_tr: 'verimliliği artırmak' },
      { phrase: 'enhance performance', meaning_tr: 'performansı geliştirmek' },
      { phrase: 'enhance the ability to', meaning_tr: 'yeteneği geliştirmek' }
    ],
    synonyms: ['improve', 'boost', 'upgrade', 'augment'],
    antonyms: ['impair', 'diminish', 'degrade', 'undermine'],
    mnemonic_hint: '"En-hance": Yükseğe çıkarmak, seviyesini büyütmek.',
    distractors: [
      { word: 'enforce', meaning_tr: 'zorla uygulamak', explanation_tr: 'Yasa veya kural yürütmektir.' },
      { word: 'entail', meaning_tr: 'gerektirmek', explanation_tr: 'Zorunlu kılmaktır.' },
      { word: 'enlarge', meaning_tr: 'fiziksel olarak büyütmek', explanation_tr: 'Boyutsal genişlemedir; performans artışı değildir.' }
    ]
  },
  {
    word_id: 'diminution',
    lemma: 'diminution',
    pos: 'noun',
    tier: 2,
    priority_score: 88,
    meaning_tr: 'azalma; küçülme; eksilme',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'noun', form: 'diminution', meaning_tr: 'azalma' },
      { pos: 'verb', form: 'diminish', meaning_tr: 'azalmak' }
    ],
    science_domain: 'biology',
    exam_sentence: 'A sharp diminution in biodiversity was recorded following the widespread deforestation of the wetland habitat.',
    exam_sentence_tr: 'Sulak alan habitatının yaygın şekilde ormansızlaştırılmasının ardından biyolojik çeşitlilikte keskin bir azalma kaydedildi.',
    critical_collocations: [
      { phrase: 'diminution of resources', meaning_tr: 'kaynakların azalması' },
      { phrase: 'diminution in quality', meaning_tr: 'kalitede eksilme' }
    ],
    synonyms: ['reduction', 'decrease', 'decline', 'drop'],
    antonyms: ['growth', 'expansion', 'surge'],
    mnemonic_hint: 'Diminish eyleminin isim hali.',
    distractors: [
      { word: 'destination', meaning_tr: 'varış yeri', explanation_tr: 'Gidilecek yerdir.' },
      { word: 'distribution', meaning_tr: 'dağılım', explanation_tr: 'Yayılımdır.' },
      { word: 'deprivation', meaning_tr: 'yoksunluk', explanation_tr: 'Mahrumiyettir.' }
    ]
  },
  {
    word_id: 'ubiquitous',
    lemma: 'ubiquitous',
    pos: 'adjective',
    tier: 2,
    priority_score: 90,
    meaning_tr: 'her yerde bulunan; yaygın',
    polarity_symbol: '=',
    word_family: [
      { pos: 'adjective', form: 'ubiquitous', meaning_tr: 'her yerde bulunan' },
      { pos: 'noun', form: 'ubiquity', meaning_tr: 'aynı anda her yerde bulunma' }
    ],
    science_domain: 'biology',
    exam_sentence: 'Microorganisms are ubiquitous in the biosphere, thriving in extreme environments from deep-sea hydrothermal vents to arctic ice.',
    exam_sentence_tr: 'Mikroorganizmalar biyosferde her yerde bulunur; derin deniz hidrotermal bacalarından arktik buzullara kadar ekstrem ortamlarda yaşarlar.',
    critical_collocations: [
      { phrase: 'ubiquitous presence', meaning_tr: 'her yerde bulunma' },
      { phrase: 'almost ubiquitous', meaning_tr: 'neredeyse her yerde görülen' }
    ],
    synonyms: ['omnipresent', 'pervasive', 'widespread'],
    antonyms: ['rare', 'scarce', 'localized'],
    mnemonic_hint: '"U-bi-quity" -> Her köşe bucakta var olan.',
    distractors: [
      { word: 'ambiguous', meaning_tr: 'belirsiz; iki anlamlı', explanation_tr: 'Net olmayan demektir.' },
      { word: 'unanimous', meaning_tr: 'oy birliğiyle', explanation_tr: 'Herkesin mutabık olmasıdır.' },
      { word: 'ubiquitous', meaning_tr: 'her yerde bulunan', explanation_tr: 'Doğru cevaptır.' }
    ]
  },
  {
    word_id: 'corroborate',
    lemma: 'corroborate',
    pos: 'verb',
    tier: 2,
    priority_score: 91,
    meaning_tr: 'doğrulamak; kanıtlarla desteklemek; teyit etmek',
    polarity_symbol: '=',
    word_family: [
      { pos: 'verb', form: 'corroborate', meaning_tr: 'doğrulamak' },
      { pos: 'noun', form: 'corroboration', meaning_tr: 'doğrulama; destekleyici kanıt' },
      { pos: 'adjective', form: 'corroborative', meaning_tr: 'destekleyici' }
    ],
    science_domain: 'chemistry',
    exam_sentence: 'Subsequent spectroscopic observations helped corroborate the presence of organic molecules in the comet’s coma.',
    exam_sentence_tr: 'Daha sonraki spektroskopik gözlemler, kuyruklu yıldızın komasında organik moleküllerin varlığını doğrulamaya yardımcı oldu.',
    critical_collocations: [
      { phrase: 'corroborate findings', meaning_tr: 'bulguları doğrulamak' },
      { phrase: 'corroborate the theory', meaning_tr: 'teoriyi desteklemek / teyit etmek' }
    ],
    synonyms: ['confirm', 'verify', 'substantiate', 'validate'],
    antonyms: ['refute', 'contradict', 'disprove'],
    mnemonic_hint: 'Co-roborate -> "Robust" (sağlam) hale getirmek, kanıtla sağlamlaştırmak.',
    distractors: [
      { word: 'collaborate', meaning_tr: 'iş birliği yapmak', explanation_tr: 'Birlikte çalışmaktır, kanıtlamak değildir.' },
      { word: 'corrode', meaning_tr: 'paslanmak; aşınmak', explanation_tr: 'Metallerin kimyasal aşınmasıdır.' },
      { word: 'correlate', meaning_tr: 'ilişkili olmak', explanation_tr: 'Bağlantılı olmaktır, doğrulamak değildir.' }
    ]
  },
  {
    word_id: 'fluctuate',
    lemma: 'fluctuate',
    pos: 'verb',
    tier: 1,
    priority_score: 93,
    meaning_tr: 'dalgalanmak; inip çıkmak; değişkenlik göstermek',
    polarity_symbol: '=',
    word_family: [
      { pos: 'verb', form: 'fluctuate', meaning_tr: 'dalgalanmak' },
      { pos: 'noun', form: 'fluctuation', meaning_tr: 'dalgalanma; iniş-çıkış' },
      { pos: 'adjective', form: 'fluctuating', meaning_tr: 'dalgalanan' }
    ],
    science_domain: 'physics',
    exam_sentence: 'Solar radiation outputs fluctuate cyclically over an approximately eleven-year solar magnetic cycle.',
    exam_sentence_tr: 'Güneş radyasyon çıktıları, yaklaşık on bir yıllık bir güneş manyetik döngüsü boyunca periyodik olarak dalgalanır.',
    critical_collocations: [
      { phrase: 'fluctuate wildly', meaning_tr: 'şiddetle dalgalanmak' },
      { phrase: 'fluctuate between', meaning_tr: 'arasında gidip gelmek' },
      { phrase: 'seasonal fluctuations', meaning_tr: 'mevsimsel dalgalanmalar' }
    ],
    synonyms: ['oscillate', 'vary', 'shift', 'alternate'],
    antonyms: ['stabilize', 'remain constant'],
    mnemonic_hint: '"Fluid" (akışkan, dalgalı sıvı) gibi sabit kalmayıp inip çıkmak.',
    distractors: [
      { word: 'frustrate', meaning_tr: 'hayal kırıklığına uğratmak', explanation_tr: 'Duygusal bir durumdur.' },
      { word: 'fulfil', meaning_tr: 'yerine getirmek', explanation_tr: 'Görevi tamamlamaktır.' },
      { word: 'fracture', meaning_tr: 'kırılmak; çatlamak', explanation_tr: 'Fiziksel kırılmadır.' }
    ]
  },
  {
    word_id: 'alleviate',
    lemma: 'alleviate',
    pos: 'verb',
    tier: 2,
    priority_score: 92,
    meaning_tr: 'hafifletmek; dindirmek; etkisini azaltmak',
    polarity_symbol: '↓',
    word_family: [
      { pos: 'verb', form: 'alleviate', meaning_tr: 'hafifletmek' },
      { pos: 'noun', form: 'alleviation', meaning_tr: 'hafifletme; rahatlatma' }
    ],
    science_domain: 'medicine',
    exam_sentence: 'Novel analgesic formulations aim to alleviate chronic neuropathic pain without causing severe dependency.',
    exam_sentence_tr: 'Yeni analjezik formülasyonlar, ciddi bağımlılığa yol açmaksızın kronik nöropatik ağrıyı hafifletmeyi hedefler.',
    critical_collocations: [
      { phrase: 'alleviate pain', meaning_tr: 'ağrıyı dindirmek' },
      { phrase: 'alleviate symptoms', meaning_tr: 'semptomları hafifletmek' },
      { phrase: 'alleviate poverty', meaning_tr: 'yoksulluğu azaltmak' }
    ],
    synonyms: ['ease', 'relieve', 'mitigate', 'soothe'],
    antonyms: ['aggravate', 'exacerbate', 'worsen'],
    mnemonic_hint: '"Relieve" (rahatlatmak) gibi sonu biten: yükü hafifletip rahatlatmak.',
    distractors: [
      { word: 'allocate', meaning_tr: 'tahsis etmek; paylaştırmak', explanation_tr: 'Bütçe veya kaynak ayırmaktır.' },
      { word: 'alienate', meaning_tr: 'yabancılaştırmak', explanation_tr: 'Uzaklaştırmaktır.' },
      { word: 'elevate', meaning_tr: 'yükseltmek', explanation_tr: 'Yukarı kaldırmaktır; ağrıyı hafifletmek değildir.' }
    ]
  },
  {
    word_id: 'exacerbate',
    lemma: 'exacerbate',
    pos: 'verb',
    tier: 2,
    priority_score: 93,
    meaning_tr: 'kötüleştirmek; şiddetlendirmek; daha vahim hale getirmek',
    polarity_symbol: '↑',
    word_family: [
      { pos: 'verb', form: 'exacerbate', meaning_tr: 'şiddetlendirmek' },
      { pos: 'noun', form: 'exacerbation', meaning_tr: 'şiddetlenme; alevlenme' }
    ],
    science_domain: 'environment',
    exam_sentence: 'Prolonged droughts exacerbated by deforestation drastically undermine agricultural resilience across arid zones.',
    exam_sentence_tr: 'Ormansızlaşmayla daha da şiddetlenen uzun süreli kuraklıklar, kurak bölgelerdeki tarımsal direnci ciddi biçimde zayıflatır.',
    critical_collocations: [
      { phrase: 'exacerbate the problem', meaning_tr: 'sorunu daha da kötüleştirmek' },
      { phrase: 'exacerbate symptoms', meaning_tr: 'semptomları şiddetlendirmek' }
    ],
    synonyms: ['worsen', 'aggravate', 'intensify', 'inflame'],
    antonyms: ['alleviate', 'mitigate', 'ease', 'soothe'],
    mnemonic_hint: '"Acerbic" (keskin, acı) kökünden: Bir derdi daha keskin ve acı hale getirmek.',
    distractors: [
      { word: 'exaggerate', meaning_tr: 'abartmak', explanation_tr: 'Bir şeyi olduğundan büyük göstermektir.' },
      { word: 'excavate', meaning_tr: 'kazı yapmak', explanation_tr: 'Arkeolojik kazı yapmaktır.' },
      { word: 'exasperate', meaning_tr: 'çileden çıkarmak', explanation_tr: 'İnsanı öfkelendirmektir.' }
    ]
  },
  {
    word_id: 'substantiate',
    lemma: 'substantiate',
    pos: 'verb',
    tier: 2,
    priority_score: 90,
    meaning_tr: 'kanıtlamak; somut delillerle desteklemek',
    polarity_symbol: '=',
    word_family: [
      { pos: 'verb', form: 'substantiate', meaning_tr: 'somut kanıtlarla desteklemek' },
      { pos: 'adjective', form: 'substantial', meaning_tr: 'önemli; kayda değer' },
      { pos: 'noun', form: 'substantiation', meaning_tr: 'kanıtlama; somutlaştırma' }
    ],
    science_domain: 'physics',
    exam_sentence: 'Without repeatable empirical trials, researchers cannot substantiate their theoretical claims regarding dark matter interactions.',
    exam_sentence_tr: 'Tekrarlanabilir ampirik denemeler olmaksızın araştırmacılar, karanlık madde etkileşimlerine ilişkin teorik iddialarını kanıtlayamazlar.',
    critical_collocations: [
      { phrase: 'substantiate claims', meaning_tr: 'iddiaları kanıtlamak' },
      { phrase: 'substantiate findings', meaning_tr: 'bulguları somutlaştırmak' }
    ],
    synonyms: ['corroborate', 'validate', 'prove', 'verify'],
    antonyms: ['disprove', 'undermine', 'refute'],
    mnemonic_hint: '"Substance" (öz, madde, somut varlık) katmak: İddiaya madde ve somutluk kazandırmak.',
    distractors: [
      { word: 'substitute', meaning_tr: 'yerine geçmek / koymak', explanation_tr: 'İkame etmektir.' },
      { word: 'submerge', meaning_tr: 'suya batırmak', explanation_tr: 'Batırmaktır.' },
      { word: 'subtract', meaning_tr: 'çıkarmak (matematik)', explanation_tr: 'Eksiltmektir.' }
    ]
  }
];

/**
 * Text-to-speech pronunciation utility using native browser Web Speech API.
 * Safe fallback in environments without speech synthesis (e.g. Node/SSR).
 */
export function playPronunciation(word: string): boolean {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return false;
  }
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US';
    utterance.rate = 0.9;
    window.speechSynthesis.speak(utterance);
    return true;
  } catch {
    return false;
  }
}

/**
 * Returns progression steps for any word, using explicit progression if defined
 * or systematically synthesizing a 4-level scaffold from entry properties.
 */
export function getWordProgression(word: AcademicVocabEntry): readonly WordProgressionStep[] {
  if (word.progression && word.progression.length > 0) {
    return word.progression;
  }

  const primaryCollocation = word.critical_collocations[0]?.phrase || `${word.lemma} process`;
  const collocationTr = word.critical_collocations[0]?.meaning_tr || word.meaning_tr;

  return [
    {
      level: 0,
      title: 'Atom Cümle (Temel İskelet)',
      englishText: `${word.lemma.toUpperCase()} is essential in science.`,
      turkishTranslation: `${word.lemma} bilimde temel bir kavramdır.`,
      focusPoint: `Kavram: "${word.lemma}" -> Türkçe karşılık: "${word.meaning_tr}".`,
      tokens: [
        { text: word.lemma, role: 'SUBJECT', explanation_tr: 'Özne / Hedef Kelime', isTargetWord: true },
        { text: 'is', role: 'VERB', explanation_tr: 'Fiil' },
        { text: 'essential in science.', role: 'OBJECT', explanation_tr: 'Tamamlayıcı öbek' }
      ]
    },
    {
      level: 1,
      title: '1. Basamak Genişletme (Eş Dizim Odaklı)',
      englishText: `Scientists frequently observe ${primaryCollocation}.`,
      turkishTranslation: `Bilim insanları sıklıkla ${collocationTr} gözlemler.`,
      focusPoint: `Akademik eş dizim kullanımı: "${primaryCollocation}".`,
      tokens: [
        { text: 'Scientists', role: 'SUBJECT', explanation_tr: 'Özne' },
        { text: 'frequently observe', role: 'VERB', explanation_tr: 'Zarf + Fiil' },
        { text: primaryCollocation, role: 'OBJECT', explanation_tr: 'Hedef eş dizim', isTargetWord: true }
      ]
    },
    {
      level: 2,
      title: '2. Basamak: Neden-Sonuç ve Bağlaç Genişletmesi',
      englishText: `Because ${primaryCollocation} occurs, the overall reaction rate changes.`,
      turkishTranslation: `${collocationTr} gerçekleştiği için genel reaksiyon hızı değişir.`,
      focusPoint: `Because bağlacıyla fen olgusu bir sonuca bağlandı.`,
      tokens: [
        { text: 'Because', role: 'CONNECTOR', explanation_tr: 'Sebep bağlacı' },
        { text: primaryCollocation, role: 'SUBORDINATE', explanation_tr: 'Yan cümle öznesi', isTargetWord: true },
        { text: 'occurs,', role: 'VERB', explanation_tr: 'Fiil' },
        { text: 'the overall reaction rate changes.', role: 'OBJECT', explanation_tr: 'Ana cümle' }
      ]
    },
    {
      level: 3,
      title: '3. Basamak: Gerçek YÖKDİL Seviyesi Cümle',
      englishText: word.exam_sentence,
      turkishTranslation: word.exam_sentence_tr,
      focusPoint: `Sınav seviyesindeki cümlede hedef kelimenin yeri ve çevirisi.`,
      tokens: [
        { text: word.exam_sentence.split(' ')[0] || 'The', role: 'SUBJECT', explanation_tr: 'Özne' },
        { text: word.lemma, role: 'TARGET_WORD', explanation_tr: 'Hedef Kelime', isTargetWord: true },
        { text: '...', role: 'OBJECT', explanation_tr: 'Akademik tamamlama' }
      ]
    }
  ];
}

/**
 * Returns trap word comparisons for any word.
 */
export function getTrapWords(word: AcademicVocabEntry): readonly TrapWordComparison[] {
  if (word.trap_words && word.trap_words.length > 0) {
    return word.trap_words;
  }

  // Synthesize from distractors
  return word.distractors.map((d) => ({
    trapWord: d.word,
    trapMeaning: d.meaning_tr,
    confusionReason: d.explanation_tr,
    memoryHook: `Dikkat: "${word.lemma}" (${word.meaning_tr}) ile "${d.word}" (${d.meaning_tr}) karıştırılmamalıdır.`
  }));
}

