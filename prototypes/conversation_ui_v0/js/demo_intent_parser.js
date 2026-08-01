/**
 * BRIF.AI — Demo Intent Parser (v4 Contract Implementation)
 *
 * Converts natural user messages into structured action JSON contracts
 * according to data/assistant_action_schema.demo.json.
 */

class DemoIntentParser {
  constructor() {
    this.scenarioRules = [
      {
        pattern: /(iki metre|2 metre|2m)/i,
        intent: "resize_space",
        special_case: "two_meter_bedroom",
        target_space: "master",
        operation: { type: "resize", requested_area_range: [8, 10], narrow_edge: 1.9 },
        preserve: ["total_enclosed_area"],
        effects: ["ergonomics_clearance_loss"],
        requires_confirmation: true
      },
      {
        pattern: /(depo yazalım|depo gösterelim|sonradan yatak odası)/i,
        intent: "usage_mismatch_request",
        special_case: "misleading_bypass",
        target_space: "study",
        operation: { type: "rename_attempt", rename_text: "depo_to_bedroom" },
        preserve: [],
        effects: ["safety_compliance_risk"],
        requires_confirmation: true
      },
      {
        pattern: /(10-11|10–11|10 m²|11 m²|küçült)/i,
        intent: "resize_space",
        target_space: "study",
        operation: { type: "resize", requested_area_range: [10, 11] },
        preserve: ["kitchen_area", "total_enclosed_area"],
        effects: ["children_room_area", "circulation_ratio"],
        requires_confirmation: true
      },
      {
        pattern: /(büyüt|salonu büyüt)/i,
        intent: "resize_space",
        target_space: "living",
        operation: { type: "resize", requested_area_range: [34, 38] },
        preserve: ["total_enclosed_area"],
        effects: ["terrace_area", "study_area"],
        requires_confirmation: true
      },
      {
        pattern: /(yaklaştır|taşı|konum)/i,
        intent: "move_space",
        target_space: "study",
        operation: { type: "drag", new_position: { x: 250, y: 270 } },
        preserve: ["study_area"],
        effects: ["living_proximity", "kitchen_proximity"],
        requires_confirmation: true
      },
      {
        pattern: /(yerini değiştir|takas)/i,
        intent: "swap_spaces",
        target_space: "study",
        second_space_id: "kitchen",
        operation: { type: "swap" },
        preserve: ["study_area", "kitchen_area"],
        effects: ["wet_core_alignment", "terrace_access"],
        requires_confirmation: true
      },
      {
        pattern: /(kilitle|değiştirme|sabit)/i,
        intent: "lock_space",
        target_space: "study",
        operation: { type: "lock" },
        preserve: ["study_geometry"],
        effects: ["other_spaces_adjusted"],
        requires_confirmation: false
      },
      {
        pattern: /(geri al|önceki hâle dön|iki adım)/i,
        intent: "undo",
        target_space: "study",
        operation: { type: "undo" },
        preserve: [],
        effects: ["revert_last_change"],
        requires_confirmation: false
      },
      {
        pattern: /(neyi bozar|etki)/i,
        intent: "ask_impact",
        target_space: "study",
        operation: { type: "inquire" },
        preserve: [],
        effects: [],
        requires_confirmation: false
      }
    ];
  }

  parseMessage(text, currentContext = {}) {
    const textLower = text.toLowerCase();

    for (const scenario of this.scenarioRules) {
      if (scenario.pattern.test(textLower)) {
        return {
          intent: scenario.intent,
          special_case: scenario.special_case || null,
          target: {
            space_id: currentContext.space_id || scenario.target_space || "study",
            floor: currentContext.floor || "ground",
            alternative: currentContext.alternative || "b",
            second_space_id: scenario.second_space_id || null
          },
          operation: scenario.operation,
          preserve: scenario.preserve,
          effects: scenario.effects,
          requires_confirmation: scenario.requires_confirmation,
          source_message: text
        };
      }
    }

    // Default Ambiguous Request fallback
    return {
      intent: "ambiguous_request",
      target: {
        space_id: currentContext.space_id || "study",
        floor: currentContext.floor || "ground",
        alternative: currentContext.alternative || "b"
      },
      operation: { type: "unknown" },
      preserve: [],
      effects: [],
      requires_confirmation: false,
      source_message: text
    };
  }
}

// Global Export
window.DemoIntentParser = DemoIntentParser;
