# FAZ 3 IMPLEMENTATION AUDIT

Tarih: 3 Ekim 2026

## Repository inspection

React/Vite kitaplık projesi, strict TypeScript, Dexie v1–v3 şemaları, Zod
doğrulaması, 13 boyutlu LearnerSkillVector, QuestionAttempt, tactical motorlar,
ErrorAttribution v1 ve mevcut testler incelendi. Uygulanabilir AGENTS.md bulunmadı.
Yeni bağımlılık veya proje yapılandırması eklenmedi. Depodaki Python uygulamasına
ve diğer çalışma dosyalarına dokunulmadı.

Başlangıçta **161/161** test geçti. Değişiklik öncesi alınan SHA-256 özetleriyle
dondurulmuş **40/40 kaynak, örnek ve test dosyasının** birebir aynı kaldığı son
kontrolde doğrulandı. Başlangıç özetleri `tmp/phase3-baseline/frozen-hashes.json`
içindedir. MES, lexical scheduler, state gate, WordPopover, Faz 1 migration,
QuestionFamily, QuestionAttempt, tactical solver ve ErrorAttribution değişmedi.

### Eklenen dosyalar

| Grup | Dosyalar |
| --- | --- |
| Tip ve dışa açılan API | `src/types/evidence.ts`, `src/evidence.ts` |
| Kanıt servisleri | `src/services/evidence/calibration.ts`, `validation.ts`, `mapping.ts`, `extractEvidence.ts`, `aggregateEvidence.ts`, `updateLearnerModel.ts`, `db.ts` |
| Testler | `tests/yokdil/phase3/fixtures.ts`, `evidence.test.ts`, `database.test.ts` |
| Rapor | `FAZ3_IMPLEMENTATION_AUDIT.md` |

Mevcut dosyalardaki eklemeler: `src/index.ts` içine tek barrel export satırı ve
`README.yokdil-phase1.md` sonuna Faz 3 açıklaması. Önceki 161 test değiştirilmedi.

## Evidence model

`SkillEvidence` kimlikleri JSON tuple ile deterministiktir. Kaynak deneme, soru,
oturum, beceri, family, yön, kaynak, tür, güç, güvenilirlik, assistance,
attribution_weight, mapping_weight, sonuç ve zaman birlikte saklanır.
Transfer koşulları kayıt üzerinde korunur. Çıkarım pure ve derin immutable'dır.
`EvidenceRun` üretimde kullanılan bağlamı ve tam kanıt üyeliğini saklar.
Confidence HIGH/MEDIUM/LOW + doğru/yanlış ayrı `ConfidenceCalibrationRecord`
olayıdır; null korunur ve bunun için kalibrasyon kaydı üretilmez.

Sadece çıkarım veya doğrulanmış import ile elde edilen geçmiş aggregation'a
verilmelidir. Pure aggregation'ın elinde soru/deneme kataloğu olmadığı için
kaynak doğrulamasını persistence katmanı yapar.

## Skill mapping

Mevcut 13 SkillId korunur. Family, subclass/tactical focus, reading subtype,
skill_ids ve solver'ın mevcut tactical kontrolleri birlikte değerlendirilir.
Birincil beceri 1, açık ikincil beceri .6, tactical ek beceri .3 ağırlıkla başlar;
aynı beceride maksimum alınır ve toplam 1'e normalize edilir. Aynı family farklı
reading subtype veya focus ile farklı beceriye eşlenebilir.

12 içerik becerisi için çıkarım vardır. 13. boyut PACING_STAMINA modelde ve tip
sözleşmesinde korunur; bu fazda nitelikli blok telemetrisi bulunmadığından bu
boyuta kanıt yazılmaz. Tek soruda gecikme veya TIME_PRESSURE sinyali pacing cezası
üretmez. TIMED_PERFORMANCE v1'de ayrılmış fakat kabul edilmeyen bir kaynaktır.

## Positive evidence

Doğru sonuç POSITIVE kalır. .8 taban güç; assistance, ipucu/kelime/şık değişimi,
editoryal difficulty, mevcut benchmark'a göre süre, zayıf confidence kalite
çarpanı, doğrulanan eleme kalitesi ve mapping_weight ile azaltılır.
Assistance çarpanı .55'tir. Üç ipucu, düşük güven ve kötü süreç tam yardımsız
kanıttan belirgin biçimde daha zayıftır. Hızlı yanıt için ek ödül verilmez.

Üç doğrulanmış yanlış eleme birincil beceriye zayıf tactical kanıt sağlayabilir.
Kullanıcının gerekçesi eleme işaretlerinden türetilmez. CONNECTOR_DISCOURSE için
açık `identified_relation` gözleminin gönderim öncesi kaydedilmiş ve beklenen
ilişkiyle eşleşmiş olması gerekir. Yanlış final yanıtı, ayrı pozitif tactical
ve negatif sonuç kanıtlarıyla birlikte temsil edilebilir.

## Negative evidence

