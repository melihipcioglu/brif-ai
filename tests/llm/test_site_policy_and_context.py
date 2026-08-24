"""Tests for LLM contracts and PolicyValidator regarding site geometry proposals."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from brif_ai.brief.models.snapshot import BriefSnapshot, Stakeholder
from brif_ai.conversation.elicitation.models import ElicitationContext, ElicitationTopic
from brif_ai.llm.contracts import (
    ActionType,
    ActiveContextSnapshot,
    ArchitecturalIntentResult,
    ConversationRequest,
    EntityTarget,
    IntentType,
    PendingProposalContext,
    ProposedAction,
    ProposedSiteGeometry,
)
from brif_ai.llm.policy_validator import (
    ArchitecturalIntentPolicyValidator,
    PolicyValidationError,
)
from brif_ai.spatial.site.models import SiteGeometryRole, SitePoint


def _create_sample_request(
    message: str = "Parsel sınırı: (0;0), (20;0), (20;30), (0;30)",
    elicitation_context: ElicitationContext | None = None,
) -> ConversationRequest:
    return ConversationRequest(
        message=message,
        active_context=ActiveContextSnapshot(
            project_id="proj_1",
            context_fingerprint="fp_01",
            generation_id=1,
        ),
        visible_entities=[],
        current_decisions=[],
        pending_proposals=[],
        brief_snapshot=BriefSnapshot(
            project_id="proj_1",
            schema_version="brief.v0",
            brief_version=1,
            created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
            stakeholders=[
                Stakeholder(id="stk_1", display_name="Owner", role="CLIENT_OWNER", active=True)
            ],
            brief_items=[],
            space_requests=[],
            usage_scenarios=[],
            evidence=[],
            contradictions=[],
            open_questions=[],
        ),
        elicitation_context=elicitation_context,
    )


class TestSiteGeometryContractInvariants:
    """Test safety invariants on ProposedSiteGeometry and ArchitecturalIntentResult."""

    def test_site_geometry_requires_user_confirmation(self) -> None:
        prop = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
            ],
        )
        with pytest.raises(ValidationError, match="require user confirmation"):
            ArchitecturalIntentResult(
                assistant_message="Parsel sınırı önerildi.",
                intent=IntentType.GATHER_REQUIREMENT,
                target=EntityTarget(project_id="proj_1"),
                user_requirements=[],
                interpreted_priorities=[],
                constraints_to_check=[],
                missing_information=[],
                proposed_actions=[],
                proposed_site_geometries=[prop],
                needs_follow_up=False,
                needs_user_confirmation=False,  # Invalid
                confidence=1.0,
                warnings=[],
            )

    def test_site_geometry_forbids_needs_follow_up(self) -> None:
        prop = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
            ],
        )
        with pytest.raises(ValidationError, match="needs_follow_up must be false"):
            ArchitecturalIntentResult(
                assistant_message="Parsel sınırı önerildi.",
                intent=IntentType.GATHER_REQUIREMENT,
                target=EntityTarget(project_id="proj_1"),
                user_requirements=[],
                interpreted_priorities=[],
                constraints_to_check=[],
                missing_information=[],
                proposed_actions=[],
                proposed_site_geometries=[prop],
                needs_follow_up=True,  # Invalid
                follow_up_question="Emin misiniz?",
                follow_up_topic=ElicitationTopic.HOUSEHOLD,
                needs_user_confirmation=True,
                confidence=1.0,
                warnings=[],
            )

    def test_site_geometry_cannot_mix_with_proposed_actions(self) -> None:
        prop = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
            ],
        )
        action = ProposedAction(
            action_type=ActionType.SUGGEST_SPACE_RESIZE,
            description="Eylem",
            requires_user_confirmation=True,
        )
        with pytest.raises(ValidationError, match="cannot mix proposed site geometries"):
            ArchitecturalIntentResult(
                assistant_message="Öneri.",
                intent=IntentType.GATHER_REQUIREMENT,
                target=EntityTarget(project_id="proj_1"),
                user_requirements=[],
                interpreted_priorities=[],
                constraints_to_check=[],
                missing_information=[],
                proposed_actions=[action],
                proposed_site_geometries=[prop],
                needs_follow_up=False,
                needs_user_confirmation=True,
                confidence=1.0,
                warnings=[],
            )

    def test_max_one_site_geometry_proposal(self) -> None:
        prop1 = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
            ],
        )
        prop2 = ProposedSiteGeometry(
            proposal_id="p2",
            role=SiteGeometryRole.BUILDABLE_ENVELOPE,
            vertices=[
                SitePoint(x_m=2.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=2.0),
                SitePoint(x_m=18.0, y_m=28.0),
            ],
        )
        with pytest.raises(ValidationError, match="maximum one site geometry proposal allowed"):
            ArchitecturalIntentResult(
                assistant_message="İki öneri.",
                intent=IntentType.GATHER_REQUIREMENT,
                target=EntityTarget(project_id="proj_1"),
                user_requirements=[],
                interpreted_priorities=[],
                constraints_to_check=[],
                missing_information=[],
                proposed_actions=[],
                proposed_site_geometries=[prop1, prop2],
                needs_follow_up=False,
                needs_user_confirmation=True,
                confidence=1.0,
                warnings=[],
            )

    def test_pending_proposal_context_xor(self) -> None:
        prop = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
            ],
        )
        ctx = PendingProposalContext(
            context_fingerprint="fp1",
            generation_id=1,
            site_geometry=prop,
        )
        assert ctx.site_geometry is not None

        # Two proposals at once fails XOR
        with pytest.raises(ValidationError, match="Exactly one"):
            PendingProposalContext(
                context_fingerprint="fp1",
                generation_id=1,
                site_geometry=prop,
                action=ProposedAction(
                    action_type=ActionType.SUGGEST_SPACE_RESIZE,
                    description="Eylem",
                    requires_user_confirmation=True,
                ),
            )


class TestPolicyValidatorSiteProposals:
    """Test PolicyValidator handling of site geometry proposals."""

    def test_valid_site_proposal_passes(self) -> None:
        validator = ArchitecturalIntentPolicyValidator()
        req = _create_sample_request("Parsel sınırı: (0;0), (20;0), (20;30), (0;30)")
        prop = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=0.0),
                SitePoint(x_m=20.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
            rationale="Parsel sınırı tanımı",
        )
        raw_result = ArchitecturalIntentResult(
            assistant_message="Parsel sınırınızı eklemek ister misiniz?",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id="proj_1"),
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_site_geometries=[prop],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=1.0,
            warnings=[],
        )
        validated = validator.validate(raw_result, req)
        assert len(validated.proposed_site_geometries) == 1
        assert validated.needs_user_confirmation is True

    def test_site_proposal_source_mismatch_fails_policy(self) -> None:
        validator = ArchitecturalIntentPolicyValidator()
        # Message has 4 points
        req = _create_sample_request("Parsel sınırı: (0;0), (20;0), (20;30), (0;30)")
        # Proposal has different coordinates
        prop = ProposedSiteGeometry(
            proposal_id="p1",
            role=SiteGeometryRole.PARCEL_BOUNDARY,
            vertices=[
                SitePoint(x_m=0.0, y_m=0.0),
                SitePoint(x_m=25.0, y_m=0.0),
                SitePoint(x_m=25.0, y_m=30.0),
                SitePoint(x_m=0.0, y_m=30.0),
            ],
        )
        raw_result = ArchitecturalIntentResult(
            assistant_message="Parsel önerisi.",
            intent=IntentType.GATHER_REQUIREMENT,
            target=EntityTarget(project_id="proj_1"),
            user_requirements=[],
            interpreted_priorities=[],
            constraints_to_check=[],
            missing_information=[],
            proposed_actions=[],
            proposed_site_geometries=[prop],
            needs_follow_up=False,
            needs_user_confirmation=True,
            confidence=1.0,
            warnings=[],
        )
        with pytest.raises(
            PolicyValidationError, match="Site geometri kaynak doğrulaması başarısız"
        ):
            validator.validate(raw_result, req)
