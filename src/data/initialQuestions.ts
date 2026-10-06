import type { AnchorChain, CheckCriterion, DistractorPattern, OptionId, Question, SemanticRoleMap, TacticalMetadata } from '../types/question';
import { OPTION_IDS } from '../types/question';
import { questionSchema } from '../services/questions/validation';
import { deepFreeze } from '../services/questions/attempts';
import { tacticalSolvers } from '../services/questions/strategies';

/** All items are original practice material, not released ÖSYM questions. */
type Choice = readonly [text: string, reason: string, patterns: readonly DistractorPattern[], failed: readonly CheckCriterion[]];
interface Seed {
  readonly id: string; readonly family: Question['family']; readonly domain: string; readonly stem: string;
  readonly passage?: string; readonly correct: OptionId; readonly choices: readonly [Choice, Choice, Choice, Choice, Choice];
  readonly tactical: TacticalMetadata; readonly checks: readonly CheckCriterion[]; readonly triage: string;
  readonly skills: Question['skill_ids']; readonly lexical?: readonly string[];
}
function make(seed: Seed): Question {
  const analyses = seed.choices.map((choice, i) => {
    const id = OPTION_IDS[i];
    if (id === undefined) throw new Error('Invalid choice index');
    return { option_id: id, verdict: id === seed.correct ? 'CORRECT' as const : 'ELIMINATE' as const, reasons: [choice[1]], patterns: choice[2] };
  });
  const q = questionSchema.parse({
    id: seed.id, family: seed.family, science_domain: seed.domain, stem: seed.stem,
    ...(seed.passage === undefined ? {} : { passage: seed.passage }),
    ...(seed.tactical.kind === 'GAP_FILL' ? { subclass: seed.tactical.focus } : {}),
    options: seed.choices.map((choice, i) => ({ id: OPTION_IDS[i], text: choice[0] })), correct_option: seed.correct,
    tactical: seed.tactical, option_evidence: Object.fromEntries(seed.choices.map((choice, i) => [OPTION_IDS[i], seed.checks.map((criterion) => ({ criterion, matches: !choice[3].includes(criterion), evidence: choice[1] }))])),
    explanation: {
      triage: { summary: seed.triage, cues: [seed.tactical.kind === 'TRANSLATION' ? 'Eyleyen ve eylemi ayırın; kip ve kapsamı koruyun.' : seed.triage], checks: ['Bağlam kanıtını bulun.', 'Her adayı aynı anlam kontrollerinden geçirin.'] },
      option_analysis: analyses, verification: { summary: 'Doğru adayı cümleye veya metne geri yerleştirerek anlamı doğrulayın.', evidence: analyses.find((a) => a.option_id === seed.correct)?.reasons ?? [] },
      distractor_patterns: [...new Set(analyses.flatMap((a) => a.patterns))],
    },
    lexical_ids: seed.lexical ?? [], skill_ids: seed.skills, difficulty: 0.5, provenance: 'ORIGINAL_PRACTICE',
  });
  const solver = tacticalSolvers[q.family];
  const supported = solver.analyzeOptions(q, solver.triage(q)).filter((a) => a.verdict === 'CORRECT');
  if (supported.length !== 1 || supported[0]?.option_id !== q.correct_option) throw new Error(`Inconsistent authored evidence: ${q.id}`);
  return q;
}
const sentenceChecks: readonly CheckCriterion[] = ['DISCOURSE_RELATION', 'REFERENT', 'CLAUSE_COMPATIBILITY', 'CONTINUATION', 'TENSE_ASPECT', 'SCOPE'];
const clozeChecks: readonly CheckCriterion[] = ['DISCOURSE_RELATION', 'CONTINUATION', 'PASSAGE_SUPPORT'];
const readingChecks: readonly CheckCriterion[] = ['PASSAGE_SUPPORT', 'SEMANTIC_EQUIVALENCE', 'SCOPE', 'REFERENT', 'DISCOURSE_FUNCTION', 'TOPIC', 'CONTINUATION'];
const irrelevantChecks: readonly CheckCriterion[] = ['TOPIC', 'SCOPE', 'REFERENT', 'CHRONOLOGY', 'DISCOURSE_FUNCTION', 'LEXICAL_CONTINUITY'];
const strong: AnchorChain = { referent: 1, topic_continuity: 1, connector: 1, tense_aspect: 1, cause_effect: 1, lexical_chain: 1 };
const weak: AnchorChain = { referent: 0.2, topic_continuity: 0.2, connector: 0.3, tense_aspect: 0.8, cause_effect: 0.1, lexical_chain: 0.2 };
const anchors = (correct: OptionId): Readonly<Record<OptionId, AnchorChain>> => ({ A: correct === 'A' ? strong : weak, B: correct === 'B' ? strong : weak, C: correct === 'C' ? strong : weak, D: correct === 'D' ? strong : weak, E: correct === 'E' ? strong : weak });
const roles1: SemanticRoleMap = { agent: 'scientists', action: 'detect', patient: 'small-planets', voice: 'ACTIVE', modality: 'may', polarity: 'positive', time: 'present', propositions: ['with-new-sensor'] };
const roles2: SemanticRoleMap = { agent: 'roots', action: 'absorb', patient: 'water', voice: 'ACTIVE', polarity: 'positive', condition: 'soil-moist', degree: 'more-quickly', propositions: [] };
const roles3: SemanticRoleMap = { agent: 'researchers', action: 'measure', patient: 'temperature', voice: 'ACTIVE', time: 'past', degree: 'twice', propositions: ['before-reaction'] };
const roles4: SemanticRoleMap = { agent: 'thick-clouds', action: 'reduce', patient: 'surface-sunlight', voice: 'ACTIVE', modality: 'can', polarity: 'positive', propositions: [] };

