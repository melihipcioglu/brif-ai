import type { Question } from '../types/question';
import { deepFreeze } from '../services/questions/attempts';
import { make, type Choice } from './authoringUtils';

const trans = (id: string, domain: string, stem: string, correct: 'A'|'B'|'C'|'D'|'E', direction: 'ENG_TR' | 'TR_ENG', choices: readonly [Choice, Choice, Choice, Choice, Choice]) => make({
  id, family: direction === 'ENG_TR' ? 'TRANSLATION_ENG_TR' : 'TRANSLATION_TR_ENG', domain, stem, correct,
  tactical: { kind: 'TRANSLATION', direction, source: { agent: 'a', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, candidates: { A: { agent: correct==='A'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, B: { agent: correct==='B'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, C: { agent: correct==='C'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, D: { agent: correct==='D'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] }, E: { agent: correct==='E'?'a':'x', action: 'b', patient: 'c', voice: 'ACTIVE', propositions: [] } } },
  checks: ['SEMANTIC_EQUIVALENCE', 'SCOPE', 'TENSE_ASPECT'], triage: 'Cümledeki özne, ana fiil, zaman ve bağlaçları dikkatle eşleştirin.', skills: ['TRANSLATION_SEMANTICS'],
  choices,
});

export const batch8Questions: readonly Question[] = deepFreeze([
  // TRANSLATION ENG -> TR 3 (Chemistry - Chemical Equilibrium)
  trans('b8-trans-engtr-1', 'chemistry', 'When a dynamic chemical equilibrium is reached, the rates of forward and reverse reactions become equal.', 'C', 'ENG_TR', [
    ['Dinamik kimyasal dengeye ulaşıldığı için ileri ve geri tepkime hızları eşitlenebilir.', 'İçin (because) değil, dığında/ulaşıldığında (when) zarf tümce yapısı vardır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['İleri ve geri tepkime hızları eşitlendiği zaman yeni bir dinamik kimyasal denge kurulur.', 'Neden ve sonuç yer değiştirmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Dinamik bir kimyasal dengeye ulaşıldığında, ileri ve geri tepkimelerin hızları eşit hale gelir.', 'Zaman yantümcesi ve yüklem (become equal) tam ve eksiksiz çevrilmiştir.', [], []],
    ['Dinamik kimyasal denge, ileri tepkimenin geri tepkimeden daha hızlı gerçekleştiği bir durumdur.', 'Eşitlik yerine hız farkı iddiası anlamı tamamen bozar.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['İleri ve geri tepkimelerin hızları eşitlense bile dinamik kimyasal dengeye ulaşılamayabilir.', 'Zıtlık/ödünleme yapısı (even if) orijinal cümlede yer almaz.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 4 (Environment - Permafrost Thaw)
  trans('b8-trans-engtr-2', 'environment', 'Accelerated permafrost thawing in the Arctic releases potent greenhouse gases trapped beneath the frozen soil.', 'D', 'ENG_TR', [
    ['Kutup altındaki donmuş toprak eridikçe sera gazlarının salınımı hızlanabilir.', 'İhtimal kipi (may accelerate) değil kesin bildirim (releases) söz konusudur.', ['PARTIAL_TRUTH'], ['SEMANTIC_EQUIVALENCE']],
    ['Kuzey Kutbu\'nda sera gazlarının salınması, donmuş toprağın derinliklerindeki çözünmeyi hızlandırmıştır.', 'Sera gazı salınımı özne değil, çözünmenin sonucudur.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Donmuş toprağın altında hapsolmuş sera gazları Kuzey Kutbu\'ndaki buzulların erimesine yol açar.', 'Cümlenin ana öznesi sera gazları değil hızlanan erimedir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Kuzey Kutbu\'nda hızlanan donmuş toprak erimesi, donmuş toprağın altında hapsolmuş güçlü sera gazlarını açığa çıkarır.', 'Özne, sıfat tamlaması ve eylem tam örtüşmektedir.', [], []],
    ['Kuzey Kutbu\'ndaki donmuş toprak tabakası güçlü sera gazlarını tuttuğu için erime yavaşlamaktadır.', 'Erime yavaşlamamakta, hızlanmaktadır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 5 (Astronomy - Black Holes)
  trans('b8-trans-engtr-3', 'astronomy', 'Supermassive black holes at the centers of galaxies exert profound gravitational influence on surrounding stellar orbits.', 'A', 'ENG_TR', [
    ['Galaksilerin merkezlerindeki süper kütleli kara delikler, çevredeki yıldız yörüngeleri üzerinde derin bir yerçekimi etkisi oluşturur.', 'Özne, yer tamlayıcısı ve yüklem eksiksiz karşılık bulmuştur.', [], []],
    ['Yıldız yörüngelerinin derin yerçekimi etkisi, galaksi merkezlerindeki süper kütleli kara delikleri kontrol eder.', 'Özne ve nesne rolleri ters çevrilmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Galaksilerin merkezinde bulunan kara delikler, yıldız yörüngelerinin yerçekiminden derinden etkilenir.', 'Etkiler (exert influence) yerine etkilenir (are influenced) edilgen yapılmıştır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Çevredeki yıldız yörüngeleri değiştikçe galaksilerin merkezindeki kara deliklerin kütlesi hızla artar.', 'Yörüngelerin değişmesi kara deliğin kütlesini artıran etken olarak sunulamaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Galaksi merkezlerindeki süper kütleli kara delikler yıldızların yörüngelerinden tamamen bağımsız hareket eder.', 'Bağımsız hareket eder iddiası güçlü etki (profound influence) ile çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 6 (Medicine - mRNA Vaccines)
  trans('b8-trans-engtr-4', 'medicine', 'Unlike conventional vaccines, mRNA vaccines instruct human cells to produce a harmless viral protein that triggers an immune response.', 'E', 'ENG_TR', [
    ['Geleneksel aşılar gibi mRNA aşıları da bağışıklık yanıtını tetikleyen zararsız bir viral protein içerir.', 'Geleneksel aşılar gibi (like) değil, geleneksel aşıların aksine (unlike) denmiştir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['İnsan hücreleri zararsız viral proteinler ürettiğinde geleneksel aşılar güçlü bir bağışıklık yanıtı oluşturur.', 'mRNA aşısının mekanizması geleneksel aşıya mal edilmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['mRNA aşıları bağışıklık yanıtını tetiklemek amacıyla insan hücrelerini geleneksel aşılardan korur.', 'Geleneksel aşılardan koruma iddiası cümlenin amacıyla alakasızdır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Zararsız viral proteinlerin bağışıklık tepkisini tetiklemesi için mRNA aşılarının geleneksel yöntemlerle üretilmesi gerekir.', 'Geleneksel yöntemle üretilme şartı orijinal metinde yer almaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Geleneksel aşıların aksine, mRNA aşıları insan hücrelerine bir bağışıklık tepkisini tetikleyen zararsız bir viral protein üretmeleri talimatını verir.', 'Kıyaslama (unlike), nesne ve sıfat tümceleri kusursuz yansıtılmıştır.', [], []],
  ]),

  // TRANSLATION ENG -> TR 7 (Technology - Fiber Optics)
  trans('b8-trans-engtr-5', 'technology', 'Fiber optic cables transmit data as pulses of light, which allows for vastly superior bandwidth over copper wiring.', 'B', 'ENG_TR', [
    ['Bakır kablolar veriyi ışık darbeleri şeklinde ileterek fiber optik kablolardan daha üstün bir bant genişliği sağlar.', 'Bakır kablo ile fiber optik kablonun rolleri ters çevrilmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Fiber optik kablolar veriyi ışık darbeleri olarak iletir; bu da bakır kablolamaya kıyasla çok daha üstün bir bant genişliğine olanak tanır.', 'Ana cümle ve ilave niteleme yantümcesi eksiksiz çevrilmiştir.', [], []],
    ['Veri ışık darbeleriyle iletildiğinde fiber optik kablolar bakır kablolardan daha fazla enerji tüketir.', 'Daha fazla enerji tüketir bilgisi üstün bant genişliği avantajıyla çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Fiber optik kabloların bant genişliği üstün olsa bile veriyi bakır kablolar kadar hızlı iletemezler.', 'Daha hızlı iletemezler iddiası orijinal cümlenin teknolojisine zıttır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Işık darbeleri bakır kablolama yoluyla iletildiği için fiber optik teknolojisi üstün bir bant genişliğine sahiptir.', 'Bakır kablo ışık darbesi iletmez.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 8 (Geology - Plate Tectonics)
  trans('b8-trans-engtr-6', 'geology', 'Subduction zones are regions where one tectonic plate is forced beneath another into the Earth\'s mantle.', 'C', 'ENG_TR', [
    ['Bir tektonik levhanın diğerini mantoya doğru ittiği bölgelere okyanus sırtları adı verilir.', 'Okyanus sırtı değil yitim zonları (subduction zones) tanımlanmıştır.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['Yitim zonları, iki tektonik levhanın birbirinden ayrılarak Dünya\'nın mantosuna doğru battığı alanlardır.', 'Birbirinden ayrılarak (diverging) değil biri diğerinin altına girerek.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Yitim zonları, bir tektonik levhanın diğerinin altına, Dünya\'nın mantosuna doğru itildiği bölgelerdir.', 'Tanım cümlesi ve edilgen yapı (is forced) birebir doğru çevrilmiştir.', [], []],
    ['Dünya\'nın mantosuna giren tektonik levhalar yitim zonlarında birleşerek yeni kara parçaları oluşturur.', 'Yeni kara parçaları oluşturma detayı orijinal cümlede yoktur.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['İki levha birbiriyle çarpışmadığı takdirde yitim zonlarında hiçbir jeolojik hareketlilik oluşmaz.', 'Koşul cümlesi tanım cümlesinin yerini alamaz.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 9 (Biology - Biodiversity Hotspots)
  trans('b8-trans-engtr-7', 'biology', 'Although biodiversity hotspots represent less than three percent of Earth\'s land surface, they harbor more than half of all plant species.', 'D', 'ENG_TR', [
    ['Biyoçeşitlilik sıcak noktaları Dünya kara yüzeyinin yüzde üçünden fazlasını kapladığı için bitki türlerinin yarısını barındırır.', 'Yüzde üçünden fazlasını (more than) değil, daha azını (less than) kaplar.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Dünya yüzeyindeki bitki türlerinin yarısından fazlası biyoçeşitlilik sıcak noktalarının dışında yaşar.', 'Noktaların içinde barınır bilgisi tersyüz edilmiştir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Biyoçeşitlilik sıcak noktaları kara yüzeyinin yüzde üçünü oluşturduğunda bitki türlerinin korunması kolaylaşır.', 'Zaman/koşul yapısı zıtlık bildiren although bağlacına uymaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Biyoçeşitlilik sıcak noktaları Dünya kara yüzeyinin yüzde üçünden daha azını temsil etmesine rağmen, tüm bitki türlerinin yarısından fazlasını barındırır.', 'Ödünleme bağlacı ve oranlar eksiksiz yansıtılmıştır.', [], []],
    ['Tüm bitki türlerinin yarısından fazlası yok olma tehlikesiyle karşı karşıya olduğundan biyoçeşitlilik alanları daralmaktadır.', 'Yok olma tehlikesi cümlede yer almayan bir yorumdur.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION ENG -> TR 10 (Physics - Wave-Particle Duality)
  trans('b8-trans-engtr-8', 'physics', 'Under specific experimental conditions, subatomic particles can behave simultaneously as localized particles and extended waves.', 'A', 'ENG_TR', [
    ['Belirli deneysel koşullar altında, atom altı parçacıklar eş zamanlı olarak yerelleşmiş parçacıklar ve yayılmış dalgalar gibi davranabilir.', 'Koşul, zarf (simultaneously) ve benzetme yapısı kusursuz çevrilmiştir.', [], []],
    ['Atom altı parçacıkların dalga veya parçacık gibi davranabilmesi için deney koşullarının sürekli değiştirilmesi gerekir.', 'Sürekli değiştirilme zorunluluğu orijinal cümlede yoktur.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Belirli deneysel koşullarda atom altı parçacıklar parçacık özelliğini tamamen yitirerek sadece dalgaya dönüşür.', 'Sadece dalgaya dönüşmez, ikisi gibi eş zamanlı davranır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Atom altı parçacıklar yerelleşmiş dalgalar gibi davrandıklarında parçacık yapıları laboratuvarda ölçülemez.', 'Ölçülemez çıkarımı metinde yer almaz.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
    ['Deneysel koşullar ne olursa olsun atom altı parçacıklar her zaman hem parçacık hem dalga özelliği sergiler.', 'Ne olursa olsun/her zaman genellemesi under specific conditions ile çelişir.', ['EXTREME_QUALIFIER'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 1 (Chemistry - Catalysts)
  trans('b8-trans-treng-1', 'chemistry', 'Katalizörler kimyasal tepkimelerin aktivasyon enerjisini düşürerek reaksiyon hızını önemli ölçüde artırır.', 'B', 'TR_ENG', [
    ['Catalysts decrease the speed of reactions even if they lower the activation energy.', 'Tepkime hızını düşürür (decrease) iddiası artırır ile çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Catalysts significantly increase the reaction rate by lowering the activation energy of chemical reactions.', 'Zarf (significantly), eylem ve vasıta yapısı (by lowering) eksiksiz çevrilmiştir.', [], []],
    ['Chemical reactions accelerate naturally when catalysts are removed from the solution.', 'Katalizörün uzaklaştırılması tepkimeyi hızlandırmaz.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['By increasing the activation energy, catalysts prevent chemical reactions from proceeding rapidly.', 'Aktivasyon enerjisini artırmak reaksiyonu yavaşlatır, ifadenin tam tersidir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['The activation energy of chemical reactions increases dramatically because catalysts accelerate the process.', 'Aktivasyon enerjisi artmaz, düşer.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 2 (Environment - Renewable Energy)
  trans('b8-trans-treng-2', 'environment', 'Güneş panelleri, güneş ışığını doğrudan elektrik enerjisine dönüştürmek için fotovoltayik hücreler kullanır.', 'E', 'TR_ENG', [
    ['Solar panels generate sunlight by consuming large amounts of electrical energy in cells.', 'Güneş panelleri güneş ışığı üretmez, elektrik tüketmez.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Photovoltaic cells prevent solar panels from transforming sunlight into usable electricity.', 'Elektriğe dönüşümü engeller (prevent) iddiası yanlıştır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Solar panels convert electrical energy directly into intense sunlight using modern cells.', 'Elektriği güneş ışığına dönüştürmez, tam tersidir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['By storing electricity in batteries, solar panels eliminate the need for photovoltaic cells.', 'Fotovoltayik hücre ihtiyacını ortadan kaldırmaz, onları kullanır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Solar panels use photovoltaic cells to convert sunlight directly into electrical energy.', 'Özne, fiil, amaç bildiren mastar ve zarf (directly) eksiksiz karşılanmıştır.', [], []],
  ]),

  // TRANSLATION TR -> ENG 3 (Medicine - Antibiotics)
  trans('b8-trans-treng-3', 'medicine', 'Gereksiz antibiyotik kullanımı, dirençli bakteri suşlarının ortaya çıkışını dünya çapında hızlandırmaktadır.', 'C', 'TR_ENG', [
    ['Resistant bacterial strains eliminate the need for antibiotics across global healthcare systems.', 'Dirençli bakteriler antibiyotik ihtiyacını ortadan kaldırmaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['The emergence of antibiotics has completely halted bacterial evolution worldwide.', 'Bakteri evrimini durdurduğu iddiası gerçek dışıdır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Unnecessary antibiotic use is accelerating the emergence of resistant bacterial strains worldwide.', 'Özne (unnecessary antibiotic use), şimdiki zaman ve zarflar tam karşılanmıştır.', [], []],
    ['Bacterial infections have become entirely untreatable because antibiotics are rarely prescribed.', 'Nadir reçete edildiği iddiası gereksiz kullanım ile çelişir.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Accelerating the emergence of bacteria helps pharmaceutical companies discover new antibiotics.', 'İlaç şirketlerine yardım ettiği çıkarımı orijinal cümlede yoktur.', ['UNSUPPORTED_DETAIL'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 4 (Biology - Cellular Respiration)
  trans('b8-trans-treng-4', 'biology', 'Hücresel solunum, glikoz moleküllerini parçalayarak hücrenin kullanabileceği kimyasal enerjiyi açığa çıkarır.', 'A', 'TR_ENG', [
    ['Cellular respiration releases chemical energy that the cell can use by breaking down glucose molecules.', 'Ana eylem, sıfat tümcesi ve vasıta yapısı kusursuz şekilde çevrilmiştir.', [], []],
    ['Cells break down chemical energy in order to synthesize fresh glucose molecules during respiration.', 'Solunum sırasında glikoz sentezlenmez, glikoz parçalanır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Glucose molecules consume cellular energy whenever chemical respiration ceases completely.', 'Glikozun enerji tüketmesi solunumun işleviyle çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['By releasing toxic chemicals, cellular respiration protects glucose stores from depletion.', 'Zehirli kimyasal salınımı orijinal cümlede yer almaz.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Chemical energy is absorbed by cells before glucose molecules are converted into oxygen.', 'Glikoz oksijene dönüşmez.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 5 (Physics - Optics)
  trans('b8-trans-treng-5', 'physics', 'Işık farklı yoğunluktaki bir ortama geçtiğinde, hızı değiştiği için kırılmaya uğrar.', 'D', 'TR_ENG', [
    ['Light refracts when passing into a medium of identical density because its speed increases.', 'Aynı yoğunluk (identical density) değil, farklı yoğunluk (different density) olmalıdır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Because light never changes speed in dense materials, refraction cannot be observed.', 'Hızının değişmediği iddiası kırılma mekanizmasıyla çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Refraction forces light to maintain a constant velocity regardless of medium properties.', 'Sabit hızda kalmaya zorlamaz.', ['FALSE_FRIEND'], ['SEMANTIC_EQUIVALENCE']],
    ['When light passes into a medium of different density, it undergoes refraction because its speed changes.', 'Zaman yantümcesi, neden bildiren yan tümce ve ana eylem tam olarak çevrilmiştir.', [], []],
    ['Light accelerates continuously in order to avoid refraction when entering transparent liquids.', 'Kırılmayı önlemek için hızlandığı iddiası fizik dışıdır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 6 (Environment - Deforestation)
  trans('b8-trans-treng-6', 'environment', 'Ormanların yok edilmesi sadece yaban hayatını tehdit etmekle kalmaz, aynı zamanda toprak erozyonunu da tetikler.', 'B', 'TR_ENG', [
    ['Deforestation prevents soil erosion while providing abundant new habitats for local wildlife.', 'Toprak erozyonunu önlemez ve yeni yaşam alanı sağlamaz, tam tersidir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Deforestation not only threatens wildlife but also triggers soil erosion.', 'Not only ... but also kalıbı ve iki yüklem tam olarak aktarılmıştır.', [], []],
    ['Soil erosion threatens wildlife whenever forests are actively protected by conservationists.', 'Ormanlar korunduğunda değil yok edildiğinde erozyon tetiklenir.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Threatening wildlife is the primary reason why tropical governments encourage deforestation.', 'Yaban hayatını tehdit etmenin ana amaç olduğu bilgisi çarpıtmadır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Although deforestation causes soil erosion, it has no significant impact on wildlife species.', 'Yaban hayatına etkisi olmadığı iddiası not only threatens ile çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 7 (Engineering - Composite Materials)
  trans('b8-trans-treng-7', 'engineering', 'Hafif kompozit malzemeler, yakıt verimliliğini artırmak amacıyla modern yolcu uçaklarında yaygın olarak kullanılmaktadır.', 'C', 'TR_ENG', [
    ['Modern passenger aircraft avoid lightweight composite materials to maintain structural stability.', 'Uçakların kompozit malzemelerden kaçındığı iddiası cümlenin zıddıdır.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Fuel efficiency declines dramatically when modern passenger aircraft adopt composite alloys.', 'Yakıt verimliliğinin düştüğü iddiası artırmak amacıyla ile çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Lightweight composite materials are widely used in modern passenger aircraft to improve fuel efficiency.', 'Edilgen yüklem, yer tamlayıcısı ve amaç mastarı tam karşılanmıştır.', [], []],
    ['Composite materials consume excessive fuel because they add substantial weight to aircraft.', 'Fazla yakıt tükettiği ve ağırlık eklediği iddiası hafiflikle çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Modern passenger aircraft rely on fossil fuels instead of utilizing composite structures.', 'Fosil yakıt kıyaslaması orijinal cümlede yer almaz.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
  ]),

  // TRANSLATION TR -> ENG 8 (Astronomy - Telescopes)
  trans('b8-trans-treng-8', 'astronomy', 'Radyo teleskoplar, optik teleskopların göremediği soğuk gaz bulutlarını ve uzak gök cisimlerini tespit edebilir.', 'E', 'TR_ENG', [
    ['Optical telescopes can observe cold gas clouds that remain completely invisible to radio instruments.', 'Optik ve radyo teleskopların tespit yetenekleri ters çevrilmiştir.', ['SEMANTIC_ROLE_SWAP'], ['SEMANTIC_EQUIVALENCE']],
    ['Radio telescopes fail to detect cold gas clouds because distant celestial bodies emit only visible light.', 'Soğuk gazları tespit edemediği iddiası cümlenin anlamıyla çelişir.', ['POLARITY_INVERSION'], ['SEMANTIC_EQUIVALENCE']],
    ['Cold gas clouds prevent both radio and optical telescopes from examining distant galaxies.', 'Gaz bulutlarının iki teleskop türünü de engellediği iddiası yanlıştır.', ['CAUSE_EFFECT_REVERSAL'], ['SEMANTIC_EQUIVALENCE']],
    ['Because radio telescopes are obsolete, astronomers rely exclusively on optical instruments.', 'Radyo teleskopların eskidiği ve kullanılmadığı iddiası gerçeğe aykırıdır.', ['SCOPE_DRIFT'], ['SEMANTIC_EQUIVALENCE']],
    ['Radio telescopes can detect cold gas clouds and distant celestial bodies that optical telescopes cannot see.', 'Yetebilirlik kipi (can detect), sıfat tamlamaları ve niteleme sıfat tümcesi eksiksiz çevrilmiştir.', [], []],
  ]),
]);
