# BRIF.AI — Universal Architectural Context Platform v6.0

Bu klasör, BRIF.AI platformu için hazırlanmış **Genel Bağlam ve Kapsam Yönetimi Sistemi (v6.0)** sürümüdür.

> **MİMARİ TEMEL İLKE:**  
> **Context is determined by entity relationships and active workspace scope, never by room names or project-specific labels.**  
> *(Bağlam, oda adlarına veya örnek projeye özel koşullara göre değil; varlık ilişkileri ve aktif çalışma kapsamına göre belirlenir.)*

---

## Prototipi Çalıştırma

Prototipi yerel bilgisayarınızda görüntülemek için şu komutu çalıştırın:

```powershell
py -3.13 -m http.server 8080 -d prototypes/conversation_ui_v0
```

Daha sonra tarayıcınızda şu adrese gidin:

[http://localhost:8080](http://localhost:8080)

---

## v6.0 Genel Bağlam Mimarisi Yenilikleri

1. **Evrensel Varlık Hiyerarşisi (`EntityHierarchy`)**:
   - `Project -> Building/Block/Tower -> Level/Floor -> Zone/Department -> Space -> Element` hiyerarşisini destekler.
   - Oda adlarına bağlı kod yazımını tamamen yasaklar.

2. **Merkezi Bağlam Durum Makinesi (`ContextStateMachine`)**:
   - Tüm bağlam olayları (`PROJECT_SELECTED`, `LEVEL_SELECTED`, `ENTITY_SELECTED`, `SCENARIO_SUSPENDED` vb.) merkezi reducer üzerinden yönetilir.
   - Dağınık JS dosyalarının bağımsız olarak etiket değiştirmesini engeller.

3. **Bağlam Uyumluluk Doğrulayıcısı (`ContextValidator`)**:
   - Her görünüm veya bağlam değişiminde aktif görünüm ile konuşma kapsamının uyumunu denetler.
   - Uyumsuzluk durumunda eski bağlamı askıya alır (`suspendedContext`) ve çalışma alanında uyarır:
     `"⚠️ Önceki konu başka bir kat/zon kapsamındaydı. Bu görünümde mevcut katı inceliyoruz."`
   - Kullanıcı tek tıkla `[↩ Önceki Bağlama Dön]` butonuyla askıdaki bağlama dönebilir.

4. **Konuşma Geçmişi İçin Bağlam Anlık Görüntüleri (Context Snapshots)**:
   - Her sohbet mesajı `{ messageId, projectId, buildingId, levelId, zoneId, entityId, scenarioId, timestamp }` anlık görüntüsüyle saklanır.
   - Görünüm değişiminde geçmiş silinmez, ancak yeni kapsamda aktif bağlam gibi sızdırılmaz.

5. **Sentetik Çoklu Proje Test Süiti**:
   - **Test A**: İki katlı müstakil konut (`house_2story`)
   - **Test B**: 50 katlı finans kulesi (`tower_50floor` — A Kulesi 18. Kat vs 32. Kat)
   - **Test C**: Çok bloklu teknoloji kampüsü (`campus_multiblock` — Blok A vs Blok B)
