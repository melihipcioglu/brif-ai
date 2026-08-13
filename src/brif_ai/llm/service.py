"""Provider-neutral local conversation service."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from brif_ai.brief.models.common import (
    BriefItemKind,
    OpenQuestionStatus,
    Priority,
)
from brif_ai.brief.models.snapshot import BriefSnapshot
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
    apply_approved_brief_mutation,
)
from brif_ai.conversation.elicitation.models import get_permitted_mutations_for_topic
from brif_ai.conversation.elicitation.planner import (
    ElicitationPlanner,
    question_for_topic,
)
from brif_ai.llm.contracts import (
    ArchitecturalIntentResult,
    BriefMutationApprovalRecord,
    ConversationInterpretationResponse,
    ConversationRequest,
    EntityTarget,
    HealthResponse,
    IntentType,
    LocalModelInfo,
    ProposalApprovalRecord,
    ProposedAction,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    ScopeMismatchError,
    is_neutral_elicitation_start,
)
from brif_ai.llm.provider import (
    LocalLLMProvider,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from brif_ai.llm.settings import LocalLLMSettings

LLM_DISABLED_MESSAGE = "Yerel yapay zekâ bağlantısı devre dışı. Demo konuşma modu kullanılıyor."


def _build_provider_output_schema(
    request: ConversationRequest,
) -> dict[str, object]:
    """Constrain neutral elicitation turns before provider inference."""

    schema = deepcopy(ArchitecturalIntentResult.model_json_schema())
    elicitation = request.elicitation_context

    # Active OPEN takes precedence over neutral-start follow-up selection.
    # When an elicitation question is already OPEN, the provider may interpret
    # the user's answer but may never create another follow-up question.
    if elicitation is not None and elicitation.open_question_topics:
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return schema

        active_topic = elicitation.open_question_topics[0]
        permitted = get_permitted_mutations_for_topic(active_topic)
        permitted_strs = [m.value for m in permitted]

        properties["intent"] = {
            "type": "string",
            "enum": [IntentType.GATHER_REQUIREMENT.value],
        }
        properties["needs_follow_up"] = {
            "type": "boolean",
            "enum": [False],
        }
        properties["follow_up_question"] = {"type": "null"}
        properties["follow_up_topic"] = {"type": "null"}
        properties["needs_user_confirmation"] = {
            "type": "boolean",
            "enum": [True],
        }

        properties["target"] = {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "enum": [request.active_context.project_id]},
                "building_id": {"type": "null"},
                "level_id": {"type": "null"},
                "zone_id": {"type": "null"},
                "entity_id": {"type": "null"},
            },
            "required": ["project_id"],
        }

        # An active elicitation question is a brief-understanding turn,
        # never a geometry/plan-action turn.
        properties["proposed_actions"] = {
            "type": "array",
            "maxItems": 0,
        }

        current_mutations = properties.get("proposed_brief_mutations")
        if isinstance(current_mutations, dict):
            properties["proposed_brief_mutations"] = {
                **current_mutations,
                "maxItems": 1,
            }

        # Constrain mutation_type in $defs for ProposedBriefMutation
        defs = schema.get("$defs", {})
        if isinstance(defs, dict) and "ProposedBriefMutation" in defs:
            mutation_def = defs["ProposedBriefMutation"]
            if isinstance(mutation_def, dict) and "properties" in mutation_def:
                mut_props = mutation_def["properties"]
                if isinstance(mut_props, dict) and "mutation_type" in mut_props:
                    mut_props["mutation_type"] = {
                        "type": "string",
                        "enum": permitted_strs,
                    }

        if active_topic.value == "household":
            # Reuse the Pydantic-generated HouseholdComposition schema instead of
            # hand-writing a second JSON-schema dialect for Ollama. Ollama receives
            # a required structured object; unrelated turns use explicit null counts.
            required = schema.get("required")
            if not isinstance(required, list):
                required = []
                schema["required"] = required
            if "household_composition" not in required:
                required.append("household_composition")

            if not isinstance(defs, dict):
                raise TypeError("ArchitecturalIntentResult $defs must be an object")
            household_def = defs.get("HouseholdComposition")
            if not isinstance(household_def, dict):
                raise TypeError("HouseholdComposition schema definition is missing")
            household_def["required"] = [
                "total_count",
                "adult_count",
                "child_count",
                "child_ages",
                "notes",
            ]
            properties["household_composition"] = {"$ref": "#/$defs/HouseholdComposition"}

        return schema

    if (
        elicitation is None
        or elicitation.allowed_follow_up_topic is None
        or not is_neutral_elicitation_start(request.message)
    ):
        return schema

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise TypeError("ArchitecturalIntentResult schema properties must be an object")

    allowed_topic = elicitation.allowed_follow_up_topic.value

    properties["intent"] = {
        "type": "string",
        "enum": [IntentType.GATHER_REQUIREMENT.value],
    }
    properties["needs_follow_up"] = {
        "type": "boolean",
        "enum": [True],
    }
    properties["follow_up_question"] = {
        "type": "string",
        "minLength": 1,
    }
    properties["follow_up_topic"] = {
        "type": "string",
        "enum": [allowed_topic],
    }
    properties["needs_user_confirmation"] = {
        "type": "boolean",
        "enum": [False],
    }
    properties["answers_current_open_question"] = {
        "type": "boolean",
        "enum": [False],
    }

    # A neutral starter carries no new requirement or proposal.
    for field in (
        "user_requirements",
        "interpreted_priorities",
        "constraints_to_check",
        "proposed_actions",
        "proposed_brief_mutations",
        "warnings",
    ):
        current = properties.get(field)
        if not isinstance(current, dict):
            raise TypeError(f"{field} schema must be an object")
        properties[field] = {**current, "maxItems": 0}

    # Keep the response compact and focused on the one planner-selected gap.
    current_missing = properties.get("missing_information")
    if not isinstance(current_missing, dict):
        raise TypeError("missing_information schema must be an object")
    properties["missing_information"] = {
        **current_missing,
        "maxItems": 1,
    }

    return schema


class StaleContextError(ValueError):
    """An asynchronous response or proposal belongs to an older context."""


class LocalLLMConversationService:
    def __init__(
        self,
        settings: LocalLLMSettings,
        provider: LocalLLMProvider,
        policy_validator: ArchitecturalIntentPolicyValidator | None = None,
        elicitation_planner: ElicitationPlanner | None = None,
    ) -> None:
        self.settings = settings
        self.provider = provider
        self.policy_validator = policy_validator or ArchitecturalIntentPolicyValidator()
        self.elicitation_planner = elicitation_planner or ElicitationPlanner()

    async def health(self) -> HealthResponse:
        selected_model = self.settings.model or None
        if not self.settings.enabled:
            return HealthResponse(
                status="degraded",
                llm_enabled=False,
                provider=self.settings.provider,
                provider_reachable=False,
                selected_model=selected_model,
                model_available=False,
                message="Yerel yapay zekâ bağlantısı bilinçli olarak devre dışı.",
            )

        try:
            models = await self.provider.list_models()
        except (ProviderUnavailableError, ProviderTimeoutError) as error:
            return HealthResponse(
                status="unavailable",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=False,
                selected_model=selected_model,
                model_available=False,
                message=str(error),
            )
        except ProviderResponseError:
            return HealthResponse(
                status="degraded",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=True,
                selected_model=selected_model,
                model_available=False,
                message="Yerel sağlayıcının model listesi doğrulanamadı.",
            )
        except Exception:
            return HealthResponse(
                status="unavailable",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=False,
                selected_model=selected_model,
                model_available=False,
                message="Yerel yapay zekâ sağlık kontrolü tamamlanamadı.",
            )

        if selected_model is None:
            return HealthResponse(
                status="degraded",
                llm_enabled=True,
                provider=self.settings.provider,
                provider_reachable=True,
                selected_model=None,
                model_available=False,
                message="Yerel model seçilmedi.",
            )

        model_available = selected_model in {model.name for model in models}
        return HealthResponse(
            status="ok" if model_available else "degraded",
            llm_enabled=True,
            provider=self.settings.provider,
            provider_reachable=True,
            selected_model=selected_model,
            model_available=model_available,
            message=(
                "Yerel yapay zekâ bağlantısı hazır."
                if model_available
                else "Seçilen yerel model yüklü değil."
            ),
        )

    async def list_models(self) -> list[LocalModelInfo]:
        return await self.provider.list_models()

    async def interpret(
        self,
        request: ConversationRequest,
    ) -> ConversationInterpretationResponse:
        # Server-authoritative computation of elicitation context (Hardening Requirement 2)
        has_pending = len(request.pending_proposals) > 0
        computed_elicitation = self.elicitation_planner.plan_context(
            request.brief_snapshot,
            pending_proposals_exist=has_pending,
            user_message=request.message,
        )
        request = request.model_copy(update={"elicitation_context": computed_elicitation})

        if not self.settings.enabled:
            return ConversationInterpretationResponse(
                success=False,
                llm_enabled=False,
                provider=self.settings.provider,
                model=self.settings.model or None,
                context_fingerprint=request.active_context.context_fingerprint,
                generation_id=request.active_context.generation_id,
                result=None,
                error=LLM_DISABLED_MESSAGE,
            )

        # BROWSER REGRESSION: NEUTRAL START WITH EXISTING OPEN QUESTION
        # Replay an already persisted OPEN question deterministically.
        existing_open_topics = computed_elicitation.open_question_topics
        if (
            existing_open_topics
            and request.brief_snapshot is not None
            and is_neutral_elicitation_start(request.message)
        ):
            active_topic = existing_open_topics[0]
            active_question = next(
                (
                    oq
                    for oq in request.brief_snapshot.open_questions
                    if oq.status == OpenQuestionStatus.OPEN and oq.topic_key == active_topic.value
                ),
                None,
            )
            canonical_question = (
                active_question.question
                if active_question is not None
                else question_for_topic(active_topic)
            )
            safe_result = ArchitecturalIntentResult(
                intent=IntentType.GATHER_REQUIREMENT,
                target=EntityTarget(),
                assistant_message=canonical_question,
                user_requirements=[],
                interpreted_priorities=[],
                constraints_to_check=[],
                missing_information=[f"Gerekli bilgi: {active_topic.value}"],
                proposed_actions=[],
                proposed_brief_mutations=[],
                answers_current_open_question=False,
                needs_follow_up=False,
                follow_up_question=None,
                follow_up_topic=None,
                needs_user_confirmation=False,
                confidence=1.0,
                warnings=[],
            )
            return ConversationInterpretationResponse(
                success=True,
                llm_enabled=True,
                provider=self.settings.provider,
                model=self.settings.model,
                context_fingerprint=request.active_context.context_fingerprint,
                generation_id=request.active_context.generation_id,
                result=safe_result,
                error=None,
            )

        # Mode A: Deterministic Neutral Starter Handling
        # "Başlayalım." should not invoke a creative LLM generation to ask the canonical wording.
        has_active_open = len(computed_elicitation.open_question_topics) > 0
        if (
            not has_active_open
            and computed_elicitation.allowed_follow_up_topic is not None
            and is_neutral_elicitation_start(request.message)
        ):
            allowed_topic = computed_elicitation.allowed_follow_up_topic
            canonical_question = question_for_topic(allowed_topic)
            safe_result = ArchitecturalIntentResult(
                intent=IntentType.GATHER_REQUIREMENT,
                target=EntityTarget(),
                assistant_message=canonical_question,
                user_requirements=[],
                interpreted_priorities=[],
                constraints_to_check=[],
                missing_information=[f"Gerekli bilgi: {allowed_topic.value}"],
                proposed_actions=[],
                proposed_brief_mutations=[],
                needs_follow_up=True,
                follow_up_question=canonical_question,
                follow_up_topic=allowed_topic,
                needs_user_confirmation=False,
                confidence=1.0,
                warnings=[],
            )
            return ConversationInterpretationResponse(
                success=True,
                llm_enabled=True,
                provider=self.settings.provider,
                model=self.settings.model,
                context_fingerprint=request.active_context.context_fingerprint,
                generation_id=request.active_context.generation_id,
                result=safe_result,
                error=None,
            )

        result = await self.provider.interpret(
            request,
            _build_provider_output_schema(request),
        )
        try:
            safe_result = self.policy_validator.validate(result, request)
        except ScopeMismatchError:
            safe_result = self.policy_validator.recover_scope_mismatch(result, request)

        # FINAL HOUSEHOLD NORMALIZATION AT SERVICE BOUNDARY
        is_household_open = (
            request.elicitation_context is not None
            and bool(request.elicitation_context.open_question_topics)
            and getattr(
                request.elicitation_context.open_question_topics[0],
                "value",
                request.elicitation_context.open_question_topics[0],
            )
            == "household"
        )
        if is_household_open:
            from brif_ai.conversation.elicitation.household import (
                extract_household_composition,
                format_household_statement,
                has_defensible_household_evidence,
            )

            try:
                llm_household = safe_result.household_composition
                if (
                    llm_household is None
                    or all(
                        count is None
                        for count in (
                            llm_household.total_count,
                            llm_household.adult_count,
                            llm_household.child_count,
                        )
                    )
                    or not has_defensible_household_evidence(request.message)
                ):
                    raise ValueError(
                        "Household extraction is not grounded in the current user message."
                    )
                household_comp = extract_household_composition(
                    request.message,
                    llm_composition=llm_household,
                )
            except ValueError:
                safe_result = safe_result.model_copy(
                    update={
                        "proposed_actions": [],
                        "answers_current_open_question": False,
                        "proposed_brief_mutations": [],
                        "household_composition": None,
                        "needs_follow_up": False,
                        "follow_up_question": None,
                        "follow_up_topic": None,
                        "needs_user_confirmation": False,
                    }
                )
            else:
                household_statement = format_household_statement(household_comp)
                finalized_mutations = [
                    ProposedBriefMutation(
                        mutation_id="mut_household_context",
                        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
                        brief_item=BriefItemProposalPayload(
                            kind=BriefItemKind.CONTEXT,
                            normalized_statement=household_statement,
                            priority=Priority.MUST,
                        ),
                    )
                ]

                safe_result = safe_result.model_copy(
                    update={
                        "intent": IntentType.GATHER_REQUIREMENT,
                        "target": EntityTarget(project_id=request.active_context.project_id),
                        "assistant_message": (
                            f"Anladım. {household_statement} "
                            "Bunu hane bilgisi olarak brief'e eklemeyi öneriyorum."
                        ),
                        "user_requirements": [household_statement],
                        "interpreted_priorities": [],
                        "constraints_to_check": [],
                        "missing_information": [],
                        "proposed_actions": [],
                        "proposed_brief_mutations": finalized_mutations,
                        "household_composition": household_comp,
                        "answers_current_open_question": True,
                        "needs_follow_up": False,
                        "follow_up_question": None,
                        "follow_up_topic": None,
                        "needs_user_confirmation": True,
                        "warnings": [],
                    }
                )

        # Server-authoritative follow-up wording:
        # the LLM may classify/interpret, but it cannot author the V1
        # elicitation question that is shown or persisted.
        if (
            safe_result.needs_follow_up
            and request.elicitation_context is not None
            and request.elicitation_context.allowed_follow_up_topic is not None
            and safe_result.follow_up_topic == request.elicitation_context.allowed_follow_up_topic
        ):
            canonical_question = question_for_topic(safe_result.follow_up_topic)
            safe_result = safe_result.model_copy(
                update={
                    "assistant_message": canonical_question,
                    "follow_up_question": canonical_question,
                }
            )

        return ConversationInterpretationResponse(
            success=True,
            llm_enabled=True,
            provider=self.settings.provider,
            model=self.settings.model,
            context_fingerprint=request.active_context.context_fingerprint,
            generation_id=request.active_context.generation_id,
            result=safe_result,
            error=None,
        )

    @staticmethod
    def ensure_current_context(response_fingerprint: str, current_fingerprint: str) -> None:
        if response_fingerprint != current_fingerprint:
            raise StaleContextError("Eski bağlama ait yerel model cevabı reddedildi.")

    @staticmethod
    def record_user_approval(
        proposed_action: ProposedAction,
        proposal_fingerprint: str,
        current_fingerprint: str,
        *,
        approved_at: datetime | None = None,
    ) -> ProposalApprovalRecord:
        LocalLLMConversationService.ensure_current_context(
            proposal_fingerprint,
            current_fingerprint,
        )
        return ProposalApprovalRecord(
            proposal_status="user_approved",
            approved_at=approved_at or datetime.now(timezone.utc),  # noqa: UP017
            context_fingerprint=current_fingerprint,
            proposed_action=proposed_action,
        )

    @staticmethod
    def record_brief_mutation_approval(
        proposed_mutation: ProposedBriefMutation,
        proposal_fingerprint: str,
        current_fingerprint: str,
        proposal_generation_id: int,
        current_generation_id: int,
        user_message: str,
        snapshot: BriefSnapshot,
        *,
        current_project_id: str | None = None,
        approved_at: datetime | None = None,
        source_reference: str | None = None,
    ) -> tuple[BriefSnapshot, BriefMutationApprovalRecord]:
        LocalLLMConversationService.ensure_current_context(
            proposal_fingerprint,
            current_fingerprint,
        )
        if proposal_generation_id != current_generation_id:
            raise StaleContextError("Eski jenerasyona ait öneri onaylanamaz.")

        if current_project_id is not None and snapshot.project_id != current_project_id:
            raise ValueError(
                f"brief_snapshot project_id '{snapshot.project_id}' "
                f"does not match current_project_id '{current_project_id}'"
            )

        ts = approved_at or datetime.now(timezone.utc)  # noqa: UP017
        new_snapshot = apply_approved_brief_mutation(
            snapshot,
            proposed_mutation,
            user_message,
            source_reference=source_reference or current_fingerprint,
            approved_at=ts,
        )

        record = BriefMutationApprovalRecord(
            proposal_status="user_approved",
            approved_at=ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc),  # noqa: UP017
            context_fingerprint=current_fingerprint,
            generation_id=current_generation_id,
            mutation_id=proposed_mutation.mutation_id,
            proposed_brief_mutation=proposed_mutation,
            resulting_brief_version=new_snapshot.brief_version,
        )
        return new_snapshot, record
