# BRIF.AI — Conversation & Spatial Analysis UI Prototype v4

Bu klasör, BRIF.AI mimari karar destek platformu için hazırlanmış 4 aşamalı bağımsız, etkileşimli kullanıcı deneyimi (UX) prototipinin **v4** sürümüdür.

> **DÜRÜSTLÜK VE BİLDİRİM NOTU:**  
> - **UX Prototipi**: Bu çalışma bir ön yüz (frontend) UX prototipidir; herhangi bir canlı LLM veya yapay zekâ modeli bağlı değildir.
> - **Demo Ön Kontrolü**: Resmî mevzuat veritabanı veya yerel idare onay sistemi bağlı değildir (`DEMO_UNVERIFIED`).
> - **Şematik Plan**: Kat planları mimari proje, uygulama veya ruhsat çizimi değildir. Geometrik değişiklikler örnek veri modelleri üzerinde simüle edilmektedir.
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

## v4 Yenilikleri ve Mimari Yapı

1. **Bağlamsal BRIF.AI Asistanı (`js/contextual_assistant.js`)**:
   - 4 aşamada ve Mimar Önizlemesinde kesintisiz çalışan tek bir asistan kimliği.
   - Tarayıcı belleğinde tutulan son 8 konuşma turu geçmişi.
   - Aktif aşamaya göre dinamik bağlam rozeti (Örn: `Taslak Plan — Alternatif B / Zemin Kat — Çalışma Odası Seçili`).

2. **İşlem Önizleme Sözleşmesi (`data/assistant_action_schema.demo.json`)**:
   - Kullanıcı niyetini (intent) ve doğal dil komutlarını yapılandırılmış JSON işlem kontratlarına çevirir.
   - Gelecek mimaride LLM niyeti belirleyecek, geometri motoru planı güncelleyecektir.

3. **Etkileşimli Plan Editörü & Geometri Motoru (`js/plan_editor.js` & `data/plan_alternatives.demo.json`)**:
   - Yapılandırılmış JSON verisinden dinamik SVG üretimi.
   - Mouse ile oda sürükleme (drag), ghost çizgi önizlemesi, bina dış sınırı ve oda çakışma engeli.
   - Resize kulpları ve klavye erişilebilirliği (Ok tuşları: taşıma, Shift+Ok: boyutlandırma).
   - Mekân kilitleme (lock) ve takas (swap) simülasyonu.

4. **Teknik Ön Kontrolör (`js/rule_evaluator.js` & `data/rules.demo.json`)**:
   - 4 kategori: Mevzuat/Yasal ön kontrol, Ergonomi & kullanılabilirlik, Geometri & mekânsal ilişkiler, Kullanıcı tercihiyle çelişki.
   - **2 Metre Yatak Odası Senaryosu**: Dar kenar <= 2.0m tespit edildiğinde konfor riski uyarısı ve aksiyonel alternatifler.
   - **Yanıltıcı Kullanım Adı Reddi**: Depo gösterip yatak odası kullanma taleplerini güvenlik/mevzuat riski nedeniyle açıkça reddetme ve mimara not ekleme.

5. **Karar ve Revizyon Geçmişi (`js/change_history.js`)**:
   - Undo/Redo yığını (Ctrl+Z / Ctrl+Y).
   - Mimar Önizleme modunda profesyonel kronolojik Karar ve Revizyon Raporu.
