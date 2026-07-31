# BRIF.AI — Conversation UI Prototype v0

Bu klasör, BRIF.AI mimari karar destek platformu için hazırlanmış bağımsız, etkileşimli bir kullanıcı deneyimi (UX) prototipidir.

> **NOT:** Bu çalışma bir ön yüz UX prototipidir. Herhangi bir backend, veritabanı veya canlı yapay zekâ model çağrısı içermez. Etkileşimler ve yanıtlar tarayıcı tarafında simüle edilmektedir.

## Prototipi Çalıştırma

Prototipi yerel bilgisayarınızda görüntülemek için şu komutu çalıştırın:

```powershell
py -3.13 -m http.server 8080 -d prototypes/conversation_ui_v0
```

Daha sonra tarayıcınızda şu adrese gidin:

[http://localhost:8080](http://localhost:8080)

## Özellikler

1. **Doğal Diyalog Arayüzü**: Anket, Google Forms veya radio button listeleri yerine mimari bir yapay zekâ danışmanıyla konuşma hissi veren diyalog ekranı.
2. **Canlı İhtiyaç Profili ("Sizi nasıl anladım?")**: Sohbet ilerledikçe sağ panelde otomatik olarak güncellenen "Yaşam düzeni", "Öncelikler" ve "Henüz netleşmeyenler" kartları.
3. **Mimar Önizleme Modu**: Sağ üstteki düğme ile müşteri görünümünden teknik mimari brief ve güven düzeyi analiz raporuna geçiş.
4. **Etkileşimli Teyit**: Yanlış anlaşılma durumunda ilgili mimari yorumu doğrudan düzenleme veya onaylama imkânı.