Yanlış sonuç yalnız eşlenen hata sinyalleriyle paylaştırılır. Güç:
`.8 × assistance × attribution_weight × mapping_weight`.
Payı sıfır olan beceri NEUTRAL/0 olur; historical accuracy için sonuç satırı
korunur. Yardım negatif kanıt gücünü de azaltır; tarihsel yanlış yanıtı silmez.

## Attribution handling

ErrorAttribution dağılımı bir **attribution signal** olarak kullanılır; ampirik
veya nedensel olasılık iddiası yoktur. VOCABULARY/UNKNOWN_TERMINOLOGY kelimeye,
CONNECTOR bağlaca, GRAMMAR mevcut tense/voice becerilerine, READING_INFERENCE
çıkarıma, DISTRACTOR birincil soru becerisine gider. CARELESS, TIME_PRESSURE ve
ilgisiz beceri payları dağıtılmadan kalır. Kalan paylar yeniden normalize edilmez.

Negatif güvenilirlik, sonuç güvenilirliğinin `(.35 + .25 × attributionConfidence)`
katıdır. .4 kelime payı tam kelime hatasına dönüşmez; aynı pay kütlede tekrar
çarpılmaz. Tek kelime tıklaması tam negatif kelime kanıtı sayılmaz.

## Practice vs Transfer

Practice sonuç güvenilirliği .7, transfer .9'dur. Transfer için unseen,
yardımsızlık, en az 14 gün gecikme ve exam-like koşulları birlikte gerekir.
Eksik koşullar practice kalır. Gecikme, yeni sorunun değil ilgili becerinin
önceki çalışma zamanından ölçülür. Bağlam gözlemleri çağıran katmandan gelir.

Persistence, aynı sorunun önceki kayıtlı denemesini saptadığında unseen iddiasını
reddeder. Yeni geri tarihli kayıt veya import, mevcut transfer olayını sessizce
geçersiz kılamaz. Transfer için ayrıca ikinci bir sonuç olayı üretilmez.
VerifiedScoreGain veya sınav puanı iddiası yoktur.

## Mastery aggregation

Tam geçmişte `mass = strength × reliability × recencyWeight` hesaplanır.
`recencyWeight = .75 + .25 × exp(-ageDays / 180)`; eski kanıtın katkısı sıfırlanmaz.
Aynı deneme/beceri içindeki sonuç+tactical toplam güvenilir kütlesi en fazla 1'dir.
Pozitif P ve negatif N ayrı izlenir: `mastery = P / (8 + P + N)`.
Sabit 8 başlangıç kütlesi, 22 sorudan öğrenilmiş bir prior değildir.
Tek deneme mastery'yi en fazla 1/9'a çıkarabilir; değer daima [0,1]'dedir.

`updateLearnerSkillVector(current, history)` yalnız etkilenen becerileri tam
geçmişten yeniden hesaplar. Mevcut mastery tekrar kanıt olarak eklenmez.
`loadLearnerSkillVector` veritabanındaki tam kanıt geçmişini denetleyip yeniden
hesaplar. Kalıcı snapshot cache eklenmedi.

Yardımsız ve yardımlı accuracy ayrı, mapping_weight ağırlıklı tarihsel doğru/toplam
oranlarıdır. Tactical satırlar yeni yanıt sayılmaz. Hata oranı yanlış sonuçların
mapping_weight × attribution_weight toplamının tüm sonuç mapping_weight
toplamına oranıdır. Tek .4 attribution için error_rate=.4; yanına bir eşit ağırlıklı
doğru eklendiğinde .2'dir. `evidence_count` farklı denemeleri sayar.

## Uncertainty

`max(coverageFloor, 1 / (1 + (P + N) / 4))` kullanılır. İki family'den azda .35,
iki family fakat üç farklı sorudan azda .15, yeterli kapsamda .05 tabanı vardır.
Bilgilendirici kütle yoksa belirsizlik 1 kalır. Unrelated skill değerleri ve
belirsizlikleri değişmez; tekrarlanan kelime soruları reading inference güveni
yaratmaz. Bu değerler bir v1 sezgisel modeldir, doğrulanmış başarı olasılıkları değildir.

## Persistence

**Append-only ve idempotency: PASS.** EvidenceDatabase üç tablo ekler:
skill_evidence, confidence_calibration, evidence_runs. Ana kanıt indeksleri
`&id, skill_id, attempt_id, created_at, source` şeklindedir.
persistAttemptWithEvidence, Faz 2 kayıt servisini dış transaction içinde çağırır;
ham deneme ve üç kanıt tablosu atomik yazılır. Tam retry no-op, değişen içerik veya
bağlam conflict'tir. Storage hatası yeni denemeyi de geri alır.

