# FAZ 2 IMPLEMENTATION AUDIT

Tarih: 2 Ekim 2026

## Repository inspection

Mevcut React/Vite kitaplık derlemesi, TypeScript strict seçenekleri, Tailwind/Lucide,
Dexie v2 sözleşmesi, Faz 1 doğrulama ve migration katmanları ile Vitest/Testing
Library/fake-indexeddb altyapısı incelendi. Depodaki Python uygulamasına dokunulmadı.
Uygulanabilir bir AGENTS.md bulunmadı. Yeni bağımlılık kurulmadı.

Başlangıçta Faz 1'in 99 testi geçti. Değişiklik öncesi alınan SHA-256 özetleriyle
Faz 1'in 17 kaynak/test dosyasının aynı kaldığı doğrulandı. MES, scheduler,
lexical state gate'leri, WordPopover, lexical persistence, v1→v2 migration ve
eski JSON sözleşmesinde değişiklik yoktur.

## New files

| Grup | Dosyalar |
| --- | --- |
| Model/API | `src/types/question.ts`, `src/questions.ts` |
| Servis | `src/services/questions/validation.ts`, `strategies.ts`, `attribution.ts`, `attempts.ts`, `db.ts` |
| Soru bankası | `src/data/initialQuestions.ts` |
| Bileşenler | `src/components/questions/QuestionSolver.tsx`, `QuestionStem.tsx`, `QuestionOptions.tsx`, `OptionRow.tsx`, `ConfidenceSelector.tsx`, `PostAnswerAnalysis.tsx`, `TriagePanel.tsx`, `OptionAnalysisPanel.tsx`, `questions.css` |
| Testler | `tests/yokdil/phase2/model.test.ts`, `strategies.test.ts`, `database.test.ts`, `QuestionSolver.test.tsx` |
| Çalışan örnek | `examples/phase2/index.html`, `examples/phase2/main.tsx` |
| Rapor ve görseller | Bu rapor; `artifacts/phase2/focus-mode.jpg`, `post-answer.jpg`, `mobile-reading.jpg` |

## Modified files

- `src/index.ts`: mevcut export'lara ek olarak Faz 2 barrel export'u.
- `tsconfig.json`: strict seçenekleri korunarak örnek TSX dosyalarının kontrol kapsamına alınması.
- `README.yokdil-phase1.md`: Faz 2 modeli, örneği, bağlantı yönetimi ve yedek sözleşmesi.

Bu çalışma öncesinden kalan diğer değişiklikler korunmuştur.

## Database

**v2 → v3: PASS**

`QuestionDatabase extends YokdilDatabase`, yeni `solver_attempts` store'unu ekler:

```text
&id, question_id, session_id, attempted_at, family
```

Tarihsel `question_attempts` hâlâ `LexicalAttempt` saklar; rename veya veri
yeniden yazımı yoktur. V2→v3 testi lexical kayıtları, lexical denemeleri ve günlük
oturumları yükseltme öncesi/sonrası tam nesne eşitliğiyle karşılaştırır.
V1→v2 dönüşümü miras alınan, değiştirilmemiş Faz 1 koduyla çalışır.

Faz 2 `QuestionAttempt` ayrı entity'dir. Doğrulanan yazma yardımcıları append-only
çalışır; aynı ID ve aynı içerik idempotent, farklı içerik hata üretir. Batch'in
son kaydındaki hata önceki yazımları da geri alır. Session referansları doğrulanır.

V3 JSON zarfı Faz 1 yedeğini `lexical_progress` altında korur. Dört tablo tek
transaction ile dışa/içe aktarılır. Solver conflict'i lexical importu da geri alır.
Tam round-trip, yinelenen import, referans hatası ve conflict rollback testleri geçti.

## Question families

| QuestionFamily | Özgün soru sayısı |
| --- | ---: |
| GAP_FILL | 5 |
| CLOZE_TEST | 2 |
| SENTENCE_COMPLETION | 2 |
| TRANSLATION_ENG_TR | 2 |
| TRANSLATION_TR_ENG | 2 |
| PARAGRAPH_COMPLETION | 2 |
| IRRELEVANT_SENTENCE | 2 |
| READING_COMPREHENSION | 5 |
| Toplam | **22** |

Yedi fen alanı temsil edilir. Sorular özgündür ve `ORIGINAL_PRACTICE` olarak
işaretlidir; ÖSYM sorusu oldukları iddia edilmez. Banka telemetri tablosunda tutulmaz.

## Solver strategies

