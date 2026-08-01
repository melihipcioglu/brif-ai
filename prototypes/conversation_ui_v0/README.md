# BRIF.AI — Conversation-First Architectural Workspace v5.2

Bu klasör, BRIF.AI mimari karar destek platformu için hazırlanmış sohbet merkezli kullanıcı deneyimi (UX) prototipinin **v5.2 Kalite ve Tutarlılık Revizyonu** sürümüdür.

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

## v5.2 Revizyon Yenilikleri

1. **Tek ve Güvenilir Aktif Bağlam Kaynağı (`sessionState`)**:
   - Sohbet bağlam rozeti, seçili aşama, kat, alternatif ve mekân adı tek bir oturum durumundan yönlendirilir.
   - Ebeveyn banyosu senaryosunda eski "Çalışma Odası" bağlam etiketi kalmaz.

2. **Dinamik Bağlam Rozetleri**:
   - Aşama ve senaryoya göre anlık değişen bağlam etiketleri (Örn: `Ebeveyn Banyosu hakkında konuşuyorsunuz`, `Kat İlişkisi Anlatımı`, `Cephe Yönlenmesi — Ebeveyn Süiti`).

3. **Bağlama Duyarlı İlk Giriş Mesajları**:
   - Jenerik karşılama mesajı yalnız ilk açılışta gösterilir. Aşama değişimlerinde kısa bağlamsal giriş mesajları sunulur.

4. **Kullanıcı Beyanı, Sistem Yorumu ve Mimari Öneri Ayrımı**:
   - Sohbet cevaplarında ve mimar karar raporunda kullanıcının söylediği, sistemin yorumu ve mimari öneri net biçimde ayrılmıştır.

5. **Aşamalı İşlem Durum Çubuğu (Workflow Tracker Bar)**:
   - 5 adımlı durum çubuğu (`1. Talep Alındı ➔ 2. İhtiyaç Netleştirildi ➔ 3. Değerlendirme Yapıldı ➔ 4. İki Seçenek Hazırlandı ➔ 5. Kullanıcı Kararı Bekleniyor`).

6. **Tamamen Türkçeleştirilmiş Mimar Teknik Brief ve Karar Özeti**:
   - Tüm ham İngilizce terimler Türkçeleştirilmiştir (`Karar bekleniyor`, `Uygulandı`, `Ertelendi`, `Kaynak`, `Güven düzeyi`, `Doğrulama durumu`).

7. **"Sohbette Değiştir" Aksiyon Entegrasyonu**:
   - Mekân kartlarındaki butona tıklandığında sohbet paneli ilgili mekâna odaklanır.
