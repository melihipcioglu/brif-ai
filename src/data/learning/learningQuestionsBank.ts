import type { LearningPracticeQuestion } from '../../types/learning';

export const learningQuestionsBank: readonly LearningPracticeQuestion[] = [
  // --- GAP FILL: VOCABULARY IN CONTEXT ---
  {
    id: 'lp-gap-inhibit-1',
    kind: 'LEARNING_PRACTICE',
    family: 'GAP_FILL',
    science_domain: 'biology',
    target_word_ids: ['inhibit'],
    stem: 'To prevent the uncontrolled division of abnormal cells, oncologists administer targeted pharmacological agents specifically designed to ____ enzymatic pathways responsible for tumor growth.',
    options: [
      { id: 'A', text: 'accelerate' },
      { id: 'B', text: 'inhabit' },
      { id: 'C', text: 'inhibit' },
      { id: 'D', text: 'exhibit' },
      { id: 'E', text: 'reproduce' }
    ],
    correct_option: 'C',
    pedagogical_explanation: {
      triage_tr:
        'Cümledeki "prevent the uncontrolled division" (kontrolsüz bölünmeyi engellemek) ve "enzymatic pathways responsible for tumor growth" (tümör büyümesinden sorumlu yollar) ifadeleri negatif yönde bir baskılama eylemi gerektirir.',
      target_word_insight_tr:
        '"Inhibit" (engellemek, baskılamak), biyokimyasal ve tıbbi metinlerde enzim veya hücre bölünmesini durdurmak için kullanılan temel fiildir.',
      distractor_breakdowns: {
        A: 'accelerate (hızlandırmak): Tümör büyümesini hızlandırmak tedavi amacıyla tamamen çelişir.',
        B: 'inhabit (yaşamak/ikamet etmek): Yazım benzerliğine dayalı çeldiricidir; enzim yollarında yaşanmaz.',
        C: 'inhibit (engellemek): Doğru seçenek. Süreci baskılar.',
        D: 'exhibit (sergilemek): Bir özelliği göstermektir; eylemin amacına uymaz.',
        E: 'reproduce (üremek): Tümörün bölünmesini önlemek için çoğalma yapılmaz.'
      }
    }
  },
  {
    id: 'lp-gap-susceptible-1',
    kind: 'LEARNING_PRACTICE',
    family: 'GAP_FILL',
    science_domain: 'medicine',
    target_word_ids: ['susceptible'],
    stem: 'Due to severe deficiencies in cellular immunity, preterm neonates are exceptionally ____ to opportunistic systemic microbial infections.',
    options: [
      { id: 'A', text: 'impervious' },
      { id: 'B', text: 'susceptible' },
      { id: 'C', text: 'suspicious' },
      { id: 'D', text: 'negligible' },
      { id: 'E', text: 'redundant' }
    ],
    correct_option: 'B',
    pedagogical_explanation: {
      triage_tr:
        'Cümle başındaki "Due to severe deficiencies in cellular immunity" (bağışıklık yetersizliğinden dolayı) ifadesi, bebeklerin enfeksiyonlara karşı savunmasız/duyarlı olduğunu gösterir. "____ to" edat kalıbı da bunu destekler.',
      target_word_insight_tr:
        '"Susceptible to" (bir hastalığa veya riske karşı savunmasız olmak) YÖKDİL Sağlık ve Fen alanlarında sıkça "vulnerable to" veya "prone to" yerine kullanılır.',
      distractor_breakdowns: {
        A: 'impervious (etkilenmez/geçirimsiz): Bağışıklık yetersizliğinin tam tersi bir direnç ifade eder.',
        B: 'susceptible (savunmasız/duyarlı): Doğru seçenek.',
        C: 'suspicious (şüpheli): İnsan duygusu/kuşkudur; patolojik duyarlılık değildir.',
        D: 'negligible (ihmal edilebilir): Sayısal küçüklüğü belirtir; enfeksiyona yatkınlığı anlatamaz.',
        E: 'redundant (gereksiz fazlalık): Anlam bütünlüğüyle uyuşmaz.'
      }
    }
  },
  {
    id: 'lp-gap-accelerate-1',
    kind: 'LEARNING_PRACTICE',
    family: 'GAP_FILL',
    science_domain: 'chemistry',
    target_word_ids: ['accelerate'],
    stem: 'Platinum nanoparticles embedded in catalytic converters significantly ____ the breakdown of hazardous carbon monoxide into carbon dioxide.',
    options: [
      { id: 'A', text: 'decelerate' },
      { id: 'B', text: 'deteriorate' },
      { id: 'C', text: 'accelerate' },
      { id: 'D', text: 'deplete' },
      { id: 'E', text: 'fluctuate' }
    ],
    correct_option: 'C',
    pedagogical_explanation: {
      triage_tr:
        '"Catalytic converters" (katalitik konvertörler) kimyasal tepkimelerin hızını artırarak zararlı gazların dönüşümünü çabuklaştırır.',
      target_word_insight_tr:
        '"Accelerate" (hızlandırmak), kimyasal kataliz ve fiziksel parçacık kinetiğinde tepkime hızını artırmayı ifade eder.',
      distractor_breakdowns: {
        A: 'decelerate (yavaşlatmak): Katalizörün hızlandırıcı işlevinin zıttıdır.',
        B: 'deteriorate (kötüleşmek): Kalite bozulmasıdır; eylemsel hız artışı değildir.',
        C: 'accelerate (hızlandırmak): Doğru seçenek.',
        D: 'deplete (tüketmek): Kaynak tüketimidir.',
        E: 'fluctuate (dalgalanmak): Değişkenlik göstermektir.'
      }
    }
  },

  // --- SENTENCE COMPLETION ---
  {
    id: 'lp-sentence-deteriorate-1',
    kind: 'LEARNING_PRACTICE',
    family: 'SENTENCE_COMPLETION',
    science_domain: 'environment',
    target_word_ids: ['deteriorate', 'exacerbate'],
    stem: 'Unless industrial nations implement stringent emission caps to curb greenhouse gas release, ____.',
    options: [
      { id: 'A', text: 'global water and air quality will deteriorate at an unprecedented pace' },
      { id: 'B', text: 'atmospheric pollution had already been brought under complete control' },
      { id: 'C', text: 'renewable energy infrastructure was completely dismantled decades ago' },
      { id: 'D', text: 'marine organisms can easily thrive without dissolved oxygen' },
      { id: 'E', text: 'soil fertility diminishes whenever natural compost is applied' }
    ],
    correct_option: 'A',
    pedagogical_explanation: {
      triage_tr:
        '"Unless" (madıkça / mezse) olumsuz bir koşul sunar ("Unless nations implement emission caps" = Önlem alınmazsa). Dolayısıyla ana cümlede geleceğe dönük olumsuz bir netice aranmalıdır.',
      target_word_insight_tr:
        '"Deteriorate" (kötüleşmek) çevre kirliliğinde hava ve su kalitesinin düşmesini en yetkin biçimde açıklar.',
      distractor_breakdowns: {
        A: 'global water and air quality will deteriorate at an unprecedented pace: Doğru mantıksal ve zamansal (will + deteriorate) tamamlayıcı.',
        B: 'atmospheric pollution had already been brought...: Geçmiş zaman (had) ve olumlu anlam Unless ile çelişir.',
        C: 'was completely dismantled decades ago: Zaman uyuşmazlığı (decades ago).',
        D: 'marine organisms can easily thrive...: Biyolojik gerçekliğe ve olumsuz koşula aykırıdır.',
        E: 'soil fertility diminishes whenever natural compost is applied: Kompost verimliliği azaltmaz, artırır.'
      }
    }
  },

  // --- TRANSLATION: ENG -> TR ---
  {
    id: 'lp-trans-engtr-abundant-1',
    kind: 'LEARNING_PRACTICE',
    family: 'TRANSLATION_ENG_TR',
    science_domain: 'physics',
    target_word_ids: ['abundant', 'negligible'],
    stem: 'Because solar radiation is abundant in equatorial regions, thermal dissipation losses remain virtually negligible in modern parabolic collectors.',
    options: [
      { id: 'A', text: 'Ekvator bölgelerinde güneş radyasyonu bol olduğu için, modern parabolik toplayıcılarda termal dağılma kayıpları neredeyse ihmal edilebilir kalmaktadır.' },
      { id: 'B', text: 'Modern parabolik toplayıcılar ekvator bölgelerindeki güneş radyasyonunu bol miktarda topladığı için termal kayıplar artmaktadır.' },
      { id: 'C', text: 'Ekvator bölgelerinde güneş radyasyonu azaldığında modern parabolik toplayıcılar ihmal edilebilir düzeyde ısı üretir.' },
      { id: 'D', text: 'Güneş radyasyonunun bol olması, modern parabolik toplayıcıların termal kayıpları tamamen yok etmesini gerektirmiştir.' },
      { id: 'E', text: 'Termal kayıplar neredeyse ihmal edilebilir olduğunda ekvator bölgelerinde güneş radyasyonu bollaşır.' }
    ],
    correct_option: 'A',
    pedagogical_explanation: {
      triage_tr:
        'Cümle "Because" (olduğu için) yan cümlesi ile başlar. "abundant" (bol), "thermal dissipation losses" (termal dağılma kayıpları), "virtually negligible" (neredeyse ihmal edilebilir).',
      target_word_insight_tr:
        '"Abundant" (bol) ve "negligible" (ihmal edilebilir) kelimelerinin tam Türkçe karşılıklarını taşıyan tek şık A seçeneğidir.',
      distractor_breakdowns: {
        A: 'Doğru seçenek: Özne, fiil, bağlaç ve hedef kelimeler eksiksiz aktarılmıştır.',
        B: 'Termal kayıpların arttığını (artmaktadır) iddia ederek zıt anlam yüklemiştir.',
        C: 'Güneş radyasyonunun azaldığını (azaldığında) söyleyerek şartı tersine çevirmiştir.',
        D: 'Gerektirmiştir (required) gibi orijinalde olmayan bir zorunluluk fiili eklemiştir.',
        E: 'Neden ile sonucu yer değiştirmiştir.'
      }
    }
  },

  // --- IRRELEVANT SENTENCE ---
  {
    id: 'lp-irrel-plausible-1',
    kind: 'LEARNING_PRACTICE',
    family: 'IRRELEVANT_SENTENCE',
    science_domain: 'technology',
    target_word_ids: ['plausible', 'empirical', 'corroborate'],
    stem: 'Choose the irrelevant sentence in the passage.',
    passage:
      '(I) For decades, astrophysicists sought a plausible model to explain the rapid expansion rate of the early universe. (II) Recent space telescope observations have finally provided empirical evidence corroborating this cosmic inflation theory. (III) Many recreational astronomers prefer using lightweight manual binoculars for stargazing on weekends. (IV) By matching mathematical simulations with these newly acquired empirical datasets, researchers narrowed down error margins significantly. (V) Consequently, the refined model offers unprecedented insights into primordial energy densities.',
    options: [
      { id: 'A', text: 'I' },
      { id: 'B', text: 'II' },
      { id: 'C', text: 'III' },
      { id: 'D', text: 'IV' },
      { id: 'E', text: 'V' }
    ],
    correct_option: 'C',
    pedagogical_explanation: {
      triage_tr:
        'Metin kozmik enflasyon modeli, akla yatkın hipotezler (plausible model) ve deneysel kanıtlar (empirical evidence) üzerinedir. (III) numaralı cümle ise hafta sonu hobi olarak dürbünle yıldız izleyen amatör astronomlardan bahsederek bilimsel akışı tamamen bozar.',
      target_word_insight_tr:
        'Konu bütünlüğü kozmolojik modeller ve ampirik kanıtlar zinciriyken, gündelik hobi faaliyeti alakasız cümledir.',
      distractor_breakdowns: {
        A: 'I numaralı cümle problemin temelini ve akla yatkın model arayışını sunar.',
        B: 'II numaralı cümle I\'de aranan modelin deneysel kanıtla doğrulandığını (corroborate) açıklar.',
        C: 'III numaralı cümle tamamen alakasızdır (hafif el dürbünleriyle hafta sonu gözlemi).',
        D: 'IV numaralı cümle "these newly acquired empirical datasets" diyerek II\'ye doğrudan referans verir.',
        E: 'V numaralı cümle sonuçta modelin getirdiği kazanımı özetler.'
      }
    }
  }
];

export function getPracticeQuestionsForWords(
  targetWordIds: readonly string[]
): readonly LearningPracticeQuestion[] {
  const matching = learningQuestionsBank.filter((q) =>
    q.target_word_ids.some((id) => targetWordIds.includes(id))
  );
  if (matching.length > 0) return matching;
  return learningQuestionsBank.slice(0, 3);
}
