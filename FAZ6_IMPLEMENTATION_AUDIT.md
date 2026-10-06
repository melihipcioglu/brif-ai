# FAZ 6 IMPLEMENTATION AUDIT

Tarih: **6 Ekim 2026**, Europe/Istanbul. Sonuç: **FAZ 6 = PASS**.

Teslim: mevcut Faz 5 kanıtlarını salt okunur değerlendiren performans aralığı
motoru. Gerçekleşmiş başarı oranı ile sınav benzeri bağlama genelleme ayrı
tutulur. Kalibre edilmiş ÖSYM puanı üretilmez. Faz 7 başlatılmadı.

## A. Repository audit — rapor yerine kodun doğrulanması

Başlangıçta önceki rapor ve README, kaynaklarla karşılaştırıldı. 313 test,
TypeScript ve üretim derlemesi yeniden çalıştırılarak başlangıç durumu doğrulandı.
Uygulamadan önce matematik ve estimator contract testleri yazıldı; eksik yeni
modüller nedeniyle beklenen RED sonucu görüldü. Ardından uygulama ve sınır
testleri tamamlandı.

| Denetim konusu | Kodda doğrulanan gerçek sözleşme |
| --- | --- |
| 1. Qualified block | `session/pacing.ts: deriveTimedBlockResult`: COMPLETED + explicit TIMED_BLOCK; en az 5 planlanan ve tamamlanan farklı soru, 180.000 ms aktif süre, completion ≥ .80, yardım ≤ .20, retry olmaması, pozitif yanıt süreleri toplamının aktif süreyi aşmaması. |
| 2. Gerçek execution | `SessionEvent` QUESTION komutu gerçek solver_attempts ID'sine bağlanır. `recordSessionQuestion` actual attempt ve Faz 3 evidence receipt'ini aynı transaction'da yazar. `projectAdaptiveSession` planı journal üzerinden yeniden oynatır. |
| 3. Lexical ayrımı | Tarihsel `question_attempts` tablosu LexicalAttempt'tir; QuestionAttempt tablosu `solver_attempts` adını taşır. LexicalReview/micro-test performans trial'ı değildir. |
| 4. Pacing | Qualified timed sonuçtan ayrı validator/store ile TIMED_PERFORMANCE üretilir. Doğruluk düşükse NEUTRAL pacing mümkündür; bu bloktaki yanlış cevaplar performans analizinden çıkarılmaz. |
| 5. Kesinti/abandon | ACTIVE blok tamamlanmadıkça sonuç oluşmaz. ABANDON unfinished blokları SKIPPED yapar; önceden COMPLETED qualified bloklar korunur. Restore plan+olay replay'idir, cevap taslağı değildir. |
| 6. Extension | EXTEND olayı yeni immutable SessionPlan parçası taşır. Başlangıç planı yeniden yazılmaz. Block/item tekrarları projection tarafından reddedilir. |
| 7. Taxonomy | `types/question.ts`: 8 QuestionFamily. `types/learner.ts`: 13 SkillId. `evidence/mapping.ts: primaryQuestionSkill` 12 içerik becerisini kapsar; PACING_STAMINA tek soru içerik kategorisi değildir. |
| 8. Tekrar koruması | Append-only attempt ID, session+sequence ve global attempt_ref korunur. Aynı soru için farklı gerçek attempt'ler geçmişte bulunabilir; Faz 5 session-local tekrar koruması estimator için bütün geçmiş deduplication yerine geçmez. |
| 9. Zaman | UTC epoch ms; response_time_ms ve aktif süre ms. Frozen replay monoton olay zamanı ister; lease'i aşan boşluk pause'dur. Planlanan süre başarı/süre kanıtı değildir. |
| 10. Frozen liste | `tmp/phase5-baseline/frozen-hashes.json`: 63 dosya; tam liste ve hash'ler aşağıdadır. Bu tarihsel liste Faz 5'in yeni dosyalarını içermez. Faz 6 başlangıcında 82 mevcut dosyanın ayrıca hash'i alındı. |

