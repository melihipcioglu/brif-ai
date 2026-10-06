# FAZ 4 IMPLEMENTATION AUDIT

Tarih: 3 Ekim 2026

## Semantic contract

**SkillGap = 1 - mastery**, yalnız kanıt temelli beceri açığı indeksidir.
Mastery'den hata olasılığı türetilmez. Score Leak, kaybedilecek sınav puanı değil,
göreli çalışma önceliğidir. ExpectedTrainingValue, tahmini puan veya öğrenme
kazanımı değil, **dakika başına çalışma değeri indeksi** olarak tanımlanmıştır.

Harita birimi `INDEX_0_100`, yorum etiketi `RELATIVE_TRAINING_PRIORITY`; eylem
değeri birimi `PRIORITY_INDEX_PER_MINUTE`'tır. Açıklamalar değerlendirme, çalışma
ve tekrar gerekçelerini anlatır; başarı garantisi veya yüzde hata iddiası üretmez.
Yeni kaynak kodunda hata olasılığı, exam score veya score gain hesaplaması yoktur.
Frozen learner tipindeki tarihsel olasılık yorumu korunmuş dosyanın parçasıdır;
Faz 4 bu yorumu kullanmaz. README'de yeni sözleşmenin geçerliliği açıkça belirtilmiştir.

## Repository inspection and frozen boundaries

TypeScript strict, Zod, mevcut 13 SkillId, Faz 3 aggregation ve audited v4
persistence incelendi. Yeni bağımlılık kurulmadı; uygulanabilir AGENTS.md bulunmadı.
Başlangıçta 214 test geçti. Önceki fazların **52/52 kaynak, örnek ve test dosyası**
SHA-256 karşılaştırmasında aynı kaldı. Başlangıç kaydı:
`tmp/phase4-baseline/frozen-hashes.json`.

Yeni kod yalnız `src/types/priority.ts`, `src/priority.ts` ve
`src/services/priority/` altındadır. Mevcut `src/index.ts` içine yeni barrel export
satırı, README sonuna Faz 4 bölümü eklendi. MES, lexical scheduler, state gate,
WordPopover, QuestionAttempt, tactical solvers, ErrorAttribution, evidence
extraction/aggregation ve migration dosyaları değiştirilmedi. Diğer proje
çalışmaları korunmuştur.

## Implemented files and APIs

| Dosya | İşlev |
| --- | --- |
| `src/types/priority.ts` | Coverage, profil, harita, aday, katkı ve plan sözleşmeleri |
| `src/services/priority/calibration.ts` | Belgelenmiş editoryal PRIORITY_V1 parametreleri |
| `src/services/priority/validation.ts` | Kapalı taxonomy, finite sınırlar ve tutarlılık kontrolleri |
| `src/services/priority/coverage.ts` | `deriveEvidenceCoverage` |
| `src/services/priority/scoreLeak.ts` | `buildScoreLeakMap` |
| `src/services/priority/nextBestAction.ts` | `planNextBestAction` |
| `src/services/priority/db.ts` | `loadNextBestActionPlan`, salt okunur v4 adaptörü |
| `src/priority.ts` | Dışa açılan API |
| `tests/yokdil/phase4/` | priority, coverage ve database regresyonları |

## Evidence coverage and need separation

Tam ve denetlenmiş geçmişten her beceri için farklı bilgilendirici deneme, soru,
family, yardımsız/transfer deneme sayıları ve son bilgilendirici zaman çıkarılır.
Bir denemenin tactical ve result satırları veya aynı olayın retry kopyaları yeni
deneme sayılmaz. NEUTRAL ve reliability=0 kapsam desteği oluşturmaz.
Eksik coverage UNKNOWN/null, bilinen boş geçmiş KNOWN/0'dır.

V1 formülleri:

```text
coverageIndex = (1 - exp(-informativeAttempts / 8))
                × (.6 × min(questionCount / 5, 1) + .4 × min(familyCount / 2, 1))
support = (1 - uncertainty) × coverageIndex
SkillGap = 1 - mastery
practiceNeed = SkillGap × (.25 + .75 × support)
diagnosticNeed = .6 × uncertainty + .4 × (1 - coverageIndex)
retentionNeed = (1 - exp(-ageDays / 30)) × support × (.25 + .75 × mastery)
```

Kapsam bilinmiyorsa coverageIndex=0; bilgilendirici tarih yoksa retentionNeed=0.
Sayı/breadth hedefleri ve zaman penceresi beceri profiline göre değiştirilebilir.
Belirsizlik ve kapsam desteği, kalibre edilmiş olasılık olarak yorumlanmaz.
Zaman geçmesi mastery'yi düşürmez; tekrar ihtiyacını değiştirir.

## Score Leak Priority Map

```text
priorityIndex = 100 × examRelevance
                × (.45 × practiceNeed + .35 × diagnosticNeed + .20 × retentionNeed)
```

Tüm 13 beceri, ayrı ihtiyaçlar, açıklama etiketleri ve eklenebilir üç skor bileşeni
ile döner. Değer [0,100] indeksidir, yüzde değildir. Exam relevance varsayılanı
her beceride 1'dir; bilinmeyen sınav frekansları uydurulmamıştır. Öncelik eşitliğinde
mevcut SKILL_IDS sırası kullanılır. Faz 3 kaynak metrikleri değişmez.