Yedi motor, sekiz family anahtarı üzerinden çalışır; çevirinin iki yönü aynı motoru paylaşır.

- Gap Fill, `tactical.focus` metadata'sını kullanır. Soru numarasına dayalı
  vocab/grammar/preposition eşlemesi yoktur. Beş subclass örneklerle kapsanır.
  Grammar; zaman/görünüş, çatı, kısaltma, kip, cümlecik ilişkisi ve temporal
  bağlam kontrollerini birleştirir. Zaman etiketi tek başına eleme yapmaz.
- Cloze; önceki, hedef ve sonraki cümleyi, macro açıklamayı ve tam pasajı korur.
  İki farklı bilim alanında bağımsız bağlam testi vardır.
- Sentence Completion; beklenen `DiscourseRelation` ile aday ilişkisini ilk
  kontrol olarak karşılaştırır; referent, clause, continuation, tense ve scope izler.
  Polarite etiketi semantik olarak uygun şıkkı tek başına elemez.
- Translation; kanonik semantic-role haritalarını karşılaştırır. Kelime sırası
  değişmiş eşdeğer çeviri kabul edilir; çatı/kip ve önerme ekleme/çıkarma ayrışmaları reddedilir.
- Paragraph Completion; `AnchorChain` altı bileşeninin ortalamasını, ilişki ve
  devamlılık kanıtlarıyla birlikte kullanır. Editoryal eşik 0.65'tir.
  Yüzeydeki ilk/son sözcük kestirmesi yoktur.
- Irrelevant Sentence; konu, kapsam, gönderim, kronoloji, söylem işlevi ve
  sözcüksel süreklilik bakımından sorunun istediği dışarıda kalan cümleyi değerlendirir.
  Bilimsel olarak doğru bir cümle konu dışı olabilir.
- Reading; beş alt tip için metin desteği, eşdeğerlik ve kapsam yanında ilgili
  gönderim/ana düşünce/amaç/çıkarım kontrolünü seçer. Kesinlik sözcükleri ve lexical
  overlap otomatik doğruluk veya yanlışlık sinyali olarak kullanılmaz.

Her özgün soruda tam bir desteklenen aday olduğu, bu adayın anahtarla uyuştuğu
hem katalog oluşturulurken hem testte doğrulanır. Yetersiz yapılandırılmış kanıt
`INSUFFICIENT` sonucunu üretir; bilgi uydurulmaz.

## Distractor taxonomy

On kapalı union sınıfı korunur: POLARITY_INVERSION, EXTREME_QUALIFIER, FALSE_FRIEND,
SCOPE_DRIFT, TEMPORAL_MISMATCH, REFERENCE_MISMATCH, CAUSE_EFFECT_REVERSAL,
PARTIAL_TRUTH, UNSUPPORTED_DETAIL, SEMANTIC_ROLE_SWAP.
Bir şık birden fazla desen taşıyabilir. UI etiketleri Türkçedir.
`EXTREME_QUALIFIER` desteklenen bir şıkta da kontrol sinyali olarak bulunabilir.

## WordPopover integration

Faz 1 component'i değiştirilmeden stem/passage içindeki tanımlı lexical lemma ve
kalıplara bağlandı. Kelime kontrolü soru yanıtını seçmez; portal kısayolları ana
soru kısayollarından ayrıdır. Escape davranışı korunur. Gösterilen yardım sayılır;
yardım doğru yanıtı yanlışa dönüştürmez ve lexical scheduler'a otomatik review yazmaz.

## Telemetry

Seçilen yanıt, correctness, gerçek geçen süre, nullable confidence, eleme,
tuzak bayrağı, kelime kimlikleri, yardım sayısı, gerçek yanıt değişim sayısı,
soru/family/session kimlikleri ve UTC zaman damgası saklanır.
İlk seçim ve aynı seçimin tekrarı değişim sayılmaz. Confidence default `null`'dır.
Süre referansı isteğe bağlıdır; deadline veya tahmini sınav puanı yoktur.

Submit, veri kopyasını iç içe `Object.freeze` ile sabitler; kontroller kilitlenir.
Kayıt hatasında aynı nesne/ID yeniden kaydedilir. Başarılı kayıt sonrası retry,
eski attempt'i değiştirmeden yeni ID üretir. Taktik açıklama sadece submit sonrası render edilir.

## Error attribution

