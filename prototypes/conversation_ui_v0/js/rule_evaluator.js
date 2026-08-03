/**
 * BRIF.AI — Technical Rule Evaluator Engine (v4 Demo)
 *
 * Categorizes controls into 4 distinct groups:
 * 1. Mevzuat / yasal ön kontrol (Demo baseline)
 * 2. Ergonomi ve iç mimari kullanılabilirlik
 * 3. Proje geometrisi ve mekânsal ilişkiler
 * 4. Kullanıcı tercihleriyle çelişki
 */

class RuleEvaluator {
  constructor() {
    this.rules = [
      {
        rule_id: "R_BEDROOM_NARROW_EDGE_2M",
        category: "Ergonomi ve iç mimari kullanılabilirlik",
        applies_to: ["bedroom", "master", "child1", "child2"],
        parameter: "narrow_edge",
        threshold: 2.0,
        severity: "CRITICAL_RISK",
        statusText: "Konfor açısından riskli",
        user_message: "Bu genişlik (<= 2.0 m), seçili yatak odası kullanımı için demo ön kontrolündeki alt sınırın altında kalıyor. Ayrıca yatak, dolap ve geçiş alanı birlikte sağlanamıyor.",
        architect_message: "Yatak odası dar kenarı 2.0m altına düşürüldü. Çift/tek kişilik yatak (200cm) ve sirkülasyon daralması mevcut.",
        alternatives: [
          "Odayı genişlet",
          "Yatak yönünü değiştir",
          "Komşu mekândan sınırlı alan aktar",
          "Programdaki başka bir mekânı küçült",
          "Bu hacmin gerçek kullanım amacını yeniden değerlendir",
          "Mimara teyit için bırak"
        ],
        source_type: "Ergonomi Standartları Simülasyonu",
        source_status: "DEMO_UNVERIFIED"
      },
      {
        rule_id: "R_MISLEADING_NAME_BYPASS",
        category: "Mevzuat / yasal ön kontrol",
        applies_to: ["all_spaces"],
        parameter: "rename_attempt",
        threshold: "depo_to_bedroom",
        severity: "REJECTED_METHOD",
        statusText: "Uygulanamaz / Yasal Risk",
        user_message: "Bu alanı depo adıyla gösterip sürekli yatak odası olarak kullanmayı önermiyorum. Bunun yerine hacmi yasal ve güvenli kullanıma yaklaştıran seçenekleri inceleyebilir veya ihtiyacınızı mimara açık bir özel kullanım notuyla aktarabiliriz.",
        architect_message: "Kullanıcı özel kullanım talebi — resmî kullanım ve uygunluk teyidi gerekli. Yasal süzgeç/yangın kaçışı bypass talebi reddedildi.",
        alternatives: [
          "Odayı yasal yatak odası standartlarına getirmek için genişlet",
          "Mimara açık özel kullanım notu olarak ilet"
        ],
        source_type: "Mimari Etik & Güvenlik İlkesi",
        source_status: "DEMO_UNVERIFIED"
      },
      {
        rule_id: "R_WORK_ACOUSTIC_PREFERENCE",
        category: "Kullanıcı tercihleriyle çelişki",
        applies_to: ["study"],
        parameter: "acoustic_distance",
        threshold: 20,
        severity: "USER_CONFLICT",
        statusText: "Kullanıcı tercihiyle çelişiyor",
        user_message: "Çalışma odası yaşam alanına çok yaklaştığında online toplantılarda ses çakışması riski oluşabilir. Seçtiğiniz 'Sessizlik' tercihiyle çelişki doğabilir.",
        architect_message: "Kullanıcı 'Sessizlik' istedi; ancak çalışma alanı salona tam açık hale getirildi.",
        alternatives: ["Kapalı duvar sınırını koru", "Kayar akustik cam panel ekle"],
        source_type: "Kullanıcı Tercih Matrisi",
        source_status: "DEMO_UNVERIFIED"
      },
      {
        rule_id: "R_OUT_OF_BOUNDS",
        category: "Proje geometrisi ve mekânsal ilişkiler",
        applies_to: ["all_spaces"],
        parameter: "boundary",
        threshold: 0,
        severity: "GEOMETRY_ERROR",
        statusText: "Uygulanamaz",
        user_message: "Mekân dış bina sınırlarının dışına çıkartılamaz. Şematik konut kabuğu korunmalıdır.",
        architect_message: "Sürükleme dış gabari sınırlarını aştı. Grid kısıtı uygulandı.",
        alternatives: ["Bina içi boş alana taşı"],
        source_type: "Geometri Çekirdeği",
        source_status: "DEMO_UNVERIFIED"
      }
    ];
  }

  evaluateSpaceOperation(space, operationType, params = {}) {
    const results = [];

    // 1. Two-Meter Bedroom Special Scenario (Requirement 12)
    if ((space.use_type === 'bedroom' || space.id === 'master' || space.id === 'child1' || space.id === 'child2') && params.narrow_edge && params.narrow_edge <= 2.0) {
      const r = this.rules.find(rule => rule.rule_id === 'R_BEDROOM_NARROW_EDGE_2M');
      if (r) results.push({ ...r, current_value: params.narrow_edge });
    }

    // 2. Misleading Name Bypass Request (Requirement 13)
    if (params.is_misleading_rename) {
      const r = this.rules.find(rule => rule.rule_id === 'R_MISLEADING_NAME_BYPASS');
      if (r) results.push({ ...r, current_value: params.rename_text });
    }

    // 3. Acoustic Conflict Check (Requirement 15)
    if (space.id === 'study' && params.is_open_living) {
      const r = this.rules.find(rule => rule.rule_id === 'R_WORK_ACOUSTIC_PREFERENCE');
      if (r) results.push({ ...r });
    }

    // 4. Out of bounds check
    if (params.out_of_bounds) {
      const r = this.rules.find(rule => rule.rule_id === 'R_OUT_OF_BOUNDS');
      if (r) results.push({ ...r });
    }

    // Default Pass if no violations
    if (results.length === 0) {
      results.push({
        rule_id: "R_PASS_DEFAULT",
        category: "Proje geometrisi ve mekânsal ilişkiler",
        severity: "PASS",
        statusText: "Ön kontrolden geçti",
        user_message: "Yapılan şematik düzenleme ön kontrol kriterlerine ve ilişkilerine uygundur.",
        architect_message: "Şematik koordinasyon kontrolü başarılı.",
        alternatives: [],
        source_type: "Şematik Koordinasyon Kontrolü",
        source_status: "DEMO_UNVERIFIED"
      });
    }

    return results;
  }
}

// Global Export
window.RuleEvaluator = RuleEvaluator;
