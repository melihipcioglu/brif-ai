import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make } from './authoringUtils';

export const batch5Questions: readonly Question[] = deepFreeze([
  // IRRELEVANT_SENTENCE
  make({
    id: 'b5-irrelevant-1', family: 'IRRELEVANT_SENTENCE', domain: 'medicine',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) The discovery of penicillin marked a turning point in human history. (II) Before its introduction, minor bacterial infections were often fatal. (III) Alexander Fleming accidentally noticed its bacteria-killing properties in 1928. (IV) Today, viral infections like the flu are treated with antiviral drugs. (V) Thanks to mass production during World War II, it saved countless soldiers.',
    correct: 'D',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Penicillin history', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Metin antibiyotik (penisilin) tarihi iken, IV numaralı cümle antiviral ilaçlardan bahsetmektedir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Giriş cümlesi penisilinin önemini tanıtır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Penisilin öncesi dönemi anlatarak (I) ile bağlanır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Bulunuş sürecini vererek konuyu sürdürür.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['IV', 'Viral enfeksiyonlar (flu) ve antiviraller bakteriyel penisilin konusunun dışındadır.', [], []],
      ['V', '2. Dünya Savaşı\'ndaki kullanımıyla (III) ve (II) cümlelerine geri döner.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),
  make({
    id: 'b5-irrelevant-2', family: 'IRRELEVANT_SENTENCE', domain: 'astronomy',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Exoplanets are planets that orbit stars outside our solar system. (II) The first confirmed discovery of an exoplanet occurred in 1992. (III) Our sun is a medium-sized star classified as a yellow dwarf. (IV) Since then, thousands of exoplanets have been detected using various astronomical methods. (V) The ultimate goal is to find Earth-like planets capable of supporting life.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Exoplanet discovery', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Gezegen dışı sistemleri anlatırken, güneşimizin sınıfını anlatan III numaralı cümle akışı bozar.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Egzogezegen tanımını verir.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'İlk keşif tarihini bildirir.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Güneşimizin (yellow dwarf) sınıfı egzogezegen (diğer yıldız sistemleri) konusunun dışındadır.', [], []],
      ['IV', 'Since then (o zamandan beri) diyerek (II) nolu cümleye doğrudan bağlanır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Gözlemlerin nihai amacını belirterek konuyu sonlandırır.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),
  make({
    id: 'b5-irrelevant-3', family: 'IRRELEVANT_SENTENCE', domain: 'technology',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) The advent of 3D printing has revolutionized modern manufacturing. (II) It allows engineers to create complex geometric shapes that traditional methods cannot produce. (III) Laser cutting is another popular method for shaping flat metal sheets. (IV) Furthermore, 3D printing significantly reduces material waste by building objects layer by layer. (V) This makes it an environmentally friendly option for aerospace and automotive industries.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: '3D printing benefits', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: '3D yazıcıların özellikleri sıralanırken araya giren lazer kesim yöntemi (III) ilgisizdir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Ana konuyu, yani 3D yazıcıları tanıtır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Geleneksel yöntemlerle kıyaslayarak (I)\'i açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Lazer kesim, odaklanılan 3D printing (katman katman üretim) konusu dışındadır.', [], []],
      ['IV', 'Furthermore diyerek (II)\'ye ek fayda sağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'This makes it diyerek (IV)\'teki atık azaltmanın sonucunu verir.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),
  make({
    id: 'b5-irrelevant-4', family: 'IRRELEVANT_SENTENCE', domain: 'biology',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Mitochondria are often referred to as the powerhouses of the cell. (II) They generate most of the chemical energy needed to power the cell\'s biochemical reactions. (III) Chloroplasts perform photosynthesis in plant cells. (IV) This energy is stored in a small molecule called ATP. (V) Without functional mitochondria, a human cell cannot survive for very long.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Mitochondria function', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Mitokondrinin enerji üretimi anlatılırken (III) kloroplastlardan bahsetmektedir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Mitokondri tanımını yapar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Enerji üretme işlevini (I) için detaylandırır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Kloroplastların (chloroplasts) fotosentez yapması mitokondrinin anlatıldığı paragrafa yabancıdır.', [], []],
      ['IV', 'This energy referansı ile doğrudan (II) numaralı cümleye bağlanır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Mitokondrilerin hayati rolünü özetler.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),
  make({
    id: 'b5-irrelevant-5', family: 'IRRELEVANT_SENTENCE', domain: 'environment',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Coral bleaching occurs when corals are stressed by changes in conditions such as temperature, light, or nutrients. (II) They expel the symbiotic algae living in their tissues, causing them to turn completely white. (III) The Great Barrier Reef is the largest coral reef system in the world. (IV) If the stress is not severe, the corals can recover their algae and survive. (V) However, prolonged bleaching often leads to the death of the coral colony.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Coral bleaching', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Mercan beyazlamasının biyolojik süreci anlatılırken (III) spesifik bir coğrafi ansiklopedik bilgi verir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Beyazlama mekanizmasını tanımlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Beyazlamanın (turn white) fiziksel sonucunu açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Büyük Set Resifi\'nin en büyük olması beyazlamanın hücresel sürecini bölen alakasız bilgidir.', [], []],
      ['IV', 'Stresin azalması durumundaki iyileşmeyi anlatarak süreci devam ettirir.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Stresin uzaması durumundaki ölümü (IV ile zıtlık) bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),
  make({
    id: 'b5-irrelevant-6', family: 'IRRELEVANT_SENTENCE', domain: 'physics',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) The principles of aerodynamics are essential in the design of modern aircraft. (II) Engineers must carefully balance lift, weight, thrust, and drag. (III) Most commercial airlines serve in-flight meals to keep passengers happy. (IV) By optimizing the shape of the wings, lift can be maximized while reducing drag. (V) This results in significant fuel savings and better flight stability.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Aerodynamics aircraft', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Uçaklarda aerodinamik tasarımı (fizik) anlatan metne uçak içi yemek servisi (III) cümlesi uymaz.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Aerodinamiğin tasarım için gerekliliğini sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Dört temel kuvveti sayarak fiziksel açıklamaya geçer.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Yemek servisi (in-flight meals) mühendislik ve fizik akışını tamamen bozar.', [], []],
      ['IV', 'Kanat şekillerinin optimize edilmesiyle (II) nolu cümlenin detayına iner.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'This results diyerek (IV)\'ün pratik sonucunu verir.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),
  make({
    id: 'b5-irrelevant-7', family: 'IRRELEVANT_SENTENCE', domain: 'chemistry',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Water is known as the universal solvent because it dissolves more substances than any other liquid. (II) This is due to the polarity of the water molecule, which attracts both positive and negative ions. (III) Humans should drink at least eight glasses of water a day. (IV) Consequently, it can easily break down the crystal lattice of salts like sodium chloride. (V) This solvent property is what allows our blood to carry vital nutrients to cells.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Water as solvent', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Suyun kimyasal solvent (çözücü) özelliği anlatılırken günde kaç bardak içilmesi gerektiği (III) ilgisizdir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Evrensel çözücü (universal solvent) tanımını yapar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Moleküler kutupluluğu (polarity) açıklayarak bu özelliğin sebebini sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'İçilmesi gereken su miktarı (eight glasses) kimyasal özellikler (polarity, ions) akışına aykırıdır.', [], []],
      ['IV', 'Consequently (Sonuç olarak) diyerek (II) numaralı cümlenin sonucunu (tuzu çözme) bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Biyolojik sonucunu vererek metni bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']]
    ]
  }),

  // READING_COMPREHENSION
  make({
    id: 'b5-reading-1', family: 'READING_COMPREHENSION', domain: 'biology',
    stem: 'According to the passage, memory T cells are crucial because they ____.',
    passage: 'The human immune system is incredibly adaptive. When a novel pathogen enters the body, naive T cells and B cells are activated to fight the infection. Once the virus is cleared, most of these cells undergo apoptosis, or programmed cell death. However, a small fraction remains behind as memory cells. These memory T cells patrol the bloodstream for decades. If the identical pathogen attempts to invade again, memory cells recognize it instantly and mount a rapid, overwhelming defense before symptoms can even develop. This mechanism is precisely what vaccines exploit to confer long-lasting immunity without causing the actual disease.',
    correct: 'E',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Parçada hafıza hücrelerinin (memory cells) aynı patojen geldiğinde hızlı bir savunma başlattığı (mount a rapid defense) söylenmiştir.',
    skills: ['READING_DETAIL'],
    choices: [
      ['prevent the initial entry of completely novel pathogens', 'Yeni patojenlerin ilk girişini (initial entry) önlemez, ikinci girişe tepki verir.', ['TEMPORAL_MISMATCH'], ['PASSAGE_SUPPORT']],
      ['undergo apoptosis immediately after destroying a virus', 'Apoptosis geçirenler ölenlerdir; hafıza hücreleri geriye kalanlardır.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['cause mild symptoms during the second infection', 'Semptomlar gelişmeden önce (before symptoms develop) virüsü durdururlar.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['are the only cells capable of recognizing harmless vaccines', 'Sadece onların aşıları tanıdığı (only cells) gibi aşırı genellemeler parçada geçmez.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['enable the immune system to respond rapidly to a repeated infection', 'Tekrar eden enfeksiyona (repeated infection) hızlı cevap vermeleri parçanın ana fikridir.', [], []]
    ]
  }),
  make({
    id: 'b5-reading-2', family: 'READING_COMPREHENSION', domain: 'biology',
    stem: 'It can be inferred from the passage that vaccines ____.',
    passage: 'Messenger RNA vaccines represent a breakthrough in modern immunization. Unlike conventional vaccines that introduce weakened antigens, mRNA vaccines deliver genetic instructions directly to host cells. Encapsulated within protective lipid nanoparticles, the synthetic mRNA instructs ribosomes to transiently produce a harmless viral protein. The host immune system recognizes this protein as foreign and mounts a robust response without exposing the patient to the live virus. Once translated, the mRNA is naturally degraded by cellular enzymes within hours, leaving behind durable immunological memory.',
    correct: 'C',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'INFERENCE' },
    checks: ['CONTINUATION', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Aşıların (vaccines) hastalığa yol açmadan (without exposing to live virus) hafıza hücrelerini uyardığı anlatılır.',
    skills: ['READING_INFERENCE'],
    choices: [
      ['contain extremely dangerous viruses that cause severe symptoms', 'Hastalığa neden olmadan (without causing) ifadesine terstir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['prevent apoptosis in all naive T cells', 'Tüm T hücrelerinde (all) apoptosis\'i durdurduğu bilgisi metinde yer almaz.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['mimic an infection to generate memory cells safely', 'Hastalığa neden olmadan bağışıklık kazandırması, güvenli bir şekilde taklit ettiği (mimic) anlamına gelir.', [], []],
      ['are completely ineffective against novel pathogens', 'Etkisiz (ineffective) olduklarına dair olumsuz bir bilgi yoktur.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['eliminate the need for the immune system to adapt', 'Bağışıklık sisteminin uyarılmasını kullandıkları belirtilmiştir, ihtiyacı ortadan kaldırmazlar.', ['CAUSE_EFFECT_REVERSAL'], ['PASSAGE_SUPPORT']]
    ]
  }),
  make({
    id: 'b5-reading-3', family: 'READING_COMPREHENSION', domain: 'biology',
    stem: 'The primary purpose of the passage is to ____.',
    passage: 'Immunological protection operates at both individual and population levels. When a high percentage of a community becomes immune to an infectious agent through vaccination or prior recovery, transmission chains are effectively broken. This phenomenon, known as herd immunity, provides indirect protection to vulnerable individuals who cannot be vaccinated themselves. Explaining how memory cells provide immunity and how vaccines utilize this process enables public health authorities to design targeted immunization strategies that curtail disease dissemination.',
    correct: 'A',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'MAIN_IDEA' },
    checks: ['TOPIC', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metin, immün sistemdeki hafıza hücrelerinin bağışıklık sağlaması ve aşıların bu süreci kullanmasını açıklamaktadır.',
    skills: ['MAIN_IDEA'],
    choices: [
      ['explain how memory cells provide immunity and how vaccines utilize this process', 'Hafıza hücrelerinin bağışıklık sağlaması ve aşıların bu süreci kullanması paragrafın tümünü özetler.', [], []],
      ['argue against the use of apoptosis in cellular development', 'Apoptosis eleştirilmemiş, sadece bir süreç olarak verilmiştir.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['compare the effectiveness of naive T cells with B cells', 'Bu iki hücre tipi karşılaştırılmamış, birlikte enfeksiyona karşı aktifleştiği söylenmiştir.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']],
      ['warn readers about the dangers of novel pathogens', 'Okuyucuyu uyarmak metnin öğretici, açıklayıcı (informative) doğasıyla örtüşmez.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']],
      ['demonstrate that vaccines are the only way to activate B cells', 'Aşıların B hücrelerini aktive etmenin "tek yolu" (only way) olduğu iddia edilmemiştir.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']]
    ]
  }),
  make({
    id: 'b5-reading-4', family: 'READING_COMPREHENSION', domain: 'astronomy',
    stem: 'According to the passage, dark matter is unique because it ____.',
    passage: 'Astronomers can easily observe stars and galaxies using light, whether visible, infrared, or radio waves. However, calculations of galaxy rotation speeds reveal a perplexing anomaly: galaxies are spinning so fast that the gravity from their visible matter should not be enough to hold them together. They should theoretically tear themselves apart. This implies the existence of a massive, invisible substance called dark matter. Unlike normal matter, dark matter does not emit, absorb, or reflect light, rendering it entirely invisible to our current instruments. Its presence is inferred purely through its gravitational effects on visible objects and the bending of light around massive galaxy clusters.',
    correct: 'B',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Parçada karanlık maddenin ışık yaymadığı, emmediği veya yansıtmadığı, bu yüzden doğrudan gözlenemediği yazar.',
    skills: ['READING_DETAIL'],
    choices: [
      ['spins at speeds much faster than visible galaxies', 'Karanlık madde değil, galaksiler (galaxies are spinning) hızlı dönmektedir.', ['SEMANTIC_ROLE_SWAP'], ['PASSAGE_SUPPORT']],
      ['does not interact with light and thus cannot be seen directly', 'Işığı yaymaz/emmez/yansıtmaz (does not emit/absorb/reflect) ifadesi doğrudan görülemeyeceğini (invisible) doğrular.', [], []],
      ['is composed entirely of radio waves and infrared energy', 'Radyo dalgaları ve kızılötesi ile gözlemlenemediği açıkça belirtilmiştir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['prevents gravity from affecting visible objects', 'Karanlık madde kütle çekimini engellemez, tam tersine yerçekimi etkisi (gravitational effects) yaratır.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['can be easily detected by modern telescopes', 'Tamamen görünmezdir (entirely invisible), kolayca tespit edilemez.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']]
    ]
  }),
  make({
    id: 'b5-reading-5', family: 'READING_COMPREHENSION', domain: 'astronomy',
    stem: 'The author implies that without dark matter, ____.',
    passage: 'In general relativity, massive astronomical bodies warp the spacetime fabric around them, bending the trajectories of light rays that pass nearby. When astronomers observe distant galaxy clusters, they frequently detect distorted, magnified arcs of background galaxies—a phenomenon termed gravitational lensing. By quantifying the degree of light curvature, cosmologists can map the total mass distribution within the cluster. Intriguingly, the mass calculated from lensing substantially exceeds the visible stellar and gas mass combined, showing that galaxies would tear themselves apart without an unseen gravitational scaffold.',
    correct: 'D',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'INFERENCE' },
    checks: ['CONTINUATION', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Karanlık madde kütlesi olmasaydı görünür maddenin kütlesinin galaksiyi bir arada tutmaya yetmeyeceği ve galaksilerin parçalanacağı ifade edilir.',
    skills: ['READING_INFERENCE'],
    choices: [
      ['visible matter would emit significantly more light', 'Işık yayma ile kütle çekimi eksiği ilişkilendirilmemiştir.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']],
      ['galaxy clusters would stop spinning altogether', 'Dönmeyi durduracağı değil, dönme hızından dolayı dağılacağı (tear apart) anlatılır.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['the bending of light would become much stronger', 'Karanlık madde olmadığında kütle çekimi azalacağı için ışık bükülmesi artmaz, azalır.', ['CAUSE_EFFECT_REVERSAL'], ['PASSAGE_SUPPORT']],
      ['galaxies would break apart due to their high rotational speeds', 'Görünür maddenin çekimi yetmeyeceği için galaksilerin parçalanacağı (tear themselves apart) doğrudan çıkarılır.', [], []],
      ['astronomers would be unable to use radio waves for observation', 'Radyo dalgaları normal maddenin gözlemi için vardır, karanlık madde eksikliği bunu engellemez.', ['SCOPE_DRIFT'], ['PASSAGE_SUPPORT']]
    ]
  })
]);

