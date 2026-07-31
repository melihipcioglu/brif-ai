# BRIF.AI — Conversation & Spatial Analysis UI Prototype v0

Bu klasör, BRIF.AI mimari karar destek platformu için hazırlanmış 4 aşamalı bağımsız, etkileşimli kullanıcı deneyimi (UX) prototipidir.

> **DÜRÜSTLÜK VE BİLDİRİM NOTU:**  
> - Bu çalışma bir ön yüz (frontend) UX prototipidir.
> - Görsel kartlar ve şematik kat planları yerel olarak hazırlanmış özgün SVG mimari çizimleridir.
> - Mekân programı ve ilişki diyagramları örnek prototip verisidir.
> - Herhangi bir canlı veritabanı, yapay zekâ modeli veya otomatik plan üretim motoru **kullanılmamaktadır**.
> - Kullanıcı onayı alınmadan gerçek sisteme entegre edilmeyecektir.

---

## Prototipi Çalıştırma

Prototipi yerel bilgisayarınızda görüntülemek için şu komutu çalıştırın:

```powershell
py -3.13 -m http.server 8080 -d prototypes/conversation_ui_v0
```

Daha sonra tarayıcınızda şu adrese gidin:

[http://localhost:8080](http://localhost:8080)

---

## Prototip Aşamaları ve Özellikler

1. **Süreç Navigasyonu (Stepper Bar)**:
   - `Yaşamınızı Anlama` (Sohbet diyalogu)
   - `Görsel Tercihler` (Kontrollü mekânsal ilişki kartları)
   - `Mekân Programı` (Kart tabanlı program ve ilişki diyagramı)
   - `Taslak Plan` (Şematik plan alternatifleri ve dayanaklar)

2. **Görsel Tercihler Analizi**:
   - Telifsiz, özgün mimari SVG illüstrasyonları (`assets/preferences/`).
   - `Bana uygun` seçildiğinde mekânsal nitelik çipleri (`Sessizlik`, `Görsel bağlantı`, `Esneklik`, `Gün ışığı`, vb.).
   - Seçimlerin "Sizi nasıl anladım?" paneline dayanaklı olarak yansıması.

3. **Mekân Programı ve İlişki Şeması**:
   - Ön değerlendirme alan aralıkları ve kullanıcı müdahale butonları.
   - İnteraktif mekânsal düğüm grafiği ve ilişki türleri (doğrudan yakınlık, kontrollü esnek bağlantı, akustik ayrışma).

4. **Şematik Taslak Plan Alternatifleri**:
   - `Alternatif A — Kontrollü Ayrışma` vs `Alternatif B — Esnek Bağlantı` (`assets/plans/`).
   - Mekânlara tıklayarak mekan kararlarının kullanıcı beyanı ve tercihlerine dayandırılması.
   - Kullanıcı plan eğiliminin kaydedilmesi.

5. **Mimar Önizlemesi**:
   - Sağ üstteki düğme ile müşteri görünümünden teknik mimari brief, güven düzeyi ve kullanıcı eğilimi sentezine geçiş.