Ek bulgular ve kararlar:

- 22 seed sorunun tümü `ORIGINAL_PRACTICE`; zorluk metadata'sı .5 editoryal
  değerdir. Empirik zorluk ayarlaması veya resmi sınav ölçeği yoktur.
- Kodda 80 soru/100 puan blueprint sözleşmesi bulunmadı. Proje adındaki 80+
  böyle bir sözleşme sayılmadı; 1.25 puan dönüşümü eklenmedi.
- `types/learner.ts` içindeki eski ErrorProbability yorumu frozen kaldı;
  hesaplanan mastery kanıt kütlesi indeksidir. README'nin çelişen erken cümlesi
  düzeltildi. Faz 6, mastery/SkillGap/priority/NBA değerlerini istatistik girdisi yapmaz.
- Transfer receipt, caller-observed unseen/exam_like/prior_practice context'ini
  korur. Faz 3 database denetimi önceki kayıtlı denemeyi yakalar; pasif soru
  görüntüleme veya dış kaynak exposure log'u bulunmaz.
- Kayıtlarda gerçek kullanıcı/sentetik köken alanı bulunmaz. Yeni migration
  yerine açık, zorunlu entegrasyon kaynağı kullanıldı; bilinmeyen köken reddedilir.

## B. Files changed

### Added

| Dosya | Amaç |
| --- | --- |
| `src/types/performance.ts` | Snapshot, evidence, coverage, interval, provenance ve discriminated result tipleri |
| `src/performance.ts` | Yeni bağımsız giriş noktası |
| `src/services/performance/calibration.ts` | Merkezi v1 eşikleri ve confidence sabitleri |
| `src/services/performance/statistics.ts` | Saf Wilson ve dışa yuvarlanan yüzde sunumu |
| `src/services/performance/selectEvidence.ts` | Replay, kaynak karşılaştırması, eligibility, ilk deneme ve deduplication |
| `src/services/performance/coverage.ts` | Aile/beceri kapsamı ve dağılım |
| `src/services/performance/estimate.ts` | Gözlem, genelleme alt kümesi, readiness gate ve sonuç |
| `src/services/performance/db.ts` | Mevcut v5 üzerinden tek read-only transaction adaptörü |
| `tests/yokdil/phase6/fixtures.ts` | Yalnız testlerde kullanılan gerçek modele uygun fixture'lar |
| `tests/yokdil/phase6/statistics.test.ts` | Matematik sınırları |
| `tests/yokdil/phase6/estimator.test.ts` | Sonuç ve determinism sözleşmesi |
| `tests/yokdil/phase6/eligibility.test.ts` | Kaynak, tekrar, leakage ve invalid-record sınırları |
| `tests/yokdil/phase6/coverage.test.ts` | Kapsam, concentration ve readiness |
| `tests/yokdil/phase6/integration.test.ts` | Frozen Faz 5 gerçek persistence hattı, resume/extension/import ve read-only davranış |
| `FAZ6_IMPLEMENTATION_AUDIT.md` | Bu kapanış denetimi |

Geçici doğrulama kaydı: `tmp/phase6-baseline/all-existing-hashes.json`.

### Modified

- `src/index.ts`: yalnız `export * from './performance'` eklendi.
- `README.yokdil-phase1.md`: Faz 6 entegrasyonu/semantiği eklendi; tarihsel
  ErrorProbability cümlesi SkillGap sözleşmesiyle düzeltildi.

63 frozen dosya değiştirilmedi. 82 dosyalık ek başlangıç listesinden 81'i
aynıdır; tek fark ana export dosyasıdır. Package/lockfile/config dosyaları ve
Faz 5 kaynak/test dosyaları değişmedi. Önceden mevcut ilgisiz `.gitignore` ve
Python/tez çalışma dosyaları bu fazın değişikliği değildir.

## C. Performance model

