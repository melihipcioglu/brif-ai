# BRIF.AI — Scope-Driven Workspace Platform v6.1

Bu klasör, BRIF.AI platformu için hazırlanmış **Kapsam-Güdümlü Çalışma Alanı Çözümleyicisi ve Uyumlu Render Koruması (v6.1)** sürümüdür.

> **MİMARİ TEMEL İLKE:**  
> **No workspace content may render unless its document scope is compatible with the active context.**  
> *(Belge kapsamı aktif bağlamla uyumlu olmayan hiçbir çalışma alanı içeriği gösterilemez.)*

---

## Prototipi Çalıştırma

Prototipi yerel bilgisayarınızda görüntülemek için şu komutu çalıştırın:

```powershell
py -3.13 -m http.server 8080 -d prototypes/conversation_ui_v0
```

Daha sonra tarayıcınızda şu adrese gidin:

[http://localhost:8080](http://localhost:8080)

---

## v6.1 Kapsam Çözümleyici ve Render Koruması Yenilikleri

1. **Kapsam-Güdümlü Belge Deposu (`ScopedDocumentStore`) & Çözümleyici (`WorkspaceScopeResolver`)**:
   - Belge seçim önceliği: `entity` > `zone` > `level` > `building` > `project`.
   - Uyumlu belge bulunamadığında eski projelerin/katların belgeleri asla sızdırılmaz.

2. **Uyumlu Render Koruması (`RenderCompatibilityGuard`)**:
   - Uyumsuz belge tespit edildiğinde önceki DOM içeriği anında temizlenir.
   - Ekranda dürüst boş durum ("Bu kapsam için çalışma alanı verisi bulunmuyor") gösterilir.

3. **İlk Ayrışan Hiyerarşi Seviyesi Hesaplaması**:
   - Askıya alınan bağlam mesajları hiyerarşik parent zincirine göre dinamik üretilir:
     - Proje ayrışması: *"Önceki konuşmanız İki Katlı Müstakil Konut projesine aitti. Şimdi 50 Katlı Finans Kulesi projesini inceliyorsunuz."*
     - Kat ayrışması: *"Önceki konuşmanız 18. Kat kapsamındaydı. Şimdi 32. Kat inceleniyor."*

4. **Teknik ID'lerin UI'dan Kaldırılması & Breadcrumb Üretimi**:
   - `lvl_ground` veya `tower_a` gibi ham ID'ler kullanıcıya gösterilmez.
   - İnsan tarafından okunabilir breadcrumb üretilir: `50 Katlı Finans Kulesi › A Kulesi › 18. Kat › Yönetim Zonu`.

5. **Kapsama Filtrelenmiş Sohbet & Mimar Karar Raporu**:
   - Sohbet görünümünde aktif kapsama uyan mesajlar gösterilir.
   - Mimar raporu bileşik kapsam anahtarıyla üretilir; başka projenin raporu ekrana sızdırılmaz.
