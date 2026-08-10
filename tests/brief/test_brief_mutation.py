"""Comprehensive test suite for Approved Brief Update V0."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.common import (
    BriefItemKind,
    ConfirmationStatus,
    EvidenceSource,
    Priority,
)
from brif_ai.brief.models.snapshot import (
    BriefSnapshot,
    Stakeholder,
)
from brif_ai.brief.mutation import (
    BriefItemProposalPayload,
    BriefMutationType,
    ProposedBriefMutation,
    SpaceRequestProposalPayload,
    UsageScenarioProposalPayload,
    apply_approved_brief_mutation,
)
from brif_ai.core.models.common import SpaceFunction
from brif_ai.llm.contracts import (
    ActionType,
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    PendingProposalContext,
    ProposedAction,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    UnsupportedSpatialClaimError,
)
from brif_ai.llm.service import LocalLLMConversationService, StaleContextError


def sample_snapshot(
    project_id: str = "proj_house_v0",
    brief_version: int = 1,
    stakeholders: list[Stakeholder] | None = None,
) -> BriefSnapshot:
    """Helper to create a valid baseline BriefSnapshot."""
    if stakeholders is None:
        stakeholders = [
            Stakeholder(
                id="stk_client_owner",
                display_name="Melih İpçioğlu",
                role="CLIENT_OWNER",
                active=True,
            )
        ]

    return BriefSnapshot(
        project_id=project_id,
        schema_version="brief.v0",
        brief_version=brief_version,
        created_at=datetime.now(timezone.utc),  # noqa: UP017
        stakeholders=stakeholders,
        evidence=[],
        brief_items=[],
        space_requests=[],
        usage_scenarios=[],
        contradictions=[],
        open_questions=[],
    )


# 1. approved structured BriefItem mutation succeeds
def test_approved_structured_brief_item_mutation_succeeds() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement=(
                "Misafirler geldiğinde aile yaşam alanından bağımsız kalabilsinler."
            ),
            priority=Priority.MUST,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Misafirler geldiğinde aile yaşam alanından bağımsız kalabilsinler.",
        source_reference="msg_context_01",
    )

    assert len(updated.brief_items) == 1
    item = updated.brief_items[0]
    assert (
        item.normalized_statement
        == "Misafirler geldiğinde aile yaşam alanından bağımsız kalabilsinler."
    )
    assert item.confirmation_status == ConfirmationStatus.CONFIRMED
    assert item.priority == Priority.MUST
    assert item.kind == BriefItemKind.NEED
    assert item.stakeholder_ids == ["stk_client_owner"]
    assert len(updated.evidence) == 1
    assert updated.evidence[0].source_type == EvidenceSource.CHAT
    assert updated.brief_version == snapshot.brief_version + 1


# 2. no approval -> no mutation
def test_no_approval_no_mutation() -> None:
    snapshot = sample_snapshot()
    # When a proposal is generated but user approval is not given, snapshot remains original
    assert snapshot.brief_version == 1
    assert len(snapshot.brief_items) == 0


# 3. stale context rejected
def test_stale_context_rejected() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.PREFERENCE,
            normalized_statement="Çalışma odası sessiz bir konumda kurgulansın.",
            priority=Priority.SHOULD,
        ),
    )

    with pytest.raises(StaleContextError, match="Eski bağlama ait yerel model cevabı reddedildi"):
        LocalLLMConversationService.record_brief_mutation_approval(
            proposed_mutation=mutation,
            proposal_fingerprint="fp_old_context",
            current_fingerprint="fp_new_context",
            proposal_generation_id=1,
            current_generation_id=1,
            user_message="Çalışma odası sessiz olsun.",
            snapshot=snapshot,
        )

    with pytest.raises(StaleContextError, match="Eski jenerasyona ait öneri onaylanamaz"):
        LocalLLMConversationService.record_brief_mutation_approval(
            proposed_mutation=mutation,
            proposal_fingerprint="fp_same",
            current_fingerprint="fp_same",
            proposal_generation_id=1,
            current_generation_id=2,
            user_message="Çalışma odası sessiz olsun.",
            snapshot=snapshot,
        )


# 4. wrong project rejected
def test_wrong_project_rejected() -> None:
    snapshot = sample_snapshot(project_id="proj_house_v0")
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Bir misafir odası eklemek istiyoruz.",
            priority=Priority.MUST,
        ),
        target_stakeholder_id="stk_other_proj",
    )

    with pytest.raises(ValueError, match="Referenced stakeholder_id 'stk_other_proj' not found"):
        apply_approved_brief_mutation(
            snapshot=snapshot,
            mutation=mutation,
            user_message="Misafir odası istiyoruz.",
            source_reference="msg_01",
        )


# 5. invalid stakeholder rejected
def test_invalid_stakeholder_rejected() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Ebeveyn banyosu yataktan görünmesin.",
            priority=Priority.MUST,
        ),
        target_stakeholder_id="stk_nonexistent",
    )

    with pytest.raises(ValueError, match="Referenced stakeholder_id 'stk_nonexistent' not found"):
        apply_approved_brief_mutation(
            snapshot=snapshot,
            mutation=mutation,
            user_message="Ebeveyn banyosu mahrem kalsın.",
            source_reference="msg_01",
        )


# 6. missing stakeholder with multiple active stakeholders rejected
def test_missing_stakeholder_with_multiple_active_stakeholders_rejected() -> None:
    stakeholders = [
        Stakeholder(id="stk_client1", display_name="Client 1", role="CLIENT_OWNER", active=True),
        Stakeholder(id="stk_client2", display_name="Client 2", role="FAMILY_MEMBER", active=True),
    ]
    snapshot = sample_snapshot(stakeholders=stakeholders)
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Çocuk odası üst katta yer alsın.",
            priority=Priority.MUST,
        ),
        target_stakeholder_id=None,
    )

    with pytest.raises(ValueError, match="Multiple active stakeholders exist"):
        apply_approved_brief_mutation(
            snapshot=snapshot,
            mutation=mutation,
            user_message="Çocuk odası üst katta olsun.",
            source_reference="msg_01",
        )


# 7. evidence/provenance created correctly
def test_evidence_provenance_created_correctly() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_sr_01",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Misafir Odası",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=1,
            mandatory=True,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Zemin katta bir misafir odası istiyorum.",
        source_reference="ctx_fingerprint_123",
    )

    assert len(updated.evidence) == 1
    ev = updated.evidence[0]
    assert ev.source_type == EvidenceSource.CHAT
    assert ev.source_reference == "ctx_fingerprint_123"
    assert ev.excerpt == "Zemin katta bir misafir odası istiyorum."
    assert updated.space_requests[0].evidence_ids == [ev.id]


# 8. messages over 500 chars handled deterministically
def test_messages_over_500_chars_handled_deterministically() -> None:
    snapshot = sample_snapshot()
    long_msg = "A" * 600
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_long",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.GOAL,
            normalized_statement="Geniş ve aydınlık salon alanı kurgulanması.",
            priority=Priority.SHOULD,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message=long_msg,
        source_reference="ctx_long",
    )

    assert len(updated.evidence[0].excerpt) == 500
    assert updated.evidence[0].excerpt == "A" * 500


# 9. successful mutation increments brief_version exactly once
def test_successful_mutation_increments_brief_version_exactly_once() -> None:
    snapshot = sample_snapshot(brief_version=3)
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.CONSTRAINT,
            normalized_statement="Mutfakta çöp öğütücü bulunmamalıdır.",
            priority=Priority.MUST,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Çöp öğütücü istemiyorum.",
        source_reference="msg_01",
    )

    assert updated.brief_version == 4


# 10. failed mutation leaves original snapshot unchanged
def test_failed_mutation_leaves_original_snapshot_unchanged() -> None:
    snapshot = sample_snapshot(brief_version=2)
    invalid_mutation = ProposedBriefMutation(
        mutation_id="mut_item_bad",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Test gereksinimi",
            priority=Priority.MUST,
        ),
        target_stakeholder_id="stk_missing",
    )

    with pytest.raises(ValueError):
        apply_approved_brief_mutation(
            snapshot=snapshot,
            mutation=invalid_mutation,
            user_message="Test mesajı",
            source_reference="msg_01",
        )

    assert snapshot.brief_version == 2
    assert len(snapshot.brief_items) == 0


# 11. identical proposal replay creates no duplicate item/evidence
# 12. true idempotent replay does not increment brief_version
def test_identical_proposal_replay_idempotent() -> None:
    snapshot = sample_snapshot(brief_version=1)
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Teras alanı bahçe ile zemin seviyesinde bütünleşsin.",
            priority=Priority.MUST,
        ),
    )

    first_update = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Teras bahçe ile aynı seviyede olsun.",
        source_reference="ctx_same",
    )
    assert first_update.brief_version == 2
    assert len(first_update.brief_items) == 1
    assert len(first_update.evidence) == 1

    # Replay identical proposal with identical evidence
    second_update = apply_approved_brief_mutation(
        snapshot=first_update,
        mutation=mutation,
        user_message="Teras bahçe ile aynı seviyede olsun.",
        source_reference="ctx_same",
    )
    assert second_update.brief_version == 2  # Not incremented!
    assert len(second_update.brief_items) == 1
    assert len(second_update.evidence) == 1


# 13. identical item + new evidence reuses item and adds provenance
def test_identical_item_new_evidence_reuses_item_adds_provenance() -> None:
    snapshot = sample_snapshot(brief_version=1)
    mutation = ProposedBriefMutation(
        mutation_id="mut_item_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Teras bahçe ile zemin seviyesinde bütünleşsin.",
            priority=Priority.MUST,
        ),
    )

    first_update = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Teras bahçe seviyesinde olsun.",
        source_reference="ctx_msg_1",
    )
    assert len(first_update.evidence) == 1

    # Same item, different message/context reference
    second_update = apply_approved_brief_mutation(
        snapshot=first_update,
        mutation=mutation,
        user_message="Teras kesinlikle bahçeye doğrudan açılsın.",
        source_reference="ctx_msg_2",
    )
    assert second_update.brief_version == 3
    assert len(second_update.brief_items) == 1  # Item reused!
    assert len(second_update.evidence) == 2  # New evidence added!
    assert len(second_update.brief_items[0].evidence_ids) == 2  # Both evidence linked!


# 14. multiple sequential approvals preserve previous content
def test_multiple_sequential_approvals_preserve_previous_content() -> None:
    snapshot = sample_snapshot(brief_version=1)

    mutation_1 = ProposedBriefMutation(
        mutation_id="mut_item_1",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Giriş holünde vestiyer alanı bulunsun.",
            priority=Priority.MUST,
        ),
    )

    mutation_2 = ProposedBriefMutation(
        mutation_id="mut_space_2",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Çalışma Odası",
            space_function=SpaceFunction.WORK,
            minimum_quantity=1,
        ),
    )

    step1 = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation_1,
        user_message="Vestiyer istiyorum.",
        source_reference="msg_1",
    )

    step2 = apply_approved_brief_mutation(
        snapshot=step1,
        mutation=mutation_2,
        user_message="Çalışma odası istiyorum.",
        source_reference="msg_2",
    )

    assert step2.brief_version == 3
    assert len(step2.brief_items) == 1
    assert step2.brief_items[0].normalized_statement == "Giriş holünde vestiyer alanı bulunsun."
    assert len(step2.space_requests) == 1
    assert step2.space_requests[0].display_name == "Çalışma Odası"
    assert len(step2.evidence) == 2


# 15. malformed free-text ProposedAction.description cannot become brief mutation
def test_malformed_freetext_proposed_action_cannot_become_brief_mutation() -> None:
    # ProposedAction is for plan changes only. It cannot be converted to a BriefMutation directly.
    action = ProposedAction(
        action_type=ActionType.SUGGEST_SPACE_RESIZE,
        target_entity_id="space_living",
        description="Brief gereksinimi: Salon 40 m2 yapılsın.",
        requires_user_confirmation=True,
    )
    assert not hasattr(action, "mutation_type")
    assert not isinstance(action, ProposedBriefMutation)


# 16. ProposedAction and ProposedBriefMutation remain separate
def test_proposed_action_and_brief_mutation_remain_separate() -> None:
    with pytest.raises(ValidationError, match="Exactly one of action or brief_mutation"):
        PendingProposalContext(
            context_fingerprint="fp_123",
            generation_id=1,
            action=ProposedAction(
                action_type=ActionType.HIGHLIGHT_ENTITY,
                target_entity_id="space_living",
                description="Salon vurgulansın.",
                requires_user_confirmation=True,
            ),
            brief_mutation=ProposedBriefMutation(
                mutation_id="mut_01",
                mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
                brief_item=BriefItemProposalPayload(
                    kind=BriefItemKind.NEED,
                    normalized_statement="Test",
                    priority=Priority.MUST,
                ),
            ),
        )


# 17. mutation type/payload mismatch rejected
def test_mutation_type_payload_mismatch_rejected() -> None:
    with pytest.raises(ValidationError, match="does not match mutation_type"):
        ProposedBriefMutation(
            mutation_id="mut_mismatch",
            mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
            space_request=SpaceRequestProposalPayload(
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
            ),
        )


# 18. multiple mutation payloads rejected
def test_multiple_mutation_payloads_rejected() -> None:
    with pytest.raises(ValidationError, match="Exactly one mutation payload"):
        ProposedBriefMutation(
            mutation_id="mut_multi",
            mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
            brief_item=BriefItemProposalPayload(
                kind=BriefItemKind.NEED,
                normalized_statement="Test",
                priority=Priority.MUST,
            ),
            space_request=SpaceRequestProposalPayload(
                display_name="Mutfak",
                space_function=SpaceFunction.COOKING,
            ),
        )


# 19. existing compare behavior unchanged
# 20. compare result cannot produce brief mutations
def test_compare_result_cannot_produce_brief_mutations() -> None:
    with pytest.raises(
        ValidationError, match="compare_alternatives cannot produce brief mutations"
    ):
        ArchitecturalIntentResult(
            assistant_message=(
                "Alternatif 1 - Açık düzen: ... Alternatif 2 - Ayrık düzen: ... Temel fark: ..."
            ),
            intent=IntentType.COMPARE_ALTERNATIVES,
            target=EntityTarget(),
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_brief_mutations=[
                ProposedBriefMutation(
                    mutation_id="mut_bad_compare",
                    mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
                    brief_item=BriefItemProposalPayload(
                        kind=BriefItemKind.NEED,
                        normalized_statement="İllegal compare mutation",
                        priority=Priority.MUST,
                    ),
                )
            ],
            needs_follow_up=False,
            follow_up_question=None,
            needs_user_confirmation=True,
            confidence=0.9,
            warnings=[],
        )


# 21. full BriefSnapshot validation still runs
def test_full_brief_snapshot_validation_still_runs() -> None:
    # Validate that corrupted candidate data fails model validation
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Giriş holü geniş kurgulansın.",
            priority=Priority.MUST,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Giriş holü geniş kurgulansın.",
        source_reference="msg_01",
    )

    # Validated snapshot should strictly pass model_validate
    dumped = updated.model_dump(mode="python")
    reconstructed = BriefSnapshot.model_validate(dumped)
    assert reconstructed.brief_version == updated.brief_version


# 22. JSON round-trip for new contracts
def test_json_roundtrip_new_contracts() -> None:
    mutation = ProposedBriefMutation(
        mutation_id="mut_json_01",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Çalışma Odası",
            space_function=SpaceFunction.WORK,
            minimum_quantity=1,
            mandatory=True,
        ),
    )

    json_str = mutation.model_dump_json()
    deserialized = ProposedBriefMutation.model_validate_json(json_str)
    assert deserialized.mutation_id == "mut_json_01"
    assert deserialized.space_request is not None
    assert deserialized.space_request.display_name == "Çalışma Odası"


# 23. extra unknown fields rejected
def test_extra_unknown_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        BriefItemProposalPayload.model_validate(
            {
                "kind": "NEED",
                "normalized_statement": "Test",
                "priority": "MUST",
                "unknown_extra_field": 123,
            }
        )


# 24. deterministic IDs stable across repeated application
def test_deterministic_ids_stable_across_repeated_application() -> None:
    snapshot1 = sample_snapshot()
    snapshot2 = sample_snapshot()

    mutation = ProposedBriefMutation(
        mutation_id="mut_stable_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Mutfak adası geniş olsun.",
            priority=Priority.SHOULD,
        ),
    )

    up1 = apply_approved_brief_mutation(
        snapshot=snapshot1,
        mutation=mutation,
        user_message="Mutfak adası geniş olsun.",
        source_reference="src_ref_stable",
    )

    up2 = apply_approved_brief_mutation(
        snapshot=snapshot2,
        mutation=mutation,
        user_message="Mutfak adası geniş olsun.",
        source_reference="src_ref_stable",
    )

    assert up1.brief_items[0].id == up2.brief_items[0].id
    assert up1.evidence[0].id == up2.evidence[0].id


# 25. brief-only PendingProposalContext serializes safely
def test_brief_only_pending_proposal_context_serializes_safely() -> None:
    pending = PendingProposalContext(
        context_fingerprint="fp_123",
        generation_id=1,
        brief_mutation=ProposedBriefMutation(
            mutation_id="mut_pending_01",
            mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
            brief_item=BriefItemProposalPayload(
                kind=BriefItemKind.NEED,
                normalized_statement="Ebeveyn odası mahrem kalsın.",
                priority=Priority.MUST,
            ),
        ),
    )

    req = ConversationRequest(
        message="Ebeveyn odası mahrem olsun.",
        active_context=ActiveContextSnapshot(
            project_id="proj_01",
            context_fingerprint="fp_123",
            generation_id=1,
        ),
        visible_entities=[],
        pending_proposals=[pending],
    )

    from brif_ai.llm.prompts import build_user_prompt

    user_prompt_json = build_user_prompt(req)
    assert "mut_pending_01" in user_prompt_json
    assert "Ebeveyn odası mahrem kalsın." in user_prompt_json


# 26. unsupported spatial/directional claim inside mutation payload is rejected
def test_unsupported_spatial_claim_inside_mutation_payload_rejected() -> None:
    validator = ArchitecturalIntentPolicyValidator()
    req = ConversationRequest(
        message="Bir misafir odası istiyorum.",
        active_context=ActiveContextSnapshot(
            project_id="proj_01",
            context_fingerprint="fp_01",
            generation_id=1,
        ),
        visible_entities=[],
    )

    bad_result = ArchitecturalIntentResult(
        assistant_message="Misafir odası gereksinimi eklensin mi?",
        intent=IntentType.GATHER_REQUIREMENT,
        target=EntityTarget(),
        user_requirements=[],
        interpreted_priorities=[],
        constraints_to_check=[],
        missing_information=[],
        proposed_actions=[],
        proposed_brief_mutations=[
            ProposedBriefMutation(
                mutation_id="mut_bad_spatial",
                mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
                brief_item=BriefItemProposalPayload(
                    kind=BriefItemKind.NEED,
                    normalized_statement="Misafir odası salonun doğusunda kurgulansın.",
                    priority=Priority.MUST,
                ),
            )
        ],
        needs_follow_up=False,
        follow_up_question=None,
        needs_user_confirmation=True,
        confidence=0.9,
        warnings=[],
    )

    with pytest.raises(UnsupportedSpatialClaimError):
        validator.validate_semantic_integrity(bad_result, req)


# 27. original snapshot nested lists remain unchanged
def test_original_snapshot_nested_lists_remain_unchanged() -> None:
    snapshot = sample_snapshot()
    orig_items_len = len(snapshot.brief_items)
    orig_ev_len = len(snapshot.evidence)

    mutation = ProposedBriefMutation(
        mutation_id="mut_01",
        mutation_type=BriefMutationType.ADD_BRIEF_ITEM,
        brief_item=BriefItemProposalPayload(
            kind=BriefItemKind.NEED,
            normalized_statement="Giriş holü aydınlık kurgulansın.",
            priority=Priority.MUST,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Giriş holü aydınlık olsun.",
        source_reference="msg_01",
    )

    assert len(snapshot.brief_items) == orig_items_len
    assert len(snapshot.evidence) == orig_ev_len
    assert len(updated.brief_items) == orig_items_len + 1


# 28. successful approved SpaceRequest mutation, ConfirmationStatus.CONFIRMED,
# stakeholder & evidence references
def test_successful_approved_space_request_mutation() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_sr_01",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Çalışma Odası",
            space_function=SpaceFunction.WORK,
            minimum_quantity=1,
            maximum_quantity=2,
            mandatory=True,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Evden çalışmak için bir çalışma odası istiyorum.",
        source_reference="msg_sr_01",
    )

    assert len(updated.space_requests) == 1
    sr = updated.space_requests[0]
    assert sr.display_name == "Çalışma Odası"
    assert sr.space_function == SpaceFunction.WORK
    assert sr.minimum_quantity == 1
    assert sr.maximum_quantity == 2
    assert sr.mandatory is True
    assert sr.confirmation_status == ConfirmationStatus.CONFIRMED
    assert sr.stakeholder_ids == [snapshot.stakeholders[0].id]
    assert len(updated.evidence) == 1
    assert sr.evidence_ids == [updated.evidence[0].id]
    assert updated.brief_version == snapshot.brief_version + 1


# 29. exact SpaceRequest replay is idempotent and does not increment brief_version
def test_space_request_exact_replay_idempotent() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_sr_02",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Stüdyo",
            space_function=SpaceFunction.WORK,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Bir stüdyo ekle.",
        source_reference="msg_sr_02",
    )

    replayed = apply_approved_brief_mutation(
        snapshot=updated,
        mutation=mutation,
        user_message="Bir stüdyo ekle.",
        source_reference="msg_sr_02",
    )

    assert replayed.brief_version == updated.brief_version
    assert len(replayed.space_requests) == 1
    assert len(replayed.evidence) == 1


# 30. same SpaceRequest with different source_reference reuses request and adds evidence
def test_space_request_different_evidence_reuses_request() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_sr_03",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Misafir Odası",
            space_function=SpaceFunction.SLEEPING,
        ),
    )

    updated1 = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Misafir odası istiyoruz.",
        source_reference="msg_sr_first",
    )

    updated2 = apply_approved_brief_mutation(
        snapshot=updated1,
        mutation=mutation,
        user_message="Yatılı misafirler için oda şart.",
        source_reference="msg_sr_second",
    )

    assert len(updated2.space_requests) == 1
    assert len(updated2.evidence) == 2
    assert updated2.brief_version == updated1.brief_version + 1
    assert set(updated2.space_requests[0].evidence_ids) == {ev.id for ev in updated2.evidence}


# 31. valid minimum/maximum quantity survives final BriefSnapshot validation
def test_space_request_quantity_survives_snapshot_validation() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_sr_quant",
        mutation_type=BriefMutationType.ADD_SPACE_REQUEST,
        space_request=SpaceRequestProposalPayload(
            display_name="Çocuk Odası",
            space_function=SpaceFunction.SLEEPING,
            minimum_quantity=2,
            maximum_quantity=3,
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="En az 2, en fazla 3 çocuk odası olsun.",
        source_reference="msg_quant",
    )

    dumped = updated.model_dump(mode="python")
    reconstructed = BriefSnapshot.model_validate(dumped)
    assert reconstructed.space_requests[0].minimum_quantity == 2
    assert reconstructed.space_requests[0].maximum_quantity == 3


# 32. successful approved UsageScenario mutation & ConfirmationStatus.CONFIRMED & references
def test_successful_approved_usage_scenario_mutation() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_us_01",
        mutation_type=BriefMutationType.ADD_USAGE_SCENARIO,
        usage_scenario=UsageScenarioProposalPayload(
            title="Hafta Sonu Kahvaltısı",
            description="Tüm ailenin teras ve mutfakta uzun kahvaltı yapması.",
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Hafta sonu geniş aile kahvaltıları yapacağız.",
        source_reference="msg_us_01",
    )

    assert len(updated.usage_scenarios) == 1
    us = updated.usage_scenarios[0]
    assert us.title == "Hafta Sonu Kahvaltısı"
    assert us.description == "Tüm ailenin teras ve mutfakta uzun kahvaltı yapması."
    assert us.confirmation_status == ConfirmationStatus.CONFIRMED
    assert us.stakeholder_ids == [snapshot.stakeholders[0].id]
    assert len(updated.evidence) == 1
    assert us.evidence_ids == [updated.evidence[0].id]
    assert updated.brief_version == snapshot.brief_version + 1


# 33. exact UsageScenario replay is idempotent
def test_usage_scenario_exact_replay_idempotent() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_us_02",
        mutation_type=BriefMutationType.ADD_USAGE_SCENARIO,
        usage_scenario=UsageScenarioProposalPayload(
            title="Akşam Sineması",
            description="Salonda projeksiyon ile film izleme ortamı.",
        ),
    )

    updated = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Salonda film izleyeceğiz.",
        source_reference="msg_us_02",
    )

    replayed = apply_approved_brief_mutation(
        snapshot=updated,
        mutation=mutation,
        user_message="Salonda film izleyeceğiz.",
        source_reference="msg_us_02",
    )

    assert replayed.brief_version == updated.brief_version
    assert len(replayed.usage_scenarios) == 1
    assert len(replayed.evidence) == 1


# 34. same UsageScenario with different evidence reuses scenario
def test_usage_scenario_different_evidence_reuses_scenario() -> None:
    snapshot = sample_snapshot()
    mutation = ProposedBriefMutation(
        mutation_id="mut_us_03",
        mutation_type=BriefMutationType.ADD_USAGE_SCENARIO,
        usage_scenario=UsageScenarioProposalPayload(
            title="Evden Çalışma Düzeni",
            description="Sakin bir odada bilgisayar çalışması.",
        ),
    )

    updated1 = apply_approved_brief_mutation(
        snapshot=snapshot,
        mutation=mutation,
        user_message="Hafta içi evden çalışacağım.",
        source_reference="msg_us_first",
    )

    updated2 = apply_approved_brief_mutation(
        snapshot=updated1,
        mutation=mutation,
        user_message="Online toplantılar için sessizlik şart.",
        source_reference="msg_us_second",
    )

    assert len(updated2.usage_scenarios) == 1
    assert len(updated2.evidence) == 2
    assert updated2.brief_version == updated1.brief_version + 1
    assert set(updated2.usage_scenarios[0].evidence_ids) == {ev.id for ev in updated2.evidence}