Akış: complete source snapshot → frozen execution replay → regenerated block
comparison → eligible, unique first-attempt observations → coverage → Wilson
interval → readiness gate → immutable result.

`observed`: uygun cevapların n/correct/incorrect/accuracy değerleri, qualified
block sayısı ve örneklem aralığı. `generalization`: bunların içinden saklanmış
Faz 3 transfer koşullarını sağlayan alt küme. `observed_coverage` ve `coverage`
bu iki kümenin kapsamını ayrı gösterir. Sonuçlar tekrar hesaplanır; kayıtlı
learner snapshot veya eski estimator sonucu yeni evidence sayılmaz.

`exam_range` READY dışında null'dır. READY aralığı da açıkça
`CORRECT_RESPONSE_PROPORTION`, `EXAM_LIKE_PRACTICE_PROXY`, `calibrated=false`,
`point_scale=null` taşır. Bu, benzer şartlardaki sınav benzeri alıştırma oranına
koşullu genellemedir. Gerçek YÖKDİL/YDS puanı veya gelecekte alınacak skor için
ampirik doğrulanmış tahmin değildir.

## D. Evidence eligibility

Faz 5 completed timed blok sonucu, gerçek journal ve doğrulanmış attempt'lerden
yeniden üretilir. Stored result ve pacing extension kayıtlarıyla tam canonical
eşitlik aranır. Faz 3 receipt ve skill evidence de frozen extractor ile yeniden
üretilip doğrulanır. Source değişirse cached bayraklara güvenilmez.

Dahil edilenler: qualified bloktaki gerçek, yardımsız, ilk kayıtlı, son 30 gün
içindeki QuestionAttempt. Doğru ve yanlış aynı koşullarla dahil edilir. Sıfır
doğruluk veya NEUTRAL pacing, tek başına dışlama nedeni değildir.

Hariç tutulanlar: lexical/micro-test, plan-only, non-timed, incomplete/skipped,
unqualified, gerçek aktif süre yetersiz, assisted, duplicate, tekrar sorular,
eski kayıtlar, demo/synthetic/unknown kaynaklar. `completed=true`, yüksek mastery
veya SkillGap yalnız başına gözlem oluşturmaz. Kaynakta bozuk/çatışan kayıt varsa
tüm snapshot istatistiksiz reddedilir; iyi görünen cevaplardan seçme yapılmaz.

Tekrar denetimi bütün soru geçmişini kullanır; önceki cevap blok dışında veya
unqualified olsa da sonraki cevabın ilk deneme sayılmasını engeller. Aynı soru
kimliği ve normalize edilmiş stem/passage/options anahtarı korunur. Aynı attempt
ID'si aynı içerikle tekrar verilirse tek sayılır; çatışan içerikle verilirse
reddedilir. Eşzamanlı farklı ilk denemelerden keyfi bir başarı seçilmez.

`NOT_EXAM_LIKE_TRANSFER`, kaydın observed kümesinde bulunabildiğini fakat
genelleme kümesine alınmadığını belirtir. Diğer dışlama nedenleri kaynak
referanslarıyla provenance içinde yer alır. Corrupt snapshot için tek, sıralamadan
bağımsız SOURCE/INVALID_RECORD nedeni üretilir; kısmi sonuç verilmez.

Origin sınırı: USER_EXECUTION/IMPORTED_USER_EXECUTION bir entegrasyon güven
sözleşmesidir, correctness beyanı değildir. Bilinen demo veritabanı ayrıca
zorunlu dışlanır. Unknown import normal biçimde reddedilir. Köken etiketi yalan
olan, kendi içinde tutarlı sahte veri ile gerçek davranışı mevcut şemadan
kesin ayırma iddiası yoktur.

## E. Coverage

