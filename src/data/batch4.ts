import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, anchors } from './authoringUtils';

export const batch4Questions: readonly Question[] = deepFreeze([
  // CLOZE_TEST
  make({
    id: 'b4-cloze-1', family: 'CLOZE_TEST', domain: 'medicine',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Vaccines stimulate the immune system to fight specific pathogens. ____, they prevent serious illnesses and save millions of lives annually. This makes them a cornerstone of public health.',
    correct: 'C',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Vaccines stimulate the immune system to fight specific pathogens.', target_sentence: '____, they prevent serious illnesses and save millions of lives annually.', next_sentence: 'This makes them a cornerstone of public health.', macro_context: 'Vaccine benefits', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CONCESSION', C: 'RESULT', D: 'CONDITION', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Bağışıklık sistemini uyarmanın sonucunu bulun.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['However', 'Zıtlık durumu söz konusu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Even though', 'Bağışıklık sistemini uyarmasına rağmen hayat kurtarır denilemez.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['As a result', 'Uyarmasının doğrudan bir sonucu olarak hastalıkları önler.', [], []],
      ['Otherwise', 'Aksi takdirde (otherwise) anlamı bozmaktadır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['In addition', 'Ekleme yapılabilir ancak "as a result" neden-sonuç bağını daha güçlü kurar.', ['PARTIAL_TRUTH'], ['DISCOURSE_RELATION']]
    ]
  }),
  make({
    id: 'b4-cloze-2', family: 'CLOZE_TEST', domain: 'physics',
    stem: 'Choose the correct verb form for the blank.',
    passage: 'Quantum computers use principles of quantum mechanics to process information. By ____ superposition and entanglement, they can perform complex calculations faster than classical computers. Their potential applications are vast.',
    correct: 'A',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Quantum computers use principles of quantum mechanics to process information.', target_sentence: 'By ____ superposition and entanglement, they can perform complex calculations faster than classical computers.', next_sentence: 'Their potential applications are vast.', macro_context: 'Quantum computing', relation: 'ADDITION', candidate_relations: { A: 'ADDITION', B: 'RESULT', C: 'CONTRAST', D: 'RESULT', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'By edatından sonra gelen aktif fiilimsi formunu (gerund) bulun.',
    skills: ['VOICE_REDUCTION'],
    choices: [
      ['utilizing', 'Kullanarak (by utilizing) aktif ve doğru bir yapıdır.', [], []],
      ['utilized', 'Geçmiş zaman/edilgen yapı edatla kullanılmaz.', ['SEMANTIC_ROLE_SWAP'], ['DISCOURSE_RELATION']],
      ['to utilize', 'Mastar yapısı by edatından sonra gelmez.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['having utilized', 'Geçmişte kullanarak anlamı genel geçer prensiple çelişir.', ['TEMPORAL_MISMATCH'], ['DISCOURSE_RELATION']],
      ['utilize', 'Yalın fiil edattan sonra doğrudan kullanılamaz.', ['PARTIAL_TRUTH'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-cloze-3', family: 'CLOZE_TEST', domain: 'biology',
    stem: 'Choose the correct word for the blank.',
    passage: 'Photosynthesis is vital for life on Earth. During this process, plants ____ sunlight, carbon dioxide, and water into oxygen and energy-rich carbohydrates. This provides food for other organisms.',
    correct: 'B',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Photosynthesis is vital for life on Earth.', target_sentence: 'During this process, plants ____ sunlight, carbon dioxide, and water into oxygen and energy-rich carbohydrates.', next_sentence: 'This provides food for other organisms.', macro_context: 'Photosynthesis conversion', relation: 'ADDITION', candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'CONTRAST', D: 'RESULT', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Bir şeyleri oksijen ve karbonhidrata dönüştürmeyi (into) tamamlayacak fiili bulun.',
    skills: ['VOCAB_CONTEXT'],
    choices: [
      ['destroy', 'Yok etmek fotosentezin yapım (sentez) özelliğiyle çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['convert', 'Dönüştürmek (convert into) sürecin temel tanımıdır.', [], []],
      ['abandon', 'Bırakmak veya terk etmek anlamsızdır.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']],
      ['release', 'Sadece oksijen salınır; güneş ışığı ve suyu "salmak" yanlıştır.', ['PARTIAL_TRUTH'], ['PASSAGE_SUPPORT']],
      ['consume', 'Tüketmek doğru olsa da, "consume into" kalıbı yanlıştır.', ['FALSE_FRIEND'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-cloze-4', family: 'CLOZE_TEST', domain: 'environment',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Renewable energy sources like wind and solar are abundant. ____, they depend heavily on weather conditions, which can lead to unpredictable energy generation. Therefore, energy storage solutions are crucial.',
    correct: 'D',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Renewable energy sources like wind and solar are abundant.', target_sentence: '____, they depend heavily on weather conditions, which can lead to unpredictable energy generation.', next_sentence: 'Therefore, energy storage solutions are crucial.', macro_context: 'Renewable energy limitations', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'CONDITION', D: 'CONTRAST', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Bol olmaları (olumlu) ile hava koşullarına bağlı olmaları (olumsuz) arasındaki zıtlığı bağlayın.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['Consequently', 'Bağımlılık, bol olmalarının bir sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Furthermore', 'Ekleme bağlacı zıtlığı karşılayamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['If so', 'Koşul cümlesi anlamı bozar.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['However', 'Olumlu özellik (bolluk) ile olumsuz sınırlandırmayı bağlayan doğru zıtlık bağlacıdır.', [], []],
      ['Thus', 'Sonuç bağlacıdır, zıtlık oluşturmaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']]
    ]
  }),
  make({
    id: 'b4-cloze-5', family: 'CLOZE_TEST', domain: 'astronomy',
    stem: 'Choose the correct word for the blank.',
    passage: 'The James Webb Space Telescope operates in the infrared spectrum. This capability allows it to peer through dense cosmic dust and observe the ____ of the first galaxies. It has revolutionized our understanding of the early universe.',
    correct: 'A',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'The James Webb Space Telescope operates in the infrared spectrum.', target_sentence: 'This capability allows it to peer through dense cosmic dust and observe the ____ of the first galaxies.', next_sentence: 'It has revolutionized our understanding of the early universe.', macro_context: 'JWST early galaxies', relation: 'ADDITION', candidate_relations: { A: 'ADDITION', B: 'RESULT', C: 'CONTRAST', D: 'RESULT', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'İlk galaksilerle ilgili gözlemlenebilecek olumlu veya nötr kavramı bulun.',
    skills: ['VOCAB_CONTEXT'],
    choices: [
      ['formation', 'İlk galaksilerin oluşumunu (formation) gözlemlemek astronominin temel amacıdır.', [], []],
      ['destruction', 'İlk galaksiler yeni oluştuğundan yok olmalarını gözlemlemek beklenmez.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['pollution', 'Galaksiler kirlilik (pollution) barındırmaz.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']],
      ['abandonment', 'Terk edilmeleri anlamsız bir ifadedir.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']],
      ['resistance', 'Direnç göstermeleri bağlama uymaz.', ['FALSE_FRIEND'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-cloze-6', family: 'CLOZE_TEST', domain: 'geology',
    stem: 'Choose the appropriate structure for the blank.',
    passage: 'Fossils provide crucial evidence of ancient life. By examining the rock layers ____ these fossils, geologists can determine the relative age of different species. This technique is known as relative dating.',
    correct: 'E',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Fossils provide crucial evidence of ancient life.', target_sentence: 'By examining the rock layers ____ these fossils, geologists can determine the relative age of different species.', next_sentence: 'This technique is known as relative dating.', macro_context: 'Fossil dating', relation: 'ADDITION', candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'CONTRAST', D: 'RESULT', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Fosilleri barındıran kaya katmanlarını niteleyen aktif kısaltmayı bulun.',
    skills: ['VOICE_REDUCTION'],
    choices: [
      ['are containing', 'İkinci bir çekimli yüklem (are) yan cümle olmaksızın kullanılamaz.', ['PARTIAL_TRUTH'], ['CONTINUATION']],
      ['contained', 'Fosiller kaya katmanlarını barındırmaz, kaya katmanları fosilleri barındırır (aktif anlam).', ['SEMANTIC_ROLE_SWAP'], ['DISCOURSE_RELATION']],
      ['to contain', 'Amaç bildiren mastar yapısı doğrudan ismi bu şekilde nitelemez.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['will contain', 'Gelecek zaman kipi geçmişteki veya genel geçer durumla uyuşmaz.', ['TEMPORAL_MISMATCH'], ['CONTINUATION']],
      ['containing', 'Fosilleri barındıran (containing) katmanlar anlamında doğru present participle yapısıdır.', [], []]
    ]
  }),

  // SENTENCE_COMPLETION
  make({
    id: 'b4-sentence-1', family: 'SENTENCE_COMPLETION', domain: 'medicine',
    stem: 'Since early detection is one of the most effective strategies against cancer, ____.',
    correct: 'B',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Erken teşhisin etkili bir strateji olmasının (neden) sonucunu (tavsiye/uygulama) bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['many patients wait until symptoms become severe before seeking help', 'Bu durum bir zıtlık oluşturur, "since" bağlacıyla uyumsuzdur.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['health organizations strongly recommend regular screenings for high-risk individuals', 'Erken teşhisin öneminden dolayı düzenli taramalar önerilmesi doğru mantıksal sonuçtur.', [], []],
      ['the disease was previously considered completely incurable', 'Geçmişteki düşünce erken teşhisin öneminin bir sonucu değildir.', ['TEMPORAL_MISMATCH'], ['DISCOURSE_RELATION']],
      ['most modern treatments focus entirely on managing late-stage symptoms', 'Geç aşamaya odaklanmak, erken teşhisin önemine aykırıdır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['genetic factors play a minor role in overall disease progression', 'Genetik faktörler erken teşhis konusuyla mantıksal bir sonuç ilişkisi kurmaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']]
    ]
  }),
  make({
    id: 'b4-sentence-2', family: 'SENTENCE_COMPLETION', domain: 'technology',
    stem: 'Even though blockchain technology was initially designed for cryptocurrencies, ____.',
    correct: 'C',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'CAUSE', C: 'CONTRAST', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Başlangıçta kripto para için tasarlanmasına rağmen (zıtlık), günümüzdeki farklı kullanımlarını bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['its value is highly dependent on market speculation and investor sentiment', 'Piyasa dalgalanması, teknolojinin ilk tasarımıyla zıtlık oluşturmaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['only a few people understood its complex cryptographic foundations at the time', 'Sınırlı anlayış, zıtlık (even though) bağlacını karşılamaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['it is now being adopted for secure data management in various industries', 'İlk amacının aksine günümüzde başka endüstrilerde de kullanılması tam bir zıtlık / genişleme sunar.', [], []],
      ['traditional banking systems have completely replaced it in recent years', 'Yerini bankalara bırakması "başlangıçta öyle tasarlandı" fikriyle anlamlı bir bağlam yaratmaz.', ['UNSUPPORTED_DETAIL'], ['DISCOURSE_RELATION']],
      ['it failed to gain any traction outside of niche online communities', 'Eğer sadece kripto için tasarlanmış ve başarısız olmuşsa ortada zıtlık (even though) kalmaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']]
    ]
  }),
  make({
    id: 'b4-sentence-3', family: 'SENTENCE_COMPLETION', domain: 'chemistry',
    stem: 'By modifying the molecular structure of the polymer, ____.',
    correct: 'D',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'ADDITION', D: 'RESULT', E: 'CONDITION' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Moleküler yapıyı değiştirmenin (araç/yöntem) olası sonucunu bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['it was almost impossible to measure its exact weight', 'Zorluk çekilmesi, bilerek yapılan değiştirme işleminin hedeflenen sonucu olamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['the researchers had abandoned their experiment early', 'Deneyin terk edilmesi moleküler değişikliğin mantıksal bir sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['traditional plastics take centuries to decompose completely', 'Geleneksel plastiklerin doğada çözünmesi konuyla bağlantılı değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['scientists were able to create a material that is both stronger and more flexible', 'Yapının değiştirilmesi sayesinde daha güçlü ve esnek bir materyal elde edilmesi doğru sonuçtur.', [], []],
      ['because chemical reactions often release unpredictable amounts of heat', 'Because bağlacıyla başlamak ana cümleyi (main clause) eksik bırakır.', ['PARTIAL_TRUTH'], ['CLAUSE_COMPATIBILITY']]
    ]
  }),
  make({
    id: 'b4-sentence-4', family: 'SENTENCE_COMPLETION', domain: 'biology',
    stem: 'Unless a significant amount of the coral reef ecosystem is protected, ____.',
    correct: 'E',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONDITION', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CAUSE', E: 'CONDITION' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Korunmadıkça (-medikçe) meydana gelecek olumsuz sonucu bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['they provide shelter for thousands of marine species', 'Korunmadıkça barınak sağlarlar anlamı zıt ve mantıksızdır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['tourists will continue to visit these beautiful underwater habitats', 'Turist ziyareti, ekosistem tahribatının doğrudan ekolojik sonucu değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['marine biologists discovered new species in the deepest parts of the ocean', 'Geçmiş zaman (discovered) Type 1 koşul cümlesiyle uyumsuzdur.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
      ['some forms of algae are known to thrive in highly acidic waters', 'Alglerin büyümesi korunmama durumuyla ilişkili temel bir sonuç değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['many dependent species will likely face extinction within the next few decades', 'Korunmadıkça bağlı türlerin yok olma tehlikesi yaşaması uygun ve mantıklı bir sonuçtur.', [], []]
    ]
  }),
  make({
    id: 'b4-sentence-5', family: 'SENTENCE_COMPLETION', domain: 'physics',
    stem: '____, the spacecraft relies on a combination of solar panels and long-lasting batteries.',
    correct: 'A',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CAUSE', candidate_relations: { A: 'CAUSE', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Uzay aracının güneş paneli ve batarya kullanmasının nedenini (since, because vb.) arayın.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['Since it needs a continuous supply of energy during its journey into deep space', 'Sürekli enerji ihtiyacı, güneş paneli ve batarya kullanımının mantıklı nedenidir.', [], []],
      ['Although it was primarily designed to study the atmosphere of nearby planets', 'Zıtlık (although) enerji kaynağı seçimi ile ilişkisizdir.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['In order to reduce the enormous costs associated with launching heavy payloads', 'Panel ve batarya kullanmak yükü artırır, bu nedenle maliyet azaltmakla doğrudan ilişkili değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Provided that astronauts can repair the outer hull during a spacewalk', 'Koşul cümlesi, enerji donanımının genel nedeni olamaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Before engineers discovered a critical flaw in the propulsion system', 'İtici sistemdeki hata ile enerji kaynağının seçimi arasında mantıksal bir neden bağı yoktur.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']]
    ]
  }),
  make({
    id: 'b4-sentence-6', family: 'SENTENCE_COMPLETION', domain: 'environment',
    stem: 'While electric vehicles emit zero exhaust gases during operation, ____.',
    correct: 'C',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'CAUSE', C: 'CONTRAST', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Sıfır egzoz gazı salımına (olumlu) rağmen, çevresel bir dezavantaj veya sınırlama arayın.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['they are becoming increasingly popular in many developing countries', 'Popülerleşme, egzoz gazı sıfır olmasıyla zıtlık (while) oluşturmaz, destekler.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['the government offers significant tax incentives to buyers', 'Teşvikler de destekleyici bir faktördür, zıtlık oluşturmaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['their manufacturing process and battery disposal still have a considerable environmental impact', 'Üretim ve batarya atıklarının çevreye etkisi (olumsuz), sıfır emisyonla (olumlu) tam bir zıtlık oluşturur.', [], []],
      ['most cities lack the necessary infrastructure to support them', 'Altyapı eksikliği pratik bir sorundur ancak "çevre/emisyon" odaklı "exhaust gases" vurgusunu birebir karşılamaz.', ['PARTIAL_TRUTH'], ['DISCOURSE_RELATION']],
      ['consumers often worry about the limited driving range on a single charge', 'Menzil endişesi çevre teması (egzoz) yerine pratiklik temasına aittir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']]
    ]
  }),

  // PARAGRAPH_COMPLETION
  make({
    id: 'b4-para-1', family: 'PARAGRAPH_COMPLETION', domain: 'geology',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Tectonic plates are massive pieces of the Earth\'s crust that constantly move over the fluid mantle. When these plates collide, immense pressure builds up over time. ____. This sudden release of energy sends seismic waves through the ground, causing what we experience as an earthquake.',
    correct: 'D',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'ADDITION', D: 'RESULT', E: 'RESULT' }, anchors: anchors('D') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Basınç birikimi ile "This sudden release of energy" arasına girecek olayı bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Some tectonic plates move apart, creating new crust at mid-ocean ridges.', 'Uzaklaşma (move apart), çarpışma (collide) temasından koparır.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['Scientists have developed sensitive instruments to measure this movement.', 'Cihazlar, enerjinin açığa çıkması (This sudden release) sürecini açıklamaz.', ['FALSE_FRIEND'], ['CONTINUATION']],
      ['The Earth\'s core remains incredibly hot due to radioactive decay.', 'Çekirdeğin ısısı yüzeydeki basınç boşalması sürecini tamamlamaz.', ['SCOPE_DRIFT'], ['TOPIC']],
      ['Eventually, the rock breaks or slips, releasing all the accumulated stress at once.', 'Kayanın kırılması ve stresi tek seferde boşaltması, sonraki "This sudden release..." ifadesine mükemmel uyar.', [], []],
      ['Mountains are often formed slowly through this continuous collision.', 'Dağ oluşumu doğru olsa da, "This sudden release" (anlık enerji salımı) ile uyuşmaz.', ['PARTIAL_TRUTH'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-para-2', family: 'PARAGRAPH_COMPLETION', domain: 'astronomy',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Black holes have gravitational fields so intense that nothing can escape them, not even light. As a result, they cannot be observed directly through traditional telescopes. ____. By tracking how these stars orbit an invisible point of immense mass, scientists can deduce the presence of a black hole.',
    correct: 'B',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' }, anchors: anchors('B') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Doğrudan gözlemlenememesi ile "these stars orbit..." arasına, etraftaki yıldızlara olan etkilerini bağlayan cümleyi koyun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Many black holes form after the collapse of massive stars at the end of their lifecycle.', 'Oluşum süreci (form after), gözlem yöntemi temasıyla ilgisizdir.', ['SCOPE_DRIFT'], ['TOPIC']],
      ['Instead, astronomers must look for their effects on nearby stars and gas clouds.', 'Doğrudan gözlem yerine çevreye olan etkinin aranması, "these stars" referansını sağlar.', [], []],
      ['Therefore, scientists have completely given up on studying them.', 'Vazgeçilmesi yanlıştır, ardından çalışmaların nasıl yapıldığı (tracking) anlatılmaktadır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['The speed of light is considered the absolute limit in the universe.', 'Işık hızı limiti, gözlem metoduyla ilgili cümleyi tamamlamaz.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['Our own galaxy, the Milky Way, contains billions of completely dark planets.', 'Karanlık gezegenler kara delik gözlemi konusundan uzaktır.', ['SCOPE_DRIFT'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-para-3', family: 'PARAGRAPH_COMPLETION', domain: 'biology',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Antibiotic resistance is becoming a major global health crisis. When bacteria are exposed to antibiotics, susceptible ones die off quickly. ____. Over time, these resilient bacteria multiply, rendering standard treatments ineffective.',
    correct: 'A',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'ADDITION', D: 'RESULT', E: 'RESULT' }, anchors: anchors('A') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Duyarlı olanların (susceptible) ölmesi ile dirençli olanların (resilient) çoğalması arasına girecek zıtlığı bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['However, those with protective mutations survive the initial treatment.', 'Zayıflar ölürken, koruyucu mutasyonu olanların hayatta kalması "these resilient bacteria" referansını açıklar.', [], []],
      ['This means that the patient will recover entirely within a few days.', 'İyileşme (recover) direnç krizinin ana fikriyle zıttır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['Most antibiotics are derived from naturally occurring fungi.', 'Aşıların kökeni, bakteriyel direnç mekanizması arasına sığmaz.', ['SCOPE_DRIFT'], ['TOPIC']],
      ['As a result, no bacteria can ever survive the application of antibiotics.', 'Hiçbir bakterinin yaşamadığı (no bacteria) iddiası sonraki "multiply" (çoğalır) kelimesiyle çelişir.', ['EXTREME_QUALIFIER'], ['CONTINUATION']],
      ['Doctors often prescribe antibiotics for simple viral infections like the common cold.', 'Doktorların yanlış reçete yazması krizin nedeni olsa da, süreç içindeki hücresel sağkalım mekanizmasını anlatmaz.', ['FALSE_FRIEND'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-para-4', family: 'PARAGRAPH_COMPLETION', domain: 'chemistry',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Chemical equilibrium occurs when the forward and reverse reactions proceed at the exact same rate. At this point, the concentrations of reactants and products remain constant over time. ____. If conditions like temperature or pressure are altered, the system will shift to establish a new balance.',
    correct: 'C',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'ADDITION', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'ADDITION', D: 'RESULT', E: 'RESULT' }, anchors: anchors('C') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Sabit kalma (constant) durumunun doğasını açıklayan ve sonraki "koşullar değişirse" kısmına zemin hazırlayan cümleyi bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['This indicates that all chemical reactions have completely stopped.', 'Reaksiyonların tamamen durması (stopped) denge anında değil, hiç hız olmadığında geçerlidir (kinetik kavramına ters).', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['Only the forward reaction continues to produce new materials.', 'Sadece ileri tepkimenin sürmesi denge (equilibrium) kuralıyla çelişir.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['However, this does not mean the reaction has stopped, merely that it is dynamically balanced.', 'Dinamik denge (dynamically balanced) olması, sabitliğin (constant) durağan (static) olmadığını vurgular.', [], []],
      ['Chemists usually avoid reaching this state because it is highly unstable.', 'Dengeden kaçınmak (avoid) ve dengesiz (unstable) olduğunu söylemek yanlıştır.', ['FALSE_FRIEND'], ['TOPIC']],
      ['The initial products will always decompose rapidly into gases.', 'Ürünlerin gaza bozunması her denge için geçerli değildir.', ['UNSUPPORTED_DETAIL'], ['CONTINUATION']]
    ]
  }),
  make({
    id: 'b4-para-5', family: 'PARAGRAPH_COMPLETION', domain: 'technology',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Machine learning algorithms require vast amounts of data to recognize complex patterns. During the training phase, the system analyzes this data to adjust its internal parameters. ____. The more diverse and accurate the initial data, the better the algorithm performs in real-world scenarios.',
    correct: 'E',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'ADDITION', D: 'RESULT', E: 'RESULT' }, anchors: anchors('E') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Parametreleri ayarlamasının (adjust) amacını/sonucunu anlatan ve veri kalitesine (accurate data) bağlanan cümleyi bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Unfortunately, this process makes computers significantly slower for normal tasks.', 'Bilgisayarların yavaşlaması (slower) paragrafın "performans iyileşmesi" temasıyla zıttır.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['Human programmers must write every single rule manually for it to work.', 'Manuel kural yazımı, makine öğrenmesi algoritmalarının veriyle öğrenme prensibine (adjust parameters) aykırıdır.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['Hardware limitations prevent most algorithms from completing this step.', 'Donanım sınırlamaları, algoritmanın nasıl daha iyi performans gösterdiğiyle bağdaşmaz.', ['FALSE_FRIEND'], ['CONTINUATION']],
      ['This means the data is completely erased after a few hours.', 'Verinin silinmesi mantık dışıdır.', ['UNSUPPORTED_DETAIL'], ['CONTINUATION']],
      ['By doing so, it gradually minimizes errors and improves its predictive accuracy.', 'Hataları en aza indirmesi ve tahminsel doğruluğunu artırması (improves), sonraki performans artışına mantıklı bir geçiştir.', [], []]
    ]
  }),
  make({
    id: 'b4-para-6', family: 'PARAGRAPH_COMPLETION', domain: 'medicine',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Human skin is a complex organ that serves as the body\'s first line of defense. It prevents harmful microorganisms from entering the bloodstream and protects internal tissues from physical damage. ____. For example, sweat glands help cool the body during exercise, while blood vessels dilate or constrict to manage heat loss.',
    correct: 'B',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'ADDITION', candidate_relations: { A: 'CONTRAST', B: 'ADDITION', C: 'RESULT', D: 'CONDITION', E: 'RESULT' }, anchors: anchors('B') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Savunma ve korumanın ötesinde, ter bezleri ve kan damarlarıyla sağlanan "sıcaklık düzenlemesi" (heat loss, cool) işlevine geçiş cümlesi bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['The inner layer is primarily composed of fat cells and connective tissue.', 'İç katmanların yapısı, sonraki ter bezleri/sıcaklık örneğine doğrudan hazırlık yapmaz.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['In addition to protection, the skin plays a crucial role in regulating body temperature.', 'Korumanın yanı sıra (in addition to protection) sıcaklık düzenlemesi (regulating temperature) sonraki örneklere mükemmel uyar.', [], []],
      ['Severe burns can completely destroy these protective barriers.', 'Yanıklar ve hasar, sıcaklık düzenlemesi (cooling) temasından kopuktur.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Most skin conditions require immediate medical attention to avoid infection.', 'Cilt hastalıkları ana konumuz (cildin doğal işlevleri) dışındadır.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['Therefore, avoiding excessive sun exposure is highly recommended by dermatologists.', 'Güneşten kaçınma tavsiyesi "for example" ile verilen ter bezleri mekanizmasına uymaz.', ['FALSE_FRIEND'], ['CONTINUATION']]
    ]
  })
]);

