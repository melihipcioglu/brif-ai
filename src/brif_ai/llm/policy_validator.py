"""Project-context safety checks applied after schema validation."""

from __future__ import annotations

from brif_ai.llm.contracts import (
    PLAN_CHANGE_ACTIONS,
    ArchitecturalIntentResult,
    ConversationRequest,
    IntentType,
)


class PolicyValidationError(ValueError):
    """A schema-valid model response violated active project policy."""


class ArchitecturalIntentPolicyValidator:
    """Treat model output as untrusted suggestions constrained by active context."""

    def validate(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        active = request.active_context
        target = result.target

        self._match_scope("project_id", target.project_id, active.project_id)
        self._match_scope("building_id", target.building_id, active.building_id)
        self._match_scope("level_id", target.level_id, active.level_id)
        self._match_scope("zone_id", target.zone_id, active.zone_id)

        visible_ids = {
            entity.entity_id
            for entity in request.visible_entities
            if entity.project_id == active.project_id
            and (active.building_id is None or entity.building_id == active.building_id)
            and (active.level_id is None or entity.level_id == active.level_id)
            and (active.zone_id is None or entity.zone_id == active.zone_id)
        }
        referenced_ids = {action.target_entity_id for action in result.proposed_actions}
        if target.entity_id is not None:
            referenced_ids.add(target.entity_id)
        for entity_id in referenced_ids - {None}:
            if entity_id not in visible_ids:
                raise PolicyValidationError(
                    f"model referenced entity_id {entity_id!r} outside visible_entities"
                )

        is_modification = result.intent in {
            IntentType.MODIFY_SPACE,
            IntentType.MODIFY_RELATIONSHIP,
        } or any(action.action_type in PLAN_CHANGE_ACTIONS for action in result.proposed_actions)

        if (
            is_modification
            and target.entity_id is None
            and not any(action.target_entity_id for action in result.proposed_actions)
        ):
            return result.model_copy(
                update={
                    "needs_follow_up": True,
                    "follow_up_question": result.follow_up_question
                    or (
                        "Hangi görünür mekân veya öğe için değişiklik önerisi "
                        "hazırlamamı istersiniz?"
                    ),
                    "needs_user_confirmation": bool(result.proposed_actions),
                }
            )

        if result.proposed_actions:
            actions = [
                action.model_copy(update={"requires_user_confirmation": True})
                if action.action_type in PLAN_CHANGE_ACTIONS
                else action
                for action in result.proposed_actions
            ]
            return result.model_copy(
                update={"proposed_actions": actions, "needs_user_confirmation": True}
            )

        return result

    @staticmethod
    def _match_scope(field: str, proposed: str | None, active: str | None) -> None:
        if proposed is not None and proposed != active:
            raise PolicyValidationError(
                f"model returned {field} {proposed!r} outside the active context"
            )