V4 JSON zarfı değişmeyen v3 yedeğini içerir. Yedi tablo aynı transaction'dadır.
Zod finite sayı/aralık/taxonomy/kimlik/transfer kontrollerinin yanında bütün
kanıtlar kaynak deneme ve receipt bağlamından yeniden üretilir. In-range güç
değiştirme, eksik/fazla kayıt, sahte referans ve kalibrasyon değişikliği reddedilir.
Herhangi bir hata nested Faz 1 importu dahil tamamını geri alır. İçe aktarma merge
ve en fazla 20 MiB'dır; özgün sürümde tam soru kataloğu gerekir.

## Migration

**v3 → v4: PASS.** Yalnız yeni tablolar eklenir; lexical_store, question_attempts,
daily_sessions ve solver_attempts içerikleri testte JSON byte-equivalent kaldı.
Faz 3 çıkarımı sonrasında da lexical ve QuestionAttempt kayıtları değişmedi.
Mevcut denemeler migration sırasında otomatik yeniden yazılmaz veya işlenmez.

## Tests

| Katman | Sonuç |
| --- | --- |
| Phase 1 | **99/99 PASS**, değişmedi |
| Phase 2 | **62/62 PASS**, değişmedi |
| Phase 3 | **53/53 PASS**: 32 çıkarım/aggregation/validation, 21 persistence/backup |
| Total | **214/214 PASS**, 12 test dosyası |

İstenen 22 senaryonun tamamı kapsandı: yardımsız/yardımlı farkı; üç ipucu;
beceriler arasında farklı hata payı; .4 fractional kanıt; kelime tıklaması;
LOW+correct; yanlış final+doğru tactical süreç; retry; tek denemede mastery sınırı;
mastery aralığı; ilgili ve ilgisiz uncertainty; iki historical accuracy;
fractional error_rate; transfer reliability; tek soruda pacing üretmeme;
lexical/attempt immutability; dört eski tablonun migration korunumu; yedi tablo
round trip; corrupt evidence için atomic rollback.

Ek kontroller: NaN/Infinity/aralık dışı değerler, değişen ID/bağlam, concurrent
retry, storage failure rollback, eksik/tekrarlı kayıtlar, içerik yeniden üretimi,
ayrı confidence kayıtları, kaynak dışı Dexie değişikliğinin tespiti, bilinen
maruziyet ve geri tarihli transfer çakışması, geçmiş sırası ve tekrar hesaplama.

Son çalıştırmalar:

```text
npm run typecheck  PASS
npm test           PASS — 214 tests / 12 files
npm run build      PASS — strict typecheck + Vite production library build
Frozen hashes      PASS — 40/40 unchanged
```

## TypeScript

**PASS.** strict, noUncheckedIndexedAccess ve exactOptionalPropertyTypes korunur.
Yeni API'ler readonly tipler ve Zod ile doğrulanır; yeni kaynaklarda any/TODO yoktur.

## Production build

**PASS.** 37 modül derlendi. Mevcut çıktı adları korundu:
`dist-yokdil/yokdil-phase-one.js` 144.71 kB (gzip 41.06 kB),
`dist-yokdil/yokdil-phase-one.css` 14.01 kB (gzip 3.65 kB).

## Known limitations

- Bütün katsayılar editoryal v1 parametreleridir; bilimsel/ampirik kalibrasyon yoktur.
- 22 soru yalnız test ve entegrasyon içeriğidir; bunlardan prior veya güçlük modeli öğrenilmez.
- PACING_STAMINA için nitelikli blok bağlamı yoktur; boyut değişmeden korunur.
- Unseen/exam-like ve önceki ilgili çalışma bağlamını çağıran katman gözlemler;
  yerel geçmiş dışındaki maruziyet bağımsız olarak doğrulanamaz.
- Eleme telemetrisi kullanıcının gerekçesini ispatlamaz; ek ilişki kanıtı açık
  kullanıcı gözlemi gerektirir. Frozen Faz 2 UI bu yeni alanı otomatik toplamaz.
- Pure update tam geçmiş ister; yalnız event delta'sı göndermek desteklenmez.
  Persistence tüm geçmişi denetler ve yeniden hesaplar; büyük geçmişler için
  artımlı cache veya performans optimizasyonu bu fazda yapılmadı.
- Doğrudan Dexie yazımları helper sözleşmesinin dışındadır; yerel veriyi kötü
  niyetli değiştirmeye karşı güvenlik/kimlik doğrulama sistemi kurulmadı.
- Fake-indexeddb ile transaction/migration regresyonları ve üretim derlemesi
  doğrulandı. Faz 3 yeni UI içermediğinden yeni tarayıcı görsel denetimi yapılmadı.
- Soru kataloğu sürümlü ve yedeğe dışarıdan sağlanmalıdır. Yeni kod, eski lexical
  ve solver export fonksiyonlarının kapsamını değiştirmez; tam yedek için v4 API gerekir.
- Score Leak, NBA, Performance Estimator, Daily Session Engine, sınav puanı
  tahmini, VerifiedScoreGain ve ML/LLM answer reasoning eklenmedi.

## FINAL

**FAZ 3 = PASS**

FAZ 1 ve FAZ 2 frozen sınırları korundu. Faz 4'e geçilmedi.