## ExpectedTrainingValue and Next Best Action

Uygulama gerçek ve kullanılabilir adayları sağlar. Üç tür vardır: DIAGNOSTIC,
TARGETED_PRACTICE, RETENTION_REVIEW. Tür, haritadaki ilgili ihtiyacı seçer.
Benzersiz hedef ağırlıklarının toplamı 1 olmalıdır.

```text
trainingValueIndex = 100 × Σ(targetWeight × alignedNeed × examRelevance × trainability)
ExpectedTrainingValue = trainingValueIndex / max(5, expectedMinutes)
```

Trainability ve süre girdisi editoryaldir. Minimum etkin maliyet, çok kısa
tahminlerin aşırı ödüllendirilmesini önler. Süre bütçesi actual expectedMinutes
girdisine göre denetlenir. Adayların her beceri katkısı ayrı döner.

Unavailable, bütçeyi aşan, değeri sıfır ve herhangi bir hedefinde tekrar ihtiyacı
bulunmayan review adayları neden kodlarıyla elenir. Pacing hedefi TIMED_BLOCK
formatı gerektirir. Uygun aday yoksa NO_ELIGIBLE_ACTION/selected=null döner.
Sıralama ETV azalan, toplam değer azalan, süre artan, ID sözlük sırasıdır;
giriş sırası ve locale sonucu değiştirmez. Plan otomatik eylem uygulamaz.

Cold-start senaryoda aynı süre için diagnostic adayı practice adayından önde;
desteklenen beceri açığında practice, eski ve güçlü kanıtta review seçimi test edildi.

## Validation and persistence

NaN/Infinity, aralık dışı değerler, bilinmeyen alan/beceri, tekrarlı aday/hedef,
yanlış ağırlık toplamı, sıfır/negatif maliyet, gelecekte recency ve learner ile
çelişen coverage reddedilir. Pure fonksiyonlar açık as_of girdisi kullanır.
Çıktılar derin immutable; girişler değiştirilmez.

Yeni migration, veri tablosu veya plan cache'i yoktur. V4 adaptörü aynı salt
okunur transaction içinde Faz 3 kaynak kanıt denetimini, learner hesabını ve
coverage çıkarımını yapar. In-range değiştirilmiş kanıttan plan üretilmez.
İşlem öncesi/sonrası yedi tablonun aynı kaldığı ve schema_version=4'ün korunduğu
test edildi. Önerinin değeri yeni başarı kanıtı olarak veritabanına yazılmaz.

## Tests

| Faz | Sonuç |
| --- | --- |
| Phase 1 | 99/99 PASS |
| Phase 2 | 62/62 PASS |
| Phase 3 | 53/53 PASS |
| Phase 4 | 39/39 PASS |
| Total | **253/253 PASS — 15 dosya** |

Faz 4 kapsamı: SkillGap semantiği, 13 boyut, cold-start, unknown/empty coverage,
uncertainty yönlendirmesi, quantity/breadth, destekli gap, recency, relevance,
bounded/additive indeksler, trainability, maliyet tabanı, çoklu hedefler, bütçe ve
kullanılabilirlik, null öneri, review/pacing sınırları, deterministic ties,
immutability, kalibre edilmemiş iddia üretmeme, input validation, coverage
deduplication ve frozen Faz 3 üzerinden salt okunur veritabanı entegrasyonu.

```text
npm run typecheck  PASS
npm test           PASS — 253/253
npm run build      PASS
Frozen hashes      PASS — 52/52 unchanged
```

## TypeScript and production build

**TypeScript strict: PASS. Production build: PASS.** 45 modül derlendi.
Mevcut dosya adları korundu: JavaScript 154.98 kB (gzip 44.02 kB),
CSS 14.01 kB (gzip 3.65 kB). Yeni UI bulunmadığı için görsel tarayıcı testi
yapılmadı; saf motor ve IndexedDB adaptörü otomatik testlerle doğrulandı.

## Known limitations

- V1 parametreleri editoryal sezgilerdir; ampirik kalibrasyon ve puan tahmini yoktur.
- 22 seed soru prior, sınav frekansı, trainability veya difficulty öğrenmekte kullanılmaz.
- Pure API aynı snapshot'a ait tam, denetlenmiş coverage bekler; tamlığı yalnız
  sayılardan ispatlayamaz. V4 adaptörü bu tutarlılık için tek audited snapshot kullanır.
- Aday havuzu, içerik uygunluğu ve süre tahminini çağıran uygulama sağlar. Hazır
  içerik varmış gibi varsayım yapılmaz; yeni bir çalışma ekranı veya içerik kataloğu yoktur.
- Pacing için yalnız aday format kontrolü vardır. TIMED_BLOCK gerçekten mevcut
  olmalıdır; Faz 3'ün blok kanıtı üretmeme sınırı ve 13. boyutu koruma davranışı değişmez.
- Günlük oturum motoru, cooldown planlayıcısı, otomatik eylem yürütme ve plan persistence yoktur.
- Performance Estimator, VerifiedScoreGain, sınav puanı tahmini ve sonraki fazlar kapsam dışıdır.

## FINAL

**FAZ 4 = PASS**

Faz 1, Faz 2 ve Faz 3 FROZEN sınırları korunmuştur.
