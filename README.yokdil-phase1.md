# YÖKDİL Fen 80+ · Faz 1

İstenen altı modül `src/types`, `src/services`, `src/components` ve `src/data`
altındadır. Mevcut Python uygulamasından bağımsızdır. React 18+ uyumludur;
bu çalışma React 19, Vite, TypeScript, Dexie, Tailwind ve Lucide ile doğrulanır.

## Kurulum ve doğrulama

```sh
npm ci
npm run typecheck
npm test
npm run build
```

Bu faz bir uygulama ekranı değil, Vite'a entegre edilebilir modül paketidir.
Derleme `dist-yokdil/` üretir; mevcut `dist/` dizinine dokunmaz.
`strict`, `noUncheckedIndexedAccess` ve `exactOptionalPropertyTypes` açıktır.
Kaynakları başka projeye taşırken `src/services/validation.ts`, `src/services/progressMigration.ts`,
`src/types/progress.ts` ve `WordPopover.css` dosyalarını da taşıyın.
Vite yapılandırmasına `@tailwindcss/vite` eklentisini ekleyin. Bileşenin CSS'i
Tailwind preflight yüklemez; sayfa genelindeki eleman stillerini sıfırlamaz.
Hazır derlemeyi kullanıyorsanız üretilen CSS dosyasını da yükleyin.

## Veri sözleşmesi

- `LexicalState`, `Tier`, `PosType` kapalı union tipleridir. Kategorik değerler
  interface ile temsil edilmez. İstenen LexicalRecord alanlarının tamamı bulunur.
- Tarihler UTC epoch milisaniyedir; henüz karşılaşılmadığında `null` kullanılır.
  `stability` ve aralıklar gün, MES/öncelik 0–100 ölçeğindedir.
- `SkillMetrics.mastery`, doğruluk, belirsizlik ve hata oranı **0–1**'dir.
  `SkillGap = 1 - mastery` yalnız kanıt temelli beceri açığı indeksidir;
  hata olasılığı veya sınav puanı değildir. Modelde 80 değil 0.8 saklanır.
  `recency` son kanıtın UTC zamanıdır. On üç beceri adı dondurulmuş şemayla aynıdır.
- `contexts_seen` sadece exposure/telemetri bilgisidir. Pasif karşılaşma, yardımlı,
  yardımsız veya yanlış deneme bu kümeyi büyütebilir. MES veya MASTERED kanıtı değildir.
- `unaided_success_contexts` yalnız doğru `effective_grade >= 2` denemelerle artar.
  Tekildir ve `contexts_seen` alt kümesidir. Çoklu bağlam MES'i yalnız bu alanı kullanır.
- `collocations_mastered` doğrudan yardımsız test edilen kolokasyonları,
  `distractor_errors` kelime/hata sayısını tutar.
- `evidence` ek alanı gecikmeli hatırlama ve çeldirici testlerinin kanıtını saklar.
  Yalnız `last_success_at`, geçmişte 14 gün gecikmeli başarı olduğunu ispatlamaz.
  `exam_sentence_tr` özgün örnek cümlenin çevirisidir.
- `delayed_unaided_correct_count_3d` ve `_14d` ayrı sayımlardır; aynı 14 günlük başarı
  her iki sayımı da artırır. `_14d <= _3d <= unaided_correct_count` doğrulanır.
- Her kayıtta açık `mastery_requirements` saklanır. Entry bunu atlayabilir;
  varsayılan `collocation_required: false`, `distractor_required: true` olur.
  Her kelimeye yapay bir edat testi eklenmez. `susceptible to` entry'sinde kolokasyon
  şartı açıkça `true` olarak işaretlidir. Sözlükteki tek içerik değişikliği bu metadata'dır.
- Tier: 1 değişim/sebep fiilleri, 2 sıfatlar, 3 bağlaçlar, 4 kolokasyon/edat,
  5 temel fen, 6 nadir/spesifik. `susceptible to` sıfat temelli bir kalıp
  olduğu için başlangıç verisinde Tier 2'dir.
- On iki başlangıç maddesinin her birinde en az üç aile üyesi, üç kolokasyon ve
  üç açıklamalı çeldirici vardır. Öncelikler editoryal başlangıç değerleridir;
  doğrulanmış sınav sıklığı iddiası içermez. Cümleler özgün alıştırmalardır.
  Aileler yaygın sınavla ilgili biçimleri kapsar; tüm sözlük türevlerini içermez.

## Scheduler ve MES

```ts
import { scheduleLexicalReview, calculateReviewPriority } from './src/services/lexicalScheduler';

const result = scheduleLexicalReview(word, {
  grade: 3,
  context_id: 'biology-passage-17',
  response_time_ms: 3200,
  reviewed_at: Date.now(),
  assistance_used: false,
  distractor_test: { word: 'inhabit', resisted: true },
}, 1.0);

// Görüntülenen tekrar kuyruğu için o an hesaplanır; lexical_state değiştirilmez.
const reviewPriority = calculateReviewPriority(result.record, Date.now());
```

| Derece | Durum | Yeni stability | Aralık |
| --- | --- | --- | --- |
| 0 | Yanlış | önceki × 0.4 | 1 gün |
| 1 | Yardımlı doğru | önceki × 1.0 | max(2, yeni stability) |
| 2 | Yardımsız yavaş | önceki × 1.5 | yeni stability |
| 3 | Yardımsız güçlü | önceki × 2.2 × kişisel katsayı | yeni stability |

Kişisel katsayı varsayılanı 1.0, geçerli aralık 0.75–1.25'tir. Açıkça kaydedilen
yardım, doğru cevabın derecesini en fazla 1 yapar. Kullanıcı süre ölçümüne göre
2 veya 3 derecesini üst katmanda verir; popover derecelendirme yapmaz.
Başlangıç stability 1 gündür. Sayısal taşmayı önleyen alt sınır 1 milisaniye,
üst sınır 365.000 gündür. Bu sınırlar öğrenme modeli kalibrasyonu değildir.

MES ağırlıkları tam olarak %30/%25/%20/%15/%10'dur. Faz 1 gate audit sonrasında
alt bileşenler aşağıdaki kuralları kullanır; scheduler katsayıları değiştirilmemiştir:

1. **Gecikmeli hatırlama:** son karşılaşmadan en az 14 gün sonra en az bir
   yardımsız doğru cevap varsa 30 puan. İlk karşılaşmadan önce varsayımsal süre yoktur.
2. **Çoklu bağlam:** `25 × min(1, unique(unaided_success_contexts).length / 3)`.
   Pasif encounter, yardımlı başarı ve yanlış cevap katkı vermez.
3. **Doğruluk kanıtı:** `weightedSuccess = 2.5 × yardımsız doğru + 1.0 × yardımlı doğru`;
   `weightedFailure = 2.5 × yanlış`. Kanıt kalitesi (`quality`) başarı ve hata
   ağırlıklarını karşılaştırır; kanıt yeterliliği (`evidenceSufficiency`) başarı
   miktarı arttıkça 1'e yaklaşır. Katkı `20 × quality × evidenceSufficiency`'dir.
   Derece 2 ve 3 bu bileşende aynı 2.5 kanıt katsayısını alır.
4. **Hız:** `15 × min(1, 4000 / ortalama yanıt süresi) × quality`. Henüz süre kanıtı
   yoksa sıfırdır. 4000 ms v1 başlangıç hedefidir; ampirik kalibrasyon iddiası yoktur.
5. **Çeldirici direnci:** `10 × yardımsız direnilen çeldirici / çeldirici içeren deneme`.
   Çeldirici testi yoksa sıfırdır; sıradan doğru cevap direnç kanıtı sayılmaz.

```ts
const weightedSuccess = 2.5 * unaidedCorrect + assistedCorrect;
const weightedFailure = 2.5 * incorrectCount;
const quality = weightedSuccess === 0
  ? 0
  : weightedSuccess / (weightedSuccess + weightedFailure);
const evidenceSufficiency = -Math.expm1(-weightedSuccess / EVIDENCE_SATURATION_K);
const accuracyEvidence = quality * evidenceSufficiency;
const unaided_accuracy = MES_WEIGHTS.unaided_accuracy * accuracyEvidence;
```

`-Math.expm1(-x)`, `1 - Math.exp(-x)` ile eşdeğerdir; sıfıra yakın değerlerde
sayısal hassasiyeti korur. **`EVIDENCE_SATURATION_K = 5`**, scheduler modülünden
dışa aktarılan açık bir **MES v1 kalibrasyon parametresidir**. Birimi gün veya
deneme sayısı değil, ağırlıklı başarılı kanıt birimidir. Beş yardımlı veya iki
yardımsız doğru, yeterliliği yaklaşık %63.2'ye çıkarır. K büyüdükçe doygunluğa
ulaşmak için daha çok kanıt gerekir. Bu başlangıç seçimi ampirik doğrulama iddiası taşımaz.

Tek yardımsız doğrunun accuracy katkısı, tek yardımlı doğrunun **≈2.1706 katıdır**.
İkisi de ilk doğruyla tam 20 puana ulaşmaz. Başarı biriktikçe katkı azalan artışlarla
20'ye yaklaşır; kalıcı doğrusal 2.5× skor farkı beklenmez. Yanlış kanıt yeterliliği
artırmaz; başarı sayısı sabitken kaliteyi ve katkıyı düşürür.

| Denemeler | Evidence quality | Evidence sufficiency | MES accuracy katkısı (0–20) |
| --- | ---: | ---: | ---: |
| Kanıt yok | 0 | 0 | 0 |
| 1 assisted correct (yardımlı) | 1 | 0.181269 | ≈3.6254 |
| 1 unaided correct (yardımsız) | 1 | 0.393469 | ≈7.8694 |
| 1 assisted + 1 wrong | 0.285714 | 0.181269 | ≈1.0358 |
| 1 unaided + 1 wrong | 0.5 | 0.393469 | ≈3.9347 |
| Mixed: 1 assisted + 1 unaided + 1 wrong | 0.583333 | 0.503415 | ≈5.8732 |
| 10 assisted correct | 1 | 0.864665 | ≈17.2933 |
| 10 unaided correct | 1 | 0.993262 | ≈19.8652 |

Tablodaki değerler yalnız 20 puanlık accuracy bileşenidir, toplam MES değildir.
Hız bileşeni önceki doğruluk oranını (`quality`) kullanmaya devam eder;
kanıt yeterliliği yalnız accuracy katkısına uygulanır. Gecikme, bağlam, çeldirici,
seviye koşulları ve 30/25/20/15/10 ağırlıkları korunur. Yalnız yardımlı başarılar
bağlam, gecikmeli hatırlama ve başarılı çeldirici direnci vermez; tek başlarına
en fazla 35 MES üretirler. Toplam MES 0–100 aralığında kalır.

FAMILIAR'a geçiş için **MES ≥60 VE en az bir ≥3 günlük gecikmeli yardımsız doğru**
birlikte zorunludur. Aynı gün on yardımsız doğru, tam bağlam/hız/çeldirici katkısı
ve MES ≈69.87 bile gecikme şartını karşılayamaz.

MASTERED'a geçiş için **MES ≥85 VE en az bir ≥14 günlük gecikmeli yardımsız doğru
VE ≥3 farklı yardımsız başarılı bağlam** birlikte zorunludur. Ayrıca:

- `collocation_required` ise en az bir `collocations_mastered` girdisi gerekir.
- `distractor_required` ise en az bir başarılı yardımsız çeldirici direnci gerekir.

