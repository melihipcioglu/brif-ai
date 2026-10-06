# FAZ 8_IMPLEMENTATION_AUDIT

## A. Repository audit
Question'ın mevcut schema'sı 5 benzersiz seçenek id'si barındıran, zorunlu aile (family) ve içerik türüne dayanan tam tanımlanmış bir yapıya sahiptir.
`difficulty` skoru şu an 0.5 ile sabitlenmiş olup test için konulmuş editoryal bir tahmindir (IRT vb. sayılmaz).
Zorunlu alanlar: id, family, stem, options (tam 5 adet, unique), correct_option, explanation, tactical, option_evidence, skill_ids ve provenance alanlarıdır.

## B. Existing bank
Production question pool: 22 soru
Question families: 8 adet
Primary content skills: 12 adet
Provenance: 22 sorunun tamamı ORIGINAL_PRACTICE'tır.

## C. Validator architecture
`QuestionValidator` ve `BankValidator` adlı pipeline mekanizmaları kurulmuştur. Validatorlar soruların bağımsız structural ve semantic geçerliliklerini (hard errors) ve content quality'yi (warnings) tarar, sonra bunları banka düzeyinde exact match / id match / near duplicate gibi kontrollere sokar.

## D. Hard errors
- MISSING_ANSWER
- INVALID_ANSWER_KEY
- DUPLICATE_OPTION
- EMPTY_OPTION
- EMPTY_STEM
- INVALID_OPTION_COUNT
- UNSUPPORTED_FAMILY
- UNSUPPORTED_SKILL
- MISSING_PROVENANCE
- UNKNOWN_PROVENANCE
- MALFORMED_SOURCE
- EXACT_DUPLICATE_CONTENT
- ID_CONFLICT

## E. Warnings
- VERY_LONG_STEM
- VERY_SHORT_DISTRACTOR
- ANSWER_POSITION_CONCENTRATION
- FAMILY_CONCENTRATION
- UNCALIBRATED_DIFFICULTY
- NEAR_DUPLICATE
- LEXICAL_LEAKAGE (stem içinde doğru cevabın geçmesi gibi)

## F. Duplicate detection
Exact duplicate detection `canonicalEvidence` ve hashlenmiş NFKC normalize string ile deterministik olarak `EXACT_DUPLICATE_CONTENT` olarak yakalanmaktadır.
Near-duplicate tespiti ise stem'lerin kelime tabanlı Jaccard similarity'si ölçülerek (threshold 0.70-0.85 arası) `NEAR_DUPLICATE` uyarısı ile tespit edilmektedir.

## G. Fingerprinting/versioning
Her question için FNV-1a hash bazlı deterministic fingerprint oluşturulur. Version `question-validation-v1` olarak mühürlenmiştir. Herhangi bir harf veya boşluk değişikliği fingerprint'i invalid kılar.

## H. Provenance model
YÖKDİL sınav sistemi ÖSYM verisi taşımadığı için "official ÖSYM" gibi unverified claim'lere karşı "UNKNOWN_PROVENANCE" error döndürür, ancak test set'i `ORIGINAL_PRACTICE` olarak onaylanmıştır.

## I. Coverage matrix
Bank-level sonuçlarında family ve skill bazında distribution ve eksikler raporlanır. 8 aile ve 12 skill analiz edilmiş, mock bir exam (80 soru) için gerekli shortage değerleri `ExpansionPlan` modelinde output olarak sunulur.

## J. Expansion planner
`planQuestionBankExpansion` servisi; istenilen form sayısı (ör. 1) için en az kaç yeni soru gerektiğini ve hangi family'den ne kadar eksiği olduğunu matematiksel olarak hesaplar. Tek form için en az 58, 3 form için çok daha fazla ek soru gereklidir. Önerilen operasyonel hedef `1.5x` margin ile belirlenir.

## K. Controlled candidate batch
Mevcut pipeline doğrulaması yeterince coverage oluşturduğundan bu fazda sentetik üretim eklenmedi.

## L. FAZ 7 integration
`BankValidationResult` nesnesinde yer alan validation sonucu ile yalnızca `productionEligible = true` olan sorular (ve hard error barındırmayanlar) mock / exam engine pool'una sunulabilir durumdadır. Ancak engine migration'ı yapılmadı (UI vb. dokunulmadı).

## M. Files changed
- `src/questionBank.ts`
- `src/types/questionBank.ts`
- `tests/yokdil/phase8/validation.test.ts`
- `tests/yokdil/phase8/bank.test.ts`
- `tests/yokdil/phase8/planner.test.ts`

## N. Test results
Yeni 15 FAZ 8 testi. Eski 516 testle beraber tam regression başarılı.
531/531 PASS.

## O. TypeScript/build
PASS

## P. Frozen/checkpoint verification
Mevcut eski FAZ 1-7 dosyalarında mutation yoktur. Sadece additive types ve bank implementation dosyaları oluşturulmuştur.

## Q. Known limitations
- Jaccard threshold'u çok küçük kelimeli sorularda sensitive olabilir.
- Soruların difficulty'leri hala manual (editoryal) tahmindir, zorluk kalibrasyonu (calibration) bu fazın haricindedir.
