# BRIF.AI — Conversation-First Architectural Workspace v5

Bu klasör, BRIF.AI mimari karar destek platformu için hazırlanmış sohbet merkezli kullanıcı deneyimi (UX) prototipinin **v5** sürümüdür.

> **DÜRÜSTLÜK VE BİLDİRİM NOTU:**  
> - **UX Prototipi**: Bu çalışma bir ön yüz (frontend) UX prototipidir; herhangi bir canlı LLM veya yapay zekâ modeli bağlı değildir.
> - **Demo Mimari Değerlendirmesi**: Resmî mevzuat veritabanı veya yerel idare onay sistemi bağlı değildir (`DEMO_UNVERIFIED`).
> - **Şematik Plan**: Kat planları mimari proje, uygulama veya ruhsat çizimi değildir. Geometrik değişiklikler örnek veri modelleri üzerinde simüle edilmektedir.

---

## Prototipi Çalıştırma

Prototipi yerel bilgisayarınızda görüntülemek için şu komutu çalıştırın:

```powershell
py -3.13 -m http.server 8080 -d prototypes/conversation_ui_v0
```

Daha sonra tarayıcınızda şu adrese gidin:

[http://localhost:8080](http://localhost:8080)

---

## v5 Yenilikleri ve Mimari Yapı

1. **Sohbet Merkezli Çalışma Alanı (`%68` Sol Çalışma Alanı / `%32` Sağ Sohbet Paneli)**:
   - Kullanıcı karmaşık CAD araçları kullanmak zorunda kalmaz.
   - Tüm aşamalarda kesintisiz ve zengin sohbet paneli aktiftir; aşama değiştirildiğinde sohbet geçmişi kaybolmaz.

2. **Dinamik Görsel Sunum Motoru (`js/workspace_presenter.js`)**:
   - Sohbet cevaplarına paralel çalışma alanını dinamik günceller.
   - **Kat İlişkisi Anlatım Modu**: Zemin kat %30 saydam gösterilir, üst kat tesisat hizası ve merdiven boşluğu (sarı) vurgulanır.
   - **Seçenek Karşılaştırma Modu**: Ebeveyn banyosunu kuzeye taşıma senaryosunda Seçenek 1 ve Seçenek 2 yan yana kartlar hâlinde sunulur.

3. **Profesyonel Mimar Diyaloğu & Senaryo Orkestrasyonu (`js/conversation_orchestrator.js`)**:
   - Kullanıcı talebini körlemesine uygulamadan önce talebin arkasındaki ihtiyacı anlayan takip soruları sorar.
   - Mimari değerlendirme aşamalarını (loading progress steps) görünür biçimde simüle eder.

4. **İkincil Gelişmiş Araçlar**:
   - Manuel oda sürükleme, boyutlandırma, kilit ve takas araçları `🛠️ Planı Elle Düzenle (Gelişmiş Araçlar)` altında ikincil araç olarak korunmuştur.

5. **Temiz Mimar Karar Raporu (`js/change_history.js`)**:
   - Mimar Önizlemesinde son kullanıcı talebi, anlaşılan ihtiyaç, sunulan seçenekler, teknik ön kontroller ve teyit durumunu içeren profesyonel rapor.