export const initialQuestions: readonly Question[] = deepFreeze([
  make({ id: 'gap-vocab', family: 'GAP_FILL', domain: 'medicine',
    stem: 'Because the compound can inhibit bacterial growth, it is expected to ____ the spread of infection.', correct: 'B',
    tactical: { kind: 'GAP_FILL', focus: 'VOCAB' }, checks: ['SEMANTIC_FIT', 'COLLOCATION', 'SUBJECT_VERB'],
    triage: 'Büyümeyi baskılama ile yayılımı azaltma arasındaki neden-sonuç bağını bulun.', skills: ['VOCAB_CONTEXT'], lexical: ['inhibit', 'diminish'],
    choices: [
      ['accelerate', 'Hızlandırmak, büyümeyi baskılayan etkiyle çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_FIT']],
      ['diminish', 'Yayılımı azaltmak, bakteriyel büyümenin baskılanmasının beklenen sonucudur.', [], []],
      ['trigger', 'Yayılımı başlatmak verilen koruyucu etkiyi tersine çevirir.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_FIT']],
      ['maintain', 'Yayılımı aynı düzeyde tutma sonucu metinde desteklenmiyor.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_FIT']],
      ['overlook', 'Bir bileşik yayılımı gözden kaçıran bilinçli bir özne değildir.', ['SEMANTIC_ROLE_SWAP'], ['SUBJECT_VERB', 'SEMANTIC_FIT']],
    ] }),
  make({ id: 'gap-grammar', family: 'GAP_FILL', domain: 'geology', stem: 'By the time the survey team arrived, the lava ____ enough for samples to be collected.', correct: 'D',
    tactical: { kind: 'GAP_FILL', focus: 'GRAMMAR', temporal: { temporal_anchor: 'arrived: geçmiş varış', event_order: 'soğuma, varıştan önce tamamlanır', tense_aspect: 'past perfect', context: 'Örnek alınabilecek kadar soğuma tamamlanmış bir önkoşuldur.' } },
    checks: ['TENSE_ASPECT', 'VOICE', 'REDUCTION', 'MODALITY', 'CLAUSE_RELATION', 'TEMPORAL_CONTEXT'], triage: 'Tek zaman sözcüğüne değil; varış, tamamlanma ve soğuma sırasına bakın.', skills: ['TENSE_ASPECT'],
    choices: [
      ['will cool', 'Gelecek soğuma, geçmişte gerçekleşmiş örnek toplama önkoşulunu karşılamaz.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'TEMPORAL_CONTEXT']],
      ['is cooling', 'Şimdiki süreç, geçmişte tamamlanan soğumayı ifade etmez.', ['TEMPORAL_MISMATCH'], ['TEMPORAL_CONTEXT']],
      ['must cool', 'Zorunluluk, geçmişte gerçekleşmiş tamamlanmanın yerine geçmez.', ['UNSUPPORTED_DETAIL'], ['MODALITY']],
      ['had cooled', 'Soğuma, ekibin geçmişteki varışından önce tamamlanmıştır.', [], []],
      ['has been cooled', 'Present perfect geçmiş referans noktasına bağlanmaz; ayrıca dışarıdan soğutma eklenir.', ['TEMPORAL_MISMATCH', 'SEMANTIC_ROLE_SWAP'], ['VOICE', 'TEMPORAL_CONTEXT']],
    ] }),
  make({ id: 'gap-preposition', family: 'GAP_FILL', domain: 'biology', stem: 'Young seedlings are particularly susceptible ____ fungal infection.', correct: 'A',
    tactical: { kind: 'GAP_FILL', focus: 'PREPOSITION' }, checks: ['COLLOCATION', 'CLAUSE_COMPATIBILITY'], triage: 'Sıfatın zorunlu edatını isim öbeğiyle birlikte okuyun.', skills: ['COLLOCATION_PREPOSITION'],
    choices: [
      ['to', 'Susceptible to + isim öbeği, bir etkene yatkınlığı bildirir.', [], []],
      ['of', 'Susceptible of bu yatkınlık anlamındaki akademik kalıp değildir.', ['FALSE_FRIEND'], ['COLLOCATION']],
      ['by', 'By etkeni gösterse de susceptible sıfatının bu kalıbını tamamlamaz.', ['PARTIAL_TRUTH'], ['COLLOCATION']],
      ['at', 'At yer veya hedef çağrıştırabilir; burada sıfatın edat gereksinimine uymaz.', ['SCOPE_DRIFT'], ['COLLOCATION']],
      ['with', 'Birliktelik anlamı, enfeksiyona yatkınlık ilişkisini kurmaz.', ['SCOPE_DRIFT'], ['COLLOCATION']],
    ] }),
  make({ id: 'gap-connector', family: 'GAP_FILL', domain: 'physics', stem: 'The detector remained accurate ____ the laboratory temperature varied considerably.', correct: 'C',
    tactical: { kind: 'GAP_FILL', focus: 'CONNECTOR' }, checks: ['DISCOURSE_RELATION', 'CLAUSE_COMPATIBILITY'], triage: 'Beklenen bozulmaya rağmen doğruluk sürüyor: ödünleme ilişkisi.', skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['because', 'Sıcaklık değişimi doğruluğun nedeni olarak sunulmuyor.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['so that', 'Sıcaklık değişimi dedektör doğruluğunun amacı değildir.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['although', 'Ödünleme, sıcaklık değişimine rağmen doğruluğun korunmasını açıklar.', [], []],
      ['unless', 'Gerçekleşen değişimi koşula dönüştürür.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['therefore', 'Therefore bu konumda iki çekimli cümleyi bağlayan yan cümle bağlacı değildir.', ['PARTIAL_TRUTH'], ['CLAUSE_COMPATIBILITY']],
    ] }),
  make({ id: 'gap-structure', family: 'GAP_FILL', domain: 'chemistry', stem: 'The samples ____ in sealed containers showed no measurable loss of mass.', correct: 'E',
    tactical: { kind: 'GAP_FILL', focus: 'STRUCTURE' }, checks: ['REDUCTION', 'CLAUSE_COMPATIBILITY'], triage: 'Ana yüklem showed; boşluk samples öznesini edilgen bir kısaltmayla niteler.', skills: ['VOICE_REDUCTION'],
    choices: [
      ['were stored', 'İkinci çekimli yüklem bağlaç olmadan ana yükleme eklenemez.', ['PARTIAL_TRUTH'], ['CLAUSE_COMPATIBILITY']],
      ['storing', 'Örnekler kapları depolayan değil, kaplarda saklanan nesnelerdir.', ['SEMANTIC_ROLE_SWAP'], ['REDUCTION']],
      ['have stored', 'Ek çekimli yüklem cümle yapısını bozar.', ['PARTIAL_TRUTH'], ['CLAUSE_COMPATIBILITY']],
      ['to storing', 'Bu yapı özneyi niteleyen geçerli kısaltılmış yan cümle değildir.', ['FALSE_FRIEND'], ['REDUCTION']],
      ['stored', 'Samples that were stored yapısının edilgen kısaltmasıdır.', [], []],
    ] }),
  make({ id: 'cloze-biology', family: 'CLOZE_TEST', domain: 'biology', stem: 'Choose the connector for the blank.',
    passage: 'The plants received equal amounts of water. ____ , the shaded group grew more slowly. The researchers therefore examined the effect of light.', correct: 'B',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'The plants received equal amounts of water.', target_sentence: '____ , the shaded group grew more slowly.', next_sentence: 'The researchers therefore examined the effect of light.', macro_context: 'Su eşit tutulurken ışık farkının büyümeyle ilişkisi araştırılıyor.', relation: 'CONCESSION', candidate_relations: { A: 'RESULT', B: 'CONCESSION', C: 'ADDITION', D: null, E: null } },
    checks: clozeChecks, triage: 'Önceki kontrol koşulu ile sonraki araştırma yönünü birlikte okuyun.', skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['Consequently', 'Eşit su verilmesi tek başına gölgeli grubun yavaşlamasını açıklamaz.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Nevertheless', 'Eşit suya rağmen büyüme farkı vardır; sonraki ışık araştırmasına bağlanır.', [], []],
      ['Similarly', 'Büyüme benzerliği değil, gruplar arası fark veriliyor.', ['POLARITY_INVERSION'], ['CONTINUATION']],
      ['For instance', 'Yavaş büyüme, eşit su miktarına örnek değildir.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['In other words', 'İkinci cümle ilk cümlenin yeniden ifadesi değildir.', ['PARTIAL_TRUTH'], ['SEMANTIC_FIT', 'CONTINUATION']],
    ] }),
  make({ id: 'cloze-astronomy', family: 'CLOZE_TEST', domain: 'astronomy', stem: 'Choose the connector for the blank.',
    passage: 'Clouds blocked the telescope for most of the night. ____ , fewer images were collected than planned. The team scheduled another observation period.', correct: 'D',
    tactical: { kind: 'CLOZE_TEST', previous_sentence: 'Clouds blocked the telescope for most of the night.', target_sentence: '____ , fewer images were collected than planned.', next_sentence: 'The team scheduled another observation period.', macro_context: 'Gözlem engeli veri kaybına, veri kaybı yeni gözlem planına yol açıyor.', relation: 'RESULT', candidate_relations: { A: 'CONTRAST', B: 'ADDITION', C: 'CONCESSION', D: 'RESULT', E: null } },
    checks: clozeChecks, triage: 'Engel → az görüntü → ek gözlem zincirindeki sonuç bağını seçin.', skills: ['CONNECTOR_DISCOURSE'],
    choices: [
      ['By contrast', 'İkinci cümle gözlem engeliyle karşıtlık değil sonuç ilişkisi taşır.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['Likewise', 'Birbirine paralel iki örnek değil, neden ve sonucu vardır.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
      ['Even so', 'Az görüntü, engele rağmen şaşırtıcı bir sonuç değildir.', ['POLARITY_INVERSION'], ['DISCOURSE_RELATION']],
      ['As a result', 'Bulutlar gözlemi sınırlamış, görüntü sayısı azalmıştır.', [], []],
      ['For example', 'Az görüntü bulutun örneği değil, gözlem engelinin sonucudur.', ['SCOPE_DRIFT'], ['DISCOURSE_RELATION']],
    ] }),
  make({ id: 'sentence-concession', family: 'SENTENCE_COMPLETION', domain: 'chemistry', stem: 'Although the catalyst accelerated the reaction, ____.', correct: 'A', tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONCESSION', candidate_relations: { A: 'CONCESSION', B: 'RESULT', C: null, D: null, E: null } }, checks: sentenceChecks,
    triage: 'Although ödünleme ister; hız artışıyla birlikte süren sınırlamayı arayın.', skills: ['SENTENCE_COMPLETION', 'CONNECTOR_DISCOURSE'],
    choices: [
      ['the final yield remained low', 'Hız artsa da verimin düşük kalması beklenen yararı sınırlar; ölçütler farklıdır.', [], []],
      ['it therefore accelerated the reaction', 'Aynı bilgiyi sonuç olarak tekrarlar; ödünleme kurulmaz.', ['PARTIAL_TRUTH'], ['DISCOURSE_RELATION']],
      ['all catalysts always produce pure products', 'Tek deneyden bütün katalizörlere ve saflığa genelleme yapılamaz.', ['EXTREME_QUALIFIER', 'SCOPE_DRIFT'], ['SCOPE']],
      ['the researchers had never used any instruments', 'Araç kullanılmadığına dair kanıt yoktur.', ['UNSUPPORTED_DETAIL'], ['CONTINUATION']],
      ['the reaction caused the catalyst to be discovered centuries earlier', 'Neden ve zaman sırası verilen bağlamdan çıkarılamaz.', ['TEMPORAL_MISMATCH', 'CAUSE_EFFECT_REVERSAL'], ['TENSE_ASPECT', 'CONTINUATION']],
    ] }),
  make({ id: 'sentence-condition', family: 'SENTENCE_COMPLETION', domain: 'environment', stem: 'If the wetland is drained, ____.', correct: 'C', tactical: { kind: 'SENTENCE_COMPLETION', relation: 'CONDITION', candidate_relations: { A: null, B: 'CAUSE', C: 'CONDITION', D: 'CONDITION', E: null } }, checks: sentenceChecks,
    triage: 'Koşulun habitat üzerindeki makul sonucunu ve kip uyumunu değerlendirin.', skills: ['SENTENCE_COMPLETION'],
    choices: [
      ['it was drained before any wetlands existed', 'Koşullu gelecek olasılığı yerine bağdaşmayan geçmiş iddiası kurar.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT', 'CONTINUATION']],
      ['because migratory birds use it', 'Ana sonuç cümlesi yerine bağımlı neden öbeği getirir.', ['PARTIAL_TRUTH'], ['CLAUSE_COMPATIBILITY']],
      ['some migratory birds may lose a feeding habitat', 'Sulak alanın kaybı bazı kuşlar için beslenme alanı kaybı oluşturabilir.', [], []],
      ['every bird species will immediately disappear', 'Tek habitat kaybı bütün türlerin hemen yok olmasını kanıtlamaz.', ['EXTREME_QUALIFIER', 'SCOPE_DRIFT'], ['SCOPE']],
      ['the planet must stop receiving sunlight', 'Yerel drenaj ile güneş ışığının kesilmesi arasında bağ yoktur.', ['UNSUPPORTED_DETAIL'], ['CONTINUATION']],
    ] }),
  make({ id: 'translation-eng-tr-sensor', family: 'TRANSLATION_ENG_TR', domain: 'astronomy', stem: 'Scientists may detect small planets with the new sensor.', correct: 'B', checks: ['SEMANTIC_EQUIVALENCE'],
    tactical: { kind: 'TRANSLATION', direction: 'ENG_TR', source: roles1, candidates: { A: { ...roles1, modality: 'must' }, B: roles1, C: { ...roles1, agent: 'small-planets', patient: 'scientists' }, D: { ...roles1, polarity: 'negative' }, E: { ...roles1, propositions: [] } } },
    triage: 'May olasılığını, bilim insanlarını ve yeni sensör aracını koruyun.', skills: ['TRANSLATION_SEMANTICS'], choices: [
      ['Bilim insanları yeni sensörle küçük gezegenleri tespit etmek zorundadır.', 'Olasılık zorunluluğa çevrilmiş.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
      ['Yeni sensörle bilim insanları küçük gezegenleri tespit edebilir.', 'Araç öbeği başa taşınsa da roller ve olasılık aynıdır.', [], []],
      ['Küçük gezegenler yeni sensörle bilim insanlarını tespit edebilir.', 'Eyleyen ve etkilenen yer değiştirmiş.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
      ['Bilim insanları yeni sensörle küçük gezegenleri tespit edemez.', 'Olumlu olasılık olumsuza çevrilmiş.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
      ['Bilim insanları küçük gezegenleri tespit edebilir.', 'Yeni sensör aracılığı bilgisi çıkarılmış.', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']],
    ] }),
  make({ id: 'translation-eng-tr-roots', family: 'TRANSLATION_ENG_TR', domain: 'biology', stem: 'Roots absorb water more quickly if the soil is moist.', correct: 'E', checks: ['SEMANTIC_EQUIVALENCE'],
    tactical: { kind: 'TRANSLATION', direction: 'ENG_TR', source: roles2, candidates: { A: { ...roles2, condition: 'soil-dry' }, B: { ...roles2, degree: 'more-slowly' }, C: { ...roles2, agent: 'water', patient: 'roots' }, D: { ...roles2, condition: undefined }, E: roles2 } },
    triage: 'Toprak nemi koşulunu ve karşılaştırmalı hız derecesini koruyun.', skills: ['TRANSLATION_SEMANTICS'], choices: [
      ['Toprak kuruysa kökler suyu daha hızlı emer.', 'Nemli olma koşulu kuru olma koşuluna çevrilmiş.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
      ['Toprak nemliyse kökler suyu daha yavaş emer.', 'Daha hızlı derecesi tersine çevrilmiş.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
      ['Toprak nemliyse su kökleri daha hızlı emer.', 'Eyleyen ve etkilenen ters çevrilmiş.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
      ['Kökler suyu daha hızlı emer.', 'Nem koşulu atılmış; koşullu önerme genelleştirilmiş.', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']],
      ['Toprak nemliyse kökler suyu daha hızlı emer.', 'Koşul, roller ve karşılaştırma derecesi eksiksiz korunmuş.', [], []],
    ] }),
  make({ id: 'translation-tr-eng-temperature', family: 'TRANSLATION_TR_ENG', domain: 'chemistry', stem: 'Araştırmacılar tepkimeden önce sıcaklığı iki kez ölçtü.', correct: 'C', checks: ['SEMANTIC_EQUIVALENCE'],
    tactical: { kind: 'TRANSLATION', direction: 'TR_ENG', source: roles3, candidates: { A: { ...roles3, propositions: ['after-reaction'] }, B: { ...roles3, degree: 'once' }, C: roles3, D: { ...roles3, time: 'future' }, E: { ...roles3, modality: 'must' } } },
    triage: 'Ölçen kişiyi, iki kez bilgisini ve tepkimeden önce sırasını eşleştirin.', skills: ['TRANSLATION_SEMANTICS'], choices: [
      ['The researchers measured the temperature twice after the reaction.', 'Önce ilişkisi sonra ilişkisine çevrilmiş.', ['TEMPORAL_MISMATCH'], ['SEMANTIC_EQUIVALENCE']],
      ['The researchers measured the temperature once before the reaction.', 'İki kez bilgisi bir keze düşürülmüş.', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']],
      ['Before the reaction, the researchers measured the temperature twice.', 'Zaman öbeği başa alınmış; sıralama, roller ve miktar korunmuş.', [], []],
      ['The researchers will measure the temperature twice before the reaction.', 'Geçmiş olay geleceğe taşınmış.', ['TEMPORAL_MISMATCH'], ['SEMANTIC_EQUIVALENCE']],
      ['The researchers had to measure the temperature twice before the reaction.', 'Kaynakta bulunmayan zorunluluk eklenmiş.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ] }),
  make({ id: 'translation-tr-eng-clouds', family: 'TRANSLATION_TR_ENG', domain: 'environment', stem: 'Kalın bulutlar yüzeye ulaşan güneş ışığını azaltabilir.', correct: 'A', checks: ['SEMANTIC_EQUIVALENCE'],
    tactical: { kind: 'TRANSLATION', direction: 'TR_ENG', source: roles4, candidates: { A: roles4, B: { ...roles4, action: 'increase' }, C: { ...roles4, modality: 'always' }, D: { ...roles4, agent: 'surface-sunlight', patient: 'thick-clouds' }, E: { ...roles4, polarity: 'negative' } } },
    triage: 'Bulutların etken rolünü ve azaltabilir kipini koruyun.', skills: ['TRANSLATION_SEMANTICS'], choices: [
      ['Thick clouds can reduce the sunlight reaching the surface.', 'Etken, etkilenen ve olasılık/yeterlik kipi korunmuş.', [], []],
      ['Thick clouds can increase the sunlight reaching the surface.', 'Azaltma artırmaya çevrilmiş.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
      ['Thick clouds always reduce the sunlight reaching the surface.', 'Olasılık koşulsuz sıklığa çevrilmiş.', ['EXTREME_QUALIFIER'], ['SEMANTIC_EQUIVALENCE']],
      ['The sunlight reaching the surface can reduce thick clouds.', 'Bulutlar ile güneş ışığının anlamsal rolleri değişmiş.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
      ['Thick clouds cannot reduce the sunlight reaching the surface.', 'Olumluluk ters çevrilmiş.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ] }),
  make({ id: 'paragraph-glacier', family: 'PARAGRAPH_COMPLETION', domain: 'geology', stem: 'Choose the sentence that completes the paragraph.',
    passage: 'The glacier has retreated for several decades. ____. These newly exposed surfaces provide sites where pioneer plants can establish.', correct: 'D',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'RESULT', candidate_relations: { A: null, B: 'CONTRAST', C: 'CAUSE', D: 'RESULT', E: null }, anchors: anchors('D') }, checks: ['DISCOURSE_RELATION', 'CONTINUATION'], triage: 'These surfaces gönderimini, buz çekilmesini ve öncü bitkiler zincirini birleştirin.', skills: ['PARAGRAPH_COMPLETION', 'COHESION_COHERENCE'], choices: [
      ['Some stars are much hotter than the Sun.', 'Bilimsel bilgi doğru olabilir; buz ve yüzey zincirini tamamlamaz.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['No land has ever appeared beneath any glacier.', 'Yeni açığa çıkan yüzeylerin varlığını reddeder.', ['EXTREME_QUALIFIER', 'POLARITY_INVERSION'], ['CONTINUATION']],
      ['Pioneer plants force all glaciers to advance.', 'Neden yönünü tersine çevirir ve kapsamı geneller.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
      ['As the ice withdraws, previously covered rock becomes exposed.', 'Çekilme kayayı açığa çıkarır; these surfaces bu kayalık yüzeylere gönderir.', [], []],
      ['The same surfaces were described in an unrelated telescope manual.', 'Surfaces sözcüğü ortak olsa da gönderim ve konu bağı yoktur.', ['REFERENCE_MISMATCH'], ['CONTINUATION']],
    ] }),
  make({ id: 'paragraph-filter', family: 'PARAGRAPH_COMPLETION', domain: 'medicine', stem: 'Choose the sentence that completes the paragraph.',
    passage: 'The filter trapped large particles effectively. ____. Therefore, the team added a second layer designed to capture these smaller contaminants.', correct: 'B',
    tactical: { kind: 'PARAGRAPH_COMPLETION', relation: 'CONTRAST', candidate_relations: { A: 'ADDITION', B: 'CONTRAST', C: null, D: null, E: 'CAUSE' }, anchors: anchors('B') }, checks: ['DISCOURSE_RELATION', 'CONTINUATION'], triage: 'İkinci katmanın gerekçesini ve smaller contaminants gönderimini kurun.', skills: ['PARAGRAPH_COMPLETION'], choices: [
      ['All contaminants had already been removed.', 'İkinci katmana gerekçe oluşturan küçük kirleticileri yok sayar.', ['EXTREME_QUALIFIER'], ['CONTINUATION']],
      ['However, fine particles could still pass through its pores.', 'Küçük parçacıkların geçişi yeni katmana gerekçe ve gönderim sağlar.', [], []],
      ['The team abandoned all filtration research a century earlier.', 'Bu ekip ve devam eden deneyin zaman zinciriyle uyuşmaz.', ['TEMPORAL_MISMATCH'], ['CONTINUATION']],
      ['Large planets have stronger gravity than small particles.', 'Large ve particles örtüşmesi deneyle anlamsal bağ kurmaz.', ['SCOPE_DRIFT'], ['CONTINUATION']],
      ['The second layer caused the first experiment to begin in the past.', 'Deneyin kronolojisi ve neden yönü ters kurulmuş.', ['CAUSE_EFFECT_REVERSAL'], ['DISCOURSE_RELATION']],
    ] }),
  make({ id: 'irrelevant-moon', family: 'IRRELEVANT_SENTENCE', domain: 'astronomy', stem: 'Which sentence interrupts the paragraph?',
    passage: '(I) The Moon has almost no atmosphere. (II) Small incoming rocks therefore rarely burn up before reaching its surface. (III) Their impacts leave craters. (IV) Chlorophyll absorbs light during photosynthesis. (V) Many of these craters remain visible for long periods.', correct: 'D',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Ay yüzeyindeki krater oluşumu ve korunması', discourse_function: 'Atmosfer azlığından krater izlerine neden zinciri' }, checks: irrelevantChecks,
    triage: 'Bilimsel doğruluğu değil; konu, gönderim ve neden zincirindeki işlevi değerlendirin.', skills: ['COHESION_COHERENCE'], choices: [
      ['I', 'Atmosfer azlığı sonraki çarpma açıklamasının başlangıcıdır; çıkarılacak cümle değildir.', [], ['TOPIC']],
      ['II', 'Therefore atmosfer bilgisine bağlanır ve incoming rocks gönderimini kurar.', [], ['REFERENT']],
      ['III', 'Their impacts kayalara gönderir; kraterleri tanıtır.', [], ['REFERENT']],
      ['IV', 'Fotosentez doğru bir bilimsel konu olsa da Ay kraterleri zincirinden kopuktur.', ['SCOPE_DRIFT'], []],
      ['V', 'These craters üçüncü cümledeki kraterlere döner ve zinciri sürdürür.', [], ['LEXICAL_CONTINUITY']],
    ] }),
  make({ id: 'irrelevant-water', family: 'IRRELEVANT_SENTENCE', domain: 'physics', stem: 'Which sentence interrupts the paragraph?',
    passage: '(I) Heating increases the motion of water molecules. (II) Some energetic molecules escape from the surface. (III) Granite commonly contains quartz. (IV) This escape process is called evaporation. (V) It can occur below the boiling point.', correct: 'C',
    tactical: { kind: 'IRRELEVANT_SENTENCE', topic: 'Suyun buharlaşması', discourse_function: 'Moleküler hareketten buharlaşmanın tanımına açıklama' }, checks: irrelevantChecks,
    triage: 'This escape ve it gönderimlerinin hangi süreci sürdürdüğünü bulun.', skills: ['COHESION_COHERENCE'], choices: [
      ['I', 'Isıtma moleküler hareketi başlatan bağlamı verir.', [], ['TOPIC']],
      ['II', 'Escape process ifadesinin dayanağı yüzeyden kaçıştır.', [], ['REFERENT']],
      ['III', 'Granitin içeriği buharlaşmanın açıklamasına katkı sağlamaz.', ['SCOPE_DRIFT'], []],
      ['IV', 'Süreç adlandırılır ve sonraki it gönderimine dayanak sağlar.', [], ['DISCOURSE_FUNCTION']],
      ['V', 'Buharlaşmanın kaynama dışındaki koşulunu açıklar.', [], ['SCOPE']],
    ] }),
  make({ id: 'reading-detail', family: 'READING_COMPREHENSION', domain: 'physics', stem: 'Which statement is supported by the report?',
    passage: 'In this trial, the sensor recorded a signal only when the blue lamp was on. It recorded no signal with the red lamp or in darkness. The authors did not test other light sources.', correct: 'B',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'DETAIL' }, checks: readingChecks, triage: 'Only sözcüğünü otomatik elemeyin; deney kapsamındaki sınırlamayı metinde doğrulayın.', skills: ['READING_DETAIL'], choices: [
      ['The sensor recorded a signal with the red lamp.', 'Metin kırmızı ışıkta sinyal kaydedilmediğini açıkça söyler.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['In this trial, a signal was recorded only when the blue lamp was on.', 'Only güçlü bir sözcüktür, fakat deney kapsamı ve doğrudan metin kanıtı onu destekler.', ['EXTREME_QUALIFIER'], []],
      ['All possible light sources were tested.', 'Diğer ışık kaynakları test edilmemiştir.', ['EXTREME_QUALIFIER'], ['SCOPE']],
      ['The report proves that the sensor works in every environment.', 'Bu deney bütün ortamlara genellenemez.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['The blue lamp permanently damaged the sensor.', 'Hasar hakkında bilgi verilmemiştir.', ['UNSUPPORTED_DETAIL'], ['PASSAGE_SUPPORT']],
    ] }),
  make({ id: 'reading-inference', family: 'READING_COMPREHENSION', domain: 'environment', stem: 'What can reasonably be inferred?',
    passage: 'A restored wetland retained more rainwater than a nearby drained field during three storms. Researchers cautioned that soil differences might also affect retention. They recommended monitoring additional sites.', correct: 'E',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'INFERENCE' }, checks: readingChecks, triage: 'Bulguyu koruyun; toprak farkından kaynaklanan belirsizliği silmeyin.', skills: ['READING_INFERENCE'], choices: [
      ['Restoration always prevents all floods.', 'Üç fırtınadaki tutma ölçümü tüm selleri önleme garantisi değildir.', ['EXTREME_QUALIFIER'], ['SCOPE']],
      ['Soil differences had no possible effect.', 'Araştırmacıların olası etki uyarısını tersine çevirir.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['The wetland retained less water than the field.', 'Karşılaştırmanın yönü ters çevrilmiş.', ['POLARITY_INVERSION'], ['PASSAGE_SUPPORT']],
      ['Monitoring additional sites will eliminate rainfall.', 'İzleme yağışın nedeni veya önleyicisi değildir.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
      ['The observations are promising, but broader evidence is needed.', 'Daha fazla tutma bulgusu umut vericidir; toprak uyarısı ve yeni saha önerisi genellemeyi sınırlar.', [], []],
    ] }),
  make({ id: 'reading-main', family: 'READING_COMPREHENSION', domain: 'medicine', stem: 'What is the main idea?',
    passage: 'Wearable monitors can collect heart-rate data during daily activities. Motion can distort their measurements, however. Comparing readings with clinical instruments helps researchers assess when the devices are reliable.', correct: 'A',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'MAIN_IDEA' }, checks: readingChecks, triage: 'Fayda, sınırlama ve doğrulama cümlelerini kapsayan ana düşünceyi seçin.', skills: ['MAIN_IDEA'], choices: [
      ['Wearable monitoring is useful, but its reliability requires evaluation.', 'Üç cümledeki kullanım, hareket hatası ve klinik karşılaştırmayı birlikte kapsar.', [], []],
      ['Heart rate is measured only in hospitals.', 'Günlük etkinliklerde ölçüm bilgisiyle çelişir.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['Motion can affect readings.', 'Doğru ayrıntıdır; yarar ve doğrulama yaklaşımını kapsamayan dar bir özettir.', ['PARTIAL_TRUTH'], ['SCOPE']],
      ['Clinical instruments are never useful.', 'Karşılaştırma aracını değersizleştiren iddia metinde yoktur.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['All wearable devices cure heart disease.', 'İzleme, tedavi anlamına gelmez.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ] }),
  make({ id: 'reading-reference', family: 'READING_COMPREHENSION', domain: 'chemistry', stem: 'What does “these” refer to?',
    passage: 'The reaction produced tiny crystals in the solution. After cooling the liquid, the team separated these using a fine filter.', correct: 'C',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'REFERENCE' }, checks: readingChecks, triage: 'Çoğul gönderimin anlamsal rolünü ve filtreyle ayrılabilecek nesneyi bulun.', skills: ['COHESION_COHERENCE'], choices: [
      ['the researchers', 'Araştırmacılar filtreyle ayrılan ürünler değildir.', ['REFERENCE_MISMATCH'], ['SEMANTIC_EQUIVALENCE']],
      ['the filters', 'Filtreler araçtır; these ile ayrılan nesne değildir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
      ['the tiny crystals', 'Çözelti içindeki çoğul ürünler kristallerdir; filtreyle ayrılabilirler.', [], []],
      ['the cooling methods', 'Metinde çoğul soğutma yöntemleri tanıtılmamıştır.', ['UNSUPPORTED_DETAIL'], ['PASSAGE_SUPPORT']],
      ['the reaction times', 'Reaksiyon süreleri verilmemiştir.', ['UNSUPPORTED_DETAIL'], ['PASSAGE_SUPPORT']],
    ] }),
  make({ id: 'reading-purpose', family: 'READING_COMPREHENSION', domain: 'geology', stem: 'Why does the author mention tree rings?',
    passage: 'Past droughts can be studied through several natural records. Tree rings, for example, may be narrower in dry years. Such records help extend climate knowledge beyond modern measurements.', correct: 'D',
    tactical: { kind: 'READING_COMPREHENSION', subtype: 'PURPOSE' }, checks: readingChecks, triage: 'For example işaretinin paragraftaki örneklendirme görevini izleyin.', skills: ['READING_INFERENCE'], choices: [
      ['To prove that modern measurements are useless', 'Geçmişi genişletmek güncel ölçümleri değersizleştirmez.', ['SCOPE_DRIFT'], ['SCOPE']],
      ['To claim that droughts occur every year', 'Kurak yıllardaki daralma her yıl kuraklık olduğunu göstermez.', ['EXTREME_QUALIFIER'], ['PASSAGE_SUPPORT']],
      ['To explain how trees cause droughts', 'Kayıt ile neden birbirine karıştırılmış.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
      ['To illustrate a natural source of evidence about past climate', 'Halkalar geçmiş kuraklığı gösterebilen doğal kayda örnek olarak verilmiştir.', [], []],
      ['To compare the prices of measuring instruments', 'Fiyat veya cihaz karşılaştırması yapılmıyor.', ['UNSUPPORTED_DETAIL'], ['PASSAGE_SUPPORT']],
    ] }),
]);