8 mevcut aile ve 12 içerik becerisinde covered/missing/underrepresented listeleri,
question sayıları, farklı qualified block ve session sayıları; aile, blok ve
session başına maksimum pay ölçülür. Birincil skill, frozen taxonomy mapping'den
gelir. Çok sayıda ikincil etiket eklemek bir soruyu birkaç bağımsız skill örneği
haline getirmez. Pacing, içerik sorusu kapsamını doldurmaz.

Coverage doğrudan readiness koşuludur. Testler hem 80 tek-aile sorusunun hem de
66 dağıtılmış soruyu içeren tek büyük bloğun READY olmamasını doğrular.

## F. Readiness thresholds

Tüm eşikler `PERFORMANCE_V1` içinde merkezidir; değişiklik semantic version
incelemesi gerektirir. Kullanıcı accuracy'sine göre dinamik biçimde gevşetilmez.

| Parametre | V1 değeri | Gerekçe / sınır |
| --- | --- | --- |
| n | ≥60 | 12 içerik becerisi × 5; sınavın 80 sorulu olduğu varsayımı değil |
| Her family | ≥5 | Sekiz ailenin hiçbirini tek gözlemle temsil etmemek |
| Her primary skill | ≥3 | En az birkaç bağımsız soru kimliği; ikincil etiketleri saymamak |
| Qualified blocks | ≥4 | Tek blok başarı serisini genellememek |
| Sessions | ≥2 | Tek yürütme kümesine dayanmamak; farklı gün garantisi değildir |
| Family concentration | ≤.35 | Tek ailenin çoğunluğu ele geçirmesini engellemek |
| Block concentration | ≤.35 | Bir bloğun gözlemlere baskın olmamasını istemek |
| Session concentration | ≤.65 | Bir session'ın bütün gözlemleri belirlememesini istemek |
| Wilson width | ≤.25 | Yeterli sayının yanında örneklem belirsizliğini de sınırlamak |
| Recency | ≤30 gün | Eski örneklerle güncel aralığı yapay daraltmamak |

Bunlar **editoryal v1 release gate** değerleridir; ampirik sınav kalibrasyonu
veya resmi soru dağılımı olarak sunulmaz. 22 seed soru 8 aile ve 12 primary skill'i
kapsıyor olsa bile gerekli sayıyı sağlayamaz. Hazır katalogla READY üretmek için
eşikler düşürülmedi. Testteki genişletilmiş katalog üretim verisi değildir.

Statüler: uygun gözlem yoksa INSUFFICIENT; gözlem var fakat örneklem/genelleme
yetersizse OBSERVED_ONLY; en az 60 genellenebilir gözlem ve iki aile bulunduğu
hâlde bir kapı geçmiyorsa PROVISIONAL; bütün kapılar geçerse READY.

## G. Statistical method

