import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, type Choice } from './authoringUtils';

const trans = (id: string, domain: string, stem: string, correct: 'A'|'B'|'C'|'D'|'E', direction: 'ENG_TR' | 'TR_ENG', choices: readonly [Choice, Choice, Choice, Choice, Choice]) => make({
  id, family: direction === 'ENG_TR' ? 'TRANSLATION_ENG_TR' : 'TRANSLATION_TR_ENG', domain, stem, correct,
  tactical: { kind: 'TRANSLATION', direction, source: { agent: 'a', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, candidates: { A: { agent: correct==='A'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, B: { agent: correct==='B'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, C: { agent: correct==='C'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, D: { agent: correct==='D'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, E: { agent: correct==='E'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] } } },
  checks: ['SEMANTIC_EQUIVALENCE', 'SCOPE', 'TENSE_ASPECT'], triage: 'Identify main verb and subject.', skills: ['TRANSLATION_SEMANTICS'],
  choices
});

export const batch3Questions: readonly Question[] = deepFreeze([
  // ENG -> TR
  trans('b3-trans-engtr-1', 'technology', 'Advances in artificial intelligence have fundamentally altered the way scientists process large datasets.', 'C', 'ENG_TR', [
    ['Yapay zeka alanındaki gelişmeler, bilim insanlarının büyük veri setlerini işleme yöntemlerini değiştirebilir.', 'Değiştirebilir (may alter) değil, değiştirmiştir (have altered).', ['PARTIAL_TRUTH'], ['TENSE_ASPECT']],
    ['Bilim insanları yapay zeka kullanarak büyük veri setlerini işleme yöntemlerini tamamen değiştirmiştir.', 'Özne "Bilim insanları" değil "Advances in artificial intelligence" olmalıdır.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Yapay zeka alanındaki gelişmeler, bilim insanlarının büyük veri setlerini işleme yöntemini temelden değiştirmiştir.', 'Tüm özneler, fiiller ve zarflar doğru çevrilmiştir.', [], []],
    ['Yapay zeka geliştiği için bilim insanları büyük veri setlerini farklı bir şekilde işlemektedir.', 'Neden-sonuç cümlesi orijinal cümlede yer almaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Büyük veri setleri, yapay zekadaki gelişmeler sayesinde bilim insanları tarafından farklı işlenmektedir.', 'Edilgen (passive) yapı kullanımı orijinal cümlenin etken (active) yapısına uymaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-engtr-2', 'biology', 'Most marine biologists agree that protecting coral reefs is essential for maintaining ocean biodiversity.', 'B', 'ENG_TR', [
    ['Deniz biyologlarının çoğu, mercan resiflerini korumanın okyanus biyoçeşitliliği için faydalı olduğuna inanır.', 'Faydalı (beneficial) değil, şarttır/gereklidir (essential).', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Çoğu deniz biyoloğu, okyanus biyoçeşitliliğini sürdürmek için mercan resiflerini korumanın şart olduğu konusunda hemfikirdir.', 'Tüm bileşenler tam olarak çevrilmiştir.', [], []],
    ['Okyanus biyoçeşitliliğini korumak isteyen deniz biyologları mercan resiflerini kurtarmak zorundadır.', 'Özne ve yüklem yapısı (isteyen... zorundadır) orijinalden farklıdır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Deniz biyologları mercan resiflerinin korunmasının okyanus biyoçeşitliliğini artıracağını kabul eder.', 'Artıracağını (increase) değil, sürdürmek (maintain) içindir.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Mercan resifleri korunursa okyanus biyoçeşitliliği sürdürülebilir, çoğu deniz biyoloğu buna katılır.', 'Koşul cümlesi (korunursa) orijinal metinde yoktur.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-engtr-3', 'physics', 'The new telescope allows astronomers to observe distant galaxies with unprecedented clarity.', 'E', 'ENG_TR', [
    ['Yeni teleskop, astronomların uzak galaksileri daha önce görülmemiş bir şekilde keşfetmelerini sağlar.', 'Keşfetmelerini (discover) değil, gözlemlemelerini (observe) sağlar.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Astronomlar yeni teleskobu kullanarak uzak galaksileri çok net bir şekilde gözlemleyebilirler.', 'Özne yeni teleskop olmalıdır, astronomlar değil.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Uzak galaksiler, yeni teleskop sayesinde astronomlar tarafından daha önce görülmemiş bir netlikle gözlemlenmektedir.', 'Edilgen yapı çeviriyi orijinal yapıdan uzaklaştırır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Yeni teleskop sayesinde astronomlar uzak galaksileri eşi benzeri görülmemiş bir netlikle gözlemleyecekler.', 'Gelecek zaman (will observe) orijinalin geniş/şimdiki zamanıyla çelişir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
    ['Yeni teleskop, astronomların uzak galaksileri daha önce görülmemiş bir netlikle gözlemlemesine olanak tanır.', 'Tüm kelimeler ve sözdizimi eksiksiz yansıtılmıştır.', [], []]
  ]),
  trans('b3-trans-engtr-4', 'medicine', 'Frequent consumption of processed foods has been linked to an increased risk of metabolic diseases.', 'A', 'ENG_TR', [
    ['İşlenmiş gıdaların sık tüketimi, artan metabolik hastalık riskiyle ilişkilendirilmiştir.', 'Tam ve doğru çeviridir.', [], []],
    ['İşlenmiş gıdaları sık tüketenlerin metabolik hastalıklara yakalanma riski daha yüksektir.', 'Özne "sık tüketimi" olmalıdır, "tüketenler" değil.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['İşlenmiş gıdaların sık tüketilmesi metabolik hastalık riskini giderek artırmaktadır.', 'İlişkilendirilmiştir (has been linked) fiili atlanmış, doğrudan artırmaktadır (increases) denmiştir.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Eğer işlenmiş gıdalar sık tüketilirse metabolik hastalık riski artar.', 'Koşul cümlesi orijinal metinde yoktur.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['İşlenmiş gıdaların sık tüketimi metabolik hastalıklarla ilişkilendirilebilir.', 'İhtimal bildiren (can be linked) kip yanlış kullanılmıştır.', ['PARTIAL_TRUTH'], ['TENSE_ASPECT']]
  ]),
  trans('b3-trans-engtr-5', 'geology', 'Earthquakes occur when stored energy in the Earth\'s crust is suddenly released.', 'D', 'ENG_TR', [
    ['Depremler, yer kabuğundaki enerji aniden serbest kaldığı için meydana gelir.', 'İçin (because) değil, dığında/zaman (when) yapısı vardır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Yer kabuğundaki depolanmış enerji aniden serbest bırakılırsa depremler oluşur.', 'Koşul kipi (if/oluşursa) orijinal metinde yoktur.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Depremler sırasında yer kabuğunda depolanan enerji aniden açığa çıkar.', 'Orijinal cümle depremin neden/ne zaman olduğunu tanımlar, deprem sırasındakileri değil.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Depremler, yer kabuğunda depolanan enerji aniden açığa çıktığında meydana gelir.', 'Zaman yantümcesi ve fiiller tamamen örtüşmektedir.', [], []],
    ['Yer kabuğundaki enerji aniden açığa çıkınca büyük depremler meydana gelir.', 'Büyük (major) kelimesi orijinal cümlede yoktur.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-engtr-6', 'chemistry', 'Polymers are large molecules composed of many repeated subunits called monomers.', 'C', 'ENG_TR', [
    ['Polimerler, monomer adı verilen birçok alt birimin birleşmesiyle oluşan moleküllerdir.', 'Büyük (large) ve tekrarlanan (repeated) sıfatları atlanmıştır.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Monomer olarak adlandırılan büyük moleküller, polimer adı verilen birçok alt birimden oluşur.', 'Polimer ile monomerin yerleri karıştırılmıştır.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Polimerler, monomer olarak adlandırılan birçok tekrarlanan alt birimden oluşan büyük moleküllerdir.', 'Tanım cümlesi birebir ve eksiksiz çevrilmiştir.', [], []],
    ['Polimerler, monomerlerin tekrarlanmasıyla oluşan çok büyük moleküllerdir.', 'Çok (very) kelimesi fazladır ve alt birimler eksiktir.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Monomer adı verilen birçok alt birim tekrarlanarak polimerleri oluşturan büyük moleküllere dönüşür.', 'Cümlenin yapısı ve öznesi değiştirilmiştir.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-engtr-7', 'environment', 'Deforestation not only threatens wildlife but also accelerates global climate change.', 'B', 'ENG_TR', [
    ['Ormansızlaşma yaban hayatını tehdit ettiği için küresel iklim değişikliği hızlanmaktadır.', 'Neden-sonuç ilişkisi orijinaldeki "sadece ... değil, aynı zamanda ..." kalıbının yerini alamaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Ormansızlaşma sadece yaban hayatını tehdit etmekle kalmaz, aynı zamanda küresel iklim değişikliğini de hızlandırır.', 'Kalıp (not only... but also) ve fiiller tam olarak karşılığını bulmuştur.', [], []],
    ['Küresel iklim değişikliğini hızlandıran ormansızlaşma, yaban hayatını da tehdit eder.', 'Vurgu yapısı değiştirilmiş, bağımsız cümle yerine sıfat fiil kullanılmıştır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Ormansızlaşma hem yaban hayatını yok eder hem de küresel iklim değişikliğini artırır.', 'Yok eder (destroys) değil tehdit eder (threatens) olmalıdır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Yaban hayatını tehdit eden ormansızlaşma sadece küresel iklim değişikliğini hızlandırmakla kalmaz.', 'Cümlenin ögeleri ve not only kalıbı yanlış yerleştirilmiştir.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-engtr-8', 'astronomy', 'Although Mars has an extremely thin atmosphere, it occasionally experiences massive dust storms.', 'E', 'ENG_TR', [
    ['Marsın çok ince bir atmosferi olduğu için ara sıra devasa toz fırtınaları yaşar.', 'Neden-sonuç değil, zıtlık (although) vardır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Mars son derece ince bir atmosfere sahip olmasına rağmen orada sık sık büyük toz fırtınaları görülür.', 'Sık sık (frequently) değil ara sıra (occasionally) olmalıdır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Mars çok ince bir atmosfere sahiptir ancak zaman zaman şiddetli toz fırtınaları yaratır.', 'Yaratır (creates) değil yaşar/maruz kalır (experiences).', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Marsın atmosferi son derece ince olsa da devasa toz fırtınalarını engelleyemez.', 'Engelleyemez (cannot prevent) cümlede bulunmayan bir çıkarımdır.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Mars son derece ince bir atmosfere sahip olmasına rağmen, ara sıra devasa toz fırtınaları yaşar.', 'Tüm bağlaçlar, sıfatlar ve zarflar doğru çevrilmiştir.', [], []]
  ]),

  // TR -> ENG
  trans('b3-trans-treng-1', 'medicine', 'Aşılar, bağışıklık sistemini belirli hastalıklara karşı antikor üretmesi için uyarır.', 'A', 'TR_ENG', [
    ['Vaccines stimulate the immune system to produce antibodies against specific diseases.', 'Doğru ve tam çeviridir.', [], []],
    ['Vaccines help the immune system by producing antibodies against specific diseases.', 'Aşıların antikor ürettiği (producing) anlamı çıkar, uyardığı değil.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['The immune system is stimulated by vaccines to fight specific diseases with antibodies.', 'Edilgen (passive) yapı Türkçe orijinal cümlenin etken (active) yapısına uymaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Vaccines stimulate the immune system because they produce antibodies against certain diseases.', 'Neden-sonuç (because) bağlacı orijinal cümlede yer almaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Vaccines can stimulate the immune system to produce antibodies against many diseases.', 'İhtimal (can) ve birçok (many) kelimeleri orijinalde yoktur.', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-treng-2', 'biology', 'Hücre bölünmesi, tüm canlı organizmaların büyümesi ve onarımı için temel bir süreçtir.', 'D', 'TR_ENG', [
    ['Cell division is a fundamental process that helps all living organisms grow and repair.', 'Sıfat tümcesi (that helps) orijinaldeki "için" (for) edat yapısına tam uymaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['For the growth and repair of all living organisms, cell division is extremely necessary.', 'Son derece gerekli (extremely necessary) ifadesi "temel bir süreçtir" kısmını tam karşılamaz.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Cell division is an important process because all living organisms need to grow and repair.', 'Neden-sonuç cümlesi orijinal metnin isim cümlesi yapısıyla örtüşmez.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Cell division is a fundamental process for the growth and repair of all living organisms.', 'Tüm sözdizimi ve terimler tam eşleşmektedir.', [], []],
    ['Cell division has been a fundamental process for all living organisms to grow and repair.', 'Present perfect zaman kullanımı geniş zamanlı orijinal metinle çelişir.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']]
  ]),
  trans('b3-trans-treng-3', 'chemistry', 'Katalizörler kimyasal bir reaksiyonun hızını artırır ancak reaksiyonun sonunda değişmeden kalırlar.', 'C', 'TR_ENG', [
    ['Catalysts increase the rate of a chemical reaction while remaining completely unchanged.', 'Zarf tümcesi (while remaining) orijinaldeki zıtlık bağlacının (ancak / but) yerini tutmaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Although catalysts increase the rate of a chemical reaction, they are left unchanged at the end.', 'Zıtlık (although) başlangıca alınmış ve son kısım edilgen olmuştur.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Catalysts increase the rate of a chemical reaction but they remain unchanged at the end of the reaction.', 'Bağlaçlar, özneler ve fiiller birebir uymaktadır.', [], []],
    ['Because catalysts remain unchanged at the end of the reaction, they increase the reaction rate.', 'Neden-sonuç ilişkisi orijinal cümlenin mantığını saptırmıştır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Catalysts can increase the rate of a chemical reaction but usually remain unchanged at the end.', 'İhtimal (can) ve genellikle (usually) zarfları orijinalde yoktur.', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-treng-4', 'geology', 'Depremlerin tam olarak ne zaman meydana geleceğini tahmin etmek şu anki teknolojiyle imkansızdır.', 'B', 'TR_ENG', [
    ['It is very difficult to predict exactly when earthquakes will occur with current technology.', 'Çok zor (very difficult) değil, imkansızdır (impossible).', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Predicting exactly when earthquakes will occur is impossible with current technology.', 'Fiilimsi özne ve diğer tüm ifadeler doğrudur.', [], []],
    ['With current technology, scientists cannot predict exactly when earthquakes occur.', 'Bilim insanları kelimesi orijinal cümlede yoktur.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Because of current technology, it is impossible to predict the exact time earthquakes will occur.', 'Nedensellik (Because of) orijinaldeki araç/vasıta (with) edatından farklıdır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Predicting when earthquakes might occur exactly has been impossible with current technology.', 'Present perfect zaman şimdiki duruma (is impossible) uymaz.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']]
  ]),
  trans('b3-trans-treng-5', 'physics', 'Işık bir prizmadan geçtiğinde, farklı renklere sahip bir spektruma ayrılır.', 'E', 'TR_ENG', [
    ['Because light passes through a prism, it separates into a spectrum of different colors.', 'İçin (because) değil, dığında/zaman (when) kullanılmalıdır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Light separates into a spectrum of different colors before it passes through a prism.', 'Geçmeden önce (before) mantıksal ve çevirisel bir hatadır.', ['TEMPORAL_MISMATCH'], ['SEMANTIC_EQUIVALENCE']],
    ['When light passes through a prism, it creates a spectrum with many colors.', 'Yaratır (creates) ve birçok (many) kelimeleri orijinal metinden sapmadır.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['If light is passed through a prism, it is separated into a spectrum of different colors.', 'Koşul kipi (if) ve edilgen yapı kullanılmıştır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['When light passes through a prism, it separates into a spectrum with different colors.', 'Doğru ve eksiksiz bir çeviridir.', [], []]
  ]),
  trans('b3-trans-treng-6', 'astronomy', 'Kara delikler, ışığın bile kaçamayacağı kadar güçlü bir yerçekimi kuvvetine sahiptir.', 'A', 'TR_ENG', [
    ['Black holes have a gravitational force so strong that even light cannot escape it.', 'Birebir, eksiksiz ve doğru yapı çevirisidir.', [], []],
    ['Black holes are so strong that their gravitational force does not let even light escape.', 'Sözdizimi değiştirilmiş ve farklı bir vurgu kullanılmıştır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Because the gravitational force of black holes is strong, even light cannot escape.', 'Neden-sonuç bağı orijinaldeki "so... that" sıfat kalıbının yerini almaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Black holes have a very strong gravitational force, therefore even light cannot escape.', 'İki ayrı cümle ve therefore bağlacı orijinal yapıya uymaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Even light could not escape the gravitational force possessed by black holes.', 'Zaman uyuşmazlığı (could not) ve cümlenin tamamen baştan kurulması yanlıştır.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']]
  ]),
  trans('b3-trans-treng-7', 'environment', 'Yenilenebilir enerji kaynaklarının kullanımı, karbon emisyonlarını azaltmak için kritik öneme sahiptir.', 'D', 'TR_ENG', [
    ['Using renewable energy sources can be critical for reducing carbon emissions.', 'Olabilir (can be) değil, sahiptir/öyledir (is).', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']],
    ['Renewable energy sources have a critical importance because they reduce carbon emissions.', 'İçin (for/to) amaç bildirirken, because neden bildirir.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['To reduce carbon emissions, we must use renewable energy sources critically.', 'Özne (we) eklenmiş ve zarf (critically) yanlış kullanılmıştır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['The use of renewable energy sources is of critical importance for reducing carbon emissions.', 'İsim tamlaması ve tüm ifadeler kelimesi kelimesine uygundur.', [], []],
    ['Reducing carbon emissions has a critical importance for the use of renewable energy sources.', 'Neden ve sonuç unsurlarının yerleri ters çevrilmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']]
  ]),
  trans('b3-trans-treng-8', 'technology', 'Yapay zeka, sağlık hizmetlerinden finans sektörüne kadar pek çok endüstriyi dönüştürmektedir.', 'C', 'TR_ENG', [
    ['Artificial intelligence will transform many industries, from healthcare to the financial sector.', 'Dönüştürecektir (will transform) şimdiki/geniş zamanla örtüşmez.', ['TEMPORAL_MISMATCH'], ['TENSE_ASPECT']],
    ['Many industries, from healthcare to finance, have been transformed by artificial intelligence.', 'Edilgen (passive) yapı kullanılmış ve zaman farklıdır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Artificial intelligence is transforming many industries, from healthcare to the finance sector.', 'Tüm bileşenler şimdiki zamanda doğru çevrilmiştir.', [], []],
    ['Artificial intelligence transforms all industries, including healthcare and the finance sector.', 'Tüm (all) ve dahil (including) kelimeleri orijinal anlamı bozar.', ['EXTREME_QUALIFIER'], ['SEMANTIC_EQUIVALENCE']],
    ['Healthcare and the finance sector are transforming many industries using artificial intelligence.', 'Özne ile nesne yer değiştirmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']]
  ])
]);



