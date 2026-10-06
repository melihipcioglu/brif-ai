import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, anchors } from './authoringUtils';

export const batch2Questions: readonly Question[] = deepFreeze([
  // CLOZE TEST 1
  make({
    id: 'b2-cloze-1', family: 'CLOZE_TEST', domain: 'chemistry',
    stem: 'Choose the appropriate connector for the blank.',
    passage: 'Catalysts speed up chemical reactions without being consumed. ____, they can be recovered and reused multiple times. This makes them highly valuable in industrial processes.',
    correct: 'D',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Catalysts speed up chemical reactions without being consumed.', target_sentence: '____, they can be recovered and reused multiple times.', next_sentence: 'This makes them highly valuable in industrial processes.', macro_context: 'Catalyst reuse', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'CONCESSION', C: 'ADDITION', D: 'RESULT', E: 'CONDITION' } },
    checks: ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Tüketilmemesinin doğrudan sonucu olarak kurtarılabilmelerini bağlayın.',
    skills: ['COHESION_COHERENCE'],
    choices: [
      ['However', 'Zıtlık ilişkisi tüketilmeme ile yeniden kullanım arasında geçerli değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Even though', 'Zıtlık/ödünleme bağlacıdır.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['For instance', 'Örneklendirme, doğrudan sonucun önüne geçemez.', ['UNSUPPORTED_DETAIL'], ['DISCOURSE_RELATION']],
      ['Therefore', 'Tüketilmemelerinin bir sonucu (therefore) olarak yeniden kullanılabilirler.', [], []],
      ['Otherwise', 'Aksi takdirde anlamı cümlenin akışını bozar.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']]
    ]
  }),
  // CLOZE TEST 2
  make({
    id: 'b2-cloze-2', family: 'CLOZE_TEST', domain: 'physics',
    stem: 'Choose the appropriate word for the blank.',
    passage: 'Nuclear fusion requires extreme conditions. To initiate the reaction, temperatures ____ 100 million degrees Celsius are necessary. Scientists use magnetic fields to contain the plasma.',
    correct: 'C',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Nuclear fusion requires extreme conditions.', target_sentence: 'To initiate the reaction, temperatures ____ 100 million degrees Celsius are necessary.', next_sentence: 'Scientists use magnetic fields to contain the plasma.', macro_context: 'Fusion temps', relation: 'CONDITION', candidate_relations: { A: 'RESULT', B: 'RESULT', C: 'CONDITION', D: 'RESULT', E: 'RESULT' } },
    checks: ['REDUCTION', 'CONTINUATION', 'PASSAGE_SUPPORT'],
    triage: 'Aktif bir şekilde 100 milyon dereceyi aşan sıcaklıklar.',
    skills: ['VOICE_REDUCTION'],
    choices: [
      ['exceeded', 'Edilgen veya geçmiş zaman uyuşmaz.', ['SEMANTIC_ROLE_SWAP'], ['REDUCTION']],
      ['to exceed', 'Amaç bildiren mastar isme doğrudan bağlanmaz.', ['FALSE_FRIEND'], ['REDUCTION']],
      ['exceeding', '100 milyon dereceyi aşan (exceeding) sıcaklıklar anlamında aktif kısaltmadır.', [], []],
      ['having exceeded', 'Geçmişte aşmış anlamı genel durumla uyuşmaz.', ['TEMPORAL_MISMATCH'], ['REDUCTION']],
      ['exceed', 'Çekimli fiil cümlenin yapısını bozar.', ['PARTIAL_TRUTH'], ['CONTINUATION']]
    ]
  }),
  // GAP FILL 1
  make({
    id: 'b2-gap-vocab-1', family: 'GAP_FILL', domain: 'biology',
    stem: 'Genetic diversity allows a population to ____ to changing environmental conditions more effectively.',
    correct: 'B',
    tactical: { kind: 'GAP_FILL', focus: 'VOCAB' },
    checks: ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB'],
    triage: 'Çevresel koşullara ne yapılır?',
    skills: ['VOCAB_CONTEXT'], lexical: ['adapt'],
    choices: [
      ['surrender', 'Koşullara teslim olmak genetik çeşitliliğin avantajı olamaz.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
      ['adapt', 'Değişen koşullara uyum sağlamak (adapt) temel biyolojik mekanizmadır.', [], []],
      ['hesitate', 'Popülasyonlar koşullara tereddüt etmez.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_FIT']],
      ['ignore', 'Görmezden gelmek hayatta kalma stratejisi değildir.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
      ['object', 'Koşullara itiraz etmek anlamsızdır.', ['SCOPE_DRIFT'], ['COLLOCATION']]
    ]
  }),
  // SENTENCE COMPLETION 1
  make({
    id: 'b2-sentence-1', family: 'SENTENCE_COMPLETION', domain: 'environment',
    stem: 'Because deforestation destroys the natural habitats of countless species, ____.',
    correct: 'A',
    tactical: { kind: 'SENTENCE_COMPLETION', relation: 'RESULT', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'CONDITION', E: 'RESULT' } },
    checks: ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'],
    triage: 'Habitat tahribatının doğrudan bir sonucunu (olumsuz) bulun.',
    skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['it is one of the leading causes of biodiversity loss globally', 'Habitat kaybının doğrudan sonucu biyoçeşitlilik kaybıdır.', [], []],
      ['new tree planting initiatives are usually successful', 'Olumlu bir sonuç (başarı) tahribatın doğrudan fiziksel sonucu değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['many people prefer to live in urban areas', 'Kentleşme orman tahribatının biyolojik bir sonucu değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['they might adapt to the changes very quickly', 'Sayısız türün (countless species) hızla uyum sağlaması beklentilere zıttır.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['the timber industry has seen a massive increase in profits', 'Bu, ekonomik bir sonuçtur ve ekolojik krizin ana odak cümlesini tamamlamaz.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']]
    ]
  }),
  // PARAGRAPH COMPLETION 1
  make({
    id: 'b2-para-1', family: 'PARAGRAPH_COMPLETION', domain: 'medicine',
    stem: 'Choose the sentence that best completes the paragraph.',
    passage: 'Penicillin was discovered accidentally by Alexander Fleming in 1928. ____. It proved highly effective against various bacterial infections, saving countless lives during World War II.',
    correct: 'C',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'ADDITION', candidate_relations: { A: 'RESULT', B: 'CONTRAST', C: 'ADDITION', D: 'RESULT', E: 'ADDITION' }, anchors: anchors('C') },
    checks: ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'],
    triage: 'Keşiften (1928) sonraki aşama ile II. Dünya Savaşı kullanımı arasındaki bağlantıyı sağlayan ifadeyi bulun.',
    skills: ['PARAGRAPH_COMPLETION'],
    choices: [
      ['However, he immediately started selling it for a high price.', 'Ticari amaç metnin bilimsel/yardım odaklı tonuyla uyumsuz.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['Most bacteria today are completely immune to its effects.', 'Günümüz (today) zamanlaması II. Dünya Savaşı öncesine ait boşluğa uymaz.', ['TEMPORAL_MISMATCH'], ['PASSAGE_SUPPORT']],
      ['It took over a decade for other scientists to isolate and mass-produce it as a drug.', 'İzole edilip seri üretime geçilmesi, ardından savaşta kullanılması kronolojiyi mükemmel tamamlar.', [], []],
      ['He had intended to create a powerful painkiller rather than an antibiotic.', 'Orijinal niyetinin ağrıkesici olduğu bilgisi yalandır.', ['FALSE_FRIEND'], ['TOPIC']],
      ['Viruses were the main target of his initial laboratory experiments.', 'Bakteriyel (bacterial) bir enfeksiyon tedavi edildiği için virüsler alakasızdır.', ['SCOPE_DRIFT'], ['CONTINUATION']]
    ]
  })
]);
