import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make } from './authoringUtils';

export const batch10Questions: readonly Question[] = deepFreeze([
  // IRRELEVANT SENTENCE 5 (Medicine - Antimicrobial Resistance)
  make({
    id: 'b10-irrel-5', family: 'IRRELEVANT_SENTENCE', domain: 'medicine',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Antimicrobial resistance represents one of the most critical threats to modern global public health. (II) Overuse and misuse of antibiotics accelerate the selection of resistant genetic mutations in pathogenic bacteria. (III) Classical Renaissance oil paintings require climate-controlled museum galleries for long-term preservation. (IV) Consequently, routine surgical interventions and chemotherapy treatments carry elevated risks of untreatable secondary infections. (V) Global surveillance networks and stringent stewardship policies are urgently required to contain this escalating crisis.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Antimicrobial resistance crisis', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Antibiyotik direnci ve cerrahi enfeksiyon riski anlatılırken Rönesans yağlı boya tabloları (III) alakasızdır.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Antimikrobiyal direncin küresel halk sağlığı için kritik tehdit olduğunu belirtir.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Aşırı antibiyotik kullanımının dirençli mutasyonları seçilimle artırdığını açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Rönesans tablolarının müzede korunması tıp ve antibiyotik direnci konusuyla tamamen ilgisizdir.', [], []],
      ['IV', 'Consequently ile dirençli bakterilerin ameliyatlardaki enfeksiyon riskini bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Krizi kontrol altına almak için küresel takip politikalarının gerekliliğini vurgular.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 6 (Astronomy - Exoplanet Spectroscopy)
  make({
    id: 'b10-irrel-6', family: 'IRRELEVANT_SENTENCE', domain: 'astronomy',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Transmission spectroscopy allows astrophysicists to probe the chemical composition of exoplanetary atmospheres. (II) As an exoplanet transits its host star, starlight filters through the upper layers of its atmosphere. (III) Commercial passenger trains in Europe operate on standardized railway track gauges. (IV) Chemical species such as water vapor, carbon dioxide, and methane absorb specific wavelengths of this transmitted light. (V) By measuring these distinctive absorption dips, researchers can infer the presence of potential biosignature gases.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Exoplanet transmission spectroscopy', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Ötegezegen atmosferlerinin spektroskopik incelenmesi anlatılırken Avrupa tren rayları (III) ilgisiz bir cümledir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Geçiş spektroskopisinin ötegezegen atmosferlerini inceleme amacını tanıtır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Gezegenin yıldızının önünden geçişi sırasında ışığın filtrelenmesini açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Avrupa tren raylarının standart genişliği astrofizik ve spektroskopi akışına tamamen aykırıdır.', [], []],
      ['IV', 'Su buharı ve metan gibi moleküllerin belirli dalga boylarını emdiğini detaylandırır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Soğurma çizgilerinden biyobelirteç gazlarının tespitini bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 7 (Engineering - Solid State Batteries)
  make({
    id: 'b10-irrel-7', family: 'IRRELEVANT_SENTENCE', domain: 'engineering',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Solid-state battery architecture replaces flammable liquid organic electrolytes with solid ceramic or polymer ion conductors. (II) This structural innovation dramatically suppresses dendrite formation and eliminates catastrophic fire risks in electric vehicles. (III) Ancient Egyptian pharaohs constructed monumental stone pyramids along the Nile River. (IV) Furthermore, the mechanical rigidity of solid electrolytes permits the safe utilization of pure metallic lithium anodes. (V) Consequently, these next-generation cells promise substantial enhancements in both volumetric energy density and operational lifespan.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Solid-state battery safety and density', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Katı hal bataryalarının yangın güvenliği ve enerji yoğunluğu anlatılırken Mısır piramitleri (III) anlamsızdır.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Katı hal bataryalarının sıvı elektrolit yerine katı iletken kullandığını açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Dendrit oluşumunu engelleyip yangın riskini ortadan kaldırdığını belirtir.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Antik Mısır piramitlerinin inşası elektrokimya ve batarya mühendisliğiyle tamamen ilgisizdir.', [], []],
      ['IV', 'Furthermore ile saf lityum metal anot kullanımına izin verdiğini ekler.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Enerji yoğunluğunun ve ömrün artacağını belirterek sonucu bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 8 (Environment - Permafrost Thawing)
  make({
    id: 'b10-irrel-8', family: 'IRRELEVANT_SENTENCE', domain: 'environment',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Arctic permafrost soils contain vast reservoirs of ancient organic carbon that have remained frozen for millennia. (II) As rising polar temperatures accelerate permafrost thaw, microbial communities rapidly decompose this previously inaccessible organic substrate. (III) The Olympic Games are celebrated every four years in different host cities around the world. (IV) This microbial respiration converts organic matter into massive volumes of atmospheric carbon dioxide and potent methane gas. (V) This positive biogeochemical feedback loop exacerbates global warming and threatens planetary climate stability.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Arctic permafrost carbon feedback', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Kuzey Kutbu donmuş toprak erimesi ve metan salımı anlatılırken Olimpiyat Oyunları (III) konuyu böler.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Donmuş toprakta bin yıllardır hapsolmuş organik karbon rezervlerini tanıtır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Isınmayla birlikte mikropların bu organik maddeyi ayrıştırmaya başladığını sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Olimpiyat Oyunları kutlaması kutup biogeokimyası ve iklim geri beslemesi konusuyla tamamen ilgisizdir.', [], []],
      ['IV', 'Mikrobiyal solunumun CO2 ve metan gazı üretmesini bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Pozitif geri besleme döngüsünün küresel ısınmayı şiddetlendirdiğini özetler.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 9 (Physics - Gravitational Waves)
  make({
    id: 'b10-irrel-9', family: 'IRRELEVANT_SENTENCE', domain: 'physics',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Gravitational waves are ripples in the fabric of spacetime produced by the acceleration of massive astrophysical bodies. (II) Catastrophic cosmic events such as binary black hole mergers generate detectable gravitational strain signals across the universe. (III) Modern acoustic violins are traditionally crafted from aged spruce and maple wood. (IV) Laser interferometers like LIGO utilize kilometer-scale optical arms to measure fractional shifts in laser interference patterns. (V) These subatomic displacements confirm Einstein\'s general theory of relativity and provide an entirely new observational window into the cosmos.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Gravitational waves spacetime LIGO', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Yerçekimi dalgaları ve lazer interferometreleri anlatılırken keman yapımı (III) ilgisiz bir cümledir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Yerçekimi dalgalarının uzay-zaman dokusundaki dalgalanmalar olduğunu açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Kara delik birleşmelerinin tespit edilebilir sinyaller yarattığını belirtir.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Kemanların ladin ve akçaağaçtan yapılması astrofizik ve görelilik akışına tamamen aykırıdır.', [], []],
      ['IV', 'LIGO lazer interferometresinin kilometre ölçekli kollarını tanıtır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Atom altı kaymaların görelilik teorisini doğruladığını bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 10 (Chemistry - Polymer Catalysis)
  make({
    id: 'b10-irrel-10', family: 'IRRELEVANT_SENTENCE', domain: 'chemistry',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Ziegler-Natta catalysts revolutionized polymer chemistry by enabling the stereospecific polymerization of 1-alkenes. (II) These coordination complexes precisely dictate the spatial orientation of monomer addition during chain growth. (III) Professional chefs frequently season steaks with freshly ground black pepper before grilling. (IV) As a result, industrial manufacturers can produce highly crystalline, high-density polyethylene and polypropylene with superior mechanical properties. (V) The widespread availability of these durable polymers transformed global packaging, construction, and consumer manufacturing.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Ziegler-Natta polymer catalysis', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Ziegler-Natta polimer katalizi ve polietilen üretimi anlatılırken aşçıların biftek baharatlaması (III) alakasızdır.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Ziegler-Natta katalizörlerinin stereospesifik polimerizasyondaki devrimini açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Koordinasyon komplekslerinin monomer eklenme yönünü belirlediğini sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Aşçıların bifteğe karabiber eklemesi polimer kimyası ve sanayi üretimi konusuyla tamamen ilgisizdir.', [], []],
      ['IV', 'As a result ile kristalin ve yüksek yoğunluklu polimerlerin üretimini bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Dayanıklı polimerlerin ambalaj ve inşaat sektöründeki devrimini özetler.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // READING COMPREHENSION 1 (Biology - Bioluminescence, DETAIL)
  make({
    id: 'b10-reading-1', family: 'READING_COMPREHENSION', domain: 'biology',
    stem: 'According to the passage, deep-sea organisms utilize bioluminescence primarily to ____.',
    passage: 'In the perpetual darkness of the deep ocean, bioluminescence is the rule rather than the exception. More than seventy percent of deep-sea species produce light through biochemical reactions involving the substrate luciferin and the enzyme luciferase. While terrestrial fireflies use luminescence almost exclusively for mate attraction, marine organisms have evolved versatile applications. Many bathypelagic squids emit glowing clouds of luminescent ink to blind predators and facilitate escape. Others project counter-illuminating ventral lights to match the faint downwelling sunlight from the surface, rendering their silhouettes completely invisible to predators hunting from below.',
    correct: 'B',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metne göre derin deniz canlılarının biyolüminesansı ne amaçla kullandığını doğrudan metin kanıtından bulun.',
    skills: ['READING_DETAIL'],
    choices: [
      ['synthesize organic nutrients through light-driven photosynthesis', 'Fotosentez yapmadıkları metnin karanlık ortam vurgusundan bellidir.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['confound predators and conceal their ventral silhouettes from hunters below', 'Kalamarların mürekkeple avcıyı kör etmesi ve alt karın ışığıyla kamufle olması metinde doğrudan desteklenir.', [], []],
      ['warm their internal body fluids in near-freezing polar waters', 'Vücut sıvılarını ısıttığı iddiası metinde yer almaz.', ['UNSUPPORTED_DETAIL'], ['PASSAGE_SUPPORT']],
      ['communicate exclusively with individuals of terrestrial species', 'Karasal türlerle iletişim kurdukları iddiası anlamsızdır.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['illuminate underwater caves to establish permanent breeding colonies', 'Sualtı mağaralarını aydınlatmak metinde bahsedilmeyen bir detaydır.', ['UNSUPPORTED_DETAIL'], ['SCOPE']],
    ],
  }),

  // READING COMPREHENSION 2 (Genetics - CRISPR Base Editing, INFERENCE)
  make({
    id: 'b10-reading-2', family: 'READING_COMPREHENSION', domain: 'biology',
    stem: 'It can be inferred from the passage that CRISPR base editors are safer than standard Cas9 nucleases because they ____.',
    passage: 'Conventional CRISPR-Cas9 genome editing functions by introducing double-stranded DNA breaks at targeted genomic loci. The host cell repairs these breaks through non-homologous end joining, an error-prone mechanism that frequently produces uncontrolled insertions, deletions, and large-scale chromosomal rearrangements. To overcome these hazards, geneticists developed base editing technology. Base editors tether a cytidine or adenine deaminase to a catalytically impaired Cas9 nickase. By converting one targeted nucleotide directly into another without cutting both DNA strands, base editing minimizes genotoxic double-strand breaks and significantly suppresses oncogenic translocations.',
    correct: 'D',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'INFERENCE' },
    checks: ['CONTINUATION', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Baz düzenleyicilerin standart Cas9 dan daha güvenli olmasının çıkarımını (çift zincir kırığı yapmaması) bulun.',
    skills: ['READING_INFERENCE'],
    choices: [
      ['eliminate all viral infections throughout the entire human organism immediately', 'Tüm viral enfeksiyonları yok ettiği çıkarımı metinde yoktur.', ['EXTREME_QUALIFIER'], ['SCOPE']],
      ['completely prevent cells from synthesizing any nuclear enzymes', 'Nükleer enzim sentezini durdurduğu iddiası çıkarılamaz.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['operate without requiring any guide RNA molecules during targeting', 'Rehber RNA gerektirmediği iddiası metinde geçmez.', ['UNSUPPORTED_DETAIL'], ['PASSAGE_SUPPORT']],
      ['avoid double-stranded DNA cleavage and reduce hazardous chromosomal rearrangements', 'Çift zinciri kesmeden doğrudan nükleotid dönüşümü yaparak kromozomal translokasyon riskini azaltması metinden doğrudan çıkarılır.', [], []],
      ['enhance the rate of non-homologous end joining in dividing somatic tissues', 'Hata eğilimli tamir mekanizmasını artırmaz, tam tersine ona olan ihtiyacı ortadan kaldırır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
    ],
  }),

  // READING COMPREHENSION 3 (Physics - Quantum Entanglement, MAIN_IDEA)
  make({
    id: 'b10-reading-3', family: 'READING_COMPREHENSION', domain: 'physics',
    stem: 'What is the primary focus of the passage?',
    passage: 'When Albert Einstein, Boris Podolsky, and Nathan Rosen published their celebrated 1935 paradox, they argued that quantum mechanics was incomplete because it predicted "spooky action at a distance." Decades later, John Stewart Bell formulated mathematical inequalities capable of experimentally verifying whether local hidden variables could explain quantum correlations. Modern Bell test experiments, employing widely separated entangled photons and ultra-fast random number generators, have decisively violated Bell inequalities without loopholes. These definitive empirical measurements demonstrate that nature is fundamentally non-local, overturning classical assumptions of local realism and providing the bedrock for quantum cryptography.',
    correct: 'A',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'MAIN_IDEA' },
    checks: ['TOPIC', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metnin ana fikrini: Bell testleri ve deneylerinin doğanın yerel olmadığını (non-local) kanıtlamasını seçin.',
    skills: ['MAIN_IDEA'],
    choices: [
      ['The experimental verification of quantum non-locality through definitive Bell tests', 'Metin, Einstein\'ın şüphelerinden Bell eşitsizliklerine ve deneylerle kuantum yerel olmamasının kanıtlanmasına odaklanır.', [], []],
      ['The technological superiority of commercial telecommunications satellite networks', 'Ticari uydu üstünlüğü kuantum fiziği ana fikriyle alakasızdır.', ['SCOPE_DRIFT'], ['TOPIC']],
      ['The total failure of all modern quantum cryptographic communication protocols', 'Kriptografik protokollerin başarısız olduğu iddiası metnin sonucuna taban tabana zıttır.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['Biographical details concerning Albert Einstein\'s youth in central Europe', 'Biyografik gençlik detayları metnin ana fikri değildir.', ['UNSUPPORTED_DETAIL'], ['SCOPE']],
      ['Mathematical proofs demonstrating that light travels infinitely fast through glass', 'Işığın sonsuz hızda ilerlediği iddiası metinde yer almaz.', ['FALSE_FRIEND'], ['TOPIC']],
    ],
  }),

  // READING COMPREHENSION 4 (Chemistry - Zeolites, DETAIL)
  make({
    id: 'b10-reading-4', family: 'READING_COMPREHENSION', domain: 'chemistry',
    stem: 'According to the passage, zeolites are uniquely effective as catalysts because ____.',
    passage: 'Zeolites are microporous, aluminosilicate crystalline minerals characterized by highly ordered frameworks of channels and cages. Because their pore diameters match the molecular dimensions of small organic molecules, zeolites exhibit exquisite shape selectivity. In petrochemical fluid catalytic cracking, heavy crude hydrocarbons enter the porous channels, where strongly acidic active sites cleave carbon-carbon bonds. Only molecules whose geometric shapes can navigate the pore network are converted and allowed to diffuse outward, while bulky precursor molecules that would form undesirable coke deposits are geometrically excluded from entering.',
    correct: 'C',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metne göre zeolitlerin etkili olmasını sağlayan doğrudan özelliği (gözenek boyutu ve şekil seçiciliği) bulun.',
    skills: ['READING_DETAIL'],
    choices: [
      ['they consist entirely of heavy radioactive transition metals', 'Ağır radyoaktif metallerden oluştukları iddiası metinde yer almaz.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['they dissolve completely in crude oil to form homogeneous solutions', 'Petrol içinde çözünüp homojen çözelti oluşturmazlar, katı mineraldirler.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['their precise pore dimensions selectively admit and convert molecules of specific shapes', 'Gözenek çaplarının molekül boyutlarıyla eşleşip şekil seçiciliği sağlaması metinde doğrudan belirtilir.', [], []],
      ['they eliminate all energy requirements in industrial chemical cracking reactors', 'Tüm enerji ihtiyacını sıfırladıkları iddiası metinde yer almayan abartıdır.', ['EXTREME_QUALIFIER'], ['SCOPE']],
      ['their amorphous non-crystalline structure prevents carbon bond cleavage', 'Kristal olmayan yapı iddiası metindeki crystalline mineral ifadesiyle çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
    ],
  }),

  // READING COMPREHENSION 5 (Environment - Permafrost Methane, INFERENCE)
  make({
    id: 'b10-reading-5', family: 'READING_COMPREHENSION', domain: 'environment',
    stem: 'The author implies that the destabilization of Arctic thermokarst lakes could ____.',
    passage: 'Thermokarst lakes form across northern latitudes when ground ice within continuous permafrost thaws, causing surface terrain to collapse into waterlogged depressions. At the lake bottoms, anoxic conditions stimulate methanogenic archaea that digest ancient thawed pleistocene organic matter. Methane gas bubbles upward through the water column and vents directly into the atmosphere, bypassing microbial oxidation in upper soil strata. Because methane is approximately thirty times more potent than carbon dioxide as a greenhouse gas over a century, accelerated lake formation could trigger a runaway climate feedback loop that models struggle to constrain.',
    correct: 'E',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'INFERENCE' },
    checks: ['CONTINUATION', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Termokarst göllerinin çözünmesinin iklim modellerini aşan güçlü sera gazı ısınmasına yol açabileceği çıkarımını seçin.',
    skills: ['READING_INFERENCE'],
    choices: [
      ['permanently cool polar surface temperatures below pre-industrial baselines', 'Kutup sıcaklıklarını sanayi öncesi seviyeye düşüreceği iddiası metinle çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['prevent all methanogenic archaea from metabolizing organic substrate', 'Arkeaların metabolizmasını durdurmaz, oksijensiz ortamda onları uyarır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['allow commercial tankers to navigate the Arctic Ocean without any icebreakers', 'Ticari tankerlerin geçişi metnin ekolojik odağı dışındadır.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['oxidize all atmospheric methane into harmless liquid water droplets instantly', 'Metanı anında suya dönüştürdüğü iddiası fiziksel olarak geçersizdir.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['release massive volumes of potent methane that accelerate planetary warming beyond current forecasts', 'Yüksek tesirli metan salarak iklim modellerini aşan küresel ısınmaya yol açabileceği metinden doğrudan çıkarılır.', [], []],
    ],
  }),

  // READING COMPREHENSION 6 (Medicine - CAR T-Cell Therapy, DETAIL)
  make({
    id: 'b10-reading-6', family: 'READING_COMPREHENSION', domain: 'medicine',
    stem: 'According to the passage, CAR T-cell therapy achieves tumor specificity by ____.',
    passage: 'Chimeric antigen receptor (CAR) T-cell therapy represents a transformative paradigm in personalized oncological medicine. In this adoptive cell transfer procedure, a patient\'s autologous T lymphocytes are harvested and genetically reprogrammed via viral vectors. The engineered chimeric receptor combines an extracellular antigen-recognition domain, derived from a monoclonal antibody single-chain variable fragment, with intracellular T-cell activation and costimulatory signaling motifs. This synthetic architecture enables the re-infused T cells to recognize cancer cell surface proteins independently of major histocompatibility complex presentation, overcoming a common immune escape route exploited by hematological malignancies.',
    correct: 'B',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metne göre CAR T-hücre tedavisinin tümör özgüllüğünü ve tanımasını nasıl sağladığını doğrudan metinden bulun.',
    skills: ['READING_DETAIL'],
    choices: [
      ['administering high doses of non-specific cytotoxic alkylating chemotherapy', 'Spesifik olmayan kemoterapi vermek yerine kişiselleştirilmiş hücre mühendisliği uygulanır.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['expressing an engineered chimeric receptor that binds cancer surface antigens independently of MHC presentation', 'MHC sunumundan bağımsız olarak kanser yüzey antijenlerine bağlanan sentetik kimerik reseptör ifadesi metinde açıkça yer alır.', [], []],
      ['destroying all circulating lymphocytes throughout the patient\'s lymphatic system', 'Tüm lenfositleri yok ettiği iddiası tedaviyle çelişir.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['replacing all bone marrow stem cells with synthetic titanium micro-particles', 'Titanyum parçacık yerleştirme iddiası tıp dışıdır.', ['FALSE_FRIEND'], ['SCOPE']],
      ['inducing severe allergic reactions against beneficial dietary proteins', 'Besin proteinlerine alerji yaratması metinde bahsedilmeyen bir durumdur.', ['UNSUPPORTED_DETAIL'], ['SCOPE']],
    ],
  }),

  // READING COMPREHENSION 7 (Astronomy - Kilonova Nucleosynthesis, MAIN_IDEA)
  make({
    id: 'b10-reading-7', family: 'READING_COMPREHENSION', domain: 'astronomy',
    stem: 'The main idea of the passage is that ____.',
    passage: 'For decades, astrophysicists debated where the heaviest elements in the periodic table, such as gold, platinum, and uranium, are forged in the universe. While core-collapse supernovae were long suspected, theoretical models struggled to reproduce the immense neutron densities required for the rapid neutron-capture process (r-process). The landmark 2017 detection of gravitational wave event GW170817, paired with multi-wavelength electromagnetic observations of the resulting kilonova, provided unambiguous evidence. The merger of two neutron stars ejects highly neutron-rich material that rapidly decompresses, providing the exact physical conditions required to synthesize cosmic abundances of the universe\'s heaviest chemical elements.',
    correct: 'C',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'MAIN_IDEA' },
    checks: ['TOPIC', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metnin ana fikrini: Nötron yıldızı birleşmelerinin ve kilonovaların evrendeki en ağır elementlerin sentezlendiği yer olmasını seçin.',
    skills: ['MAIN_IDEA'],
    choices: [
      ['Supernovae are the exclusive source of all chemical elements lighter than helium', 'Helyumdan hafif elementlerin süpernovada oluştuğu iddiası metnin ana fikri değildir.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Gravitational wave detectors have been permanently decommissioned by physicists', 'Dedektörlerin kapatıldığı iddiası metindeki keşif başarısıyla çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['Neutron star mergers synthesize the universe\'s heaviest elements through the rapid neutron-capture process', 'Nötron yıldızı birleşmelerinin r-süreciyle altın ve platin gibi en ağır elementleri sentezlediği kanıtı metnin ana fikridir.', [], []],
      ['Gold and platinum can be produced cheaply in terrestrial commercial laboratories', 'Yeryüzü laboratuvarlarında ucuza altın üretimi metinle alakasızdır.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['The expansion of the universe is decelerating due to dark matter gravitational pull', 'Evrenin genişlemesinin yavaşlaması astrofizik nükleosentez odağı dışındadır.', ['UNSUPPORTED_DETAIL'], ['TOPIC']],
    ],
  }),

  // READING COMPREHENSION 8 (Engineering - Perovskite Solar Cells, DETAIL)
  make({
    id: 'b10-reading-8', family: 'READING_COMPREHENSION', domain: 'engineering',
    stem: 'According to the passage, perovskite-silicon tandem solar cells outperform single-junction cells because they ____.',
    passage: 'Single-junction silicon solar cells are rapidly approaching their theoretical Shockley-Queisser efficiency limit of approximately twenty-nine percent. To surpass this physical ceiling, photovoltaic engineers are stacking metal-halide perovskite layers on top of standard silicon wafers to create tandem devices. Because perovskites have a tunable wider bandgap, the top cell efficiently absorbs high-energy blue and green photons, while lower-energy red and near-infrared light passes through to be absorbed by the bottom silicon cell. This complementary spectral harvesting dramatically reduces thermalization losses and has propelled laboratory power conversion efficiencies beyond thirty-three percent.',
    correct: 'A',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metne göre perovskit-silikon tandem hücrelerin tek eklemli hücreleri aşmasının doğrudan sebebini (spektral paylaşım) bulun.',
    skills: ['READING_DETAIL'],
    choices: [
      ['harvest complementary portions of the solar spectrum to minimize thermal energy losses', 'Üst perovskitin mavi/yeşil, alt silikonun kırmızı/kızılötesi ışığı soğurup termal kayıpları azaltması metinde açıkça açıklanır.', [], []],
      ['operate completely without absorbing any photons from the visible spectrum', 'Görünür ışıktan hiç foton soğurmadığı iddiası metindeki mavi/yeşil soğurma ile çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['eliminate the need for any electrical wiring or municipal grid inverters', 'Kablo ve invertör ihtiyacını ortadan kaldırdığı iddiası metinde yer almaz.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['generate significant electric power exclusively during complete nighttime darkness', 'Gece karanlığında güç ürettiği iddiası fotovoltayik mantığına zıttır.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['consist solely of radioactive uranium isotopes harvested from deep mines', 'Radyoaktif uranyum içerdiği iddiası metin dışıdır.', ['UNSUPPORTED_DETAIL'], ['SCOPE']],
    ],
  }),

  // READING COMPREHENSION 9 (Climate - Stratospheric Aerosols, INFERENCE)
  make({
    id: 'b10-reading-9', family: 'READING_COMPREHENSION', domain: 'environment',
    stem: 'It can be inferred from the passage that stratospheric aerosol injection could ____.',
    passage: 'Stratospheric aerosol injection (SAI) is a proposed solar radiation management technique inspired by explosive volcanic eruptions. By delivering sulfur dioxide precursors into the lower stratosphere via high-altitude aircraft, an artificial aerosol veil could be created to scatter a fraction of incoming solar radiation back into space. Climate modeling indicates that SAI could rapidly depress global mean surface temperatures. However, simulations also reveal serious collateral hazards: uneven regional precipitation shifts, delayed recovery of the Antarctic ozone hole, and the terrifying risk of "termination shock"—a catastrophic spike in warming if continuous aerosol replenishment were abruptly halted.',
    correct: 'D',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'INFERENCE' },
    checks: ['CONTINUATION', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Stratosferik aerosol enjeksiyonunun küresel sıcaklığı düşürse bile bölgesel yağış ve sonlandırma şoku gibi riskler barındırdığı çıkarımını seçin.',
    skills: ['READING_INFERENCE'],
    choices: [
      ['permanently eliminate all greenhouse gases from the lower troposphere', 'Sera gazlarını yok etmez, sadece güneş ışığını yansıtır.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['accelerate the immediate recovery of the Antarctic stratospheric ozone layer', 'Ozon tabakasının iyileşmesini hızlandırmaz, metne göre geciktirir (delayed recovery).', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['prevent volcanic eruptions from ever occurring across oceanic island arcs', 'Volkanik patlamaları engelleme iddiası jeolojiye aykırıdır.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['cool average surface temperatures while introducing severe regional hydrological disruptions', 'Ortalama sıcaklığı düşürürken dengesiz bölgesel yağış kaymalarına ve sonlandırma şokuna yol açabileceği metinden doğrudan çıkarılır.', [], []],
      ['replace all international treaties governing planetary carbon emissions', 'Uluslararası anlaşmaların yerini alacağı iddiası metinde yer almaz.', ['UNSUPPORTED_DETAIL'], ['SCOPE']],
    ],
  }),

  // READING COMPREHENSION 10 (Space - Pulsar Timing Arrays, MAIN_IDEA)
  make({
    id: 'b10-reading-10', family: 'READING_COMPREHENSION', domain: 'astronomy',
    stem: 'What is the primary subject of the passage?',
    passage: 'Millisecond pulsars are rapidly rotating, highly magnetized neutron stars that emit lighthouse-like beams of radio emission with rotational regularity rivaling atomic clocks. When ultra-low-frequency gravitational waves from inspiraling supermassive black hole binaries ripple across the Milky Way, they perturb the arrival times of these radio pulses by mere nanoseconds. By coordinating decades of high-precision timing data across dozens of pulsars distributed throughout the galaxy, pulsar timing array collaborations have recently detected the stochastic gravitational wave background. This monumental breakthrough opens a brand-new spectral regime in observational gravitational astrophysics, probing cosmic phenomena invisible to terrestrial laser interferometers.',
    correct: 'B',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'MAIN_IDEA' },
    checks: ['TOPIC', 'PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE'],
    triage: 'Metnin ana konusunu: Milisaniyelik pulsar zamanlama dizileriyle stokastik yerçekimi dalgası arka planının keşfedilmesini seçin.',
    skills: ['MAIN_IDEA'],
    choices: [
      ['The complete dismantling of optical telescopes across astronomical observatories', 'Optik teleskopların söküldüğü iddiası konuyla alakasızdır.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Using galactic networks of millisecond pulsars to detect low-frequency gravitational waves', 'Metin, galaktik pulsar ağlarını hassas saat gibi kullanarak düşük frekanslı yerçekimi dalgası arka planının keşfedilmesine odaklanır.', [], []],
      ['The chemical synthesis of organic compounds inside cold interstellar dust clouds', 'Organik bileşik sentezi pulsar fiziği odağı dışındadır.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['Engineering challenges encountered in building domestic quartz wristwatches', 'Kuvars kol saatleri astrofizik keşfinin konusu değildir.', ['UNSUPPORTED_DETAIL'], ['TOPIC']],
      ['Proving that general relativity fails completely in describing binary neutron stars', 'Genel göreliliğin çöktüğü iddiası metnin başarı mesajıyla çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
    ],
  }),
]);