Hiç test yapılmadığında MES sıfırdır. Okuma karşılaşması NEW → SEEN yapar.
Diğer test edilmiş durum LEARNING'dir. Başarılı cevap mevcut seviyeyi düşürmez.
Normal lexical hata MASTERED → FAMILIAR, FAMILIAR → LEARNING, LEARNING → LEARNING
uygular. NEW/SEEN hata sonrasında LEARNING olur. Faz 1'de güvenilir misconception
atfı yoktur; LEARNING → SEEN otomatik uygulanmaz.
**Sadece zaman geçmesi MES veya seviyeyi değiştirmez.** Kazanılmış seviyeler
sonradan MES düşse bile başarı üzerine gerilemez; sayısal eşikler yeni kazanım
koşullarıdır. Validation, kazanılan seviye için gerekli tarihsel kanıtları doğrular.

Tekrar önceliği:
`0.45 × priority_score + 35 × (1 − exp(−gecikme_gün / max(1, stability))) + 0.20 × (100 − MES)`.
Gecikme negatifse sıfıra alınır; sonuç 0–100'dür. Bu açık v1 politika seçimi,
zamanın sadece sıradaki önceliği artırması şartını karşılar. Saklanan
`review_priority` bir önbellektir; canlı kuyrukta `calculateReviewPriority` kullanın.

## Kayıt, yedekleme, veri kaybını önleme

```ts
import {
  seedInitialVocabulary, persistLexicalReview,
  exportProgressToJson, importProgressFromJson, requestPersistentStorage,
} from './src/services/db';

await seedInitialVocabulary(); // Yalnız eksik kelimeleri ekler.
const persistent = await requestPersistentStorage(); // Tarayıcı onayı garanti değildir.

await persistLexicalReview({
  attempt_id: crypto.randomUUID(), // Tek deneme için bir kere üretin; yeniden denemede aynısını kullanın.
  word_id: 'inhibit', question_id: 'q-17', session_id: null,
  skill_ids: ['VOCAB_CONTEXT'],
  review: {
    grade: 3, context_id: 'biology-passage-17', response_time_ms: 3200,
    reviewed_at: Date.now(), assistance_used: false,
  },
});

const json = await exportProgressToJson(); // string; indirme/paylaşma UI katmanının işi.
const imported = await importProgressFromJson(json);
```

Deneme ile kelime güncellemesi tek IndexedDB transaction'ında yazılır. Aynı kimlikli
aynı deneme tekrar sayılmaz; farklı içerikle kimlik yeniden kullanımı hata verir.
Eşzamanlı sekmeler okuma-değiştirme-yazma işlemini aynı transaction'da seri hale getirir.
Gecikme ölçümü gerektiğinde **önce review kaydedin**; test başlamadan hemen önce
`persistEncounter` çağırmak, maruz kalma zamanını değiştirip gecikmeli kanıtı sıfırlar.
Salt okuma/popover yardımı için `persistEncounter` kullanılabilir; MES artışı vermez.

Yedek ve IndexedDB şema sürümü **2**'dir. `scheduler_version` katsayılar aynı kaldığı
için `ass-v1` olarak korunmuştur; düzeltilmiş kanıt sözleşmesi backup v2 ile ayrılır.
JSON biçimi, bütün alanlar, sayılar, sayaç ilişkileri,
benzersiz kimlikler ve kelime/oturum referansları doğrulanır. Bozuk veya desteklenmeyen
şema reddedilir. İçe aktarma 20 MiB ile sınırlıdır; üç tablo tek işlemde yazılır,
herhangi bir hata bütün değişiklikleri geri alır. Veritabanı otomatik silinmez.

### Açık v1 → v2 dönüşümü

`progressMigration.ts` hem eski JSON importu hem Dexie `version(2).upgrade(...)`
için aynı deterministik dönüşümü uygular:

1. Önce eski sözleşme doğrulanır. v1, yeni alanları sessizce kabul eden bir v2
   taklidi değildir; yanlış sürüm etiketi veya bozuk kanıt reddedilir.
2. `contexts_seen` korunur; **`unaided_success_contexts: []` başlatılır**.
   Eski exposure kimlikleri başarı kimliğine kopyalanmaz; eski deneme kayıtları
   da eksik geçmişi tamamlanmış kabul etmek için kullanılmaz.
3. Eski `delayed_unaided_correct_count`, `_14d` olarak korunur. `_3d` için
   `max(_14d, max_unaided_delay_days >= 3 ve unaided_correct_count > 0 ise 1)`
   kullanılır. Bu, v1'in kanıtladığı muhafazakâr alt sayımdır; bilinmeyen olaylar
   uydurulmaz. Yeni başarılar bu sayımlara normal şekilde eklenir.
4. v1 Skill mastery bütün 13 boyutta **100'e bölünür**: 80 → 0.8, 0.8 → 0.008.
   Değer büyüklüğünden ölçek tahmini yapılmaz. v2 veriler yeniden ölçeklenmez;
   v2'de `mastery: 80` hatadır.
5. Eksik entry gereksinimleri güvenli varsayılanlarla, bilinen seed entry'lerinde
   varsa açık metadata ile doldurulur. MES yeni kanıt modeliyle hesaplanır.
   **Eski MASTERED korunmaz**, çünkü doğrulanmış bağlam kimlikleri yoktur;
   yeni FAMILIAR koşulları sağlanıyorsa FAMILIAR, aksi hâlde LEARNING olur.
   Aynı şekilde kanıtsız eski FAMILIAR, LEARNING'e döner. Bu, tek seferlik sözleşme
   düzeltmesidir; zaman aşımına dayalı state düşüşü değildir.
6. Kelime kimlikleri, exposure geçmişi, deneme sayaçları, kolokasyon ve çeldirici
   kanıtları, zamanlar, stability ve deneme kayıtları korunur. Yeni türetilmiş
   öncelik son bilinen karşılaşma zamanı üzerinden hesaplanır; tekrar import tutarlıdır.

Import sonucu `migrated_from: 1` veya `null` bildirir. Native IndexedDB yükseltmesi
aynı transaction içinde yapılır; başarısız doğrulamada eski veri ve sürüm korunur.
`question_attempts` store/JSON anahtarı değiştirilmez. TypeScript entity artık
**`LexicalAttempt`**; Faz 2'nin gerçek `QuestionAttempt` adı için alias bırakılmamıştır.

Varsayılan çakışma davranışı tüm aktarımı durdurmaktır. İsteğe bağlı
`{ on_conflict: 'keep-local' }`, çakışan yerel satırları korur ve bunları sonuçta
raporlar; sayaçları körlemesine toplamaz. Tam yedeği geri yüklemek için boş hedef
veritabanı kullanın. Bu faz cihazlar arası otomatik birleştirme/senkronizasyon içermez.
Depolama hataları çağırana iletilir; kullanıcıya başarılı kayıt gösterilmemeli,
aynı `attempt_id` ile tekrar deneme sunulmalıdır. İlerleme için localStorage yoktur.
Tarayıcı verilerinin kullanıcı tarafından silinmesi veya cihaz kaybı karşısında
IndexedDB tek başına sıfır kayıp garantisi sağlayamaz; dışa aktarılan yedek gereklidir.

## Popover entegrasyonu

```tsx
<WordPopover
  word={word}
  choiceSeed={`${sessionId}:${attemptId}`}
  onAssistance={() => { assistanceUsed.current = true; }}
  onMicroTestResult={(result) => {
    // Bu callback'i ayrı bir alıştırma olarak kaydedin; ana soruyu otomatik cevaplamayın.
    // result.outcome yalnız 'assisted' veya 'incorrect' olabilir.
    handlePracticeResult(result);
  }}
/>
```

WordPopover satır içi bir `button` üretir; başka bir button/anchor içine koymayın.
Varsayılan kademe NEW/SEEN=1, LEARNING=2, FAMILIAR=3, MASTERED=4; test veya deneyler
için `frictionLevel` açıkça verilebilir. 1: açık anlam+kolokasyon; 2: 2 saniye buzlu
anlam ve anında açma; 3: iki şıklı mikro-test ve atlama; 4: polarite/zıt anlam ve
anlamı açma. Tüm yardım türleri `onAssistance` ile bildirilir. Bileşen veritabanına
kendiliğinden yazmaz; yalnız görüntüleme nedeniyle doğru cevap kanıtı üretilmez.

A/B konumu kelime + `choiceSeed` + açılış sırasından yalnız açılış olayında türetilir.
`choiceSeed` verilmezse component'in `useId()` değeri kullanılır. Aynı açık
mikro-testte rerender veya seed değişikliği şıkları oynatmaz; sonraki karşılaşmalarda
iki konum da kullanılabilir. Render sırasında rastgele değer üretilmez.

Kademe 1 / tam reveal görünümünde lemma+POS, anlam, en fazla iki kolokasyon,
bir eş ve bir zıt anlam, bir tipik çeldirici, iki aile türevi ve bir sınav cümlesi
yer alır. Kademe 3/4'te görev öncesinde cevabı ele veren ayrıntılar gizlidir;
“Anlamı göster” her zaman kullanılabilir. Panelin mevcut boyut/taşma davranışı korunur.

Hover gecikmesi 120 ms, tıklama/klavye açılışı anındadır. Ağ isteği yoktur.
150 ms tasarım hedefidir; ana iş parçacığı duraklamalarında mutlak süre garanti
edilemez. Portal sabit konumlandırılır; backdrop, focus trap, body scroll lock,
`inert`, soru butonunda `disabled` veya sanal para yoktur. Dışarı tıklama kapanışı
alttaki soru tıklamasını iptal etmez. `Escape` kapatır; `ArrowDown` panel kontrollerine
geçer. Odak geri dönüşü `preventScroll` kullanır. Dokunmatik tıklama desteklenir.

## Teknik kaynaklar

