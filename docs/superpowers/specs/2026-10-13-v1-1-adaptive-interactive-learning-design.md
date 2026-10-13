# V1.1 ADAPTIVE & INTERACTIVE LEARNING SYSTEM SPECIFICATION

**Tarih:** 2026-10-13  
**Sürüm:** V1.1 Pedagogical Engine  
**Durum:** APPROVED BY USER (Direct Execution Mode)

---

## 1. HEDEF VE PEDAGOJİK VİZYON

Bu spesifikasyon, YÖKDİL Fen Bilimleri sınavına hazırlanan bir adayın sıfırdan başlayarak hiçbir ön bilgi varsayımı olmadan, akademik fen metinlerini ve sınav sorularını bağımsız olarak çözebilecek yetkinliğe ulaşmasını sağlayan interaktif öğrenme mimarisini tanımlar.

Sistem bir test çözme robotu ya da basit bir kelime kartı uygulaması değildir. Gerçek bir uzman öğretmenin pedagojik yöntemlerini (Bilişsel Yük Teorisi, Atomik Basamaklama, Kademeli Sorumluluk Devri / I DO - WE DO - YOU DO, Zihinsel Çapa ve Tuzak Aşısı) dijitalleştiren interaktif bir eğitim motorudur.

---

## 2. TEMEL MİMARİ BİLEŞENLER

```
                               ┌────────────────────────────────────────────────────────┐
                               │             1. BAŞLANGIÇ TANILAMA MODÜLÜ              │
                               │  Hiçbir ön bilgi varsaymaz. 5 mikro kelime + 3 cümle   │
                               │  yapısı + 2 bağlaç yön sezgisi -> Başlangıç Kalibrasyonu│
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                               ┌───────────────────────────▼────────────────────────────┐
                               │             2. ETKİLEŞİMLİ KELİME ÖĞRETİMİ             │
                               │  • Anlam, Telaffuz (Web Speech), Zihinsel Çapa          │
                               │  • Tuzak Aşısı (Inhibit vs Inhabit vs Exhibit)          │
                               │  • Basit Cümle -> Aşamalı Genişletme -> Sınav Cümlesi   │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                               ┌───────────────────────────▼────────────────────────────┐
                               │             3. ETKİLEŞİMLİ CÜMLE ÇÖZÜMLEME             │
                               │  • "I DO" (Sistem gösterir ve açıklar)                 │
                               │  • "WE DO" (Öğrenciye ögeleri seçtirir, anında dönüt)  │
                               │  • "YOU DO" (Öğrenci bağımsız analiz eder)              │
                               │  • Yanlış mantığa özel hata pedagojisi                  │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                               ┌───────────────────────────▼────────────────────────────┐
                               │             4. GÜDÜMLÜ & BAĞIMSIZ ALIŞTIRMALAR         │
                               │  • YÖKDİL Seviyesine Kademeli Yaklaşan Sorular          │
                               │  • Her Seçenek İçin "Neden Yanlış?" Çeldirici Analizi  │
                               │  • Hata yapılan yapıyı anında pekiştirme                │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                               ┌───────────────────────────▼────────────────────────────┐
                               │             5. 3 BOYUTLU KALICILIK & SARMAL TAKİP      │
                               │  • Recognition (Tanıma)                                │
                               │  • Sentence Comprehension (Cümlede Anlama)             │
                               │  • Transfer & Application (Yeni Bağlamda Kullanma)     │
                               │  • Sonraki günlerde yardımsız hatırlanmadan MASTERED   │
                               │    statüsü verilmez (Fail-closed spaced repetition).   │
                               └────────────────────────────────────────────────────────┘
```

---

## 3. DETAYLI MODÜL TANIMLARI

