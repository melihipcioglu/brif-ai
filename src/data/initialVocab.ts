import type { LexicalEntry, LexicalRecord } from '../types/lexical';
import { createLexicalRecord } from '../services/lexicalScheduler';

/**
 * Science-English starter vocabulary curated for YÖKDİL preparation.
 * Examples and distractor explanations are original teaching material, not exam quotations.
 * Tiers/priority values are editorial seeds, not measured ÖSYM occurrence frequencies.
 */
export const initialVocabEntries = [
  {
    word_id: 'inhibit', lemma: 'inhibit', pos: 'verb', tier: 1, priority_score: 98,
    exam_meaning_tr: 'engellemek; bir süreç veya etkinliği baskılamak', polarity_symbol: '↓',
    critical_collocations: [
      { phrase: 'inhibit growth', meaning_tr: 'büyümeyi baskılamak' },
      { phrase: 'inhibit enzyme activity', meaning_tr: 'enzim etkinliğini engellemek' },
      { phrase: 'inhibit the formation of', meaning_tr: 'oluşumunu engellemek' },
    ],
    synonyms: ['suppress', 'restrain'], antonyms: ['promote', 'stimulate'],
    typical_distractor: [
      { word: 'inhabit', meaning_tr: 'bir yerde yaşamak', explanation_tr: 'Yazımı benzerdir; bir süreci engellemek anlamına gelmez.' },
      { word: 'enhance', meaning_tr: 'artırmak; geliştirmek', explanation_tr: 'Etkinliğin yönünü baskılamadan artırmaya çevirir.' },
      { word: 'exhibit', meaning_tr: 'sergilemek', explanation_tr: 'Bir özelliği göstermektir; onu engellemek değildir.' },
    ],
    exam_sentence: 'Low temperatures can inhibit the growth of certain bacteria.',
    exam_sentence_tr: 'Düşük sıcaklıklar bazı bakterilerin büyümesini baskılayabilir.',
    word_family: [
      { pos: 'verb', form: 'inhibit', meaning_tr: 'engellemek' },
      { pos: 'noun', form: 'inhibition', meaning_tr: 'baskılama; engelleme' },
      { pos: 'noun', form: 'inhibitor', meaning_tr: 'baskılayıcı madde' },
      { pos: 'adjective', form: 'inhibitory', meaning_tr: 'baskılayıcı' },
    ],
  },
  {
    word_id: 'accelerate', lemma: 'accelerate', pos: 'verb', tier: 1, priority_score: 97,
    exam_meaning_tr: 'hızlandırmak; hızlanmak', polarity_symbol: '↑',
    critical_collocations: [
      { phrase: 'accelerate a reaction', meaning_tr: 'bir tepkimeyi hızlandırmak' },
      { phrase: 'accelerate the rate of', meaning_tr: 'hızını artırmak' },
      { phrase: 'accelerate particle motion', meaning_tr: 'parçacık hareketini hızlandırmak' },
    ],
    synonyms: ['speed up', 'hasten'], antonyms: ['decelerate', 'slow down'],
    typical_distractor: [
      { word: 'decelerate', meaning_tr: 'yavaşlatmak', explanation_tr: 'Hız değişiminin yönü terstir.' },
      { word: 'accumulate', meaning_tr: 'birikmek; biriktirmek', explanation_tr: 'Miktar artışını belirtir; doğrudan hız artışı değildir.' },
      { word: 'accommodate', meaning_tr: 'barındırmak; uyum sağlamak', explanation_tr: 'Benzer başlangıca rağmen süreç hızını anlatmaz.' },
    ],
    exam_sentence: 'A suitable catalyst can accelerate a chemical reaction.',
    exam_sentence_tr: 'Uygun bir katalizör kimyasal bir tepkimeyi hızlandırabilir.',
    word_family: [
      { pos: 'verb', form: 'accelerate', meaning_tr: 'hızlandırmak' },
      { pos: 'noun', form: 'acceleration', meaning_tr: 'ivme; hızlanma' },
      { pos: 'noun', form: 'accelerator', meaning_tr: 'hızlandırıcı' },
      { pos: 'adjective', form: 'accelerated', meaning_tr: 'hızlandırılmış' },
    ],
  },
  {
    word_id: 'diminish', lemma: 'diminish', pos: 'verb', tier: 1, priority_score: 96,
    exam_meaning_tr: 'azalmak; azaltmak', polarity_symbol: '↓',
    critical_collocations: [
      { phrase: 'diminish in size', meaning_tr: 'boyutu küçülmek' },
      { phrase: 'diminish the impact of', meaning_tr: 'etkisini azaltmak' },
      { phrase: 'diminish over time', meaning_tr: 'zaman içinde azalmak' },
    ],
    synonyms: ['decrease', 'reduce'], antonyms: ['increase', 'augment'],
    typical_distractor: [
      { word: 'demolish', meaning_tr: 'yıkmak', explanation_tr: 'Tamamen yıkma anlamı taşır; dereceli azalma değildir.' },
      { word: 'enhance', meaning_tr: 'artırmak; geliştirmek', explanation_tr: 'Azalmanın ters yönündedir.' },
      { word: 'distinguish', meaning_tr: 'ayırt etmek', explanation_tr: 'Nesneler arasındaki farkı saptamaktır; miktarı azaltmak değildir.' },
    ],
    exam_sentence: 'The intensity of the signal diminishes as the distance increases.',
    exam_sentence_tr: 'Mesafe arttıkça sinyalin şiddeti azalır.',
    word_family: [
      { pos: 'verb', form: 'diminish', meaning_tr: 'azalmak; azaltmak' },
      { pos: 'noun', form: 'diminution', meaning_tr: 'azalma; küçülme' },
      { pos: 'adjective', form: 'diminished', meaning_tr: 'azalmış' },
      { pos: 'adjective', form: 'diminishing', meaning_tr: 'giderek azalan' },
    ],
  },
  {
    word_id: 'deteriorate', lemma: 'deteriorate', pos: 'verb', tier: 1, priority_score: 95,
    exam_meaning_tr: 'bozulmak; niteliği veya durumu kötüleşmek', polarity_symbol: '↓',
    critical_collocations: [
      { phrase: 'deteriorate rapidly', meaning_tr: 'hızla bozulmak' },
      { phrase: 'deteriorate over time', meaning_tr: 'zamanla kötüleşmek' },
      { phrase: 'deteriorate in quality', meaning_tr: 'kalitesi bozulmak' },
    ],
    synonyms: ['worsen', 'degrade'], antonyms: ['improve', 'recover'],
    typical_distractor: [
      { word: 'determine', meaning_tr: 'belirlemek', explanation_tr: 'Bir sonuca ulaşmayı anlatır; kötüleşme değildir.' },
      { word: 'improve', meaning_tr: 'iyileşmek', explanation_tr: 'Kalite değişiminin yönü tersine döner.' },
      { word: 'fluctuate', meaning_tr: 'dalgalanmak', explanation_tr: 'Artış ve azalış içerebilir; sürekli kötüleşme anlamını vermez.' },
    ],
    exam_sentence: 'Water quality may deteriorate when untreated waste enters a river.',
    exam_sentence_tr: 'Arıtılmamış atık bir nehre karıştığında su kalitesi bozulabilir.',
    word_family: [
      { pos: 'verb', form: 'deteriorate', meaning_tr: 'kötüleşmek' },
      { pos: 'noun', form: 'deterioration', meaning_tr: 'bozulma; kötüleşme' },
      { pos: 'adjective', form: 'deteriorating', meaning_tr: 'kötüleşen' },
      { pos: 'adjective', form: 'deteriorated', meaning_tr: 'bozulmuş' },
    ],
  },
  {
    word_id: 'trigger', lemma: 'trigger', pos: 'verb', tier: 1, priority_score: 98,
    exam_meaning_tr: 'tetiklemek; bir olay veya süreci başlatmak', polarity_symbol: '↑',
    critical_collocations: [
      { phrase: 'trigger a reaction', meaning_tr: 'bir tepkimeyi tetiklemek' },
      { phrase: 'trigger a chain reaction', meaning_tr: 'zincirleme tepkime başlatmak' },
      { phrase: 'trigger an immune response', meaning_tr: 'bağışıklık yanıtını tetiklemek' },
    ],
    synonyms: ['initiate', 'set off'], antonyms: ['prevent', 'suppress'],
    typical_distractor: [
      { word: 'hinder', meaning_tr: 'engellemek; zorlaştırmak', explanation_tr: 'Sürecin başlamasını desteklemek yerine zorlaştırır.' },
      { word: 'trace', meaning_tr: 'izini sürmek', explanation_tr: 'Süreci incelemektir; başlatmak değildir.' },
      { word: 'sustain', meaning_tr: 'sürdürmek', explanation_tr: 'Başlangıcı değil, başlamış sürecin devamını anlatır.' },
    ],
    exam_sentence: 'A sudden rise in temperature can trigger a stress response in plants.',
    exam_sentence_tr: 'Sıcaklıktaki ani bir artış bitkilerde stres yanıtını tetikleyebilir.',
    word_family: [
      { pos: 'verb', form: 'trigger', meaning_tr: 'tetiklemek' },
      { pos: 'noun', form: 'trigger', meaning_tr: 'tetikleyici etken; tetik' },
      { pos: 'adjective', form: 'triggered', meaning_tr: 'tetiklenmiş' },
      { pos: 'noun', form: 'triggering', meaning_tr: 'tetikleme' },
    ],
  },
  {
    word_id: 'enhance', lemma: 'enhance', pos: 'verb', tier: 1, priority_score: 94,
    exam_meaning_tr: 'artırmak; geliştirmek; güçlendirmek', polarity_symbol: '↑',
    critical_collocations: [
      { phrase: 'enhance efficiency', meaning_tr: 'verimliliği artırmak' },
      { phrase: 'enhance performance', meaning_tr: 'performansı geliştirmek' },
      { phrase: 'enhance the ability to', meaning_tr: 'yapabilme yeteneğini geliştirmek' },
    ],
    synonyms: ['improve', 'boost'], antonyms: ['impair', 'diminish'],
    typical_distractor: [
      { word: 'inhibit', meaning_tr: 'baskılamak', explanation_tr: 'Etkinin yönü artırmadan baskılamaya döner.' },
      { word: 'enclose', meaning_tr: 'çevrelemek; içine koymak', explanation_tr: 'Fiziksel çevrelemeyi anlatır; kalite artışı değildir.' },
      { word: 'endure', meaning_tr: 'dayanmak', explanation_tr: 'Bir koşula katlanmaktır; niteliği artırmak değildir.' },
    ],
    exam_sentence: 'Improved insulation can enhance the energy efficiency of a building.',
    exam_sentence_tr: 'Daha iyi yalıtım bir binanın enerji verimliliğini artırabilir.',
    word_family: [
      { pos: 'verb', form: 'enhance', meaning_tr: 'geliştirmek' },
      { pos: 'noun', form: 'enhancement', meaning_tr: 'iyileştirme; artırma' },
      { pos: 'noun', form: 'enhancer', meaning_tr: 'artırıcı etken' },
      { pos: 'adjective', form: 'enhanced', meaning_tr: 'geliştirilmiş' },
    ],
  },
  {
    word_id: 'deplete', lemma: 'deplete', pos: 'verb', tier: 1, priority_score: 92,
    exam_meaning_tr: 'bir kaynağı tüketmek; miktarını ciddi biçimde azaltmak', polarity_symbol: '↓',
    critical_collocations: [
      { phrase: 'deplete natural resources', meaning_tr: 'doğal kaynakları tüketmek' },
      { phrase: 'deplete oxygen levels', meaning_tr: 'oksijen düzeylerini düşürmek' },
      { phrase: 'deplete energy reserves', meaning_tr: 'enerji depolarını tüketmek' },
    ],
    synonyms: ['exhaust', 'use up'], antonyms: ['replenish', 'restore'],
    typical_distractor: [
      { word: 'replenish', meaning_tr: 'yeniden doldurmak', explanation_tr: 'Kaynağı tüketmenin tersidir.' },
      { word: 'deposit', meaning_tr: 'biriktirmek; çökelmek', explanation_tr: 'Maddenin bir yere eklenmesini anlatabilir; tüketilmesini değil.' },
      { word: 'detect', meaning_tr: 'tespit etmek', explanation_tr: 'Varlığını saptamaktır; miktarını azaltmaz.' },
    ],
    exam_sentence: 'Excessive irrigation can deplete groundwater reserves.',
    exam_sentence_tr: 'Aşırı sulama yeraltı suyu rezervlerini tüketebilir.',
    word_family: [
      { pos: 'verb', form: 'deplete', meaning_tr: 'tüketmek' },
      { pos: 'noun', form: 'depletion', meaning_tr: 'tükenme; azalma' },
      { pos: 'adjective', form: 'depleted', meaning_tr: 'tükenmiş; azalmış' },
      { pos: 'adjective', form: 'depletable', meaning_tr: 'tükenebilir' },
    ],
  },
  {
    word_id: 'plausible', lemma: 'plausible', pos: 'adjective', tier: 2, priority_score: 95,
    exam_meaning_tr: 'akla yatkın; makul görünen (doğruluğu kanıtlanmış olmak zorunda değil)', polarity_symbol: '⇄',
    critical_collocations: [
      { phrase: 'a plausible explanation', meaning_tr: 'akla yatkın bir açıklama' },
      { phrase: 'a plausible hypothesis', meaning_tr: 'makul bir hipotez' },
      { phrase: 'scientifically plausible', meaning_tr: 'bilimsel açıdan akla yatkın' },
    ],
    synonyms: ['credible', 'reasonable'], antonyms: ['implausible', 'incredible'],
    typical_distractor: [
      { word: 'proven', meaning_tr: 'kanıtlanmış', explanation_tr: 'Plausible kesin kanıt içermez; yalnızca akla yatkınlığı belirtir.' },
      { word: 'possible', meaning_tr: 'mümkün', explanation_tr: 'Mümkün olmak, bir açıklamanın ikna edici olmasıyla aynı değildir.' },
      { word: 'implausible', meaning_tr: 'akla yatkın olmayan', explanation_tr: 'Olumsuz önek anlamı tersine çevirir.' },
    ],
    exam_sentence: 'The researchers proposed a plausible explanation for the unexpected result.',
    exam_sentence_tr: 'Araştırmacılar beklenmedik sonuç için akla yatkın bir açıklama önerdi.',
    word_family: [
      { pos: 'adjective', form: 'plausible', meaning_tr: 'akla yatkın' },
      { pos: 'noun', form: 'plausibility', meaning_tr: 'akla yatkınlık' },
      { pos: 'adverb', form: 'plausibly', meaning_tr: 'makul biçimde' },
      { pos: 'adjective', form: 'implausible', meaning_tr: 'akla yatkın olmayan' },
      { pos: 'noun', form: 'implausibility', meaning_tr: 'akla yatkın olmama' },
    ],
  },
  {
    word_id: 'susceptible-to', lemma: 'susceptible to', pos: 'phrase', tier: 2, priority_score: 96,
    mastery_requirements: { collocation_required: true, distractor_required: true },
    exam_meaning_tr: 'bir etkene karşı duyarlı; etkilenmeye veya zarar görmeye yatkın', polarity_symbol: '↓',
    critical_collocations: [
      { phrase: 'susceptible to infection', meaning_tr: 'enfeksiyona yatkın' },
      { phrase: 'susceptible to corrosion', meaning_tr: 'korozyona duyarlı' },
      { phrase: 'highly susceptible to', meaning_tr: 'karşı son derece duyarlı' },
    ],
    synonyms: ['vulnerable to', 'prone to'], antonyms: ['resistant to', 'immune to'],
    typical_distractor: [
      { word: 'resistant to', meaning_tr: 'karşı dirençli', explanation_tr: 'Duyarlılığın tersini anlatır; aynı to edatı yanıltabilir.' },
      { word: 'suspicious of', meaning_tr: 'şüphe duyan', explanation_tr: 'Benzer yazıma rağmen zihinsel kuşkuyu anlatır ve of alır.' },
      { word: 'responsible for', meaning_tr: 'sorumlu; nedeni olan', explanation_tr: 'Etkilenmeyi değil, sorumluluğu veya nedenselliği anlatır.' },
    ],
    exam_sentence: 'Some metals are particularly susceptible to corrosion in humid environments.',
    exam_sentence_tr: 'Bazı metaller nemli ortamlarda korozyona özellikle duyarlıdır.',
    word_family: [
      { pos: 'adjective', form: 'susceptible', meaning_tr: 'duyarlı; yatkın' },
      { pos: 'noun', form: 'susceptibility', meaning_tr: 'duyarlılık; yatkınlık' },
      { pos: 'adjective', form: 'insusceptible', meaning_tr: 'etkilenmeyen; duyarlı olmayan' },
      { pos: 'phrase', form: 'susceptible to', meaning_tr: 'bir etkene karşı duyarlı' },
    ],
  },
  {
    word_id: 'robust', lemma: 'robust', pos: 'adjective', tier: 2, priority_score: 90,
    exam_meaning_tr: 'sağlam; koşul değişimlerine karşı dayanıklı veya güvenilir', polarity_symbol: '↑',
    critical_collocations: [
      { phrase: 'robust evidence', meaning_tr: 'güçlü kanıt' },
      { phrase: 'a robust method', meaning_tr: 'sağlam bir yöntem' },
      { phrase: 'robust against noise', meaning_tr: 'gürültüye karşı dayanıklı' },
    ],
    synonyms: ['resilient', 'sturdy'], antonyms: ['fragile', 'weak'],
    typical_distractor: [
      { word: 'fragile', meaning_tr: 'kırılgan', explanation_tr: 'Dayanıklılığın tersidir.' },
      { word: 'rigid', meaning_tr: 'katı; esnek olmayan', explanation_tr: 'Katılık tek başına yöntemin güvenilir veya dayanıklı olduğunu göstermez.' },
      { word: 'rough', meaning_tr: 'kaba; yaklaşık', explanation_tr: 'Yaklaşık olmak, farklı koşullarda güvenilir olmakla aynı değildir.' },
    ],
    exam_sentence: 'A robust model should remain useful when the input data contain small errors.',
    exam_sentence_tr: 'Sağlam bir model, girdi verileri küçük hatalar içerdiğinde de işe yarar kalmalıdır.',
    word_family: [
      { pos: 'adjective', form: 'robust', meaning_tr: 'sağlam' },
      { pos: 'noun', form: 'robustness', meaning_tr: 'sağlamlık; dayanıklılık' },
      { pos: 'adverb', form: 'robustly', meaning_tr: 'sağlam biçimde' },
    ],
  },
  {
    word_id: 'negligible', lemma: 'negligible', pos: 'adjective', tier: 2, priority_score: 93,
    exam_meaning_tr: 'ihmal edilebilir; etkisi veya miktarı çok küçük', polarity_symbol: '↓',
    critical_collocations: [
      { phrase: 'a negligible effect', meaning_tr: 'ihmal edilebilir bir etki' },
      { phrase: 'negligible amounts of', meaning_tr: 'çok küçük miktarlarda' },
      { phrase: 'negligible compared with', meaning_tr: 'ile karşılaştırıldığında önemsiz' },
    ],
    synonyms: ['insignificant', 'minimal'], antonyms: ['substantial', 'considerable'],
    typical_distractor: [
      { word: 'negligent', meaning_tr: 'ihmalkâr', explanation_tr: 'Kişinin özensiz davranışını anlatır; niceliğin küçüklüğünü değil.' },
      { word: 'considerable', meaning_tr: 'kayda değer; oldukça büyük', explanation_tr: 'Miktar veya önem açısından ters yöndedir.' },
      { word: 'negative', meaning_tr: 'negatif; olumsuz', explanation_tr: 'Küçük etki mutlaka negatif etki değildir.' },
    ],
    exam_sentence: 'Under these conditions, heat loss through the container is negligible.',
    exam_sentence_tr: 'Bu koşullarda kap üzerinden gerçekleşen ısı kaybı ihmal edilebilir.',
    word_family: [
      { pos: 'adjective', form: 'negligible', meaning_tr: 'ihmal edilebilir' },
      { pos: 'adverb', form: 'negligibly', meaning_tr: 'ihmal edilebilir ölçüde' },
      { pos: 'verb', form: 'neglect', meaning_tr: 'ihmal etmek' },
      { pos: 'noun', form: 'negligence', meaning_tr: 'ihmalkârlık' },
      { pos: 'adjective', form: 'negligent', meaning_tr: 'ihmalkâr' },
    ],
  },
  {
    word_id: 'abundant', lemma: 'abundant', pos: 'adjective', tier: 2, priority_score: 91,
    exam_meaning_tr: 'bol; çok miktarda bulunan', polarity_symbol: '↑',
    critical_collocations: [
      { phrase: 'abundant in nature', meaning_tr: 'doğada bol bulunan' },
      { phrase: 'an abundant source of', meaning_tr: 'bol bulunan bir kaynak' },
      { phrase: 'abundant evidence', meaning_tr: 'bol miktarda kanıt' },
    ],
    synonyms: ['plentiful', 'copious'], antonyms: ['scarce', 'rare'],
    typical_distractor: [
      { word: 'scarce', meaning_tr: 'kıt', explanation_tr: 'Bolluğun tersidir.' },
      { word: 'redundant', meaning_tr: 'gereksiz; fazlalık oluşturan', explanation_tr: 'Bol bulunan şeyin gereksiz olması gerekmez.' },
      { word: 'sufficient', meaning_tr: 'yeterli', explanation_tr: 'Yeterli miktar, bol miktar anlamına gelmek zorunda değildir.' },
    ],
    exam_sentence: 'Solar energy is abundant in regions that receive intense sunlight.',
    exam_sentence_tr: 'Güneş enerjisi yoğun güneş ışığı alan bölgelerde boldur.',
    word_family: [
      { pos: 'adjective', form: 'abundant', meaning_tr: 'bol' },
      { pos: 'noun', form: 'abundance', meaning_tr: 'bolluk' },
      { pos: 'adverb', form: 'abundantly', meaning_tr: 'bol miktarda' },
      { pos: 'adjective', form: 'overabundant', meaning_tr: 'gereğinden fazla bol' },
    ],
  },
] as const satisfies readonly LexicalEntry[];

/** Fresh, independent progress objects on each invocation. */
export function createInitialVocab(now = Date.now()): LexicalRecord[] {
  return initialVocabEntries.map((entry) => createLexicalRecord(entry, now));
}

/** Deterministic import: no clock, IndexedDB write or other side effect at module load. */
export const initialVocab: readonly LexicalRecord[] = createInitialVocab(0);
