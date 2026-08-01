# BRIF.AI — Conversation-First Architectural Workspace v5.1

Bu klasör, BRIF.AI mimari karar destek platformu için hazırlanmış sohbet merkezli kullanıcı deneyimi (UX) prototipinin **v5.1 Kararlı** sürümüdür.

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

## v5.1 Hata Düzeltmeleri & Düzeltmeler

1. **Ebeveyn Banyosu Akışı ve Konuşma Durum Yönetimi (`js/conversation_orchestrator.js`)**:
   - Türkçe karakter normalizasyonu ve durum motoru (`ConversationState`) ile genel fallback hatası ("Bu prototipte bu isteği otomatik işleyemiyorum") tamamen giderilmiştir.
   - Quick reply ve klavye girdisi aynı senaryoyu kesintisiz yürütür.

2. **Görünür Analiz Değerlendirme Kartı (`js/workspace_presenter.js`)**:
   - Ana çalışma alanında "Demo mimari değerlendirmesi" etiketli şeffaf 6 adımlı değerlendirme kartı gösterilir.

3. **Seçenek Karşılaştırması & `alert()` Kullanılmaması**:
   - Değerlendirme sonrasında Seçenek 1 ve Seçenek 2 yan yana çalışma alanında gösterilir. Seçim sonuçları sohbet ve çalışma alanında güncellenir.

4. **Dinamik Mimar Karar Raporu (`js/change_history.js`)**:
   - Mimar raporu sabit demo metninden kurtarılmış; aktif konuşma durumundan (Ebeveyn banyosu talebi, anlaşılan ihtiyaç, seçenekler ve karar durumu) dinamik beslenecek şekilde düzeltilmiştir.

5. **Mekân Programı Kartlı Grid Düzeni**:
   - Mekân programı ham metin listesinden kartlı grid düzenine geri getirilmiştir.

6. **İlk Ekran ("Yaşam Ritminizi Anlama") Canlı Dashboard**:
   - Sol taraftaki büyük boş alan yerine canlı "Şu ana kadar sizi nasıl anladım?" paneli eklenmiştir.

7. **Aynı Koordinatta Kat İlişkisi (Overlay)**:
   - Zemin Kat (%28 saydam) ve Üst Kat aynı SVG koordinat sisteminde çakıştırılmış, metin çakışmaları giderilmiştir.

8. **Gerçek Plan Üzerinde Cephe Yönlenmesi**:
   - Yönlenme modu boş dikdörtgen yerine gerçek kat planı üzerinde Kuzey (mavi) ve Güney (sarı) cephe bantları ile gösterilir.

9. **Plan Varsayımları Modal Drawer Düzeltmesi**:
   - Formun sayfa altına taşması engellenmiş, düzgün kapatma ve kaydetme düğmelerine sahip modal drawer haline getirilmiştir.