- [Dexie TypeScript API](https://dexie.org/docs/Typescript)
- [Dexie transaction sözleşmesi](https://dexie.org/docs/Dexie/Dexie.transaction())
- [Dexie version upgrade](https://dexie.org/docs/Version/Version.upgrade())
- [React createPortal olay ve yerleşim davranışı](https://react.dev/reference/react-dom/createPortal)

Bu kaynaklar API kullanımını doğrular; MES veya kelime önceliklerinin bilimsel
kalibrasyonu için kaynak olarak sunulmaz.

## Audit doğrulaması

Mevcut 41 test senaryosu korunmuş, değişen demotion ve kanıt alanları için
beklentileri yeni sözleşmeyle uyumlu hâle getirilmiştir. `gateAudit.test.ts`,
`migration.test.ts` ve genişletilmiş popover testleriyle 89 test korunur.
`mesEvidence.test.ts` içindeki 10 ek testle toplam **99 test** vardır. Yeni testler
erken katkı oranını, 10 başarı karşılaştırmasını, doygunluğu, hata etkisini,
0–100 toplam sınırını ve hız hesabının korunmasını denetler. FAMILIAR/MASTERED
regresyonlarının seviye beklentileri aynıdır; türetilmiş MES sayıları güncellenmiştir.
Dexie yükseltme/rollback testleri `fake-indexeddb` üzerinde gerçek Dexie upgrade
akışını çalıştırır. UI testleri `jsdom` ortamındadır. Faz 2 özelliği eklenmemiştir.

## Faz 2 — Tactical Question Solver entegrasyonu

Yukarıdaki Faz 1 audit bölümü dondurulmuş Faz 1 kapsamını anlatır. Faz 2, ayrı
modüllerle eklenmiştir; Faz 1 kaynakları ve 99 testi değiştirilmemiştir.
Güncel sonuçlar [FAZ2_IMPLEMENTATION_AUDIT.md](FAZ2_IMPLEMENTATION_AUDIT.md) içindedir.
Faz 2 yalnız soru çözümü, cevap sonrası taktik analiz ve telemetri içerir.

Yeni public API `src/questions.ts` içindedir; `src/index.ts` üzerinden de dışa aktarılır.
`QuestionSolver`, soru nesnesini ilk render'da doğrular ve kopyasını sabitler.
Aynı soru kimliğinin içeriğini aktif deneme sırasında değiştirmeyin; revize edilmiş
içerik için yeni/sürümlenmiş bir soru kimliği kullanın.

```tsx
import { QuestionSolver, initialQuestions, questionDb, persistQuestionAttempt } from './src/questions';
import { seedInitialVocabulary } from './src/services/db';

// Uygulama başlangıcında; mevcut kelime ilerlemesini sıfırlamaz.
await seedInitialVocabulary(questionDb);
const words = await questionDb.lexical_store.toArray();
const question = initialQuestions[0];
if (question === undefined) throw new Error('Soru bulunamadı');

const screen = <QuestionSolver
  question={question}
  words={words}
  sessionId={null}
  saveAttempt={(attempt, currentQuestion) =>
    persistQuestionAttempt(attempt, currentQuestion, questionDb)}
/>;
```

`saveAttempt` isteğe bağlıdır; varsayılanı `persistQuestionAttempt`'tır.
Özel veritabanı veya kayıt katmanı kullanırken Promise yalnız kalıcı kayıt
tamamlandığında çözülmelidir. Hata durumunda aynı değişmez deneme yeniden
kaydedilir; yeni ID oluşturulmaz. Başarılı kayıttan sonra **Yeni deneme başlat**
ayrı ID, sıfır sayaçlar, boş yanıt ve `null` güven düzeyiyle başlar.

Örnek ekranı çalıştırmak için:

```sh
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

[Yerel önizleme](http://127.0.0.1:5173/examples/phase2/) 22 özgün soruyu içerir.
Örnek, `yokdil-fen-phase2-demo` adlı ayrı veritabanı kullanır. Kaynaklar
`examples/phase2/` altındadır ve TypeScript kontrolüne dahildir.
Derleme dosya adları Faz 1 tüketicileriyle uyumluluk için korunmuştur;
üretilen JS artık ek Faz 2 export'larını, CSS de iki fazın stillerini içerir.

### Faz 2 veri modeli ve solver sözleşmesi

- `Question` soru bankası içeriğidir; kullanıcı kaydı `QuestionAttempt`'tır.
  Banka `initialQuestions` üzerinden salt okunur içerik olarak sağlanır, telemetri
  tablosuna kopyalanmaz. Tüm örnekler `ORIGINAL_PRACTICE` olarak işaretlidir.
- Sekiz family vardır: Gap Fill, Cloze, Sentence Completion, iki yönlü Translation,
  Paragraph Completion, Irrelevant Sentence ve Reading. Yedi motor vardır;
  iki çeviri yönü aynı semantic-role motorunu paylaşır.
- Gap Fill alt sınıfı soru numarasından çıkarılmaz. Yazarın yapılandırılmış
  `tactical.focus` alanından gelir: VOCAB / GRAMMAR / PREPOSITION / CONNECTOR / STRUCTURE.
  `subclass` verilmişse bu alanla aynı olmalıdır.
- `option_evidence`, her kontrol için kanıt metni ve `true / false / null`
  eşleşmesi taşır. Bunlar editoryal anlam analizidir; motor serbest metne ilişkin
  genel bir NLP çıkarımı yaptığını iddia etmez. Eksik kontrol `INSUFFICIENT` üretir.
- Cloze önceki/hedef/sonraki cümleyi ve tüm pasajı korur. Cloze, Sentence ve
  Paragraph stratejileri beklenen `DiscourseRelation` ile her adayın
  `candidate_relations` değerini karşılaştırır. Polarite ana karar ölçütü değildir.
- Translation, dil ve kelime sırasından bağımsız kanonik `SemanticRoleMap`
  kullanır. Eyleyen, eylem, etkilenen, çatı, kip, zaman, koşul, derece ve ek
  önermeler karşılaştırılır. Yazar eşanlamlı ifadeleri aynı kanonik anlamla kodlar.
- Paragraph, altı boyutlu `AnchorChain` ortalamasını kullanır. `ANCHOR_CHAIN_MIN = 0.65`
  açık bir editoryal başlangıç eşiğidir; öğrenci başarı puanı değildir. Sözcüklerin
  ilk/son konumlarından otomatik bağlantı kararı verilmez.
- Reading, DETAIL / INFERENCE / MAIN_IDEA / REFERENCE / PURPOSE ayrımına göre
  kontrollerini seçer. `EXTREME_QUALIFIER` bir risk sinyalidir. Metin kanıtı varsa
  `only` içeren seçenek doğru olabilir. Sözcük örtüşmesi doğruluk ölçütü değildir.
- On kapalı `DistractorPattern` sınıfı bir şıkta birlikte bulunabilir.
  Serbest taxonomy metni, tekrarlı seçenekler, yanlış family/direction ve
  tutarsız güven/olasılık değerleri Zod ile reddedilir.

Çözüm sırasında yalnız soru, family, süre ve kullanıcı kontrolleri görünür.
Triage, şık analizi, doğrulama ve çeldirici çözümlemesi gönderim sonrasında render
edilir. Cevap anahtarı yerel soru nesnesinde bulunduğundan bu, güvenli sınav sunucusu
veya kopya önleme sistemi değildir; eğitim arayüzünün gösterim kuralıdır.

### Faz 2 telemetri ve etkileşim

`QuestionAttempt`: soru/oturum/deneme kimliği, family/subclass, seçilen yanıt,
doğruluk, yanıt süresi, HIGH/MEDIUM/LOW/**null** güveni, elenen şıklar, tuzak
bayrakları, kelime kimlikleri, yardım sayısı, yanıt değişim sayısı ve UTC zamanını saklar.
İlk seçim değişim sayılmaz; aynı şıkkın tekrar seçilmesi de sayılmaz. Seçili şık
elenebilir; eleme ve bayrak yanıt seçimi değildir. Yanıt doğruluğu yalnız soru
anahtarıyla hesaplanır. Kelime yardımı doğru yanıtı yanlışa dönüştürmez.

Faz 1 `WordPopover` aynen kullanılır. Soru/metindeki tanımlı lemma ve çok sözcüklü
kalıplar tam sözcük sınırlarıyla eşleştirilir. Kök türetme veya belirsiz eşleştirme
yapılmaz. `words_clicked` tıklanan ya da klavyeyle açıkça açılan farklı kelime
kimlikleridir. Hover tek başına tıklama sayılmaz; gösterilen yardım
`onAssistance` üzerinden `hints_used_count` sayacını artırabilir.
Bu entegrasyon lexical scheduler'a review yazmaz ve mikro-test sonucunu ana
sorunun doğruluğuna bağlamaz. Gönderim sonrası yardım değişmez attempt'e eklenmez.

`ErrorAttribution`, yalnız yanlış yanıtlarda bulunur. Tüm kategorilere başlangıç
ağırlığı 1, seçilmiş şıkkın her çeldirici deseninin ilgili kategorisine +2 verilir.
Kelime tıklaması VOCABULARY ve UNKNOWN_TERMINOLOGY için yalnız +0.25 ağırlıktır.
Varsa referans sürenin 1.5 katını aşma TIME_PRESSURE için +0.25'tir; süre sınırı
veya başarısızlık kuralı değildir. Ağırlıklar toplamı 1 olacak şekilde normalize
edilir. Yeterli ayrıştırıcı kanıt yoksa birincil kategori `null`, güven 0 olur.
Bu değerler kalibre edilmiş nedensel olasılık tahmini değil, açıklanabilir bir
olasılık dağılımı biçimindeki başlangıç sezgisidir. Toplam toleransı `1e-6`'dır.

Klavye: soru içindeyken A–E yanıtı seçer, Alt+A–E eleme işaretini değiştirir.
Popover ve metin girişleri bu kısayollardan ayrıdır; Escape özgün popover'a bırakılır.
Seçim native radio, eleme/bayrak `aria-pressed` düğmeleridir. Görünür odak,
fieldset/legend grupları ve semantik analiz başlıkları vardır. Strikeout yalnız
metin dekorasyonu/rengi değiştirir; satır ölçülerini değiştirmez.

### IndexedDB v3 ve tam yedek

`QuestionDatabase`, dondurulmuş `YokdilDatabase` sınıfından türeyip yalnız
`version(3).stores({ solver_attempts: '&id, question_id, session_id, attempted_at, family' })`
ekler. V1→v2 migration'a ve üç tarihsel tabloya dokunulmaz. Özellikle
`question_attempts` hâlâ **LexicalAttempt**, `solver_attempts` ise **QuestionAttempt** saklar.
`session_id` doluysa mevcut `daily_sessions` kaydına referans vermelidir;
bu faz yeni bir oturum motoru oluşturmaz.

Faz 2 uygulamasında tek v3 bağlantısını (`questionDb` veya özel `QuestionDatabase`)
kullanın ve Faz 1 persistence yardımcılarına da bu instance'ı verin. Eski v2
bağlantılarını yükseltme öncesi kapatın; v3'e geçmiş aynı veritabanını yeni bir
yalnız-v2 instance ile açmaya çalışmayın. Faz 1'in ayrı testleri/uygulamaları kendi
v2 veritabanlarında aynen çalışabilir.

`persistSolverAttempts` batch'i tek transaction'dır; bir hata tüm yeni kayıtları
geri alır. Aynı ID + aynı içerik güvenli retry'dır, farklı içerik conflict hatasıdır.
Helpers eski attempt'i `put` ile değiştirmez. Doğrudan Dexie table yazımları bu
doğrulama/değişmezlik sözleşmesinin dışında kalır.

```ts
import { exportSolverProgressToJson, importSolverProgressFromJson, initialQuestions, questionDb } from './src/questions';

const json = await exportSolverProgressToJson(initialQuestions, questionDb);
// Geri yükleme için boş veya çakışmayan bir QuestionDatabase kullanın.
await importSolverProgressFromJson(json, initialQuestions, questionDb);
```

V3 zarfı eski Faz 1 JSON'unu `lexical_progress` altında değişmeden taşır ve
`solver_attempts` ekler. Dört tablo aynı snapshot/import transaction'ındadır;
solver conflict'i lexical importu da geri alır. İçe/dışa aktarma en fazla 20 MiB'dır.
Referans doğrulaması için yedekte kullanılan tüm soruların özgün/sürümlenmiş
kataloğu verilmelidir; bu örnek katalog yedeğin içine kopyalanmaz. Eski Faz 1
export fonksiyonu hâlâ yalnız Faz 1 ilerlemesini kapsar.

Gönderilmemiş taslak yalnız component belleğindedir. Kayıt hatası varsa aynı
attempt bellekte tutulur ve yeniden kayıt düğmesi sunulur; sayfa kapatma/soru
değişimi için kalıcı outbox veya taslak kurtarma bu fazda yoktur.

## Faz 3 — Evidence Update & Learner Model Bridge

Faz 3, değişmez `QuestionAttempt` kaydını soru metadatası ve mevcut tactical
kontrollerle birleştirerek `SkillEvidence[]` üretir. Kanıt geçmişi, ayrı pozitif ve
negatif kütleler üzerinden 13 boyutlu `LearnerSkillVector` değerine dönüştürülür.
MES, lexical scheduler, state gate, WordPopover, Faz 2 motorları ve mevcut
deneme sözleşmesi değişmez. Giriş noktası `src/evidence.ts`; uygulama katmanı
isteğe bağlı kayıt adaptörünü kullanır. Faz 2 örnek arayüzü değiştirilmemiştir.

### Kanıt sözleşmesi ve beceri eşlemesi

`SkillEvidence`, `readonly` alanlardan oluşur; çıkarımın döndürdüğü nesneler ve
diziler derin dondurulur. Yön, kaynak, PRACTICE/TRANSFER türü, güç, güvenilirlik,
yardım durumu, hata sinyali payı, eşleme ağırlığı ve ham denemenin sonucu birlikte
saklanır. ID, JSON ile kodlanan `['skill-evidence-v1', attempt_id, skill_id, source]`
demetidir; ayraç çakışması yaratmaz. `EvidenceRun`, kullanılan bağlamı ve beklenen
kanıt kimliklerini saklar; farklı bağlamla aynı denemeyi yeniden işlemek çakışmadır.

| Beceri | Birincil odak / yardımcı sinyal |
| --- | --- |
| VOCAB_CONTEXT | GAP_FILL/VOCAB, SEMANTIC_FIT kontrolü |
| COLLOCATION_PREPOSITION | GAP_FILL/PREPOSITION, COLLOCATION kontrolü |
| CONNECTOR_DISCOURSE | GAP_FILL/CONNECTOR, CLOZE_TEST, DISCOURSE_RELATION |
| TENSE_ASPECT | GAP_FILL/GRAMMAR, TENSE_ASPECT / TEMPORAL_CONTEXT |
| VOICE_REDUCTION | GAP_FILL/STRUCTURE, VOICE / REDUCTION |
| SENTENCE_COMPLETION | SENTENCE_COMPLETION |
| TRANSLATION_SEMANTICS | Her iki çeviri family’si |
| PARAGRAPH_COMPLETION | PARAGRAPH_COMPLETION |
| COHESION_COHERENCE | IRRELEVANT_SENTENCE, READING/REFERENCE; referans/devam kontrolleri |
| READING_DETAIL | READING/DETAIL |
| READING_INFERENCE | READING/INFERENCE ve PURPOSE |
| MAIN_IDEA | READING/MAIN_IDEA |
| PACING_STAMINA | Boyut korunur; bu fazda blok telemetrisi olmadığı için kanıt üretilmez |

Birincil beceri ağırlığı 1, `skill_ids` içindeki diğer beceriler .6, mevcut
solver'ın destekli tactical kontrollerinden gelen ek beceriler .3'tür. Aynı
beceride en büyük ağırlık alınır, sonra soru içinde toplam 1'e normalize edilir.
Family yanında subclass/focus, reading subtype ve açık skill_ids kullanılır.
PACING_STAMINA, soru skill_ids listesinde yer alsa bile tekil sorudan üretilmez.
`TIMED_PERFORMANCE` kaynak adı gelecekteki sözleşme için ayrılmıştır; v1 doğrulaması
bu kaynaktan kayıt kabul etmez. Bu faz bir blok veya oturum motoru içermez.

### Açık v1 parametreleri: doğrulanmış bilimsel katsayılar değildir

Tüm katsayılar `services/evidence/calibration.ts` içindeki `EVIDENCE_V1` ve
`CONFIDENCE_QUALITY_V1` sabitlerindedir. Eşleme katsayıları `mapping.ts` içinde
belgelenmiştir. Mevcut 22 ORIGINAL_PRACTICE sorudan prior, güçlük dağılımı veya
başarı modeli öğrenilmemiştir. `difficulty`, varsa editoryal metadatadır.

```text
assistance = (hint > 0 veya açılan kelime > 0) ? .55 : 1
process = assistance / (1 + .15 × hints)
                     / (1 + .10 × distinctWords)
                     / (1 + .10 × optionChanges)
difficultyFactor = .75 + .25 × (difficulty ?? .5)
timingFactor = benchmark yoksa veya süre <= benchmark ise 1
               aksi hâlde max(.7, benchmark / responseTime)
confidenceQuality = HIGH:1, MEDIUM:.9, LOW:.7, null:.9
eliminationQuality = doğru şık elenmişse 0; aksi hâlde doğrulanan yanlış elemeler / 4
positiveStrength = .8 × process × difficultyFactor × timingFactor
                   × confidenceQuality × (.9 + .1 × eliminationQuality)
                   × mappingWeight
```

Benchmark seçimi: önce kişisel, yoksa genel; yoksa süre varsayımı yapılmaz.
Çok hızlı yanıt ek ödül getirmez. Düşük güven veya kötü süreç, doğru sonucu
NEGATIVE yapmaz. Confidence yalnız bu zayıf süreç çarpanında kullanılır; kendisi
bir beceri olayı veya mastery değeri değildir. Ayrıca her HIGH/MEDIUM/LOW için
ayrı `ConfidenceCalibrationRecord { attempt_id, confidence, correct }` saklanır;
null için kalibrasyon kaydı üretilmez. Burada ayrıca güven skoru hesaplanmaz.

Yanlış yanıtta ErrorAttribution v1 dağılımı yalnız `attribution_weight` olarak
kullanılır; ampirik veya nedensel olasılık değildir. VOCABULARY ve
UNKNOWN_TERMINOLOGY → VOCAB_CONTEXT; CONNECTOR → CONNECTOR_DISCOURSE;
GRAMMAR → mevcut TENSE_ASPECT/VOICE_REDUCTION becerileri arasında ağırlıklı pay;
READING_INFERENCE → aynı beceri; DISTRACTOR → sorunun birincil becerisi.
Soru eşlemesinde olmayan beceriye ceza verilmez. CARELESS/TIME_PRESSURE ve
eşlenmeyen paylar dağıtılmadan kalır; kalan ağırlıklar yeniden normalize edilmez.

```text
negativeStrength = .8 × assistance × attributionWeight × mappingWeight
resultReliability = PRACTICE:.7 veya TRANSFER:.9
negativeReliability = resultReliability × (.35 + .25 × attributionConfidence)
```

Attribution payı kütle hesabında ikinci kez çarpılmaz. Yanlış sonuca rağmen payı
sıfır olan becerinin olay yönü NEUTRAL ve gücü 0'dır; tarihsel doğruluk için
deneme bağlantısı korunur. Kelime açmak tek başına tam kelime hatası değildir.

Üç yanlış şıkkın mevcut solver ile doğrulanarak elenmesi, doğru veya seçilmiş
şıkkın bu sayıya katılmaması ve doğru şıkkın hiç elenmemesi koşuluyla birincil
beceriye `.2 × mappingWeight × process` gücünde ayrı TACTICAL_DECISION gelir.
Bu, kullanıcının gerekçeyi bildiği iddiası değildir. `identified_relation`
bağlamında gönderim öncesi açıkça kaydedilen öğrenci ilişkisi beklenen ilişkiyle
uyuşursa CONNECTOR_DISCOURSE için `.3 × mappingWeight × process` gücü kullanılır.
Sadece cevap anahtarında ilişki bulunması öğrenci başarısı sayılmaz. Tactical
güvenilirlik .4; transferde `.4 × .9/.7`. Yanlış final yanıtı böylece aynı denemede
zayıf pozitif süreç ve negatif sonuç kanıtı taşıyabilir. Her deneme/beceri için
toplam güvenilir kütle en fazla 1 olacak şekilde sınırlandırılır.

### Practice ve Transfer

`EvidenceContext.transfer`, `unseen`, `exam_like`, `prior_practice_at` içerir.
Son alan, yeni sorunun değil, ilgili becerinin önceki çalışma zamanıdır.
TRANSFER için iki bayrak true, deneme yardımsız ve süre farkı en az 14 gün olmalıdır.
Koşullar eksikse PRACTICE üretilir. Gelecekteki geçmiş çalışma zamanı reddedilir.
Geçerli koşullar kanıtın `transfer_context` alanında korunur; `transfer_level`
TRANSFER için 1, PRACTICE için 0'dır. Sonuç kaynağı iki türde de QUESTION_RESULT
olur; ikinci bir TRANSFER olayı eklenerek aynı yanıt iki kez sayılmaz.

Koşulların gözlemlenmesi çağıran katmanın sorumluluğudur. Persistence, kayıtlı
aynı soruya daha önceki maruziyet varsa unseen iddiasını reddeder. Geri tarihli
kayıt veya yedek birleştirme de mevcut transfer olayını geçersiz kılamaz; ilgili
işlem atomik olarak reddedilir. Bu, doğrulanmış sınav puanı kazanımı değildir.

### Tarihsel aggregation

```text
recencyWeight = .75 + .25 × exp(-ageDays / 180)
eventMass = strength × reliability × recencyWeight
P = pozitif olay kütleleri toplamı
N = negatif olay kütleleri toplamı
mastery = P / (8 + P + N)
uncertainty = max(coverageFloor, 1 / (1 + (P + N) / 4))
```

8, sabit ve ihtiyatlı v1 başlangıç kütlesidir; soru bankasından öğrenilmiş prior
değildir. Tek deneme mastery'yi en fazla 1/9'a çıkarabilir. P ve N ayrı döndürülür.
Coverage floor: aynı beceride iki family'den azsa .35; en az iki family fakat üç
farklı sorudan azsa .15; diğer durumda .05. Sıfır bilgilendirici kütlede belirsizlik
1 kalır. Yalnız ilişkili beceriler güncellenir; PACING_STAMINA korunur. Bu mastery
bir sınav doğruluk olasılığı veya puan tahmini olarak yorumlanmamalıdır.

`evidence_count`, beceriye bağlı farklı deneme sayısıdır; NEUTRAL sonuçları da
içerir. `unaided_accuracy` ve `assisted_accuracy`, yalnız QUESTION_RESULT/TRANSFER
sonuç satırlarının tam geçmişinde, mappingWeight ağırlıklı doğru/toplam oranıdır.
Tactical başarı accuracy'ye yeni bir doğru yanıt eklemez. `error_rate`, yanlış
sonuçların `mappingWeight × attributionWeight` toplamının tüm sonuçların
mappingWeight toplamına oranıdır. Örneğin tek .4 attribution, error_rate=.4 olur.
Accuracy ve error_rate, strength/reliability ile yeniden çarpılmaz; anlamları
tarihsel yanıt oranı ve paylaştırılmış hata oranıdır.

`aggregateEvidence` ve `updateLearnerSkillVector` pure fonksiyonlardır.
İkinci argüman **etkilenen becerilerin tam kanıt geçmişi** olmalıdır, yeni olay
delta'sı değil. Mevcut vector sadece etkilenmeyen boyutların cache'idir. Daha az
deneme içeren bariz eksik geçmiş reddedilir; aynı sayıda değiştirilmiş bir geçmişi
bu kontrol tek başına ispatlayamaz. Güvenilmeyen veriler önce persistence/import
doğrulamasından geçmelidir. Varsayılan değerlendirme zamanı en son olay zamanıdır;
isteğe bağlı `asOf` bu zamandan önce olamaz. `loadLearnerSkillVector` tam kayıt
geçmişini denetleyerek modeli sıfır başlangıçtan yeniden üretir.

### IndexedDB v4 ve entegrasyon

`EvidenceDatabase extends QuestionDatabase` yalnız üç tablo ekler:

| Tablo | İndeks |
| --- | --- |
| skill_evidence | &id, skill_id, attempt_id, created_at, source |
| confidence_calibration | &attempt_id |
| evidence_runs | &attempt_id, question_id, created_at |

V1/v2/v3 migration ve mevcut dört tablo aynıdır. Uygulamada tek v4 instance kullanın;
Faz 1/2 helper'larına da bunu verin. Önceki bağlantıları yükseltmeden önce kapatın.
Mevcut v3 denemeleri migration sırasında otomatik işlenmez; `processStoredAttempt`
ile açıkça, idempotent biçimde işlenebilir. Geçmiş değiştirilmez.

```ts
import {
  evidenceDb, persistAttemptWithEvidence, processStoredAttempt,
  loadLearnerSkillVector, exportEvidenceProgressToJson, importEvidenceProgressFromJson,
} from './src/evidence';
import { initialQuestions } from './src/questions';
import type { Question, QuestionAttempt } from './src/questions';

// QuestionSolver saveAttempt prop'una verilebilir; frozen component'i değiştirmez.
const saveAttempt = (attempt: QuestionAttempt, question: Question) =>
  persistAttemptWithEvidence(question, attempt, {}, evidenceDb);

// Daha önce saklanmış bir deneme için:
// await processStoredAttempt(question, attemptId, {}, evidenceDb);
const model = await loadLearnerSkillVector(initialQuestions, evidenceDb);
const json = await exportEvidenceProgressToJson(initialQuestions, evidenceDb);
await importEvidenceProgressFromJson(json, initialQuestions, evidenceDb);
```

`persistAttemptWithEvidence`, ham deneme + kanıt + receipt + calibration kaydını
tek transaction'da yazar. Depolama hatası tamamını geri alır. Aynı ID/içerik retry
no-op; değişen ID içeriği conflict'tir. Helpers yalnız `add` kullanır; eski kanıtı
`put`, update veya delete yapmaz. Doğrudan Dexie table yazımları bu sözleşmenin
dışındadır; okuma ve yedekleme denetimi fark edilen bozulmayı sessizce kullanmaz.

Yeni JSON zarfı `yokdil-evidence-progress`, schema_version=4'tür. İçinde değişmeyen
v3 yedeği `question_progress` altında ve üç yeni tablo bulunur. Yedi tablo aynı
snapshot/import transaction'ındadır. Sadece sayısal sınırlar değil, referanslar,
deterministic ID'ler, transfer koşulları, receipt üyeliği ve kaynak denemeden
yeniden üretilen **tam içerik eşitliği** doğrulanır. Bozuk bir kanıt, nested lexical
import dahil tüm işlemi geri alır. İçe aktarma merge'dür; üzerine yazmaz. Sınır
20 MiB; soru kataloğu yedeğin dışında, özgün ve aynı sürümde sağlanmalıdır.
Eski export fonksiyonları yeni kanıt tablolarını içermez; Faz 3 için yeni çift
kullanılmalıdır. Geçerli geçmişi geri tarihli verilerle birleştirirken transfer
çakışması çıkarsa iki yedeği koruyun; kayıtlar otomatik silinmez veya düşürülmez.

Sınırlar: blok/pacing çıkarımı, kalıcı learner snapshot cache, ampirik difficulty
ve attribution kalibrasyonu, score prediction, Score Leak, NBA, Performance
Estimator, Daily Session Engine, VerifiedScoreGain ve ML/LLM muhakemesi yoktur.
Son doğrulama sonuçları `FAZ3_IMPLEMENTATION_AUDIT.md` dosyasındadır.

## Faz 4 — Score Leak Priority Map + Next Best Action

**Semantik sözleşme:** Faz 3 mastery, ampirik olarak kalibre edilmiş sınav
doğruluk olasılığı değildir. Faz 4 yalnız `SkillGap = 1 - mastery` kullanır.
SkillGap bir kanıt temelli beceri açığı indeksidir. Score Leak bir **çalışma
önceliği haritası**, ExpectedTrainingValue ise **dakika başına göreli çalışma
değeri indeksi** anlamındadır. Hiçbiri sınav puanı kaybı, hata ihtimali, puan
kazanımı veya garanti edilen öğrenme miktarı değildir. İndeksler yüzde olarak
gösterilmemelidir. Eski frozen learner tipindeki mastery'yi hata olasılığına
bağlayan tarihsel yorum, bu fazın semantik sözleşmesi olarak kullanılmaz.

Yeni giriş noktası `src/priority.ts`:

- `deriveEvidenceCoverage(history)`: denetlenmiş, tam Faz 3 geçmişinden kapsam.
- `buildScoreLeakMap(learner, context, config?)`: 13 becerinin açıklanabilir öncelik haritası.
- `planNextBestAction(learner, candidates, context, availableMinutes, config?)`: uygun adayların sıralanması.
- `loadNextBestActionPlan(request, database?, config?)`: mevcut v4 veritabanından tek, salt okunur ve denetlenmiş snapshot ile plan.

Faz 1/2/3 motorları, tipleri, testleri ve migration'ları değiştirilmedi. Faz 4
yeni bir şema veya ilerleme kaydı yazmaz. Yeni UI ve soru içerikleri eklenmedi;
Faz 2 örnek arayüzü frozen kaldı. Motor, uygulamanın sağladığı çalışma adaylarını
değerlendirir. Plan üretmek adayın uygulanması, soru çözümü veya yeni kanıt yazımı
anlamına gelmez.

### Kanıt kapsamı ve belirsizlik

Coverage, beceri başına bilgilendirici farklı deneme, soru, family, yardımsız
deneme, transfer denemesi sayıları ve son bilgilendirici zamanı taşır. Pozitif
veya negatif güç >0 ve reliability >0 olan olaylar bilgilendiricidir. NEUTRAL ve
sıfır güvenilirlikte olaylar kapsam oluşturmaz. Aynı denemenin sonuç ve tactical
satırları tek deneme sayılır; tam retry tekrarı kapsamı artırmaz. Aynı soru tekrarları
farklı soru sayılmaz. Bilinen empty history ile sağlanmayan coverage ayrıdır:
ilki KNOWN/0, ikincisi UNKNOWN/null olarak saklanır. Eksik kapsam uydurulmaz.

```text
amount = 1 - exp(-informativeAttemptCount / 8)
breadth = .6 × min(questionCount / targetQuestionCount, 1)
        + .4 × min(familyCount / targetFamilyCount, 1)
coverageIndex = amount × breadth               # kapsam bilinmiyorsa 0
support = (1 - uncertainty) × coverageIndex
SkillGap = 1 - mastery
practiceNeed = SkillGap × (.25 + .75 × support)
diagnosticNeed = .6 × uncertainty + .4 × (1 - coverageIndex)
```

Buradaki `support` da olasılık değildir; mevcut kanıtın göreli desteğidir.
Az kanıt + yüksek belirsizlik, güçlü bir beceri zayıflığı hükmü yerine değerlendirme
ihtiyacını yükseltir. `.25` tabanı, daha az kanıtla da düşük ağırlıklı çalışma
önerilebilmesini sağlar. Aynı maliyetteki cold-start diagnostic adayı practice
adayından daha yüksek değer alır. Yardımsız/transfer sayaçları şeffaflık için
çıktıda korunur; v1 coverage formülünde ek çarpan olarak tekrar kullanılmaz.

### Tekrar ihtiyacı ve öncelik

```text
ageDays = (asOf - lastInformativeAt) / 86_400_000
ageFactor = 1 - exp(-ageDays / retentionWindowDays)
retentionNeed = ageFactor × support × (.25 + .75 × mastery)

priorityComponents.practice = 100 × examRelevance × .45 × practiceNeed
priorityComponents.diagnostic = 100 × examRelevance × .35 × diagnosticNeed
priorityComponents.retention = 100 × examRelevance × .20 × retentionNeed
priorityIndex = üç bileşenin toplamı                 # [0,100] indeks
```

Bilinen bilgilendirici zaman yoksa ageDays=null ve retentionNeed=0 olur. Zaman
geçmesi mastery'yi değiştirmez; ageFactor ölçülmüş unutma olasılığı değildir.
`examRelevance`, göreli editoryal ilgidir; sınavdaki soru sayısı veya puan ağırlığı
değildir. Harita bileşenleri ayrı döner; yüksek toplam öncelik her zaman doğrudan
çalışma ihtiyacı demek değildir, değerlendirme veya tekrar kaynaklı olabilir.

Sıralama priorityIndex azalan, eşitlikte mevcut SKILL_IDS sırasıdır. Açıklama
etiketleri sayısal skoru değiştirmez: coverage<.5 LIMITED_COVERAGE;
uncertainty≥.5 UNCERTAIN_EVIDENCE; gap≥.5 ve support≥.25 SUPPORTED_SKILL_GAP;
retentionNeed≥.25 RETENTION_NEED; relevance=0 NO_EXAM_RELEVANCE.

### Eylem değeri ve seçim

`TrainingAction`: id, title, kind, format, available, expected_minutes ve toplamı
1 olan benzersiz, pozitif beceri hedef ağırlıklarıdır. Adayı sağlayan katman,
gerçek içerik/kaynak bulunduğunu ve kullanılabilirliğini doğrular; motor içerik
varmış gibi bir aday oluşturmaz. Tahmini süre, sağlanan editoryal maliyettir.

| Eylem türü | Hizalandığı ihtiyaç |
| --- | --- |
| DIAGNOSTIC | diagnosticNeed: kapsam ve belirsizlik |
| TARGETED_PRACTICE | practiceNeed: desteklenen beceri açığı |
| RETENTION_REVIEW | retentionNeed: eski bilgilendirici kanıt ve destek |

```text
targetValue = 100 × targetWeight × alignedNeed × examRelevance × trainability
trainingValueIndex = Σ targetValue                 # [0,100] indeks
effectiveMinutes = max(5, expectedMinutes)
ExpectedTrainingValue = trainingValueIndex / effectiveMinutes
```

`trainability` göreli editoryal çalışılabilirliktir, beklenen puan artışı değildir.
5 dakikalık etkin maliyet tabanı çok kısa tahminlerin sıralamayı aşırı yükseltmesini
önler. Bütçe kontrolü gerçek expectedMinutes üzerinden yapılır; minimum etkin
maliyet hayali bir süre rezervasyonu değildir. Her becerinin katkısı çıktıdadır.
Birden fazla hedef ağırlıklı ortalama oluşturur; hedef sayısını artırmak otomatik
ek ödül getirmez. ETV birimi `PRIORITY_INDEX_PER_MINUTE`'tır.

Kullanılamayan, bütçeyi aşan, değeri sıfır olan veya hedeflerinde destekli tekrar
ihtiyacı bulunmayan review adayları elenir. Her adayın eleme nedenleri döner.
PACING_STAMINA hedefi içeren aday TIMED_BLOCK olmalıdır; tek soru süresi pacing
önerisine gerekçe olmaz. Bu kontrol blok verisi toplama/puanlama motoru değildir;
Faz 3'ün pacing kanıtı üretmeme sınırı değişmez. Uygulama gerçekten sağlayamadığı
bir blok için available=true göndermemelidir.

Aday sıralaması: ETV azalan, toplam değer azalan, süre artan, kimlik sözlük sırası.
Aday giriş sırasından ve locale'den bağımsızdır. Seçilen aday haritadaki en yüksek
satıra ait olmak zorunda değildir; eylemin türü, maliyeti, çoklu hedefleri ve
kullanılabilirliği birlikte değerlendirilir. Uygun aday yoksa
`NO_ELIGIBLE_ACTION`, selected=null döner. Çalışma zorla başlatılmaz veya kilitlenmez.

### V1 yapılandırması

`PRIORITY_V1` içindeki bütün sayılar editoryal başlangıç parametreleridir; mevcut
22 soru veya ampirik sınav verisinden öğrenilmemiştir. Üretim çağrısında tüm config
verilebilir; beceriye özel profiller context.profiles içinde geçilebilir.

| Parametre | Varsayılan |
| --- | --- |
| evidence_saturation_k | 8 |
| question_breadth_weight | .6; kalan .4 family breadth |
| unsupported_practice_floor | .25 |
| uncertainty_diagnostic_weight | .6; kalan .4 eksik kapsam |
| retention_mastery_floor | .25 |
| minimum_effective_minutes | 5 |
| priority weights | practice .45, diagnostic .35, retention .20 |
| exam_relevance / trainability | Her beceride 1 / 1; bilinmeyen farklar uydurulmaz |
| retention_window_days | 30 |
| target_question_count / target_family_count | 5 / 2; beceri profilinden değiştirilebilir |

Zod; finite sayıları, kapalı taxonomy'yi, ağırlık toplamlarını, pozitif maliyetleri,
benzersiz hedef/aday kimliklerini ve coverage tutarlılığını denetler. NaN/Infinity,
negatif süre, bilinmeyen alan/beceri, gelecekteki recency ve learner evidence_count
değerini aşan coverage reddedilir. `as_of` açık UTC epoch girdisidir; pure motor
Date.now okumaz. Pure API aynı snapshot'a ait, önceden denetlenmiş learner ve
tam coverage bekler. Coverage'ın tamlığını yalnız sayılardan kanıtlayamaz.

### Mevcut v4 veritabanına doğrudan bağlantı

```ts
import { evidenceDb } from './src/evidence';
import { initialQuestions } from './src/questions';
import { loadNextBestActionPlan, type TrainingAction } from './src/priority';

// Uygulamanın gerçekten sunabildiği seçenekleri bu fonksiyona geçirin.
export async function recommendNextAction(
  availableActions: readonly TrainingAction[],
  asOf: number,
  availableMinutes: number,
) {
  return loadNextBestActionPlan({
    questions: initialQuestions,
    actions: availableActions,
    as_of: asOf,
    available_minutes: availableMinutes,
  }, evidenceDb);
}
```

Adaptör, Faz 3'ün tam kanıt denetimini çağırır; model ve coverage aynı salt okunur
IndexedDB transaction'ında elde edilir. Bozuk kaynak kanıtından öneri üretilmez.
Yedi v4 tablo değişmez, yeni migration veya plan kaydı yoktur. Kullanıcı eylemi
gerçekleştirdiğinde yeni telemetri mevcut Faz 2→3 hattından geçer; planın tahmini
değeri mastery'ye başarı kanıtı olarak yazılamaz.

Bu faz Performance Estimator, VerifiedScoreGain, sınav puanı tahmini, ampirik
olasılık/IRT kalibrasyonu, günlük oturum yürütücüsü veya otomatik eylem uygulaması
içermez. Son doğrulama: `FAZ4_IMPLEMENTATION_AUDIT.md`.

## Faz 5 — Daily Session Engine & Adaptive Execution Orchestrator

Faz 5 yalnız plan önermekle kalmaz: süre bütçesine göre gerçek içeriği seçer,
değişmez planı saklar, gerçek çalışmayı append-only olaylarla kaydeder ve
tamamlanan uygun zamanlı bloklardan ayrı pacing kanıtı üretir. Önceki dört fazın
kaynakları, testleri ve sözleşmeleri değişmez. Yeni giriş noktası `src/sessions.ts`.
Mastery hâlâ kanıt temelli bir indekstir; oturum tamamlandı diye mastery artırılmaz.

### Süre bütçesi, gerçek adaylar ve kısıtlı planlama

Varsayılan EMERGENCY=10, NORMAL=25, INTENSIVE=50 dakikadır. Açık
`available_minutes` bunları geçersiz kılar; 0'dan büyük, en fazla 180 kesirli veya tam
dakika desteklenir. Planın blok süreleri toplamı bütçeyi aşmaz. Soru sayısı sonuçtur.
10/24/27/30/47/60 dakika test edilmiştir; süreyi sabit soru kotasına çeviren kural yoktur.

`buildSessionCandidatePool` verilen özgün soru kataloğu, gerçek lexical kayıtlar ve
deneme geçmişini kullanır. Tanılama/çalışma adayları gerçek sorulara; retention
adayları daha önce denenmiş sorulara; lexical adayları karşılaşılmış ve gerçekten
due kelimelere bağlıdır. NEW/hiç karşılaşılmamış sözcükler SRS tekrarı gibi sayılmaz.
Süre tahmini: en az üç örnek varsa aynı soru, yoksa aynı family yanıt sürelerinin
medyanı; ardından kişisel/genel benchmark veya 2 dakika fallback. Soru başına
1–10 dakika sınırı editoryaldir. Lexical tahmin mevcut response_time_avg_ms veya
20 saniye fallback; mevcut ortalama 10–120 saniye aralığına sınırlandırılır.

Zamanlı adaylar yalnız `timed_enabled=true` istendiğinde, mevcut sorulardan
asgari beş soruluk gruplar olarak oluşturulur. Bu, oturumun toplam soru kotası
değildir. Daha büyük veya farklı aile karışımlı gerçek bloklar açık
`SessionCandidate` ile sağlanabilir. Kullanılamayan, kaynağı bulunmayan veya daha
önce bu oturuma tahsis edilmiş candidate/question/lexical kimlikleri seçilmez.
Aynı sorunun farklı aday türleri aynı plana birlikte giremez. REFLECTION yalnız
açık, boş olmayan bir yansıtma istemiyle sağlanır; otomatik hayali etkinlik eklenmez.

`planDailySession` şu sırayı izler:

1. Due lexical rezervi; frozen scheduler'ın canlı `calculateReviewPriority` değerine göre seçim.
2. Yüksek uncertainty/düşük coverage için bütçesi sınırlı diagnostic exploration.
3. Bütçe ve kaynaklar elverdiğinde farklı question family kapsamı.
4. Faz 4 ETV değerleriyle, beceri tekrarını ve ağır yük yığılmasını gözeten kalan seçim.
5. Ayrı ve deterministik blok sıralaması.

Tam global optimum iddiası yoktur; açıklanabilir kısıtlı sezgiseldir. Lexical
rezerv varsayılan .25 bütçeyi aşamaz; yalnız due içerik kalırsa kalan süre boş
bırakılır. Tek beceri sınırı .45'tir; uygun alternatif kalmazsa soft constraint
esnetilir ve not eklenir. Diagnostic toplamı normalde .25, cold start'ta .60
bütçeyle sınırlanır; TIMED_BLOCK da bu paya dahildir. Aile kapsamı varsayılan 2'dir.
İçerik veya süre yetmezse eksik kapsam açık not olur, hayali blok oluşturulmaz.

Yük HIGH/MEDIUM/LOW olarak taşınır. Reading, translation ve paragraph adayları
başlangıçta HIGH, diğer sorular MEDIUM, lexical LOW kabul edilir; bu editoryal
bir sezgidir. Mevcut hafif alternatifler ağır blokların arasına alınır. Varsayılan
ordering orta yükle açılmayı, zor çalışmayı ortaya ve hafif/retention çalışmayı
sona almayı tercih eder; ağır yığılmayı önlemek gerekirse açılış tercihi esnetilir.
Yalnız ağır içerik kalırsa zorunlu boş etkinlik eklenmez. VALUE_FIRST alternatif
sıralama da aynı ağır yük sınırını korur.

### Parametreler

`SESSION_V1` ve `PACING_V1` bilimsel doğrulanmış sabitler değil, açık v1
kalibrasyon parametreleridir. Eski 22 sorudan prior, hız dağılımı veya zorluk
kalibrasyonu öğrenilmez; yalnız kullanıcının mevcut gerçek süre geçmişi kullanılabilir.

| SESSION_V1 | Varsayılan |
| --- | --- |
| mode_minutes | 10 / 25 / 50 |
| lexical_reserve_fraction | .25, yapılandırmada en fazla .50 |
| max_single_skill_fraction | .45, uygun alternatif yoksa esnek |
| diagnostic_fraction / cold_start_diagnostic_fraction | .25 / .60 |
| family_coverage_floor | 2 |
| max_consecutive_high | 1, uygun hafif içerik varsa |
| question_default_minutes / lexical_default_minutes | 2 / 1⁄3 |
| speed_min_samples | 3 |
| idle_lease_ms / inactivity_ms | 30.000 / 120.000 |
| ordering | MEDIUM_FIRST_LIGHT_FINISH |

### Değişmez plan ve gerçek yürütme

`SessionPlan` yalnız başlangıç bütçesi, seçilen bloklar, kaynak kimlikleri,
gerekçeler ve kullanılan config snapshot'ıdır. `AdaptiveStudySession` bu plan ile
`SessionEvent[]` günlüğünün yeniden oynatılmış görünümüdür. İlk planned_minutes
değişmez; uzatmalar total_budget_minutes değerine eklenir. Blok planned_minutes ve
actual_duration_ms ayrı alanlardır. Durum etiketleri: Planlandı, Devam ediyor,
Tamamlandı, Atlandı, Yarım bırakıldı. Duraklatma ACTIVE durumundaki engaged=false
ile temsil edilir; tamamlandı veya yarım bırakıldı ile karıştırılmaz.

Başlatma, blok başlatma, pause/resume, heartbeat, gerçek question/lexical sonucu,
tamamlama, skip, abandon ve extension olayları append-only'dir. Olaylar
session_id+sequence sırasını taşır. Her yazım expectedRevision ister; eski bir
revision ile yarışan yazım tamamen geri alınır. Aynı event ID+aynı içerik retry
no-op, farklı içerik conflict'tir. Gerçek attempt birden fazla bloğa veya oturuma
yeniden mal edilemez. Soru/kelimeyi aktif blokta açıkça tekrar denemek için yeni
attempt ID ve önceki attempt'e `retry_of` gerekir; bu otomatik seçim değildir.

`recordSessionQuestion`, tamamlanmış ham QuestionAttempt'i frozen Faz 3
`persistAttemptWithEvidence` hattından geçirir ve aynı transaction'da session
olayını yazar. `recordSessionLexicalReview`, frozen Faz 1 review/scheduler hattını
kullanır. Planlama, skip veya reflection completion bu fonksiyonların yerine
geçemez. Normal blok tüm gerçek maddeleri tamamlanmadan tamamlandı işaretlenemez;
zamanlı blok kısmi tamamlanabilir, fakat pacing qualification ayrıca yapılır.
Kısmi çalışmanın ardından skip/abandon, önceden tamamlanmış gerçek attempt'leri silmez.

Tarihsel DailySession tipi kullanılmaya zorlanmaz. Faz 5 adaptörlerine verilen
ham question/lexical attempt'lerde `session_id=null` kalır; adaptive session ve
block bağlantısının asıl kaynağı yeni olay günlüğüdür. Böylece eski daily_sessions
tablosunda temsili veya yanıltıcı bir aktivite satırı oluşturulmaz. Pacing
extension kanıtındaki session_id ise açıkça adaptive session referansıdır.

### Restore, zaman ve tarayıcı entegrasyonu

`restoreAdaptiveSession` plan ve olaylardan ACTIVE/PLANNED oturumu, aktif bloğu,
gerçekten tamamlanmış item ID'lerini ve gerçek attempt ID'lerini geri getirir.
Tamamlanmamış soru taslağı kaydedilmez; uygulama gönderilmemiş cevabı boş taslakla
açar. Önceden tamamlanan maddeler completed_question_ids/completed_lexical_ids
üzerinden ayırt edilir. Restore tek başına yeni evidence yazmaz.

Clock, duvar süresi/aktif süre/pause süresini ayırır. Ardışık telemetri aralığı
lease'i aşmışsa bütün aralık ihtiyatlı biçimde pause sayılır; saatlerce açık
kalmış sekme geri geldiğinde geçmiş süre otomatik çalışma sayılmaz. Bütün süreler
milisaniyedir; epoch girdileri artan ve açık olmalıdır.

İsteğe bağlı `attachSessionActivityClock` görünürlük, focus ve son kullanıcı
etkileşiminin zamanını kullanır. Pointerdown/keydown sadece bu tek zamanı yeniler;
tuş değeri, konum, içerik veya hareket geçmişi toplanmaz. Hareketsizlik sınırından
sonra görünür/focused sekme de engaged=false olur. Heartbeat aralığı lease'in
üçte biri, en fazla 10 saniyedir. Uzun süre etkileşimsiz okuma ihtiyatlı biçimde
eksik sayılabilir; inactivity_ms yapılandırılabilir. Aktivite süreleri dikkat
veya psikoloji ölçümü değildir.

Adapter'ın `stop()` metodu unmount/navigation sırasında çağrılır. Ani kapanmada
son pause olayının yazılması garanti edilemez; eksik heartbeat lease'i bu boşluğu
pause olarak ele alır. onError kayıt hatalarını uygulamaya iletir. Clock ile
kullanıcı komutları revision yarışına girerse restore edip aynı command/attempt
kimliğiyle yeniden denemek gerekir; başarısız transaction kısmi kanıt bırakmaz.

### Uzatma ve sınırda uyarlama

`planSessionExtension` yalnız aktif blok kalmadığında fresh audited snapshot ile
yeni süre parçasını planlar; önceki tüm tahsis edilmiş kimlikleri dışlar.
`extendAdaptiveSession` sonucu yeni EXTEND olayı olarak ekler. Önceden tamamlanmış
bir oturum, kullanıcının bu açık isteğiyle devam edebilir; ilk FINISH olayı ve
ilk plan değişmez. Normal item gönderimi NBA hesaplaması veya plan değişimi yapmaz.

`adaptAdaptiveSession`, blok sınırında henüz başlanmamış eski blokları ADAPTATION
nedeniyle atlandı olarak kaydeder ve yeni planı **aynı transaction** içinde ekler.
Yeni plan geçersizse skip olayları da geri alınır. Blok başarısızlığında SKIP_BLOCK
reason=FAILURE ile sınır oluşabilir. Süre aşımı uygulamaya actual/planned üzerinden
görünür; otomatik her-soruda oynak replan yapılmaz. Devam eden bir blok için önce
kullanıcı kontrollü tamamlama veya failure/skip sınırı gerekir.

### Qualified timed block ve pacing extension

`TimedBlockResult` yalnız gerçekten tamamlanmış explicit TIMED_BLOCK için kaynak
olay ve actual attempt'lerden türetilir. Planlanan soru sayısı, farklı tamamlanan
soru sayısı, doğru/yardımlı sayılar, aktif süre, hedef bütçe, aile karışımı ve
başlangıç/bitiş ayrı tutulur. Planın kendi başına doğruluk bilgisi yoktur.

| PACING_V1 qualification | Varsayılan |
| --- | --- |
| Planlanan ve gerçekten tamamlanan asgari farklı soru | 5 |
| Asgari aktif süre | 180.000 ms |
| Asgari tamamlanma oranı | .80 |
| En yüksek yardımlı oranı | .20 |
| Tekrar denemesi | Qualification dışı |
| Yanıt süreleri | Pozitif, toplamı ölçülen aktif süreyi aşamaz |

Qualification geçmezse pacing kanıtı yoktur; sonucu ve nedenleri yine saklanır.
Geçerse, doğruluk en az .70 olduğunda aktif/bütçe oranı ≤1.10 POSITIVE,
≥1.50 NEGATIVE; aradaki bölge NEUTRAL'dır. Doğruluk .70 altındaysa yalnız zaman
üzerinden pacing zayıflığı hükmü verilmez, NEUTRAL kalır. Güç, yön bilgilendiriciyse
`.30 × completionRatio`, aksi hâlde 0; reliability=.50'dir. Bunlar ampirik
performans olasılıkları değildir. Tek yavaş soru hiçbir durumda bu yolu açmaz.

Faz 3'ün reserved TIMED_PERFORMANCE reddi **aynen korunur**. Ayrı
`pacingBlockEvidenceSchema` ve `pacing_evidence` store'u bu kaynağı Faz 5'te
etkinleştirir. SkillEvidence alanlarına block_id, pacing_version ve gerçek
supporting_attempt_ids eklenir. Kaynağın terminal gerçek attempt'i bağlantı
noktasıdır; hayali question/attempt oluşturulmaz. Faz 3 skill_evidence tablosuna
block kaydı konmaz; eski v4 import/export sözleşmesi bozulmaz.

`loadSessionLearnerSnapshot` önce frozen content learner'ı doğrular, sonra
yalnız PACING_STAMINA'yı tam ve denetlenmiş block geçmişinden günceller. Pozitif
ve negatif kütleler ayrıdır; Faz 3'teki sabit prior 8 ve recency çarpanıyla
`P/(8+P+N)` kullanılır. Uncertainty en az .35'tir. Accuracy, block sonuçlarındaki
gerçek yardımlı/yardımsız soru sayılarından; error_rate, negatif blockların .30
ağırlıklı sinyalinden türetilir. Diğer 12 boyut aynen geçer. Pacing coverage'da
bir bilgilendirici blok bir terminal attempt bağlantısı sayılır; question/family
kapsamı bu gerçek bağlantıların farklı kimlikleridir, blok sayısıyla şişirilmez.
Her bloğun tam aile karışımı ayrıca sonuç kaydında korunur.

En az 8 tamamlanan soruda ilk ve son eşit yarının accuracy farkı
`degradation_signal` olarak kaydedilebilir; tek/az soru için null'dır. Bu yalnız
within-block performance degradation signal'dır. Soru zorluğu/aile karışımı
farkları ayrıştırılmaz; sağlık, yorgunluk tanısı veya otomatik mastery cezası değildir.

### IndexedDB v5 ve tam yedek

`SessionDatabase extends EvidenceDatabase` yalnız dört tablo ekler:

| Tablo | Kaynak |
| --- | --- |
| adaptive_sessions | Değişmez başlangıç SessionPlan; anahtar session_id |
| session_events | Append-only yürütme/uzatma günlüğü; benzersiz ID, session+sequence ve attempt_ref |
| timed_block_results | Olaylardan yeniden üretilebilir gerçek blok sonuçları |
| pacing_evidence | Yalnız qualified block extension kanıtları |

V4→v5, eski yedi tablonun içeriklerini byte-equivalent korur. Uygulamada tek v5
instance kullanılmalı; eski helper'lara da bu instance verilmeli, önceki v4
bağlantıları yükseltmeden önce kapatılmalıdır. Başlangıç planı için tam create
retry, çalışmaya başlanmış olsa bile mevcut planı geri getirir; parametre değişimi
aynı kimlikle yeni plan yaratmaz. Başka session'a ait block ID kabul edilmez.

`exportSessionProgressToJson` / `importSessionProgressFromJson`, frozen v4 zarfı
ve dört yeni tabloyu tek v5 zarfında taşır; boyut sınırı 20 MiB'dır. İçe aktarma
append-safe merge'dür. Olay sıraları, kaynak bağları, plan bütçesi, block kimlikleri,
gerçek sonuçlar ve pacing kanıtı yeniden üretilerek denetlenir. Değiştirilmiş
sayısal sonuç veya source referansı, eski tablolara yapılmış yeni eklemeler dahil
tüm importu geri alır. V4 export yeni session/pacing tablolarını kapsamaz; tam
Faz 5 yedeği için yeni API kullanılmalıdır. Local-first kayıt, tarayıcı verilerinin
işletim sistemi tarafından silinmesine karşı yedekleme ihtiyacını ortadan kaldırmaz.

### Entegrasyon örneği

```ts
import {
  sessionDb, createAdaptiveSession, executeSessionCommand,
  restoreAdaptiveSession, attachSessionActivityClock,
  exportSessionProgressToJson,
} from './src/sessions';
import { initialQuestions } from './src/questions';

export async function startStudy(sessionId: string) {
  const now = Date.now();
  const planned = await createAdaptiveSession({
    id: sessionId, session_id: sessionId, mode: 'NORMAL',
    available_minutes: 27, as_of: now, timed_enabled: false,
  }, initialQuestions, sessionDb);

  const active = await executeSessionCommand({
    id: crypto.randomUUID(), session_id: sessionId, at: now,
    command: { type: 'START' },
  }, planned.revision, initialQuestions, sessionDb);

  const clock = await attachSessionActivityClock(sessionId, initialQuestions, {
    onError: (error) => console.error('Oturum zamanı kaydedilemedi', error),
  }, sessionDb);
  return { active, stopClock: clock.stop };
}

// Restore sonrası completed_question_ids ile kalan maddeler ayrılır:
export const restoreStudy = (id: string) => restoreAdaptiveSession(id, sessionDb);
export const backupStudy = () => exportSessionProgressToJson(initialQuestions, sessionDb);
```

Aktif blok START_BLOCK ile açılır. Gerçek QuestionAttempt, QUESTION event'iyle
`recordSessionQuestion` üzerinden; gerçek LexicalReview, LEXICAL event'iyle
`recordSessionLexicalReview` üzerinden gönderilir. Event zamanı ile attempt'in
tamamlanma zamanı aynı olmalıdır. Question draft oluşturmak veya seçili şıkkı
değiştirmek session submission değildir. COMPLETE_BLOCK yalnız gerçek çalışma
tamamlandığında çağrılır. Uzatma için fresh plan + EXTEND, uyarlama için aynı
planla adaptAdaptiveSession kullanılır. Bu faz domain/services katmanıdır; yeni
dashboard veya çalışma ekranı eklenmemiştir.

`FutureMockSignals` yalnız ilerideki trigger girdilerini taşımak için tiptir;
sabit gün/soru takvimi, full mock scheduling veya estimator çalıştırmaz.
Faz 5 Performance Estimator, sınav puanı tahmini, VerifiedScoreGain, ampirik IRT/
error-attribution kalibrasyonu, ML veya LLM soru üretimi içermez.
Son doğrulama raporu: `FAZ5_IMPLEMENTATION_AUDIT.md`.

## Faz 6 — Evidence-Based Performance Range

Yeni giriş `src/performance.ts`; ana barrel da aynı API'yi dışa aktarır.
Bu katman mevcut v5 kayıtlarından salt okunur sonuç türetir. Yeni tablo,
migration, dependency, UI, ağ çağrısı veya progress yazımı yoktur.

### Gözlem, aralık ve ölçek

`observed`, gerçek qualified bloklardaki uygun, yardımsız, ilk denemelerin
doğru/yanlış sayısı, observed accuracy ve Wilson aralığıdır. Bu başarı oranı,
beceri mastery değeri değildir; priority/SkillGap/NBA girdisi kullanılmaz.

`exam_range` yalnız yeterlilik ve kapsam eşiklerinin tamamı geçerse doludur.
Ölçeği **0–1 doğru cevap oranı**, kapsamı `EXAM_LIKE_PRACTICE_PROXY`,
`calibrated=false` ve `point_scale=null`'dır. READY, aşağıdaki editoryal
genelleme eşiklerinin geçtiğini belirtir; kalibre edilmiş ÖSYM performansı
veya bir puanı alma ihtimali değildir. Repository'de sınav blueprint'i ve
80 soru/100 puan dönüşüm sözleşmesi bulunmadığından puan dönüşümü eklenmedi.

`INSUFFICIENT`: uygun gözlem yok. `OBSERVED_ONLY`: gözlem var, sınav benzeri
örneklem/çeşitlilik zayıf. `PROVISIONAL`: en az 60 sınav benzeri gözlem ve iki
aile var fakat kapsam, dağılım veya belirsizlik eşiklerinden biri geçmedi.
`READY`: bütün eşikler geçti. İlk üç durumda `exam_range=null` tipi zorunludur.
Başarı oranının yüksek veya düşük olması tek başına readiness belirlemez.

### Kaynak ve eligibility

`PerformanceSnapshot` tam soru kataloğu, **bütün** soru denemeleri, başlangıç
planları, session olayları, timed sonuçlar, pacing kanıtları ve Faz 3 extraction
receipt/kanıtlarını taşır. Önceden yalnız başarılı/qualified blokları süzmek
yasaktır: ilk deneme denetimi unqualified veya blok dışı geçmişi de kullanır.
Database adaptörü bu geçmişi tek read-only transaction'da alır.

Faz 5 state machine yeniden oynatılır; timed sonuç ve pacing kaydı gerçek
attempt'lerden yeniden üretilip kayıtla karşılaştırılır. Qualified bayrağı veya
session completion tek başına yeterli değildir. Phase 5 minimum 5 soru,
180 saniye aktif süre, .80 completion ve en fazla .20 yardım koşulları korunur.
Phase 6, qualified blok içinde kalan yardımlı denemeleri de örneklemden çıkarır.

İlk kayıtlı question attempt kullanılır; sonraki doğru cevap önceki yanlışı
değiştiremez. Aynı metin/options farklı question ID ile verilirse normalize
edilmiş içerik anahtarıyla tekrar yakalanır. Eşzamanlı ilk deneme belirsizliği
dışlanır. Aynı ID/aynı veri tek sayılır; çatışan ID veya bozuk kayıt tüm snapshot'ı
`INVALID_SOURCE_RECORDS` ile istatistik üretmeden reddeder. Yanlış cevapları
ayıklayarak daha yüksek accuracy oluşturulmaz.

LexicalAttempt/micro-test, incomplete/skip, unqualified, süre kanıtı yetersiz,
yalnız planlanmış ve 30 günden eski gözlemler dahil edilmez. Tamamlanan qualified
blok, çevresindeki session daha sonra abandoned olsa bile gerçek kanıt olarak
kalır. Resume ve extension olayları frozen kurallarla yeniden oynatılır.

Genelleme alt kümesi ayrıca kayıtlı Faz 3 TRANSFER koşullarını ister: yardımsız,
unseen ve exam_like context, en az 14 günlük prior-practice gecikmesi. Context
mevcut uygulamanın gözlem bildirimidir; estimator bunu cevap sonucundan türetmez.
Soru denemesi olmayan pasif exposure ve dışarıdan görülmüş cevaplar mevcut
şemadan ispatlanamaz. Bunlar her sonuçta provenance assumptions olarak belirtilir.

Mevcut v5 şeması gerçek/sentetik stream ayrımı saklamıyor. Bu nedenle
`PerformanceSource` zorunlu entegrasyon girdisidir: `USER_EXECUTION` veya
`IMPORTED_USER_EXECUTION`, gerçek kayıt hattını bilen uygulama tarafından
verilmelidir. Kullanıcının başarı beyanı değildir. `UNKNOWN`, `DEMO` ve
`SYNTHETIC` kaynaklar dışlanır; bilinen `yokdil-fen-phase2-demo` veritabanı
etiketine rağmen hiçbir zaman gerçek kullanıcı kaynağı sayılmaz. İçe aktarılmış
verinin kökeni bilinmiyorsa `UNKNOWN` kullanılmalıdır. Şema değişmeden sahte bir
kaynak etiketini veya kendi içinde tutarlı sahte olayları kriptografik olarak
tespit etmek mümkün değildir; böyle bir güvence verilmez.

### Coverage ve yeterlilik

`coverage`, genelleme alt kümesinin kapsamıdır; `observed_coverage` bütün uygun
gözlemleri ayrı gösterir. 8 mevcut question family ve `primaryQuestionSkill`
üzerinden 12 içerik becerisi sayılır. PACING_STAMINA içerik sorusu sınıfı değildir.
İkincil skill etiketleri tek soruyu birkaç kapsam örneğine dönüştürmez.
Covered, missing, underrepresented listeleri ile family/block/session
concentration, aralık kapısını gerçekten etkiler.

| PERFORMANCE_V1 | Eşik ve gerekçe |
| --- | --- |
| min_questions | 60 = 12 içerik becerisi × 5; varsayılan sınav soru sayısı değil |
| min_questions_per_family | 5; tek örnekle aile temsili ilan edilmez |
| min_questions_per_skill | 3 birincil örnek; çoklu etiket şişirmesi engellenir |
| min_blocks / min_sessions | 4 / 2; tek çalışma kümesi yeterli değildir |
| max_family_fraction | .35; tek ailenin çoğunluğu engellenir |
| max_block_fraction / max_session_fraction | .35 / .65; tek yürütmenin baskınlığı sınırlanır |
| max_interval_width | .25; örneklem belirsizliği ayrıca sınırlandırılır |
| max_age_ms | 30 gün; eski gözlemler güncel aralığı daraltmaz |

Eşikler merkezi, sürümlü **v1 yayınlama tercihleri**dir; bilimsel doğrulanmış
yeterlilik veya resmi sınav dağılımı değildir. Mevcut 22 özgün alıştırma sorusu
tek başına READY üretemez. Testlerdeki geniş katalog yalnız fixture'dır; gerçek
question pool'a soru eklenmedi.

### İstatistik ve belirsizlik

İki taraflı Wilson score interval, sabit confidence=.95 ve z=1.959963984540054
kullanır. n=0 için aralık/accuracy null; geçersiz sayımlar programmer error'dur.
0 doğru, tüm doğru, tek örnek ve büyük n sınırları testlidir. Yöntem referansı:
[NIST, Confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Bu nominal confidence seviyesi kaynak güvenilirliğini, coverage'ı veya sınav
başarısı olasılığını ifade etmez. Ortak passage/blok bağımlılığı, seçilim yanlılığı,
soru zorluğu ve farklı bir sınav dağılımı Wilson tarafından düzeltilmez; model
çıktısında bu karşılaştırılabilirlik varsayımı açıkça yer alır. IRT, difficulty
normalization veya ampirik puan kalibrasyonu yoktur.

Raw oranlar domain içinde tutulur. `outwardPercentRange` alt sınırı aşağı, üst
sınırı yukarı tam yüzdeye yuvarlar; birimi `CORRECT_RESPONSE_PERCENT`'tir.
Bu sunum sınav puanına dönüştürülmemelidir. `predictedScore` alanı yoktur.

### Entegrasyon

```ts
import { loadPerformanceEstimate, outwardPercentRange } from './src/performance';
import { sessionDb } from './src/sessions';
import { initialQuestions } from './src/questions';

export async function readPerformance(asOf: number) {
  // Yalnız gerçek kullanıcı kayıt hattının kökeni biliniyorsa bu türü kullanın.
  const result = await loadPerformanceEstimate(initialQuestions, asOf, {
    kind: 'USER_EXECUTION', reference: 'local-user-execution-stream',
  }, sessionDb);
  if (result.status !== 'READY') return { result, displayRange: null };
  return { result, displayRange: outwardPercentRange(result.exam_range) };
}
```

Saf giriş `estimatePerformance(snapshot)`; alt katmanlar
`selectPerformanceEvidence`, `analyzePerformanceCoverage`, `wilsonInterval`.
Fonksiyonlar sistem saatini/random/ağı kullanmaz ve girdiyi değiştirmez.
Provenance method/version/as_of/confidence, block/attempt referansları ve
machine-readable exclusion nedenlerini taşır. Gerçek database/IO arızaları
exception olarak iletilir; yetersiz kanıt normal domain sonucudur.

Detaylı repository denetimi, frozen dosya listesi ve son test sonuçları:
`FAZ6_IMPLEMENTATION_AUDIT.md`.

## Faz 7 - Configured Blueprint Exam Simulation & Calibration Evidence

Giriş noktası: `src/exam.ts`. Saf fonksiyonlar; yeni tablo/migration, UI,
ağ, `Date.now()` veya random yoktur. Sistem saati yerine caller `as_of` verir.

- **Blueprint açıkça verilir.** Repository'de resmî YÖKDİL dağılımı yoktur;
  `validateExamBlueprint` aile hedeflerinin toplamını ve primary-skill
  minimumlarının aile kotalarıyla birlikte (max-flow) karşılanabilirliğini doğrular.
  `source.verification`: `UNVERIFIED | INTERNAL | OFFICIAL_VERIFIED`.
- **Form.** `analyzeExamPool` / `buildExamForm`: geçersiz, çatışan ID, tekrar
  ID ve aynı içerik (farklı ID) elenir. Aynı seed + aynı havuz → girdi
  sırasından bağımsız aynı form ve fingerprint. Yetersiz havuz
  `INSUFFICIENT_POOL` raporudur; yalnız `allow_partial` ile `PARTIAL` form
  üretilir ve bu form yalnız `PRACTICE_SIMULATION` ile çalışır.
- **Exposure.** Önceki attempt/recorded exposure → `SEEN`. Attempt yokluğu
  `UNSEEN` değildir → `UNKNOWN`. `UNSEEN` yalnız form anındaki
  `CONTROLLED_INVENTORY` referansı ile verilir.
- **Simulation journal.** `createExamSimulation` → `appendExamSimulationEvent`
  → `projectExamSimulation`. Portable transcript; Faz 5 saf projection'ı
  duvar/aktif süre için yeniden kullanılır, study session veya mastery'ye yazılmaz.
  Strict modda kesinleşmiş cevap değiştirilemez ve süre sonrası gönderim reddedilir.
- **Kalibrasyon.** `qualifyExamSimulation` her zaman transcript'ten yeniden
  hesaplar: `NOT_ELIGIBLE` (bozuk/çatışan) / `PRACTICE_ONLY` (herhangi bir neden) /
  `PARTIAL_CALIBRATION` / `FULL_CALIBRATION` (yalnız `FULL` + `OFFICIAL_VERIFIED`).
  Pause, interrupt, extension, yardım, cevap revizyonu, bilinmeyen monitoring,
  SEEN/UNKNOWN exposure, eksik tamamlanma, unverified blueprint kalibrasyonu düşürür.
  `official_exam=false`, `official_score_mapping=null`.
- **Faz 6 adaptörü.** `selectCalibrationPerformanceEvidence` yalnız qualified
  kalibrasyonları alır; attempt/question/içerik tekrarlarını bir kez sayar,
  çatışan journal kopyalarından temizini seçmez, `exam_range=null` döner ve
  Faz 6 READY durumunu değiştirmez.

22 soruluk üretim havuzu tam bir configured blueprint'i karşılamaz; bu bir
`INSUFFICIENT_POOL` sonucudur, motor hatası değildir. Ayrıntı:
`FAZ7_IMPLEMENTATION_AUDIT.md`. Faz 8 uygulanmadı.
