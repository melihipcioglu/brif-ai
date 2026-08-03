"""Project-context safety checks applied after schema validation."""

from __future__ import annotations

import re

from brif_ai.llm.contracts import (
    PLAN_CHANGE_ACTIONS,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    VisibleEntity,
)

_INTERNAL_ID_PATTERN = re.compile(
    r"(?<![\w])(?P<identifier>"
    r"(?:space|project|building|block|level|lvl|zone|entity)_"
    r"[A-Za-z0-9][A-Za-z0-9_-]*"
    r")(?![\w])",
    re.IGNORECASE,
)
_PUBLIC_FALLBACKS = {
    "space": "ilgili mekân",
    "project": "ilgili proje",
    "building": "ilgili yapı",
    "block": "ilgili yapı",
    "level": "ilgili kat",
    "lvl": "ilgili kat",
    "zone": "ilgili bölge",
    "entity": "ilgili öğe",
}
_RELATIONSHIP_TERMS = (
    "görünür",
    "görünmesin",
    "mahrem",
    "yakın",
    "uzak",
    "bağlant",
    "geçiş",
    "erişim",
    "ilişki",
    "kopuk",
    "yan yana",
    "ses ilişk",
    "akustik iliş",
    "komşu",
    "arasında",
)


def sanitize_public_text(text: str, visible_entities: list[VisibleEntity]) -> str:
    """Remove machine identifiers from text that can be shown to a user."""

    entity_names = {
        entity.entity_id.casefold(): entity.name for entity in visible_entities
    }

    def replacement(match: re.Match[str]) -> str:
        identifier = match.group("identifier")
        entity_name = entity_names.get(identifier.casefold())
        if entity_name is not None:
            return entity_name
        prefix = identifier.split("_", maxsplit=1)[0].casefold()
        return _PUBLIC_FALLBACKS[prefix]

    sanitized = _INTERNAL_ID_PATTERN.sub(replacement, text)
    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" +([,.!?;:])", r"\1", sanitized)
    sanitized = "\n".join(line.strip() for line in sanitized.splitlines()).strip()
    return sanitized or "İlgili kapsam hakkında ek bilgi gerekiyor."


class PolicyValidationError(ValueError):
    """A schema-valid model response violated active project policy."""


class ScopeMismatchError(PolicyValidationError):
    """A schema-valid response referenced a scope that is not currently active."""


class ArchitecturalIntentPolicyValidator:
    """Treat model output as untrusted suggestions constrained by active context."""

    def validate(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        result = self._normalize_intent(result, request)
        result = self._sanitize_public_fields(result, request.visible_entities)
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
                raise ScopeMismatchError(
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

    def recover_scope_mismatch(
        self,
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        """Turn a recoverable scope mismatch into a safe clarification result."""

        result = self._normalize_intent(result, request)
        target_entity_id = result.target.entity_id
        entity_name = next(
            (
                entity.name
                for entity in request.visible_entities
                if entity.entity_id == target_entity_id
            ),
            None,
        )
        subject = f"{entity_name} ile ilgili" if entity_name else "İlgili mekânla ilgili"
        question = (
            f"{entity_name} seçildikten sonra bu talebi birlikte inceleyelim mi?"
            if entity_name
            else "İlgili mekânı seçerek bu talebi birlikte inceleyelim mi?"
        )
        active = request.active_context
        recovered = result.model_copy(
            update={
                "assistant_message": (
                    f"{subject} talebinizi anladım. Ancak şu anda farklı bir "
                    "mekân kapsamındasınız."
                ),
                "target": EntityTarget(
                    project_id=active.project_id,
                    building_id=active.building_id,
                    level_id=active.level_id,
                    zone_id=active.zone_id,
                    entity_id=None,
                ),
                "missing_information": [
                    "Değerlendirilecek mekânın aktif kapsamda seçilmesi gerekiyor."
                ],
                "proposed_actions": [],
                "needs_follow_up": True,
                "follow_up_question": question,
                "needs_user_confirmation": False,
                "warnings": [],
            }
        )
        return self._sanitize_public_fields(recovered, request.visible_entities)

    @staticmethod
    def _normalize_intent(
        result: ArchitecturalIntentResult,
        request: ConversationRequest,
    ) -> ArchitecturalIntentResult:
        if result.intent not in {
            IntentType.MODIFY_SPACE,
            IntentType.REQUEST_VISUAL_PREFERENCE,
        }:
            return result

        public_model_text = " ".join(
            [
                result.assistant_message,
                *result.user_requirements,
                *result.interpreted_priorities,
                *result.constraints_to_check,
                *result.missing_information,
                *result.warnings,
                *(action.description for action in result.proposed_actions),
            ]
        )
        evidence = f"{request.message} {public_model_text}".casefold()
        if any(term in evidence for term in _RELATIONSHIP_TERMS):
            return result.model_copy(update={"intent": IntentType.MODIFY_RELATIONSHIP})
        return result

    @staticmethod
    def _sanitize_public_fields(
        result: ArchitecturalIntentResult,
        visible_entities: list[VisibleEntity],
    ) -> ArchitecturalIntentResult:
        def sanitize(text: str) -> str:
            return sanitize_public_text(text, visible_entities)

        actions = [
            action.model_copy(update={"description": sanitize(action.description)})
            for action in result.proposed_actions
        ]
        return result.model_copy(
            update={
                "assistant_message": sanitize(result.assistant_message),
                "follow_up_question": (
                    sanitize(result.follow_up_question)
                    if result.follow_up_question is not None
                    else None
                ),
                "user_requirements": [sanitize(text) for text in result.user_requirements],
                "interpreted_priorities": [
                    sanitize(text) for text in result.interpreted_priorities
                ],
                "constraints_to_check": [
                    sanitize(text) for text in result.constraints_to_check
                ],
                "missing_information": [
                    sanitize(text) for text in result.missing_information
                ],
                "proposed_actions": actions,
                "warnings": [sanitize(text) for text in result.warnings],
            }
        )

    @staticmethod
    def _match_scope(field: str, proposed: str | None, active: str | None) -> None:
        if proposed is not None and proposed != active:
            raise ScopeMismatchError(
                f"model returned {field} {proposed!r} outside the active context"
            )