Kategorilerin tümünde sıfırdan büyük başlangıç ağırlığı vardır. Seçilmiş şıkkın
çeldirici desenleri, yardım ve varsa süre referansı farklı güçlerde katkı verir.
Normalize dağılım toplamı 1'dir; doğrulama toleransı `1e-6`.
Tek kelime tıklaması VOCABULARY=1.0 üretemez. Yetersiz/berabere kanıtta
`primary_category: null` mümkündür. Doğru yanıtta hata atfı `null`'dır.
Bu dağılım, henüz ampirik olarak kalibre edilmemiş bir v1 başlangıç sezgisidir.

## Accessibility

Native radio seçimleri, ayrı `aria-pressed` eleme/bayrak düğmeleri, fieldset/legend,
Türkçe erişilebilir isimler, görünür 3px klavye odağı ve semantik analiz bölgeleri vardır.
A–E seçim, Alt+A–E eleme yapar. Tab gezinmesi ve Escape/WordPopover ayrımı test edildi.
Saat her saniye ekran okuyucuya duyurularak çözümü kesmez.

Gerçek tarayıcı doğrulaması da tamamlandı:

- Submit öncesi açıklama/anahtar gizli; submit sonrası kayıt onayı ve dört analiz bölümü görünür.
- Seçili şık elenirken seçim korunuyor. Strikeout öncesi/sonrası satırların belge
  koordinatları, genişlikleri ve yükseklikleri aynı: **reflow yok**.
- WordPopover açma/kapatma, Escape, klavye seçimi ve yeni deneme çalışıyor.
- Klavye odağında `:focus-visible` ve 3px outline gözlendi.
- 390px dar pencere denemesinde kullanılabilir içerik genişliği ve scrollWidth
  aynı (375px): yatay taşma yok. Geçici viewport ayarı geri alındı.
- Gerçek IndexedDB kaydı UI'daki “Yanıt kaydedildi” sonucu ile doğrulandı.
  Test kaydı ayrı `yokdil-fen-phase2-demo` veritabanındadır.

Görseller: [Çözüm ekranı](artifacts/phase2/focus-mode.jpg),
[Cevap sonrası](artifacts/phase2/post-answer.jpg),
[Dar ekran](artifacts/phase2/mobile-reading.jpg).

## Tests

Phase 1 tests preserved: **99/99 PASS** — eski test dosyaları değişmedi.

Phase 2 tests: **62/62 PASS** — model/attribution, 22 soru ve stratejiler,
v3 persistence/backup, UI/klavye/WordPopover.

Total: **161/161 PASS**, 10 test dosyası.

Çalıştırılan son komutlar:

```text
npm run typecheck  → PASS
npm test           → PASS (161 tests)
npm run build      → PASS
```

## TypeScript

**PASS** — strict, noUncheckedIndexedAccess ve exactOptionalPropertyTypes korunur;
örnek uygulama da kontrol kapsamındadır.

## Production build

**PASS** — Vite 28 modülü derledi.
JS: 125.48 kB (gzip 35.41 kB); CSS: 14.01 kB (gzip 3.65 kB).

## Known limitations

- Motorlar insan tarafından yazılmış, yapılandırılmış anlamsal kanıtları işler.
  Keyfi yeni sorular için güvenilir metadata yazılmalıdır; genel NLP/LLM çözüm üretimi yoktur.
- 22 özgün soru entegrasyon ve strateji doğrulamasına yöneliktir. Tam sınav bankası,
  zorluk veya hata olasılığı kalibrasyonu iddiası yoktur.
- Cevap anahtarı local-first eğitim istemcisindedir. Submit öncesi UI'da gizlemek,
  güvenli sınav sunucusu veya kopya önleme mekanizması değildir.
- Submit öncesi taslak ve henüz kaydedilememiş attempt component belleğindedir.
  Sayfa kapatma/soru değişiminde kurtarma için kalıcı outbox bu fazda yoktur.
  Başarısız kayıt görünür biçimde bildirilir ve aynı attempt yeniden denenebilir.
- Yedek doğrulaması tüm ilgili soru kimliklerinin özgün/sürümlenmiş kataloğunu gerektirir.
  Eski Faz 1 export'u yalnız Faz 1 verisini içerir; birleşik yedek için v3 helper kullanılır.
- Unit UI testleri jsdom, DB testleri fake-indexeddb üzerindedir. Bunlara ek gerçek
  tarayıcı kontrolü yapıldı; farklı tarayıcı/ekran okuyucu kombinasyonlarının tamamı test edilmedi.

NBA, Score Leak, Performance Estimator, Daily Session Engine veya Faz 3 kodu eklenmedi.

## FINAL

**FAZ 2 = PASS**
