import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, anchors, type Choice } from './authoringUtils';

const trans = (id: string, domain: string, stem: string, correct: 'A'|'B'|'C'|'D'|'E', direction: 'ENG_TR' | 'TR_ENG', choices: readonly [Choice, Choice, Choice, Choice, Choice]) => make({
  id, family: direction === 'ENG_TR' ? 'TRANSLATION_ENG_TR' : 'TRANSLATION_TR_ENG', domain, stem, correct,
  tactical: { kind: 'TRANSLATION', direction, source: { agent: 'a', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, candidates: { A: { agent: correct==='A'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, B: { agent: correct==='B'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, C: { agent: correct==='C'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, D: { agent: correct==='D'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, E: { agent: correct==='E'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] } } },
  checks: ['SEMANTIC_EQUIVALENCE', 'SCOPE', 'TENSE_ASPECT'], triage: 'Cümledeki özne, ana fiil, zaman ve bağlaçları dikkatle eşleştirin.', skills: ['TRANSLATION_SEMANTICS'],
  choices,
});

export const batch9Questions: readonly Question[] = deepFreeze([
  // TRANSLATION TR -> ENG 9 (Medicine - Immunology)
  trans('b9-trans-treng-1', 'medicine', 'Bağışıklık sistemi hücreleri, vücudu istila eden yabancı patojenleri tanımak için yüzey antijenlerini kullanır.', 'A', 'TR_ENG', [
    ['Immune system cells use surface antigens to recognize foreign pathogens invading the body.', 'Özne, eylem ve sıfat-fiil nitelemesi tam olarak çevrilmiştir.', [], []],
    ['Foreign pathogens produce surface antigens in order to protect immune cells from destruction.', 'Patojenlerin bağışıklık hücrelerini koruduğu iddiası tamamen terstir.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Because surface antigens destroy immune cells, pathogens multiply rapidly inside tissues.', 'Antijenlerin bağışıklık hücrelerini yok ettiği iddiası biyolojiye aykırıdır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['The body produces foreign pathogens whenever immune system cells lose their surface antigens.', 'Vücudun patojen ürettiği çıkarımı tıp dışıdır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Immune cells fail to identify dangerous viruses even when surface antigens are present.', 'Tanıyamaz (fail to identify) iddiası tanımak için kullanır ile çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 10 (Physics - Thermodynamics)
  trans('b9-trans-treng-2', 'physics', 'Mutlak sıfır noktasına yaklaşıldığında, atomların termal hareketleri neredeyse tamamen durur.', 'C', 'TR_ENG', [
    ['Thermal motions of atoms accelerate rapidly when absolute zero is approached in laboratory trials.', 'Termal hareketlerin hızlandığı iddiası durmanın zıddıdır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Because atoms maintain constant kinetic energy, absolute zero cannot be measured accurately.', 'Kinetik enerjinin sabit kaldığı iddiası termodinamiğe uymaz.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['As absolute zero is approached, the thermal motions of atoms cease almost completely.', 'Zaman yantümcesi (as absolute zero is approached), özne ve zarf tam çevrilmiştir.', [], []],
    ['Atoms produce extreme thermal energy whenever absolute zero is reached under high pressure.', 'Aşırı termal enerji üretildiği iddiası mutlak sıfır tanımına aykırıdır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['The thermal velocity of subatomic particles remains entirely independent of cooling rates.', 'Soğuma hızından bağımsız kaldığı iddiası metinde yoktur.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // PARAGRAPH COMPLETION 1 (Biology - Cellular Mitophagy)
  make({
    id: 'b9-para-1', family: 'PARAGRAPH_COMPLETION', domain: 'biology',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Mitochondria are dynamic organelles that continuously generate cellular energy through oxidative phosphorylation. However, during periods of metabolic stress, damaged mitochondria can produce excessive reactive oxygen species. ____. Cells deploy a specialized autophagic pathway called mitophagy to selectively degrade these dysfunctional organelles, thereby safeguarding cellular homeostasis.',
    correct: 'B',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'ADDITION', D: 'CONDITION', E: 'CONTRAST' }, anchors: anchors('B') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Hasarlı mitokondrinin reaktif oksijen üretmesi ile hücrenin mitofaji başlatması arasındaki tehlike bağlantısını bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Nevertheless, most human cells survive without producing any ATP at all.', 'Hücrelerin hiç ATP üretmeden yaşaması biyolojik olarak imkansızdır.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['If left unchecked, this oxidative accumulation can trigger irreversible cell death cascades.', 'Birikimin hücresel ölüme yol açacağı uyarısı, hemen ardından gelen koruyucu mitofaji mekanizmasını mantıksal olarak açıklar.', [], []],
      ['Consequently, chloroplasts take over all energy production in human cardiac tissues.', 'Kloroplastlar insan kalbinde bulunmaz.', ['FALSE_FRIEND'], ['TOPIC']],
      ['On the contrary, cellular respiration accelerates whenever oxygen levels decline.', 'Oksijen düşünce solunum hızlanmaz.', ['CAUSE_EFFECT_REVERSAL'], ['CONTINUATION']],
      ['Furthermore, mitochondria were discovered by Dutch optical lens makers in the Renaissance.', 'Tarihsel keşif anekdotu hücresel stres mekanizması akışına uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
    ],
  }),

  // PARAGRAPH COMPLETION 2 (Physics - Superconductivity Meissner Effect)
  make({
    id: 'b9-para-2', family: 'PARAGRAPH_COMPLETION', domain: 'physics',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Superconductivity is characterized by the complete absence of electrical resistance below a critical transition temperature. Yet zero electrical resistivity is only half of the physical phenomenon. ____. Known as the Meissner effect, this expulsion prevents magnetic flux lines from penetrating the bulk superconductor, resulting in the famous phenomenon of magnetic levitation.',
    correct: 'D',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'ADDITION', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'CONDITION', D: 'ADDITION', E: 'RESULT' }, anchors: anchors('D') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Direncin sıfır olmasının yanı sıra Meissner etkisinin (manyetik alanı dışlama) tanımını tamamlayan cümleyi seçin.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['In contrast, conventional copper wires conduct electricity with negligible thermal losses.', 'Bakır tellerin kayıpsız iletimi süperiletkenlik açıklamasına zıttır.', ['POLARITY_INVERSION'], ['TOPIC']],
      ['Therefore, superconductors can only function inside high-temperature nuclear fusion cores.', 'Sadece füzyon çekirdeğinde çalışma kısıtı yanlıştır.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['Unless cooled with liquid nitrogen, all metals naturally expel surrounding magnetic fields.', 'Tüm metaller manyetik alanı dışlamaz.', ['FALSE_FRIEND'], ['SCOPE']],
      ['A true superconductor also actively expels external magnetic fields from its interior.', 'Manyetik alanı da dışlama özelliği sonraki "this expulsion" referansını tam bağlar.', [], []],
      ['Consequently, electric currents decay rapidly once the external voltage source is disconnected.', 'Akımın hemen sönümlenmesi süperiletkenlikle çelişir.', ['POLARITY_INVERSION'], ['CONTINUATION']],
    ],
  }),

  // PARAGRAPH COMPLETION 3 (Chemistry - Enzyme Inhibitors)
  make({
    id: 'b9-para-3', family: 'PARAGRAPH_COMPLETION', domain: 'chemistry',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Competitive enzyme inhibitors closely mimic the three-dimensional chemical structure of a natural substrate. By occupying the enzyme\'s active site, they physically prevent substrate molecules from binding. ____. Consequently, pharmacologists can carefully titrate inhibitor concentrations to modulate aberrant metabolic pathways without permanently deactivating essential proteins.',
    correct: 'A',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'CONTRAST' }, anchors: anchors('A') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Yarışmalı inhibitörlerin substrat konsantrasyonu artırılarak aşılabilmesi (geri dönüşümlü olması) özelliğini bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Because this binding is reversible, increasing substrate concentrations can overcome the inhibition.', 'Geri dönüşümlü bağlanma özelliği sonraki doz ayarlama (titrate) cümlesiyle kusursuz neden-sonuç bağı kurar.', [], []],
      ['However, this inhibition destroys the enzyme\'s primary covalent backbone permanently.', 'Kovalent yapıyı kalıcı yok etmesi yarışmalı (reversible) inhibisyonla çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['Therefore, enzymes immediately cease to exist inside living organisms.', 'Enzimlerin yok olması iddiası anlamsızdır.', ['EXTREME_QUALIFIER'], ['TOPIC']],
      ['Similarly, inorganic minerals serve as the sole building blocks of all biological enzymes.', 'Mineraller tek yapı taşı değildir.', ['FALSE_FRIEND'], ['SCOPE']],
      ['On the contrary, active sites can accommodate any arbitrary molecular shape indiscriminately.', 'Her molekülü rastgele kabul etme iddiası enzim özgüllüğüne aykırıdır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
    ],
  }),

  // PARAGRAPH COMPLETION 4 (Environment - Coral Resilience)
  make({
    id: 'b9-para-4', family: 'PARAGRAPH_COMPLETION', domain: 'environment',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Marine heatwaves have triggered catastrophic mass bleaching events across shallow coral reefs worldwide. When water temperatures exceed biological thresholds, corals expel their symbiotic zooxanthellae, losing both their vibrant pigmentation and nutritional supply. ____. Some colonies in the Red Sea harbor thermal-tolerant microalgae that enable them to endure temperatures several degrees above the regional average, offering vital insights for conservation genetics.',
    correct: 'E',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'RESULT', D: 'CONDITION', E: 'CONTRAST' }, anchors: anchors('E') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Yaygın beyazlama felaketine karşılık (zıtlık) bazı mercanların ısı toleransı geliştirdiğini hazırlayan cümleyi seçin.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Consequently, all marine calcifiers have completely disappeared from subtropical basins.', 'Tüm kalsiyumlaşan canlıların yok olduğu abartılı ve yanlıştır.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['Furthermore, coral reefs generate significant revenue for international tourism operators.', 'Turizm geliri biyolojik ısı toleransı akışına uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
      ['Thus, ocean currents have completely reversed their circulation patterns across the equator.', 'Akıntıların tersine döndüğü iddiası bağlamsızdır.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Unless commercial fishing is prohibited, marine heatwaves will accelerate indefinitely.', 'Aşırı avlanmanın sıcak dalgası yaratması neden-sonuç hatasıdır.', ['CAUSE_EFFECT_REVERSAL'], ['CONTINUATION']],
      ['Remarkably, not all coral populations exhibit identical vulnerability to thermal stress.', 'Tüm popülasyonların aynı kırılganlıkta olmaması, Kızıldeniz mercanlarının istisnai dayanıklılığına mükemmel geçiş sağlar.', [], []],
    ],
  }),

  // PARAGRAPH COMPLETION 5 (Medicine - Immunotherapy Checkpoints)
  make({
    id: 'b9-para-5', family: 'PARAGRAPH_COMPLETION', domain: 'medicine',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Under healthy physiological conditions, immune checkpoint pathways prevent autoimmune destruction by tempering T-cell activity. Malignant tumor cells frequently exploit these inhibitory checkpoints by expressing ligands like PD-L1, which effectively disarm immune surveillance. ____. Monoclonal antibodies targeting PD-1 or PD-L1 block this deceptive interaction, liberating the patient\'s own immune system to recognize and eradicate cancerous cells.',
    correct: 'C',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'ADDITION', C: 'RESULT', D: 'CONDITION', E: 'RESULT' }, anchors: anchors('C') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Tümörlerin bağışıklıktan kaçışı ile monoklonal antikor tedavisi arasındaki mantıksal tedavi ihtiyacını bağlayın.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['In contrast, healthy cells require continuous chemotherapy to maintain genomic integrity.', 'Sağlıklı hücrelerin kemoterapiye ihtiyacı yoktur.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Therefore, surgery has been completely abandoned as a viable therapeutic modality.', 'Cerrahinin tamamen terk edildiği iddiası yanlıştır.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['This molecular disguise allows malignancies to proliferate undetected throughout surrounding tissue.', 'Bu moleküler kamuflajın tümörün yayılmasına yol açması, antikorların hedef alacağı mekanizmayı açıklar.', [], []],
      ['Nevertheless, human T cells cannot survive inside primary lymphoid organs.', 'T hücrelerinin lenf organlarında yaşayamaması anatomik olarak yanlıştır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['Consequently, vaccines against infectious bacteria provide total lifelong immunity.', 'Bakteri aşıları kanser bağışıklık kontrol noktalarıyla alakasızdır.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
    ],
  }),

  // PARAGRAPH COMPLETION 6 (Technology - Quantum Dots)
  make({
    id: 'b9-para-6', family: 'PARAGRAPH_COMPLETION', domain: 'technology',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Quantum dots are semiconductor nanocrystals whose electronic properties are tightly governed by quantum confinement effects. When illuminated by an ultraviolet excitation source, they fluoresce at precise wavelengths determined strictly by their physical dimensions. ____. For instance, smaller quantum dots emit high-energy blue photons, while larger particles of the same material emit lower-energy red light.',
    correct: 'A',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'CONTRAST' }, anchors: anchors('A') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Boyut ile yayılan ışığın dalga boyu ilişkisini açıklayan ve sonraki "For instance" örneğine zemin hazırlayan cümleyi bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['This particle size tunability provides unparalleled control over the emitted color spectrum.', 'Boyut ayarlanabilirliğinin renk spektrumunu belirlemesi, ardından gelen küçük mavi / büyük kırmızı örneğini tam karşılar.', [], []],
      ['However, quantum dots cannot conduct electric currents under any laboratory circumstances.', 'Elektrik akımı iletemez iddiası yarıiletken doğalarıyla çelişir.', ['POLARITY_INVERSION'], ['TOPIC']],
      ['Therefore, classical physics models accurately predict all behaviors of semiconductor crystals.', 'Klasik fiziğin kuantum etkilerini açıkladığı iddiası yanlıştır.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']],
      ['Unless manufactured from pure silicon, all quantum dots disintegrate in atmospheric air.', 'Saf silikon şartı ve havada parçalanma iddiası gerçek dışıdır.', ['EXTREME_QUALIFIER'], ['CONTINUATION']],
      ['In comparison, optical lenses were developed centuries before quantum mechanics existed.', 'Tarihsel lens kıyaslaması parçacık fiziği akışını bozar.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
    ],
  }),

  // PARAGRAPH COMPLETION 7 (Astronomy - Fast Radio Bursts)
  make({
    id: 'b9-para-7', family: 'PARAGRAPH_COMPLETION', domain: 'astronomy',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Fast radio bursts (FRBs) are millisecond-duration pulses of intense radio emission originating from distant cosmological galaxies. Because their dispersion measures indicate immense travel distances through intergalactic plasma, the energy released in a single burst must be truly astronomical. ____. Magnetars, highly magnetized young neutron stars, are currently considered the leading candidate engines driving these extreme cosmic transients.',
    correct: 'D',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'ADDITION', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'CONDITION', D: 'ADDITION', E: 'RESULT' }, anchors: anchors('D') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Devasa enerjili radyo patlamalarının kökenini araştıran ve sonraki magnetar hipotezine köprü kuran cümleyi seçin.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Therefore, astronomers have concluded that all radio emissions originate inside our solar system.', 'Güneş sistemi içinden kaynaklandığı iddiası kozmolojik uzaklıkla çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['Consequently, radio telescopes have been permanently dismantled across all observatories.', 'Teleskopların söküldüğü iddiası mantıksızdır.', ['EXTREME_QUALIFIER'], ['TOPIC']],
      ['Unless radio waves travel faster than light, their origins will remain totally unknowable.', 'Işıktan hızlı seyahat şartı görelilik fiziğine aykırıdır.', ['FALSE_FRIEND'], ['CONTINUATION']],
      ['Identifying the catastrophic astrophysical mechanisms capable of generating such power has puzzled astrophysicists.', 'Bu gücü üreten mekanizmaların gizem yaratması, magnetar hipotezinin sunulmasıyla kusursuz devam eder.', [], []],
      ['In contrast, planetary rings around Saturn produce identical radio emissions continuously.', 'Satürn halkalarının aynı patlamaları ürettiği iddiası gerçek dışıdır.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
    ],
  }),

  // PARAGRAPH COMPLETION 8 (Environment - Wetlands and Carbon)
  make({
    id: 'b9-para-8', family: 'PARAGRAPH_COMPLETION', domain: 'environment',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Coastal blue carbon ecosystems, including tidal marshes and mangrove forests, sequester organic carbon at rates substantially higher than terrestrial forests. Their waterlogged, anoxic soils dramatically retard microbial respiration, preventing organic detritus from decomposing into carbon dioxide. ____. Protecting and restoring these coastal habitats therefore represents an exceptionally high-leverage strategy for global climate mitigation.',
    correct: 'B',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'ADDITION', D: 'CONDITION', E: 'CONTRAST' }, anchors: anchors('B') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Oksijensiz toprakta ayrışmanın durmasının sonucu olan uzun vadeli karbon depolanmasını belirleyin.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['In contrast, mangroves release all of their captured carbon into the atmosphere each autumn.', 'Her sonbahar tüm karbonu saldığı iddiası sekestrasyonla çelişir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['As a result, carbon can remain locked within these sediments for centuries, if not millennia.', 'Ayrışmanın durması sayesinde karbonun bin yıllarca kilitli kalması, iklim koruma stratejisini doğrudan destekler.', [], []],
      ['Consequently, coastal ecosystems have become completely uninhabitable for marine fish species.', 'Balıklar için yaşanmaz hale gelmesi ekolojik gerçeğe aykırıdır.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Nevertheless, terrestrial forests contain no organic carbon whatsoever.', 'Karasal ormanlarda hiç karbon olmadığı iddiası asılsızdır.', ['EXTREME_QUALIFIER'], ['CONTINUATION']],
      ['Furthermore, sea level rise has permanently ceased along all oceanic coastlines.', 'Deniz seviyesi yükselmesinin durduğu iddiası yanlıştır.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
    ],
  }),

  // PARAGRAPH COMPLETION 9 (Chemistry - Solid State Batteries)
  make({
    id: 'b9-para-9', family: 'PARAGRAPH_COMPLETION', domain: 'chemistry',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Conventional lithium-ion batteries rely on flammable liquid organic solvents to transport ions between the cathode and anode. Under mechanical puncture or overcharging conditions, these liquids can vaporize and ignite, triggering dangerous thermal runaway events. ____. Ceramic and polymer-based solid electrolytes eliminate flammable solvents entirely while permitting the use of high-capacity lithium metal anodes.',
    correct: 'E',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'ADDITION', C: 'CONDITION', D: 'RESULT', E: 'RESULT' }, anchors: anchors('E') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Sıvı elektrolit yangın tehlikesine çözüm olarak katı hal elektrolitlerine geçiş motivasyonunu bağlayın.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['Therefore, electric vehicles must be powered exclusively by fossil fuel combustion engines.', 'Elektrikli araçların fosil yakıtla çalışması çelişkilidir.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Consequently, lithium-ion battery production has been universally outlawed across the globe.', 'Üretimin yasaklandığı iddiası gerçek dışıdır.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['Unless batteries are kept at sub-zero temperatures, they inevitably explode during use.', 'Her kullanımda patlama iddiası abartılıdır.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['In comparison, lead-acid batteries represent the most advanced energy storage technology.', 'Kurşun-asit piller en gelişmiş teknoloji değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_FUNCTION']],
      ['To circumvent these severe safety limitations, materials scientists are developing solid-state alternatives.', 'Güvenlik sınırlarını aşmak için katı hal alternatiflerinin geliştirilmesi, sonraki katı elektrolit cümlesine tam bağlanır.', [], []],
    ],
  }),

  // PARAGRAPH COMPLETION 10 (Engineering - Aerodynamic Drag)
  make({
    id: 'b9-para-10', family: 'PARAGRAPH_COMPLETION', domain: 'engineering',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'In high-speed transportation, aerodynamic drag accounts for the vast majority of energy expenditure. Parasitic drag increases with the square of vehicle velocity, requiring disproportionately greater power output as speeds rise. ____. By optimizing laminar boundary layers and adding vortex generators, aerodynamicists reduce turbulence and achieve substantial reductions in fuel consumption.',
    correct: 'C',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'ADDITION', C: 'RESULT', D: 'CONDITION', E: 'CONTRAST' }, anchors: anchors('C') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Hızlandıkça karesiyle artan sürtünmenin mühendislik tasarımında neden optimizasyon gerektirdiğini bağlayın.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['In contrast, trains experience zero friction when traveling through open atmosphere.', 'Açık havada sürtünmesiz tren iddiası fizik kurallarına zıttır.', ['POLARITY_INVERSION'], ['TOPIC']],
      ['Therefore, high-speed rail networks have been permanently dismantled worldwide.', 'Yüksek hızlı trenlerin kaldırıldığı iddiası asılsızdır.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['Engineers therefore invest extensive wind tunnel testing to streamline vehicular profiles.', 'Rüzgar tüneli ve profil optimizasyonu yatırımı, sonraki girdap üreteçleri ve yakıt tasarrufu cümlesine zemin hazırlar.', [], []],
      ['Nevertheless, gravity has no measurable effect on ground transportation systems.', 'Yerçekiminin etkisiz olduğu iddiası mekanikle çelişir.', ['FALSE_FRIEND'], ['CONTINUATION']],
      ['Furthermore, internal combustion engines operate with one hundred percent thermal efficiency.', 'Yüzde yüz verim termodinamiğin ikinci yasasına aykırıdır.', ['EXTREME_QUALIFIER'], ['DISCOURSE_FUNCTION']],
    ],
  }),

  // IRRELEVANT SENTENCE 1 (Biology - Enzyme Kinetics)
  make({
    id: 'b9-irrel-1', family: 'IRRELEVANT_SENTENCE', domain: 'biology',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Enzyme kinetics describes the chemical rates at which enzyme-catalyzed reactions occur in living systems. (II) The Michaelis-Menten model mathematically relates reaction velocity to substrate concentration. (III) Many tropical rainforests receive more than two thousand millimeters of rainfall annually. (IV) As substrate levels saturate available catalytic sites, the reaction velocity approaches a theoretical maximum. (V) Understanding these kinetic parameters is vital for designing effective competitive pharmaceuticals.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Enzyme kinetics Michaelis-Menten', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Enzim kinetiği ve reaksiyon hızı anlatılırken tropik yağmur ormanlarının yağış miktarı (III) akışı bozar.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Enzim kinetiğinin tanımını yapar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Michaelis-Menten modelini sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Tropik yağmur ormanlarının yıllık yağış miktarı biyokimyasal reaksiyon kinetiğiyle tamamen alakasızdır.', [], []],
      ['IV', 'Substrat doygunluğunu açıklayarak (II) numaralı modeli detaylandırır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Kinetik parametrelerin ilaç tasarımındaki önemini özetler.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 2 (Physics - Superconductivity)
  make({
    id: 'b9-irrel-2', family: 'IRRELEVANT_SENTENCE', domain: 'physics',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) High-temperature superconductors can conduct electricity without resistance above the boiling point of liquid nitrogen. (II) This breakthrough significantly reduces the cooling costs associated with cryogenic equipment. (III) Commercial airlines typically serve complimentary beverages on international long-haul flights. (IV) Consequently, copper-oxide ceramic materials can be economically deployed in magnetic resonance imaging systems. (V) Researchers are actively searching for room-temperature compounds to eliminate cooling requirements altogether.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'High-temperature superconductors', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Yüksek sıcaklık süperiletkenleri ve kriyojenik maliyetler anlatılırken uçaklardaki içecek servisi (III) ilgisizdir.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Sıvı azot sıcaklığında süperiletkenlik başarısını sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Soğutma maliyetlerinin düşmesini açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Uçaklardaki ikram servisi katı hal fiziği ve süperiletkenlik konusuyla tamamen ilgisizdir.', [], []],
      ['IV', 'Seramik malzemelerin MR cihazlarında kullanımını bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Oda sıcaklığı arayışıyla gelecekteki hedefi belirtir.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 3 (Chemistry - Graphene Synthesis)
  make({
    id: 'b9-irrel-3', family: 'IRRELEVANT_SENTENCE', domain: 'chemistry',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Chemical vapor deposition is widely utilized to synthesize large-area, high-quality graphene sheets on copper substrates. (II) Hydrocarbon gases are introduced into a heated reaction chamber where they decompose into carbon atoms. (III) Ancient Greek philosophers debated the atomic theory of matter during classical antiquity. (IV) These carbon atoms then nucleate and organize into a hexagonal two-dimensional lattice across the metallic catalyst. (V) The resulting single-atom-thick monolayers exhibit superior mechanical and electronic properties.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Graphene CVD synthesis', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Grafenin kimyasal buhar biriktirme (CVD) yöntemiyle sentezini anlatan metne Antik Yunan felsefesi (III) uymaz.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'CVD yönteminin bakır üzerinde grafen üretimindeki rolünü tanıtır.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Hidrokarbon gazlarının fırında karbon atomlarına ayrışmasını açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Antik Yunan filozoflarının atom teorisi tartışması modern malzeme sentezi sürecini bozar.', [], []],
      ['IV', 'These carbon atoms referansıyla (II)\'deki atomların petek kafese dönüşümünü bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Elde edilen tek katmanlı grafenin özelliklerini özetler.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),

  // IRRELEVANT SENTENCE 4 (Environment - Ocean Deoxygenation)
  make({
    id: 'b9-irrel-4', family: 'IRRELEVANT_SENTENCE', domain: 'environment',
    stem: 'Choose the irrelevant sentence in the passage.',
    passage: '(I) Ocean deoxygenation has emerged as a severe consequence of anthropogenic climate change. (II) Warmer ocean surface waters hold less dissolved oxygen and exhibit enhanced thermal stratification. (III) Most modern smartphones feature advanced lithium-ion batteries that recharge rapidly. (IV) This increased stratification restricts vertical mixing, preventing atmospheric oxygen from reaching deeper marine layers. (V) Consequently, expanding oxygen minimum zones threaten the survival of large pelagic predators like tuna and billfish.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Ocean deoxygenation climate change', discourse_function: 'Identify the sentence that breaks the topic flow' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Okyanuslardaki oksijensizleşme anlatılırken akıllı telefon bataryaları (III) alakasız bir detaydır.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Okyanus oksijen kaybının iklim kriziyle ilişkisini sunar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['II', 'Isınan suyun daha az oksijen tutmasını ve tabakalaşmayı açıklar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['III', 'Akıllı telefonların hızlı şarj olan bataryaları okyanus ekolojisi akışına tamamen aykırıdır.', [], []],
      ['IV', 'This increased stratification diyerek (II)\'deki tabakalaşmanın derinlere oksijen gitmesini engellemesini bağlar.', ['PARTIAL_TRUTH'], ['TOPIC']],
      ['V', 'Oksijensiz alanların büyümesinin deniz avcılarına zararını özetler.', ['PARTIAL_TRUTH'], ['TOPIC']],
    ],
  }),
]);