### 3.1. Başlangıç Tanılama Modülü (`DiagnosticAssessment`)
- **Amaç:** Öğrencinin sıfır noktadaki durumunu saptar; öğrenciye gereksiz zorluk yüklemez veya bilişsel aşırı yüklenme yaşatmaz.
- **İçerik:**
  - 4 mikro kelime tanıma (Temel fen fiil/sıfatları: *increase, prevent, observe, absorb*).
  - 3 mikro cümle öge tanıma (Özne kim? Fiil nerede?).
  - 2 temel bağlaç sezgisi (*although* = zıtlık, *because* = sebep).
- **Çıktı:** Öğrenci Seviyesi:
  - `FOUNDATIONAL` (Temel iskele modu: Adım adım açıklamalar en detaylı seviyede).
  - `INTERMEDIATE` (Orta iskele modu: Standart basamaklama).
  - `ADVANCED` (İleri iskele modu: Hızlı genişletme, sınav şablonlarına odak).

### 3.2. Etkileşimli Kelime Öğretim Motoru (`InteractiveWordTrainer`)
Her kelime için şu 6 aşamalı pedagoji uygulanır:
1. **Tanıtım & Ses:** Türkçe anlam, sözcük türü, İngilizce sesli telaffuz (Web Speech API).
2. **Zihinsel Çapa & Analoji:** Türkçe zihinsel kanca (ör. *inhibit* = frene basmak, süreci durdurmak).
3. **Tuzak Aşısı:** Sınavda karışan benzer sözcüklerin yan yana netleştirilmesi (*inhibit* ≠ *inhabit* [yaşamak] ≠ *exhibit* [sergilemek]).
4. **Basit Başlangıç Cümlesi:** Öğrencinin bildiği temel sözcüklerle kurulmuş temiz cümle (Örn: *Ice inhibits bacterial growth*).
5. **Aşamalı Genişletme:** Cümleye bağlaç veya niteleyici ekleyerek zenginleştirme (Örn: *Because ice inhibits bacterial growth, fresh food lasts longer*).
6. **Akademik Fen Cümlesi ve Söküm:** Sınav seviyesindeki cümlenin ana omurgasını izole etme (*[Compounds] + INHIBIT + [Proliferation]*).

### 3.3. Etkileşimli Cümle Çözümleme Ekranı (`InteractiveSentenceDecomposer`)
- Statik salt metin kartı değildir.
- Öğrencinin cümledeki kelimelere ve söz öbeklerine tıklayarak **ÖZNE**, **ANA FİİL**, **NESNE**, **BAĞLAÇ** ve **YAN CÜMLE** ögelerini bizzat işaretleyebildiği interaktif bir çalışma masasıdır.
- **I DO (Ben Gösteriyorum):** Sistem cümleyi çözer; öğrenciye ögelerin rollerini gösterir ve mantığını açıklar.
- **WE DO (Birlikte Yapıyoruz):** Sistem sorar: *"Bu cümlenin ana eylemini bulabilir misin? Cümledeki fiile tıkla."* Öğrenci tıklar. Doğruysa tebrik ve pekiştirme açıklaması gelir; yanlışsa *"Possesses fiili Although yan cümlesinin içindedir, asıl mesajı veren ana fiile bakmalısın"* gibi yapıcı rehberlik sunar.
- **YOU DO (Sen Çözüyorsun):** Öğrenci bağımsız olarak ögeleri ve cümlenin yönünü çözer.

### 3.4. 3 Boyutlu Kelime Ustalık Modeli (`ThreeDimensionalMastery`)
Bir kelimenin durumu `MASTERED` olabilmesi için şu 3 boyutun tamamında başarılı olunmalıdır:
1. `RECOGNITION`: Kelimeyi tek başına ve telaffuzuyla tanıdı mı?
2. `SENTENCE_COMPREHENSION`: Cümledeki sözdizimi ve anlam rolünü çözdü mü?
3. `TRANSFER_APPLICATION`: Farklı ve daha önce görmediği bir fen sorusunda/bağlamında bağımsız olarak doğru kullandı mı?
- **Kritik Kural:** Aynı gün içinde 3'te 3 yapsa dahi kelime o gün `MASTERED` olmaz! En erken 3. gün ve 7. gün tekrar oturumlarında yeni bağlamda doğru yapıldığında `MASTERED` statüsüne geçer.

