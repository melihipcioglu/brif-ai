import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, anchors } from './authoringUtils';

export const batch1Questions: readonly Question[] = deepFreeze([
  // GAP FILL 1 - Vocab
  make({
    id: 'b1-gap-vocab-1', family: 'GAP_FILL', domain: 'biology',
    stem: 'Prolonged exposure to microgravity can ____ bone density in astronauts during extended space missions.',
    correct: 'A',
    tactical: { kind: 'GAP_FILL', focus: 'VOCAB' },
    checks: ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB'],
    triage: 'Uzun süreli yerçekimsiz ortamın kemik yoğunluğu üzerindeki olumsuz etkisini belirten fiili bulun.',
    skills: ['VOCAB_CONTEXT'], lexical: ['diminish', 'decrease', 'microgravity'],
    choices: [
      ['decrease', 'Yerçekimsiz ortamın kemik yoğunluğunu azaltması beklenen bir durumdur.', [], []],
      ['enhance', 'Kemik yoğunluğunu artırması yerçekimsiz ortamın bilinen etkisine zıttır.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
      ['replicate', 'Kemik yoğunluğunu kopyalamak anlamsızdır.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_FIT']],
      ['sustain', 'Yoğunluğu korumak veya sürdürmek yerçekimsiz ortamda gerçekleşmez.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
      ['formulate', 'Kemik yoğunluğu formüle edilecek soyut bir kavram değildir.', ['SCOPE_DRIFT'], ['COLLOCATION']]
    ]
  }),
  // GAP FILL 2 - Grammar
  make({
    id: 'b1-gap-grammar-1', family: 'GAP_FILL', domain: 'physics',
    stem: 'By the time the new particle accelerator becomes fully operational, researchers ____ the preliminary data for over two years.',
    correct: 'C',
    tactical: { kind: 'GAP_FILL', focus: 'GRAMMAR', temporal: { temporal_anchor: 'becomes operational: gelecek referansı', event_order: 'veri toplama gelecekteki o noktaya kadar sürmüş olacak', tense_aspect: 'future perfect continuous', context: 'Gelecekteki bir noktada ne kadar süredir devam ediyor olacağı vurgulanıyor.' } },
    checks: ['TENSE_ASPECT', 'VOICE', 'REDUCTION', 'MODALITY', 'CLAUSE_RELATION', 'TEMPORAL_CONTEXT'],
    triage: 'By the time + simple present (gelecek anlamı) ve for over two years (süreklilik) birleşimi future perfect continuous gerektirir.',
    skills: ['TENSE_ASPECT'],
    choices: [
      ['analyzed', 'Geçmiş zaman, gelecekteki referans noktasıyla uyumsuzdur.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'TEMPORAL_CONTEXT']],
      ['are analyzing', 'Şimdiki zaman süreci gelecekteki hedef noktaya taşımaz.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
      ['will have been analyzing', 'Gelecekteki bir noktaya kadar sürmüş ve devam ediyor olacak eylemi tam olarak karşılar.', [], []],
      ['had analyzed', 'Past perfect geçmişteki bir noktadan öncesini belirtir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'TEMPORAL_CONTEXT']],
      ['analyze', 'Geniş zaman for over two years süreciyle uyumsuzdur.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']]
    ]
  }),
  // GAP FILL 3 - Preposition
  make({
    id: 'b1-gap-prep-1', family: 'GAP_FILL', domain: 'technology',
    stem: 'Current battery technologies are heavily dependent ____ rare earth metals such as lithium and cobalt.',
    correct: 'B',
    tactical: { kind: 'GAP_FILL', focus: 'PREPOSITION' },
    checks: ['COLLOCATION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Dependent sıfatının aldığı doğru edatı seçin.',
    skills: ['COLLOCATION_PREPOSITION'],
    choices: [
      ['at', 'Dependent at akademik bir kullanım değildir.', ['FALSE_FRIEND'], ['COLLOCATION']],
      ['on', 'Dependent on bir şeye bağlı/bağımlı olmayı ifade eden standart akademik yapıdır.', [], []],
      ['with', 'Dependent with birliktelik belirtmez.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['for', 'Dependent for amaç belirtse de genel bağımlılıkta kullanılmaz.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['from', 'Independent from ile karıştırılabilir, dependent from yaygın değildir.', ['FALSE_FRIEND'], ['COLLOCATION']]
    ]
  }),
  // GAP FILL 4 - Connector
  make({
    id: 'b1-gap-conn-1', family: 'GAP_FILL', domain: 'medicine',
    stem: 'Antibiotics are effective against bacterial infections, ____ they have no impact on viral diseases like the flu.',
    correct: 'A',
    tactical: { kind: 'GAP_FILL', focus: 'CONNECTOR' },
    checks: ['DISCOURSE_RELATION', 'CLAUSE_COMPATIBILITY'],
    triage: 'Bakterilere etki etmesi ile virüslere etki etmemesi arasındaki zıtlığı bağlayan kelimeyi bulun.',
    skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['but', 'İki zıt durumu birbirine bağlayan temel zıtlık bağlacıdır.', [], []],
      ['because', 'Virüslere etki etmemesi, bakterilere etki etmesinin nedeni değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['so', 'Zıtlık yerine sonuç belirtir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['unless', 'Koşul ilişkisi anlamı bozar.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['for instance', 'Örneklendirme yapısı iki ana cümleyi bu şekilde bağlamaz.', ['PARTIAL_TRUTH'], ['CLAUSE_COMPATIBILITY']]
    ]
  }),
  // SENTENCE COMPLETION 1
  make({
    id: 'b1-sentence-1', family: 'SENTENCE_COMPLETION', domain: 'geology',
    stem: 'Although earthquakes cannot be accurately predicted with current technology, ____.',
    correct: 'A',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Tahmin edilememesine rağmen (olumsuz) alınan önlemler veya olumlu bir zıtlık durumu aranmalıdır.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['early warning systems can give people a few seconds to seek cover', 'Tahmin edilememesine rağmen kısa süreli uyarı sistemlerinin varlığı zıtlığı tamamlar.', [], []],
      ['they are caused by the sudden release of energy in the Earth\'s crust', 'Depremin nedeni zıtlık (although) bağlacıyla uyuşmaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['scientists have stopped trying to monitor tectonic plate movements', 'Tamamen vazgeçmeleri although zıtlığına değil, bir sonuca işaret eder.', ['FALSE_FRIEND'], ['DISCOURSE_RELATION']],
      ['most of them happen deep within the ocean floor', 'Nerede oldukları tahmin edilememe gerçeğiyle zıtlık oluşturmaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['there is no way to measure their magnitude accurately', 'Şiddet ölçümü ile tahmin farklı şeylerdir ve zıtlık ilişkisi kurmaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']]
    ]
  }),
  // PARAGRAPH COMPLETION 1
  make({
    id: 'b1-para-comp-1', family: 'PARAGRAPH_COMPLETION', domain: 'physics',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Superconductors are materials that can conduct electricity with zero resistance. When cooled below a characteristic critical temperature, their electrical resistance vanishes entirely. ____. Consequently, this remarkable property allows for the creation of powerful electromagnets used in MRI machines.',
    correct: 'C',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CAUSE', C: 'RESULT', D: 'ADDITION', E: 'RESULT' }, anchors: anchors('C') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Sıfır dirençten sonra ve MRI makinelerindeki elektromıknatısların oluşumundan (consequently) önceki köprü cümleyi bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['This makes them highly inefficient for everyday electrical grids.', 'Verimsiz olmaları, güçlü mıknatıs yapılabilmesi sonucuyla (consequently) çelişir.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['Many materials require extremely high temperatures to become superconductors.', 'Paragrafta düşük sıcaklıktan (cooled) bahsedilmiştir, yüksek değil.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['As a result, they can carry large electrical currents without losing any energy as heat.', 'Isı kaybı olmadan akım taşıma yeteneği, sıfır direncin doğrudan sonucudur ve güçlü mıknatıs yapımına mantıksal zemin hazırlar.', [], []],
      ['The critical temperature for most superconductors is well above room temperature.', 'Oda sıcaklığının üzerinde oldukları bilgisi genellikle yanlıştır ve paragrafın akışını bozar.', ['UNSUPPORTED_DETAIL'], ['TOPIC']],
      ['Electricity can only be conducted if there is some resistance present.', 'Direnç olması gerektiği iddiası, paragrafın sıfır direnç ana fikriyle doğrudan çelişir.', ['FALSE_FRIEND'], ['PASSAGE_SUPPORT']]
    ]
  }),
  // IRRELEVANT SENTENCE 1
  make({
    id: 'b1-irrelevant-1', family: 'IRRELEVANT_SENTENCE', domain: 'chemistry',
    stem: 'Choose the irrelevant sentence in the paragraph.',
    passage: '(I) Water is considered a universal solvent due to its unique chemical properties. (II) Its polar molecular structure allows it to dissolve a wide variety of substances. (III) The boiling point of water is 100 degrees Celsius at standard atmospheric pressure. (IV) Because of this dissolving capability, it plays a vital role in biological processes. (V) For example, it transports dissolved nutrients and waste products within the human body.',
    correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Suyun çözücülük özelliği', discourse_function: 'Çözücülük temasına kaynama noktasının karışması' },
    checks: ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'],
    triage: 'Paragraf suyun "çözücü" (solvent) özelliğine odaklanmıştır, kaynama noktası konu dışıdır.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['I', 'Evrensel çözücü olduğu fikri paragrafın ana girişidir.', [], ['TOPIC']],
      ['II', 'Polar yapı çözücülük özelliğini açıklar (I. cümlenin devamı).', [], ['TOPIC']],
      ['III', 'Kaynama noktası bilgisi, paragrafın çözücülük temasına uymaz.', ['SCOPE_DRIFT'], []],
      ['IV', 'Çözücülük kapasitesinin biyolojik süreçlerdeki rolünü bağlar ("this dissolving capability").', [], ['LEXICAL_CONTINUITY']],
      ['V', 'IV. cümledeki biyolojik süreçlere (besin taşıma) doğrudan bir örnektir.', [], ['DISCOURSE_FUNCTION']]
    ]
  })
]);