İki taraflı Wilson score interval kullanıldı; confidence=.95,
z=1.959963984540054. p=k/n, a=z²/n için merkez `(p+a/2)/(1+a)`,
yarı genişlik `z*sqrt((p*(1-p)+a/4)/n)/(1+a)`; sınırlar [0,1]'e korunur.
n=0 için null; negatif, kesirli, NaN/Infinity, güvensiz integer veya k>n reddedilir.
0 doğru alt sınırı 0; tüm doğru üst sınırı 1'dir. Referans:
[NIST 7.2.4.1 — Confidence intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Nominal .95 seviyesi kaynak güvenilirliği veya READY güven puanı değildir.
Wilson'un binomial karşılaştırılabilirlik/bağımsızlık varsayımı, gerçek sınavın
temsil gücünü kendiliğinden sağlamaz. Örneklem sayısı arttığında aynı oran için
aralık daralır; bunun dışında uydurma monotonicity şartı uygulanmaz.

## H. False precision safeguards

- Ana çıktı tek predictedScore değildir; observedAccuracy, alt/üst sınırlar,
  n, confidence, coverage, blockers ve ID tabanlı provenance birlikte döner.
- READY dışındaki sonuçların exam_range taşımaması discriminated union ile korunur.
- Eksik/bozuk/unknown/lexical-only veri skor veya aralık uydurmaz.
- Nokta ölçeği null'dır. Tam yüzdeye dışa yuvarlama yardımcı fonksiyonu yalnız
  doğru cevap yüzdesi gösterir; sınav puanı olarak etiketlenemez.
- Tek cevap kesinlik yaratmaz; düşük coverage büyük n ile aşılamaz.
- Kaynak, method/version, as_of, attempt/block kimlikleri ve varsayımlar döner.

## I. Tests

| Faz | Sonuç |
| --- | --- |
| Phase 1 | 99/99 PASS |
| Phase 2 | 62/62 PASS |
| Phase 3 | 53/53 PASS |
| Phase 4 | 39/39 PASS |
| Phase 5 | 60/60 PASS |
| Phase 6 | 69/69 PASS |
| Full suite | **382/382 PASS — 23 dosya** |

Sınırlar: n=0/1, 0 doğru/tüm doğru/50-50/büyük n, malformed sayımlar, küçük
örneklem, kaynak origin, lexical karışması, exact/conflicting duplicate,
önceki blok dışı deneme, farklı ID ile aynı içerik, timestamp tie, eski/future
kanıt, bozuk duration/result/evidence/sequence, opsiyonel metadata, family/skill
coverage, block/session concentration, sıralama bağımsızlığı ve immutability.

Integration: gerçek frozen storeSessionPlan/recordSessionQuestion/executeSessionCommand
hattıyla qualified kayıt, yarıda veritabanını kapatıp açma ve 10 dakikalık pause
sonrası resume (aktif süre yine 200 saniye), extension, interrupted/abandoned
bloklar, tamamlanmış bloğun sonradan abandon ile kaybolmaması, heartbeat boşluğu,
v5 export/import, bilinen demo kaynağı ve corrupt persisted result. Bütün 11
tablonun önce/sonra içerikleri eşit; DB versiyonu değişmez.

## J. Build verification

```text
npm test           PASS — 382/382, 23 files
npm run typecheck  PASS
npm run build      PASS
```

Build: 63 modül. JavaScript 213.36 kB (gzip 59.37 kB), CSS 14.23 kB
(gzip 3.66 kB). Yeni modüller ana export üzerinden üretim paketine dahildir.
Runtime dependency, schema migration, UI ve ağ isteği eklenmedi. Yeni kaynaklarda
`any`, `Date.now()`, random veya network çağrısı yoktur. Database adaptörü yalnız
read transaction kullanır. Frozen audit yardımcılarının iç export zaman damgası
istatistiğe/provenance'a taşınmaz; bütün Faz 6 zaman kararları caller as_of ile verilir.

## K. Frozen verification

**63/63 unchanged; 0 hash farkı.** Ek 82 dosyalık başlangıç denetiminde yalnız
`src/index.ts` yeni export nedeniyle değişti; diğer 81 dosya aynı kaldı.
Önceki raporun iddiasıyla yetinilmedi; SHA-256 içerikleri tekrar hesaplandı.

Tam tarihsel liste ve değişmeyen SHA-256 değerleri:

| Dosya | SHA-256 |
| --- | --- |
| src/types/evidence.ts | 002940F11FBE11104DA6FBF16BCED8ACA0C3317468BF1AED5B877F06125455E1 |
| src/types/learner.ts | E7E208A5173272F831CC89D4AD31302758587062492D2A640B6D91E36B978152 |
| src/types/lexical.ts | E500D92FB75DB63A1A977CA24A24436BAD98E4813BBAF77A573612939E3A9844 |
| src/types/priority.ts | 8ED11A31C024DF2CF17F0D19E38AD929B3443884DF84EC34CDC0155D19E34D95 |
| src/types/progress.ts | BE28CBEDD78CE1FCCDDA803F5E06197B2D000B4E25B7DE6C44DA4B0C6412B755 |
| src/types/question.ts | 85209131C66292A873F6D87FCFC82BCA49A24EBF1B75580EC38863F35E105AE5 |
| src/services/db.ts | 1EA65C48F5EF5635AEC99C460D48A2B862F66A41D65E56D1BB2DF6A82EBECF00 |
| src/services/lexicalScheduler.ts | 2A2CB56A546E008AFBF13C9AA80BB4F7C6067FDC2F92FCAFD0C753FEF8520930 |
| src/services/progressMigration.ts | 968510E941D8E2A23C86BF9A5ED4756FCD391CDBE56B090F55077F0020A97D77 |
| src/services/validation.ts | FC5D362D1209403393F62403B0F24ADC3DFE21C9FD2318685C91A58A20234C28 |
| src/services/evidence/aggregateEvidence.ts | 9F40364B4A9F2FD5C7D4E8F6A1C0963B717B795B2B6B632C984A0372B57D5BE3 |
| src/services/evidence/calibration.ts | B605F6AF5CB957F29774EF7F2B54F6A20EF9F747F916FC1DFA5AB02C8112828F |
| src/services/evidence/db.ts | 32C0C5980B8A222945B90787E8DC7CD2224E6365EC5DDDF35431388C460DAB53 |
| src/services/evidence/extractEvidence.ts | D2929DA5264E671B6F52733CAA396CE589ABCB689623732951219F86764554CC |
| src/services/evidence/mapping.ts | 6C5DD06C7E574F02A4D2CD23E1F5A1712AC7030878266D92A6C206029F70F1A7 |
| src/services/evidence/updateLearnerModel.ts | 7BF76699DCEA3EC44DFD4E20179ADBD3E78A6A0AEB98C21A43BD9F2A787E4145 |
| src/services/evidence/validation.ts | A67B681B29AD67E0E9206D72D4294DDC18072913816106D4721C5B582AD16E03 |
| src/services/priority/calibration.ts | 2892C90156589C0F3C2E295C72537EE7F530615C9B2A4B037D61F007DC756BF9 |
| src/services/priority/coverage.ts | 65A420A1E594F9EA95A9672B171970DE0F2856D28EDED4B7B0C3D39A73600453 |
| src/services/priority/db.ts | DB4AFF59E680C1385BD95552588E587D282B917CAC19B89CFC75A12FAE9BFC26 |
| src/services/priority/nextBestAction.ts | D872AF596DADFEF4815F76C8807CC635EBA73461B959AC3086FC9A1BCBC2769E |
| src/services/priority/scoreLeak.ts | 449F8BC307518D82766B14EE2FF73776A1B0BAFD0FD35BF6D2D0FAE307C51679 |
| src/services/priority/validation.ts | 0153B024D3976785C60A32DFB2893164CBD6000AA46A57F7F2556FBA0D8B21A6 |
| src/services/questions/attempts.ts | 0064C783CC14A47BF9C5D61CB969F1F4E9AD91EACE683E02E7F1B8CDB1F32B5A |
| src/services/questions/attribution.ts | 816722CFAF4F9F794256AC57149F8D661F9081D3B0A46DD9FBD26FA3967D5457 |
| src/services/questions/db.ts | 0D43D1192181F0A5161C17EBF545D3D28DBCF979E56D8893B46F5AA10A57A6B8 |
| src/services/questions/strategies.ts | 8EB08231F4569A98364A71145F67793EC529B2F6F8140C1A3BD61327721CB69E |
| src/services/questions/validation.ts | EF9315E209BAC62035948B8703AB2EEC3E4A35ACFEA7A7CF77C45DC3F414DBA1 |
| src/components/WordPopover.css | AA498B4BEDCFDCDE10C16A35BB45E719D6C23D0991B517BFC7914EC1477FA42D |
| src/components/WordPopover.tsx | 991A5EE992CBF6C0874D68DDF36F7BEADD813D8B91603A8F8E995CA1B784E490 |
| src/components/questions/ConfidenceSelector.tsx | C1329EC0C87F84C1F3DE729281379BB02FADE8190D5747A4C535A0222A0337CE |
| src/components/questions/OptionAnalysisPanel.tsx | 8B144312E038B2B9CCF0EBF676E3F2A5D95B65B4786B17B2E06139A3BD031521 |
| src/components/questions/OptionRow.tsx | A64A93BCC629A07FA0BB1FF9AFA1E7ECDE8364FEC85E0DAA610952B6AC03DE4B |
| src/components/questions/PostAnswerAnalysis.tsx | 9F73AD11AE12F00BB6315821C0EE954EC39F9F1FD7EE2B82A3389682C0E311DB |
| src/components/questions/QuestionOptions.tsx | 47135BD3FE61EBD3D96A344B451AC7447A2FD20A2C70A1D5F90D1FF5BAA41E81 |
| src/components/questions/questions.css | 8A125B089E627C16A0565CB045FF4843A9BEAB6C4812AB2EBF7FB455258B18C0 |
| src/components/questions/QuestionSolver.tsx | 36DB2AF0431A8CE928942EAC2FE8EA5C869747F2C33298D65F35B340D38C2324 |
| src/components/questions/QuestionStem.tsx | A32F9DF31CC5D226825D2C9968D32B5ED3FBC3BC65001E38EB9C5F53E2348082 |
| src/components/questions/TriagePanel.tsx | 71BFD4D32D19DB85E32468E2107C17C04710E231665AB3A0EC27DEB31FCC9156 |
| src/data/initialQuestions.ts | 5BCA9D141A79FF4C2A9372D30E856DC1C6B92441CBF625EB23A404FE1D70C2AF |
| src/data/initialVocab.ts | AD50B05004E24B326CFDA58D83934B280D0A38B07FF525FCA343529CC1F46AD6 |
| tests/yokdil/db.test.ts | 680F392B13F667A4C6F2DDEE132671EBF6D155782B662AB296B6B1E3EC18514A |
| tests/yokdil/gateAudit.test.ts | 6551AB4E436ED9028A0161941E69634E3B2E2E3AF7F66298A8E901FBAEF54A7B |
| tests/yokdil/lexicalScheduler.test.ts | DF9614130F6BA752C23AD37EC6C772B957162C9F346EC84D5100C6272D99B6DF |
| tests/yokdil/mesEvidence.test.ts | 3F72ECEB4ADE2694CD709A7DEB35331F4B6C3B5013E840A3EDA21F28FE41E475 |
| tests/yokdil/migration.test.ts | F56BB4D5C740E4C95549848E6774EB89234778E89399257D399C16864384F5DF |
| tests/yokdil/setup.ts | 1EE023720DBE5DF5AE305B750355742776D6A93507FDC83C9E062FD4B587F1DF |
| tests/yokdil/WordPopover.test.tsx | 2CC7525EF8F8587EE260DDAB083F3A16F8D90F314CA0C4653E0DEA785326E9B6 |
| tests/yokdil/phase2/database.test.ts | FE81C7BD53BB2E4420F419D632153298DE236EFB3552A6F79DF9FA91A6B60A3A |
| tests/yokdil/phase2/model.test.ts | 30BE97407FA245D2C31EBFAFA90BAF5C7517427A5C19F318B7BC46682D47BF87 |
| tests/yokdil/phase2/QuestionSolver.test.tsx | 83AFF736CCA237FFAB4FD749885490E0A9A9CFC248FDD90096CFA1B5A37FBFD2 |
| tests/yokdil/phase2/strategies.test.ts | C4EE3B80B1C30C1DA0140F66595D523DF5D4F5DE59BF17F1325C0739D39A4876 |
| tests/yokdil/phase3/database.test.ts | 599DCD54B1774F1A6AE1574368653CD80C4CCAC6CD1721CF3AEC5D14EEB78EF4 |
| tests/yokdil/phase3/evidence.test.ts | 44EF14388716D18DF976FA01E162E22DE9A0490A64F340A16CA311AC653A8A63 |
| tests/yokdil/phase3/fixtures.ts | C1F981EA2B8C07F7BD4A72E9576A8916C873D3001AB9E11526CE7F1A8138BCAF |
| tests/yokdil/phase4/coverage.test.ts | A57218C06392E57FAD11893B7142ED989BF93BE2E3E5682B053F61FCB35A3626 |
| tests/yokdil/phase4/database.test.ts | E3A392DA335929D701345C8C2277F63555A4525B9A4CEC5F84BC552B00BB077F |
| tests/yokdil/phase4/priority.test.ts | BF3D942ABB453C68E2809DE5949A197FACEECC74E0FD23BCF0873253EAA2C52F |
| examples/phase2/index.html | 983E90B61ABF6C0A1E6AB9668C918C11E247332E6B68DC03ACD5F4AFCFD4AC87 |
| examples/phase2/main.tsx | 18489E21CC8FEDADF280E8A7272904A0CC86476FDD2BC3F58F868CA0F4FC7536 |
| src/questions.ts | 2950C6EC8CD78E153BC13183D9054A547CD927F8B78E40F8E1C771C97F8C00DC |
| src/evidence.ts | 5DEB69B07F136B74A54BE71CEA19E19AC67F1476E1C6B2045CEC7F1C8EA0761E |
| src/priority.ts | FDBDC85C566D68E9691D39002FCA9AF4B28E69D09D5FED118990939C7CED0307 |

## L. Known limitations

- READY, kalibre edilmiş sınav tahmini değildir. Resmi blueprint, ampirik
  difficulty ve point scale bulunmadığından puan dönüşümü sunulmaz.
- History eksiksiz olmalıdır. Silinmiş geçmiş, dışarıdan cevap görme,
  cevaplamadan soru açma ve farklı ifadeyle aynı sorunun tekrarını şema güvenilir
  biçimde izleyemez. Exact-content alias kontrolü semantik paraphrase dedup değildir.
- Gerçek/sentetik kaynak ayrımı entegrasyon beyanına dayanır. Unknown kaynaklar
  reddedilir; false origin etiketi veya kendi içinde tutarlı sahte telemetriyi
  tespit eden kriptografik doğrulama yoktur.
- Transfer context caller-observed'dır; gelecekteki kontrollü mock/holdout
  tasarımının yerini tutmaz. Başarılı olmuş cevaptan exam_like etiketi türetilmez.
- Wilson yalnız örneklem belirsizliğini kapsar; ortak passage/blok bağımlılığı,
  adaptif seçim, item difficulty ve sınav dağılımı farkı düzeltilmez. Bunlar
  machine-readable assumptions ile ayrıca belirtilir.
- Skill/family coverage resmi sınav ağırlıkları değildir. Eşikler editoryaldir;
  gerçek kullanım verisiyle gelecekte gözden geçirilebilir.
- İstatistik son 30 güne bakar; eski soruları tekrar çözerek ilk-deneme eşiği
  sıfırlanmaz. Baştan hesaplama ve bütün geçmiş audit'i büyük veri setinde maliyetlidir.
- Corrupt snapshot fail-closed davranışı sağlam veriyi de geçici olarak
  istatistik dışı bırakır. Kaydı onarmak/silmek bu read-only katmanın işi değildir.
- Yeni UI, score history, ML/LLM, Bayesian learner, IRT/CAT, mock üretici,
  öneri/NBA değişikliği veya Faz 7 uygulanmadı.

## Final acceptance gate

Repository audit, qualified filtering, lexical ayrımı, deduplication,
coverage/readiness, belirsizlik, provenance, determinism, immutability ve bütün
regresyon/typecheck/build/frozen kontrolleri **PASS**. Yeni dependency,
migration, UI, ağ çağrısı ve otomatik progress yazımı **NONE**.

**FAZ 6 = PASS**

**FAZ 7 = NOT STARTED**

