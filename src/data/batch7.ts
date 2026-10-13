import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, type Choice } from './authoringUtils';

const trans = (id: string, domain: string, stem: string, correct: 'A'|'B'|'C'|'D'|'E', direction: 'ENG_TR' | 'TR_ENG', choices: readonly [Choice, Choice, Choice, Choice, Choice]) => make({
  id, family: direction === 'ENG_TR' ? 'TRANSLATION_ENG_TR' : 'TRANSLATION_TR_ENG', domain, stem, correct,
  tactical: { kind: 'TRANSLATION', direction, source: { agent: 'a', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, candidates: { A: { agent: correct==='A'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, B: { agent: correct==='B'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, C: { agent: correct==='C'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, D: { agent: correct==='D'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, E: { agent: correct==='E'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] } } },
  checks: ['SEMANTIC_EQUIVALENCE', 'SCOPE', 'TENSE_ASPECT'], triage: 'Cümledeki özne, ana fiil, zaman ve bağlaçları dikkatle eşleştirin.', skills: ['TRANSLATION_SEMANTICS'],
  choices,
});

export const batch7Questions: readonly Question[] = deepFreeze([
  // CLOZE TEST 7 - Astronomy (Exoplanet Atmospheres)
  make({
    id: 'b7-cloze-1', family: 'CLOZE_TEST', domain: 'astronomy',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Transmission spectroscopy detects chemical species in an exoplanet\'s atmosphere by measuring filtered starlight during a transit. ____, thick layers of high-altitude clouds can mute these spectral signatures entirely. Astronomers must model aerosol scattering to interpret ambiguous observations.',
    correct: 'C',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Transmission spectroscopy detects chemical species in an exoplanet\'s atmosphere by measuring filtered starlight during a transit.',
      target_sentence: '____, thick layers of high-altitude clouds can mute these spectral signatures entirely.',
      next_sentence: 'Astronomers must model aerosol scattering to interpret ambiguous observations.',
      macro_context: 'Transmission spectroscopy versus cloud obscuration',
      relation: 'CONTRAST',
      candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'CONTRAST', D: 'CONDITION', E: 'RESULT' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Tayfölçümün kimyasal tespit yeteneği ile kalın bulut tabakasının sinyalleri köreltmesi arasındaki zıtlığı bağlayın.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Accordingly', 'Sonuç bildiren bağlaç gözlemsel engeli açıklayamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Furthermore', 'Ek bilgi değil gözlemi zorlaştıran bir engel sunulmaktadır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Yet', 'Yet / However gelişmiş ölçüm tekniği ile bulutların yarattığı sınırlama arasındaki karşıtlığı doğru kurar.', [], []],
      ['As long as', 'Koşul yapısı doğrudan zıtlığı ifade edemez.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Hence', 'Neden-sonuç bağı zıt durumun yerini alamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 8 - Environment (Ocean Acidification)
  make({
    id: 'b7-cloze-2', family: 'CLOZE_TEST', domain: 'environment',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'As oceans absorb excess anthropogenic carbon dioxide, seawater pH declines steadily. ____, carbonate ion concentrations diminish, impairing the calcification capacity of marine organisms like corals and mollusks. This biochemical shift disrupts foundational trophic networks across marine biomes.',
    correct: 'A',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'As oceans absorb excess anthropogenic carbon dioxide, seawater pH declines steadily.',
      target_sentence: '____, carbonate ion concentrations diminish, impairing the calcification capacity of marine organisms like corals and mollusks.',
      next_sentence: 'This biochemical shift disrupts foundational trophic networks across marine biomes.',
      macro_context: 'Ocean acidification chain reaction',
      relation: 'RESULT',
      candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'CONCESSION', D: 'CONDITION', E: 'ADDITION' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'pH düşüşünün kimyasal sonucu olarak karbonat iyonlarının azalmasını bağlayın.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Consequently', 'Consequently pH düşüşünün doğrudan kimyasal sonucu olan iyon azalmasını doğru şekilde bağlar.', [], []],
      ['In contrast', 'Karşıtlık değil doğrudan sebep-sonuç ilişkisi vardır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['Even though', 'Ödünleme bağlacı bağımsız cümle yapısına uymaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Unless', 'Koşul ilişkisi gerçekleşen kimyasal süreci açıklayamaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['On the contrary', 'Zıtlık ifadesi neden-sonuç akışını bozar.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 9 - Biology (Epigenetics)
  make({
    id: 'b7-cloze-3', family: 'CLOZE_TEST', domain: 'biology',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Epigenetic modifications regulate gene expression without altering the underlying nucleotide sequence. ____, environmental stressors such as poor diet or pollutants can induce chromatin remodeling that persists across cell divisions. This discovery has transformed our understanding of developmental biology.',
    correct: 'B',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Epigenetic modifications regulate gene expression without altering the underlying nucleotide sequence.',
      target_sentence: '____, environmental stressors such as poor diet or pollutants can induce chromatin remodeling that persists across cell divisions.',
      next_sentence: 'This discovery has transformed our understanding of developmental biology.',
      macro_context: 'Epigenetics and environmental influence',
      relation: 'ADDITION',
      candidate_relations: { A: 'CONTRAST', B: 'ADDITION', C: 'CONDITION', D: 'RESULT', E: 'CONTRAST' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Epigenetik tanımının ardından çevresel stres faktörlerinin etkisini ekleyen geçiş ifadesini seçin.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['On the contrary', 'Zıtlık değil epigenetiğin pratik mekanizmasına dair ek bilgi verilmektedir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['In particular', 'In particular / Furthermore epigenetik modifikasyonların çevresel etkenlerle nasıl tetiklendiğini detaylandırır.', [], []],
      ['Unless', 'Koşul yapısı metnin bilgilendirici akışıyla uyumsuzdur.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Therefore', 'Çevresel stres faktörlerinin varlığı epigenetiğin tanımının doğrudan sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Rather', 'Düzeltme/yerine geçme durumu metinde mevcut değildir.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 10 - Engineering (Lithium Batteries)
  make({
    id: 'b7-cloze-4', family: 'CLOZE_TEST', domain: 'engineering',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Solid-state batteries replace volatile liquid electrolytes with solid non-flammable ionic conductors. ____, they substantially mitigate the risk of thermal runaway and catastrophic fires in electric vehicles. Their higher manufacturing costs, however, still impede mass commercialization.',
    correct: 'E',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Solid-state batteries replace volatile liquid electrolytes with solid non-flammable ionic conductors.',
      target_sentence: '____, they substantially mitigate the risk of thermal runaway and catastrophic fires in electric vehicles.',
      next_sentence: 'Their higher manufacturing costs, however, still impede mass commercialization.',
      macro_context: 'Solid-state battery safety benefit',
      relation: 'RESULT',
      candidate_relations: { A: 'CONTRAST', B: 'CONCESSION', C: 'CONDITION', D: 'ADDITION', E: 'RESULT' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Katı yanmaz elektrolit kullanımının mantıksal sonucu olarak yangın riskini azaltmasını bağlayın.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Nevertheless', 'Zıtlık bağlacı güvenlik avantajını açıklarken kullanılamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['Although', 'Bağımsız cümle başında tek başına ödünleme oluşturamaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Otherwise', 'Koşul/aksi takdirde anlamı doğrudan avantaja uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['In comparison', 'Kıyaslama yerine teknik değişikliğin sonucu aktarılmaktadır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Thus', 'Thus yanmaz iletken kullanımının termal kaçak riskini önleme sonucunu tam olarak bağlar.', [], []],
    ],
  }),

  // SENTENCE COMPLETION 1 - Cause/Result (Physics - Gravitational Waves)
  make({
    id: 'b7-sent-1', family: 'SENTENCE_COMPLETION', domain: 'physics',
    stem: 'Because gravitational waves interact extremely weakly with intervening matter, ____.',
    correct: 'A',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Yerçekimi dalgalarının maddeyle çok zayıf etkileşime girmesinin doğrudan fiziksel sonucunu belirleyin.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['they can travel across cosmic distances virtually unimpeded', 'Maddeyle zayıf etkileşim dalgaların evrende engellenmeden yayılabilmesi sonucunu doğurur.', [], []],
      ['optical telescopes can easily capture their high-resolution images', 'Yerçekimi dalgaları ışık olmadığından optik teleskoplarla görüntülenemez.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['most stars produce intense electromagnetic radiation continuously', 'Yıldızların ışıması yerçekimi dalgası etkileşiminin sonucu değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['they lose all of their energy within a few light years', 'Enerjisini hemen kaybetmesi zayıf etkileşimle çelişir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['astronomers have abandoned all research into black hole mergers', 'Araştırmaların terk edilmesi değil yoğunlaşması söz konusudur.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 2 - Concession (Biology - Extremophiles)
  make({
    id: 'b7-sent-2', family: 'SENTENCE_COMPLETION', domain: 'biology',
    stem: 'Although deep-sea hydrothermal vents are devoid of sunlight and subject to crushing pressure, ____.',
    correct: 'C',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'RESULT', C: 'CONTRAST', D: 'CONDITION', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Güneşsiz ve yüksek basınçlı aşırı ortama rağmen gelişen zengin ekosistemi (zıtlığı) bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['no organism can possibly maintain cellular integrity there', 'Hiçbir canlı yaşayamaz iddiası although zıtlık yapısını karşılamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['photosynthetic algae dominate the surrounding water column', 'Güneş ışığı olmayan yerde fotosentetik algler baskın olamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['thriving ecosystems powered by chemosynthetic bacteria flourish around them', 'Zorlu koşullara rağmen kemosentezle beslenen zengin ekosistemlerin varlığı zıtlığı tamamlar.', [], []],
      ['water temperatures remain constantly below freezing point', 'Hidrotermal bacalarda su sıcaklığı donma noktasında değil aşırı sıcaktır.', ['UNSUPPORTED_DETAIL'], ['DISCOURSE_RELATION']],
      ['miners frequently extract commercial minerals from the ocean floor', 'Madencilik faaliyetleri aşırı ortamın biyolojik zıtlığıyla ilgisizdir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 3 - Condition (Medicine - Organ Transplantation)
  make({
    id: 'b7-sent-3', family: 'SENTENCE_COMPLETION', domain: 'medicine',
    stem: 'Unless the recipient\'s immune system is carefully suppressed with targeted pharmacological agents, ____.',
    correct: 'B',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONDITION', B: 'RESULT', C: 'CONTRAST', D: 'ADDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Bağışıklık sistemi hedefe yönelik ilaçlarla baskılanmazsa (unless) organ naklinde gerçekleşecek olumsuz sonucu bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['the donor organ will function normally for many decades', 'Baskılanmazsa organın normal çalışması mantıken imkansızdır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['circulating cytotoxic T cells will recognize and reject the transplanted tissue', 'İlaçla baskılanmadığında bağışıklık hücrelerinin dokuyu reddetmesi doğrudan sonuçtur.', [], []],
      ['bacterial infections rarely occur in post-operative patients', 'Enfeksiyonların nadir görülmesi bağışıklık baskılanmaması koşuluna uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['blood vessels in the graft will spontaneously regenerate immediately', 'Damarların anında kendiliğinden yenilenmesi tıbbi gerçekle bağdaşmaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['surgical procedures have become significantly safer worldwide', 'Genel cerrahinin güvenli hale gelmesi cümlenin koşulunu tamamlamaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 4 - Time/Contrast (Chemistry - Graphene)
  make({
    id: 'b7-sent-4', family: 'SENTENCE_COMPLETION', domain: 'chemistry',
    stem: 'While graphene possesses extraordinary electrical conductivity and mechanical strength, ____.',
    correct: 'D',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'RESULT', D: 'CONTRAST', E: 'CONDITION' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Grafenin olağanüstü özelliklerine rağmen (while) seri üretim ve pratik kullanımındaki zorluğu belirleyin.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['it can easily replace all existing structural steel components', 'Tüm çeliğin kolayca yerini alması zıtlık değil abartılı uyum bildirir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['scientists had discovered its molecular formula over two centuries ago', 'Grafen iki yüzyıl önce değil 2004 yılında izole edilmiştir.', ['TEMPORAL_MISMATCH'], ['DISCOURSE_RELATION']],
      ['it completely lacks any crystalline carbon structure', 'Karbon kristal yapısından yoksun olduğu iddiası kimyasal olarak yanlıştır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['scaling up defect-free synthesis for industrial use remains a formidable hurdle', 'Mükemmel özelliklere rağmen endüstriyel boyutta hatasız sentez zorluğu zıtlığı tam karşılar.', [], []],
      ['its density is higher than that of most heavy metals', 'Grafenin yoğunluğunun ağır metallerden fazla olduğu iddiası gerçek dışıdır.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 5 - Reason (Environment - Microplastics)
  make({
    id: 'b7-sent-5', family: 'SENTENCE_COMPLETION', domain: 'environment',
    stem: 'Since microplastic particles are small enough to be ingested by zooplankton at the base of the food web, ____.',
    correct: 'A',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Besin zincirinin en altındaki zooplanktonlar tarafından yutulabilen mikroplastiklerin ekolojik sonucunu bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['they bioaccumulate across trophic levels and reach apex marine predators', 'Zooplankton tarafından yutulmanın sonucu üst basamaklardaki avcılara biyobirikimle ulaşmasıdır.', [], []],
      ['ocean currents invariably push them back toward urban coastlines', 'Akıntıların sahile itmesi biyolojik besin ağıyla doğrudan sonuç ilişkisi kurmaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['marine bacteria immediately digest them into harmless organic molecules', 'Bakterilerin anında zararsız moleküllere sindirdiği iddiası kirlilik kriziyle çelişir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['commercial fisheries have seen an unprecedented rise in global catches', 'Balıkçılık avının artması çevre kirliliğinin mantıksal sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['freshwater ecosystems remain entirely immune to synthetic contamination', 'Tatlı su ekosistemlerinin bağışık kalması bilimsel gerçekle uyuşmaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 6 - Concession (Engineering - Renewable Energy)
  make({
    id: 'b7-sent-6', family: 'SENTENCE_COMPLETION', domain: 'engineering',
    stem: 'Even though solar photovoltaic cells have achieved historic reductions in per-watt production costs, ____.',
    correct: 'E',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'RESULT', D: 'CONDITION', E: 'CONTRAST' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Güneş paneli maliyetlerindeki tarihi düşüşe rağmen şebeke entegrasyonu ve depolama kısıtını (zıtlığı) seçin.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['they require no electrical inverters to feed into municipal power grids', 'İnvertöre ihtiyaç duymadığı iddiası teknik olarak hatalıdır.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['fossil fuel plants have ceased operating across all developing nations', 'Fosil yakıt santrallerinin tamamen durduğu iddiası gerçek dışıdır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['solar energy output remains entirely constant throughout the night', 'Geceleri güneş enerjisi üretiminin sabit kaldığı iddiası fiziksel gerçeğe zıttır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['governments have completely eliminated all subsidies for wind turbines', 'Rüzgar sübvansiyonlarının kesilmesi güneş hücresi maliyet zıtlığıyla alakasızdır.', ['UNSUPPORTED_DETAIL'], ['DISCOURSE_RELATION']],
      ['intermittent generation necessitates substantial investments in grid-scale energy storage', 'Maliyet düşüşüne rağmen kesintili üretim yüzünden şebeke depolama yatırımı gerekliliği zıtlığı tamamlar.', [], []],
    ],
  }),

  // SENTENCE COMPLETION 7 - Cause/Effect (Medicine - Neurodegeneration)
  make({
    id: 'b7-sent-7', family: 'SENTENCE_COMPLETION', domain: 'medicine',
    stem: 'As misfolded amyloid-beta proteins aggregate into insoluble plaques within neural tissue, ____.',
    correct: 'B',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'CONDITION', D: 'ADDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Hatalı katlanan proteinlerin sinir dokusunda plaklar oluşturmasının patolojik sonucunu belirleyin.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['neuronal communication becomes dramatically faster and more resilient', 'Hücresel iletişimin hızlanması ve güçlenmesi nörodejenerasyonla çelişir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['they trigger neuroinflammatory cascades that culminate in synaptic loss', 'Plak birikiminin doğrudan patolojik sonucu sinaptik kayıpla sonuçlanan iltihabi süreçtir.', [], []],
      ['patients completely recover all previously lost cognitive faculties', 'Hastaların tamamen iyileşmesi plak birikiminin sonucu olamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['the blood-brain barrier becomes totally impermeable to oxygen and glucose', 'Oksijen ve glikoza geçirimsiz hale gelmesi fizyolojik olarak geçersizdir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['cerebral spinal fluid production ceases entirely throughout the brain', 'BOS üretiminin tamamen durması alzheimer patofizyolojisinde yer almaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 8 - Condition (Environment - Biodiversity)
  make({
    id: 'b7-sent-8', family: 'SENTENCE_COMPLETION', domain: 'environment',
    stem: 'Provided that tropical rainforest corridors are preserved between fragmented protected reserves, ____.',
    correct: 'C',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'RESULT', D: 'CONDITION', E: 'ADDITION' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Orman koridorlarının korunması koşuluyla (provided that) yaban hayatı ve gen akışı için doğacak olumlu sonucu bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['isolated populations will inevitably suffer from lethal inbreeding depression', 'Kaçınılmaz akraba evliliği koridorların korunduğu senaryonun sonucu değildir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['poachers can easily locate and capture endangered mammalian species', 'Kaçak avcıların hayvanları yakalaması koridor koruma koşulunun ana amacı değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['migratory species can maintain genetic gene flow and adapt to localized stressors', 'Koridorların korunması gen akışını sürdürmeyi ve stresörlere uyumu mümkün kılar.', [], []],
      ['canopy evapotranspiration rates will decline to near desert levels', 'Buharlaşmanın çöl seviyesine düşmesi koridor korumanın sonucu olamaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['global timber prices will plummet across international commodity markets', 'Kereste fiyatlarının düşmesi ekolojik koruma cümlesinin ana tamamlayıcısı değildir.', ['UNSUPPORTED_DETAIL'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 9 - Contrast (Physics - Dark Energy)
  make({
    id: 'b7-sent-9', family: 'SENTENCE_COMPLETION', domain: 'physics',
    stem: 'While gravity acts as an attractive force pulling massive objects together on local scales, ____.',
    correct: 'A',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Yerçekiminin yerel ölçekte çekici bir kuvvet olmasına karşılık (while) kozmik ölçekte evreni genişleten karanlık enerjiyi bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['dark energy drives the accelerated expansion of the universe across cosmic distances', 'Yerel çekim kuvvetine zıt olarak evreni hızla genişleten karanlık enerji zıtlığı tam karşılar.', [], []],
      ['all galaxies are inevitably doomed to collide into a single supermassive singularity', 'Tüm galaksilerin tek noktada çarpışacağı iddiası karanlık enerji gözlemleriyle çelişir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['electromagnetism is the weakest fundamental interaction observed in particle physics', 'Elektromanyetizmanın en zayıf kuvvet olduğu iddiası fiziksel olarak yanlıştır.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['planetary orbits around the Sun have expanded dramatically over recent decades', 'Güneş sistemi yörüngelerinin son yıllarda devasa genişlediği iddiası yanlıştır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['nuclear fusion inside white dwarfs prevents them from gravitational collapse', 'Beyaz cücelerde füzyon değil dejenere elektron basıncı çökmeyi engeller.', ['UNSUPPORTED_DETAIL'], ['DISCOURSE_RELATION']],
    ],
  }),

  // SENTENCE COMPLETION 10 - Result/Purpose (Chemistry - Green Solvents)
  make({
    id: 'b7-sent-10', family: 'SENTENCE_COMPLETION', domain: 'chemistry',
    stem: 'Supercritical carbon dioxide exhibits properties of both liquids and gases, ____.',
    correct: 'D',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CONDITION', C: 'ADDITION', D: 'RESULT', E: 'CONTRAST' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Süperkritik CO2 nin hem sıvı hem gaz özelliği taşımasının sağladığı pratik kimyasal sonucu belirleyin.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['yet it cannot dissolve any non-polar organic compound under standard conditions', 'Apolar bileşikleri çözemediği iddiası süperkritik akışkanın avantajıyla çelişir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['unless it is cooled below its critical triple point before each extraction', 'Üçlü noktanın altına soğutulması süperkritik fazı ortadan kaldırır.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['although toxic chlorinated solvents remain universally preferred in pharmaceutical labs', 'Zehirli solventlerin tercih edildiği iddiası yeşil kimya akışına uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['which makes it an exceptionally versatile and environmentally benign solvent for extractions', 'Hem sıvı yoğunluğu hem gaz difüzyonu taşıması onu çok yönlü çevre dostu bir solvent yapar.', [], []],
      ['so industrial chemical reactors must be constructed exclusively from brittle ceramics', 'Kırılgan seramikten üretilme zorunluluğu kimya mühendisliği gerçeğine aykırıdır.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // TRANSLATION ENG -> TR 1 (Biology - Photosynthesis)
  trans('b7-trans-engtr-1', 'biology', 'During oxygenic photosynthesis, plants split water molecules to release oxygen into the atmosphere.', 'B', 'ENG_TR', [
    ['Oksijenik fotosentez sırasında bitkiler, atmosfere oksijen salabilmek için su moleküllerine ihtiyaç duyarlar.', 'Su moleküllerine ihtiyaç duyarlar (need) değil, su moleküllerini ayrıştırırlar (split).', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Oksijenik fotosentez sırasında bitkiler, atmosfere oksijen salmak için su moleküllerini ayrıştırır.', 'Tüm özneler, fiiller ve amaç bildiren mastar yapısı eksiksiz çevrilmiştir.', [], []],
    ['Bitkiler atmosfere oksijen saldığında, oksijenik fotosentez yoluyla su molekülleri üretilir.', 'Su üretilmez (split edilir) ve zaman cümlesi ters kurulmuştur.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Oksijenik fotosentez yapan bitkiler, su moleküllerini parçalayarak atmosferdeki oksijeni tüketir.', 'Oksijen tüketilmez (consume), salınır (release).', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Atmosferdeki oksijen su moleküllerine ayrıştırıldığında bitkiler fotosentez gerçekleştirir.', 'Edilgen ve etken ögelerin rolleri tamamen karıştırılmıştır.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 2 (Physics - Superconductivity)
  trans('b7-trans-engtr-2', 'physics', 'Superconductors can conduct electric current indefinitely without generating any measurable heat.', 'A', 'ENG_TR', [
    ['Süperiletkenler, ölçülebilir herhangi bir ısı üretmeksizin elektrik akımını süresiz olarak iletebilir.', 'Eyleyen, eylem, zarf (indefinitely) ve edat yapısı (without generating) eksiksiz çevrilmiştir.', [], []],
    ['Süperiletkenlerin elektrik akımını iletebilmesi için üretilen ısının ölçülebilir düzeyde olması gerekir.', 'Isının ölçülebilir olması koşul değil, ısı üretilmemesi esastır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Elektrik akımını süresiz ileten süperiletkenler, zamanla az da olsa ısı üretebilirler.', 'Az da olsa ısı üretebilirler ifadesi without generating heat ile çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Ölçülebilir ısı üretmeyen bazı malzemeler elektrik akımını belirli bir süre boyunca iletir.', 'Süperiletkenler öznesi malzemeler olarak değiştirilmiş ve süresiz (indefinitely) atlanmıştır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Süperiletkenler elektrik akımını ilettiğinde ortaya çıkan ısı miktarı henüz ölçülememiştir.', 'Henüz ölçülememiştir (has not been measured yet) orijinal cümlede yoktur.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
  ]),
]);