### 3.5. Günlük Havuz & Kümülatif Sarmal Model
- **Günlük Hedef:** ~30–35 kelime:
  - 10 Yeni Kelime
  - 15 Önceki Günlerin Tekrarı
  - 8 Zorlanılan/Tekrarlanan Kelime
- Yeni kelimeler öğretildikten sonra, önceki günlerin kelimeleriyle aynı cümlelerde ve okuma parçalarında sarmal olarak harmanlanır.

### 3.6. İzolasyon ve Sınav Güvenliği
- `productionBank.ts` içerisindeki 160 soruluk bağımsız sınav bankası asla değiştirilmez, tüketilmez veya alıştırmalarda harcanmaz.
- Öğrenme alıştırmaları `src/data/learning/learningQuestionsBank.ts` içerisindeki izole öğretim bankasından beslenir.
- 63 dondurulmuş dosya (SHA-256) ve mevcut 598 test %100 yeşil kalır.

---

## 4. VERİ SÖZLEŞMELERİ (DATA CONTRACTS)

```typescript
export interface DiagnosticQuestion {
  id: string;
  type: 'VOCAB_RECOGNITION' | 'SYNTAX_IDENTIFICATION' | 'CONNECTOR_DIRECTION';
  prompt: string;
  sentence?: string;
  options: { id: string; text: string; isCorrect: boolean; feedback: string }[];
  scaffoldTip: string;
}

export interface DiagnosticResult {
  score: number;
  total: number;
  vocabScore: number;
  syntaxScore: number;
  connectorScore: number;
  assignedLevel: 'FOUNDATIONAL' | 'INTERMEDIATE' | 'ADVANCED';
  timestamp: number;
}

export interface WordProgressionStep {
  level: number;
  englishText: string;
  turkishTranslation: string;
  focusPoint: string;
  syntacticBreakdown: { token: string; role: SyntacticRole }[];
}

export interface InteractiveDecompositionTask {
  id: string;
  mode: 'I_DO' | 'WE_DO' | 'YOU_DO';
  sentence: string;
  prompt: string;
  targetRole: SyntacticRole;
  correctTokenIndex: number;
  pedagogicalRationale: string;
  errorExplanations: Record<number, string>;
}
```

---

## 5. KULLANICI DENEYİMİ (İLK GÜN YOLCULUĞU)

1. Öğrenci uygulamayı açtığında ilk olarak **Tanılama** seçeneği veya doğrudan **Bugünkü Seviyeli Çalışmam** karşılar.
2. 3 dakikalık hızlı tanılama çalışmasını tamamlar $\rightarrow$ Sistemi öğrencinin başlangıç seviyesini kalibre eder.
3. Seviyesine uygun ilk kelime paketi açılır:
   - Zihinsel çapa ve sesli telaffuz dinlenir.
   - Tuzak sözcükler incelenir (*inhibit* vs *inhabit*).
   - Basit cümleden sınav seviyesine 3 basamakta ilerlenir.
4. İnteraktif Cümle Çözümleme Masasına geçilir:
   - Öğretmen önce model olur ("I DO").
   - Ardından öğrenciyle birlikte özne, fiil, bağlaç tıklanır ("WE DO").
   - Hata yapılırsa sistem tam olarak neden yanlış olduğunu izah eder.
5. Öğrenilen kavramlarla 3 kaliteli yönlendirmeli alıştırma çözülür.
   - Her şıkkın çeldirici analizi görülür.
6. Gün sonu raporu: Öğrenilen kelimeler, 3 boyutlu ustalık ilerlemesi ve yarının tekrar takvimi kaydedilir.

---

Bu spesifikasyon, kullanıcının talep ettiği tüm gereksinimleri eksiksiz olarak kapsamaktadır.
