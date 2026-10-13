import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make } from './authoringUtils';

export const batch6Questions: readonly Question[] = deepFreeze([
  // GAP FILL 1 - Vocab (Biology)
  make({
    id: 'b6-gap-vocab-1', family: 'GAP_FILL', domain: 'biology',
    stem: 'Enzymes act as biological catalysts that ____ the activation energy required for chemical reactions in cells.',
    correct: 'A',
    tactical: { kind: 'GAP_FILL', focus: 'VOCAB' },
    checks: ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB'],
    triage: 'Enzimlerin aktivasyon enerjisini düşürme işlevini karşılayan fiili belirleyin.',
    skills: ['VOCAB_CONTEXT'], lexical: ['catalyst', 'activation energy', 'reduce'],
    choices: [
      ['lower', 'Katalizör enzimler reaksiyon için gereken aktivasyon enerjisini düşürür (lower).', [], []],
      ['elevate', 'Aktivasyon enerjisini yükseltmek reaksiyonu hızlandırmaz, yavaşlatır.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
      ['manufacture', 'Enerji üretmek/imal etmek biyokimyasal bağlamda yanlıştır.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['postpone', 'Enerjiyi ertelemek enzim işlevini ifade etmez.', ['FALSE_FRIEND'], ['SEMANTIC_FIT']],
      ['withhold', 'Enerjiyi alıkoymak/esirgemek bağlama uymaz.', ['UNSUPPORTED_DETAIL'], ['COLLOCATION']],
    ],
  }),

  // GAP FILL 2 - Vocab (Chemistry)
  make({
    id: 'b6-gap-vocab-2', family: 'GAP_FILL', domain: 'chemistry',
    stem: 'Due to its exceptional thermal stability, the synthetic polymer can ____ temperatures exceeding 400 degrees Celsius without degrading.',
    correct: 'C',
    tactical: { kind: 'GAP_FILL', focus: 'VOCAB' },
    checks: ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB'],
    triage: 'Yüksek sıcaklıklara bozulmadan dayanabilmeyi (withstand) ifade eden fiili bulun.',
    skills: ['VOCAB_CONTEXT'], lexical: ['thermal stability', 'withstand', 'polymer'],
    choices: [
      ['accelerate', 'Sıcaklığı hızlandırmak anlamsal olarak geçersizdir.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['terminate', 'Sıcaklığı sonlandırmak polimerin dayanıklılığını açıklamaz.', ['FALSE_FRIEND'], ['SEMANTIC_FIT']],
      ['withstand', 'Yüksek sıcaklıklara dayanmak/direnmek (withstand) kimyasal kararlılığı tam karşılar.', [], []],
      ['generate', 'Polimerin kendisi 400 derece sıcaklık üretmez.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_FIT']],
      ['surrender', 'Sıcaklığa teslim olmak dayanıklılıkla çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
    ],
  }),

  // GAP FILL 3 - Preposition (Physics)
  make({
    id: 'b6-gap-prep-1', family: 'GAP_FILL', domain: 'physics',
    stem: 'Electrons in superconducting materials bind into Cooper pairs and move ____ resistance through the crystal lattice.',
    correct: 'B',
    tactical: { kind: 'GAP_FILL', focus: 'PREPOSITION' },
    checks: ['COLLOCATION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Direnç olmadan / dirençsiz (without resistance) akmayı belirten doğru edatı seçin.',
    skills: ['COLLOCATION_PREPOSITION'],
    choices: [
      ['against', 'Move against resistance dirençle karşılaşmayı belirtir, süperiletkenlikle çelişir.', ['POLARITY_INVERSION'], ['COLLOCATION']],
      ['without', 'Move without resistance süperiletkenliğin sıfır direnç özelliğini tam karşılar.', [], []],
      ['into', 'Move into resistance hatalı edat tamlamasıdır.', ['FALSE_FRIEND'], ['COLLOCATION']],
      ['over', 'Move over resistance fiziksel akış bağlamında kullanılmaz.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['beneath', 'Move beneath direncin altında kalmak anlamsızdır.', ['UNSUPPORTED_DETAIL'], ['COLLOCATION']],
    ],
  }),

  // GAP FILL 4 - Preposition (Medicine)
  make({
    id: 'b6-gap-prep-2', family: 'GAP_FILL', domain: 'medicine',
    stem: 'The novel immunotherapy drug is designed to interfere ____ the signaling pathways that allow cancer cells to evade immune detection.',
    correct: 'D',
    tactical: { kind: 'GAP_FILL', focus: 'PREPOSITION' },
    checks: ['COLLOCATION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Interfere fiili ile sinyal yolağını engelleme bağlamında kullanılan edatı (with) seçin.',
    skills: ['COLLOCATION_PREPOSITION'],
    choices: [
      ['for', 'Interfere for bir amaca yönelik engelleme için standart kullanım değildir.', ['FALSE_FRIEND'], ['COLLOCATION']],
      ['at', 'Interfere at yer belirtmez, akademik dilde kullanılmaz.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['from', 'Interfere from kaynak belirtmez.', ['FALSE_FRIEND'], ['COLLOCATION']],
      ['with', 'Interfere with (müdahale etmek/engellemek) standart akademik kollokasyondur.', [], []],
      ['about', 'Interfere about biyolojik sinyal yolaklarına uymaz.', ['UNSUPPORTED_DETAIL'], ['COLLOCATION']],
    ],
  }),

  // GAP FILL 5 - Grammar (Tense/Aspect - Astronomy)
  make({
    id: 'b6-gap-grammar-1', family: 'GAP_FILL', domain: 'astronomy',
    stem: 'Since the launch of the James Webb Space Telescope in 2021, astrophysicists ____ unprecedented atmospheric data from dozens of distant exoplanets.',
    correct: 'E',
    tactical: {
      kind: 'GAP_FILL', focus: 'GRAMMAR',
      temporal: {
        temporal_anchor: 'Since the launch in 2021: geçmişten günümüze süreç',
        event_order: 'fırlatmadan günümüze kadar devam eden veri toplama süreci',
        tense_aspect: 'present perfect',
        context: 'Geçmişte başlayıp günümüze kadar gelen bilimsel veri toplama süreci.',
      },
    },
    checks: ['TENSE_ASPECT', 'VOICE', 'REDUCTION', 'MODALITY', 'CLAUSE_RELATION', 'TEMPORAL_CONTEXT'],
    triage: 'Since + geçmiş zaman noktası ile ana cümlede Present Perfect zaman uyumu aranır.',
    skills: ['TENSE_ASPECT'],
    choices: [
      ['gathered', 'Simple past, since ile başlayan süreçle uyumsuzdur.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'TEMPORAL_CONTEXT']],
      ['will gather', 'Gelecek zaman geçmişten bugüne gelen since bağlacıyla çelişir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
      ['had gathered', 'Past perfect geçmişteki başka bir olaydan öncesini gerektirir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'TEMPORAL_CONTEXT']],
      ['are gathering', 'Present continuous since kalıbında sürecin tamamını karşılamaz.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
      ['have gathered', 'Have gathered, 2021 den bu yana devam eden veri toplama sürecini tam olarak yansıtır.', [], []],
    ],
  }),

  // GAP FILL 6 - Grammar (Tense/Aspect - Climate)
  make({
    id: 'b6-gap-grammar-2', family: 'GAP_FILL', domain: 'environment',
    stem: 'Before the industrial revolution began in the mid-eighteenth century, atmospheric carbon dioxide concentrations ____ relatively stable for millennia.',
    correct: 'B',
    tactical: {
      kind: 'GAP_FILL', focus: 'GRAMMAR',
      temporal: {
        temporal_anchor: 'Before the industrial revolution began (geçmişte bir referans noktası)',
        event_order: 'Sanayi devriminden önceki bin yıllar boyunca süren kararlılık',
        tense_aspect: 'past perfect',
        context: 'Geçmişteki bir başlangıçtan da önce gerçekleşen ve süregelen durum.',
      },
    },
    checks: ['TENSE_ASPECT', 'VOICE', 'REDUCTION', 'MODALITY', 'CLAUSE_RELATION', 'TEMPORAL_CONTEXT'],
    triage: 'Before + simple past yapısı ana cümlede daha önceki durumu belirten Past Perfect gerektirir.',
    skills: ['TENSE_ASPECT'],
    choices: [
      ['remain', 'Geniş zaman geçmişteki sanayi öncesi döneme uymaz.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
      ['had remained', 'Past perfect, sanayi devriminden önceki bin yıllarca süren durumu doğru zaman ilişkisiyle ifade eder.', [], []],
      ['will have remained', 'Future perfect geleceğe aittir, geçmiş tarihle çelişir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'TEMPORAL_CONTEXT']],
      ['are remaining', 'Şimdiki zaman geçmişteki referans noktasıyla uyumsuzdur.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
      ['have remained', 'Present perfect günümüze uzanan süreci anlatır, sanayi öncesiyle sınırlı değildir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
    ],
  }),

  // GAP FILL 7 - Voice/Reduction (Biology)
  make({
    id: 'b6-gap-reduction-1', family: 'GAP_FILL', domain: 'biology',
    stem: 'Stem cells ____ in specialized culture media can differentiate into a wide variety of mature somatic cell types.',
    correct: 'C',
    tactical: { kind: 'GAP_FILL', focus: 'STRUCTURE' },
    checks: ['REDUCTION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Kültür ortamında yetiştirilen kök hücreler ifadesinde edilgen kısaltmayı (grown / maintained) bulun.',
    skills: ['VOICE_REDUCTION'],
    choices: [
      ['growing', 'Etken sıfat-fiil kök hücrelerin ortamı yetiştirdiği anlamını verir, yanlıştır.', ['SEMANTIC_ROLE_SWAP'], ['REDUCTION']],
      ['to grow', 'Amaç veya gelecek bildiren mastar yapısı bu nitelemeye uymaz.', ['FALSE_FRIEND'], ['REDUCTION']],
      ['grown', 'Geçmiş zaman ortacı (participle) edilgen kısaltma sağlayarak yetiştirilen kök hücreler anlamını verir.', [], []],
      ['having grown', 'Öncelik bildiren etken yapı nesne almadığı için anlamsızdır.', ['CAUSE_EFFECT_REVERSAL'], ['REDUCTION']],
      ['grow', 'Yalın fiil iki ana yüklem oluşturarak cümle yapısını bozar.', ['SCOPE_DRIFT'], ['CLAUSE_COMPATIBILITY']],
    ],
  }),

  // GAP FILL 8 - Voice/Reduction (Engineering)
  make({
    id: 'b6-gap-reduction-2', family: 'GAP_FILL', domain: 'engineering',
    stem: 'Composite materials ____ for aerospace applications must undergo rigorous testing to ensure structural integrity under extreme vibrations.',
    correct: 'A',
    tactical: { kind: 'GAP_FILL', focus: 'STRUCTURE' },
    checks: ['REDUCTION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Havacılık uygulamaları için geliştirilen/üretilen kompozit malzemeler anlamında edilgen kısaltmayı seçin.',
    skills: ['VOICE_REDUCTION'],
    choices: [
      ['developed', 'Edilgen kısaltma (which are developed yerine developed) doğru niteleme sağlar.', [], []],
      ['developing', 'Etken kısaltma malzemelerin uygulamaları geliştirdiği anlamına gelir.', ['SEMANTIC_ROLE_SWAP'], ['REDUCTION']],
      ['develop', 'Çekimli fiil kullanılması ikinci bir yüklem yaratarak sözdizimini bozar.', ['SCOPE_DRIFT'], ['CLAUSE_COMPATIBILITY']],
      ['having developed', 'Etken öncelik yapısı edilgen bağlamda geçersizdir.', ['CAUSE_EFFECT_REVERSAL'], ['REDUCTION']],
      ['to develop', 'Gelecek/amaç yapısı tamamlanmış tasarımı nitelemez.', ['FALSE_FRIEND'], ['REDUCTION']],
    ],
  }),

  // GAP FILL 9 - Connector (Medicine)
  make({
    id: 'b6-gap-conn-1', family: 'GAP_FILL', domain: 'medicine',
    stem: 'Early diagnosis significantly improves patient survival rates; ____, many forms of pancreatic cancer remain undetectable until advanced stages.',
    correct: 'D',
    tactical: { kind: 'GAP_FILL', focus: 'CONNECTOR' },
    checks: ['DISCOURSE_RELATION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Erken teşhisin önemi ile pankreas kanserinin geç fark edilmesi arasındaki zıtlığı bağlayan geçiş zarfını bulun.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['furthermore', 'Ek bilgi değil zıtlık ilişkisi vardır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['therefore', 'Sonuç değil karşıt bir durum ifade edilmektedir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['similarly', 'Benzerlik değil olumlu ve olumsuz iki durumun tezatı söz konusudur.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['nevertheless', 'Nevertheless iki bağımsız cümle arasındaki zıtlığı doğru şekilde bağlar.', [], []],
      ['consequently', 'Sonuç bildiren bağlaç erken teşhisin faydasının sonucu olamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
    ],
  }),

  // GAP FILL 10 - Connector (Environment)
  make({
    id: 'b6-gap-conn-2', family: 'GAP_FILL', domain: 'environment',
    stem: 'Wetlands filter environmental toxins and prevent coastal erosion; ____, they provide indispensable breeding grounds for diverse migratory birds.',
    correct: 'B',
    tactical: { kind: 'GAP_FILL', focus: 'CONNECTOR' },
    checks: ['DISCOURSE_RELATION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Sulak alanların faydalarına bir başka ek fayda ekleyen ekleme bağlacını (in addition / moreover) bulun.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['on the contrary', 'Zıtlık değil aynı doğrultuda ek fayda bildirilmektedir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['in addition', 'In addition önceki faydalara paralel olarak yeni bir ekolojik fayda ekler.', [], []],
      ['otherwise', 'Aksi takdirde koşul anlamı bağlama uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['in contrast', 'Zıtlık bildiren bağlaç paralel faydalar arasında kullanılamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['instead', 'Yerine geçme değil iki faydanın bir arada bulunması anlatılmaktadır.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 1 - Chemistry (Catalysts)
  make({
    id: 'b6-cloze-1', family: 'CLOZE_TEST', domain: 'chemistry',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Heterogeneous catalysts operate in a different phase from the reactants. ____, solid catalysts facilitate reactions among gaseous or liquid reagents while remaining easy to separate after the reaction. This operational convenience makes them indispensable in petrochemistry.',
    correct: 'A',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Heterogeneous catalysts operate in a different phase from the reactants.',
      target_sentence: '____, solid catalysts facilitate reactions among gaseous or liquid reagents while remaining easy to separate after the reaction.',
      next_sentence: 'This operational convenience makes them indispensable in petrochemistry.',
      macro_context: 'Heterogeneous catalysis phase explanation',
      relation: 'RESULT',
      candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'CONCESSION', D: 'CONDITION', E: 'ADDITION' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Farklı fazda çalışmanın doğrudan sonucu katı katalizörün sıvı/gazdan kolayca ayrılmasıdır.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Consequently', 'Farklı fazda bulunmanın mantıksal sonucu olarak kolay ayrılmasını tam olarak bağlar.', [], []],
      ['Conversely', 'Zıtlık ilişkisi metnin açıklayıcı akışına uymaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['Although', 'Ödünleme bağlacı bağımsız cümle başında tek başına kullanılamaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Unless', 'Koşul ilişkisi bağlama uymaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['In contrast', 'Karşıtlık değil açıklayıcı sonuç ilişkisi mevcuttur.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 2 - Biology (CRISPR)
  make({
    id: 'b6-cloze-2', family: 'CLOZE_TEST', domain: 'biology',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'CRISPR-Cas9 gene editing allows researchers to alter DNA sequences with unmatched precision. ____, off-target mutations remain a critical safety concern in therapeutic applications. Continued improvements in enzyme fidelity are therefore essential.',
    correct: 'C',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'CRISPR-Cas9 gene editing allows researchers to alter DNA sequences with unmatched precision.',
      target_sentence: '____, off-target mutations remain a critical safety concern in therapeutic applications.',
      next_sentence: 'Continued improvements in enzyme fidelity are therefore essential.',
      macro_context: 'CRISPR precision versus safety concerns',
      relation: 'CONTRAST',
      candidate_relations: { A: 'RESULT', B: 'ADDITION', C: 'CONTRAST', D: 'CONDITION', E: 'RESULT' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Hassas düzenleme başarısı ile hedef dışı mutasyon endişesi arasındaki zıtlığı bağlayan kelimeyi seçin.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Hence', 'Sonuç bildiren bağlaç olumlu yetenekten olumsuz endişeye geçişi açıklayamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Furthermore', 'Ek bilgi değil güçlü bir sınırlama ve zıtlık sunulmaktadır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['However', 'However yüksek hassasiyet ile hedef dışı mutasyon riski arasındaki zıtlığı kusursuz bağlar.', [], []],
      ['Provided that', 'Koşul bildiren bağlaç bağımsız cümle akışına uymaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Therefore', 'Neden-sonuç ilişkisi zıtlığın yerini tutamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 3 - Physics (Thermodynamics)
  make({
    id: 'b6-cloze-3', family: 'CLOZE_TEST', domain: 'physics',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'The second law of thermodynamics establishes that the entropy of an isolated system always increases over time. ____, natural processes are fundamentally irreversible and possess an inherent directionality. This concept is often referred to as the arrow of time.',
    correct: 'E',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'The second law of thermodynamics establishes that the entropy of an isolated system always increases over time.',
      target_sentence: '____, natural processes are fundamentally irreversible and possess an inherent directionality.',
      next_sentence: 'This concept is often referred to as the arrow of time.',
      macro_context: 'Entropy and irreversibility of natural processes',
      relation: 'RESULT',
      candidate_relations: { A: 'CONTRAST', B: 'CONCESSION', C: 'CONDITION', D: 'ADDITION', E: 'RESULT' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Entropi artışının doğrudan sonucu olarak süreçlerin geri döndürülemez olduğunu bağlayan ifadeyi bulun.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Nonetheless', 'Zıtlık ilişkisi teorik yasa ile sonucu arasına konulamaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['Even though', 'Giriş bağlacı bağımsız cümle yapısıyla uyumsuzdur.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Unless', 'Koşul ilişkisi nedenselliği bozar.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['In addition', 'Ekleme yerine doğrudan mantıksal sonuç vurgulanmaktadır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['As a result', 'As a result artan entropinin doğal süreçleri geri döndürülemez kılma sonucunu tam ifade eder.', [], []],
    ],
  }),

  // CLOZE TEST 4 - Environment (Permafrost)
  make({
    id: 'b6-cloze-4', family: 'CLOZE_TEST', domain: 'environment',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Thawing Arctic permafrost releases ancient organic matter to microbial decomposition. ____, massive amounts of methane and carbon dioxide enter the atmosphere, intensifying global heating. This positive feedback loop threatens climate stabilization targets.',
    correct: 'B',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Thawing Arctic permafrost releases ancient organic matter to microbial decomposition.',
      target_sentence: '____, massive amounts of methane and carbon dioxide enter the atmosphere, intensifying global heating.',
      next_sentence: 'This positive feedback loop threatens climate stabilization targets.',
      macro_context: 'Permafrost thaw releasing greenhouse gases',
      relation: 'RESULT',
      candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'CONDITION', D: 'CONCESSION', E: 'ADDITION' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Mikrobiyal ayrışmanın sonucu olarak metan ve karbondioksitin atmosfere salınmasını bağlayın.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['In contrast', 'Zıtlık bildiren bağlaç organik madde ayrışması ile gaz salımı arasına uymaz.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['As a consequence', 'As a consequence ayrışmanın kaçınılmaz sonucu olarak sera gazı salınımını doğru bağlar.', [], []],
      ['Only if', 'Koşul ilişkisi gerçekleşmekte olan fiziksel süreci yansıtmaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Despite this', 'Zıtlık veya ödünleme durumu metinde yoktur.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['Whereas', 'İki zıt durumu kıyaslayan bağlaç tek cümle başında kullanılamaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 5 - Medicine (Antibiotic Resistance)
  make({
    id: 'b6-cloze-5', family: 'CLOZE_TEST', domain: 'medicine',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Overuse of broad-spectrum antibiotics in livestock accelerates the evolution of resistant bacterial strains. ____, pharmaceutical companies have significantly reduced investment in developing new antimicrobial compounds. This dual trend has generated an escalating public health crisis.',
    correct: 'D',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Overuse of broad-spectrum antibiotics in livestock accelerates the evolution of resistant bacterial strains.',
      target_sentence: '____, pharmaceutical companies have significantly reduced investment in developing new antimicrobial compounds.',
      next_sentence: 'This dual trend has generated an escalating public health crisis.',
      macro_context: 'Dual challenges in antibiotic resistance',
      relation: 'ADDITION',
      candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'CONDITION', D: 'ADDITION', E: 'RESULT' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Dirençli bakterilerin artışına ek olarak şirketlerin yatırımı azaltması (ikili trend) ekleme bağlacı gerektirir.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Therefore', 'İlaç şirketlerinin yatırımı kesmesi dirençli bakterilerin doğrudan sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['On the other hand', 'Tam bir zıtlık değil krizin ikinci bir boyutunu ekleyen durum vardır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Provided that', 'Koşul bağlacı metin akışını bozar.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Simultaneously', 'Simultaneously / At the same time iki paralel olumsuz trendi birleştiren ekleme ve zaman bağı kurar.', [], []],
      ['Hence', 'Neden-sonuç ilişkisi yatırım çekilmesini gerekçelendirmez.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
    ],
  }),

  // CLOZE TEST 6 - Technology (Quantum Computing)
  make({
    id: 'b6-cloze-6', family: 'CLOZE_TEST', domain: 'technology',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Classical bits can only exist in a state of either zero or one. ____, quantum bits or qubits can exist in a superposition of both states at the same time. This fundamental distinction enables quantum processors to evaluate exponential possibilities concurrently.',
    correct: 'A',
    tactical: {
      kind: 'CLOZE_TEST',
      previous_sentence: 'Classical bits can only exist in a state of either zero or one.',
      target_sentence: '____, quantum bits or qubits can exist in a superposition of both states at the same time.',
      next_sentence: 'This fundamental distinction enables quantum processors to evaluate exponential possibilities concurrently.',
      macro_context: 'Classical bits versus quantum bits comparison',
      relation: 'CONTRAST',
      candidate_relations: { A: 'CONTRAST', B: 'RESULT', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' },
    },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Klasik bitler ile kuantum bitler arasındaki keskin karşıtlığı (zıtlığı) bağlayan kelimeyi seçin.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['In contrast', 'In contrast klasik bitler ile kübitlerin çalışma prensipleri arasındaki karşıtlığı tam olarak sunar.', [], []],
      ['Accordingly', 'Sonuç bildiren bağlaç iki karşıt prensip arasına uymaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Besides', 'Ek bilgi değil doğrudan kıyaslama ve zıtlık söz konusudur.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['As long as', 'Koşul yapısı iki mimari arasındaki yapısal farkı bağlayamaz.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['Thus', 'Kübitlerin süperpozisyonda olması klasik bitlerin sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
    ],
  }),
]);
