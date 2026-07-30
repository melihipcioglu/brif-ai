"""Source permission validation service for Publication Validation v0.

Scope and Boundaries:
---------------------
- Bu servis hukuki karar üretmez.
- Yalnız BRIF.AI v0 publication-safety policy uygular.
- usage_permission_status değerleri doğrulanmış izin belgeleri değil,
  registry declaration değerleridir.
- OPEN, PERMISSION_GRANTED ve NOT_APPLICABLE kayıtları v0 kapsamında
  issue üretmeden kabul edilir.
- Lisans türü, kullanım kapsamı, izin belgesi, izin veren kurum,
  tarih, süre, locale, dağıtım kanalı, atıf gereksinimi veya
  ticari kullanım hakkı doğrulanmaz.
- ScientificSource.notes alanı otomatik olarak yorumlanmaz ve permission
  status değerini geçersiz kılmaz.
- Kaynak kullanımının bilimsel kalitesini veya yeterliliğini değerlendirmez.
- PublicationIssue veya PublicationValidationReport üretmez.
- Yalnız _IssueDraft üretir.
- _finalize_issues çağırmaz.
- Ağ, web araştırması, LLM, AI confidence veya permission score kullanmaz.
"""

from __future__ import annotations

from brif_ai.scientific.models import (
    AdaptationType,
    ClaimScope,
    EvidenceRelation,
    QuestionEvidenceLink,
    UsagePermissionStatus,
)
from brif_ai.scientific.publication._content import _QuestionContentSelection
from brif_ai.scientific.publication._issues import _IssueDraft
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationValidationRequest

ITEM_SENSITIVE_RELATIONS = {
    EvidenceRelation.QUESTION_WORDING_BASIS,
    EvidenceRelation.RESPONSE_FORMAT_BASIS,
}

ITEM_SENSITIVE_CLAIMS = {
    ClaimScope.QUESTION_DERIVED,
    ClaimScope.ITEM_ADAPTED,
    ClaimScope.VALIDATED_ITEM,
}

ITEM_SENSITIVE_ADAPTATIONS = {
    AdaptationType.DIRECT_TRANSLATION,
    AdaptationType.FORWARD_BACK_TRANSLATION,
    AdaptationType.CULTURAL_ADAPTATION,
    AdaptationType.CONCEPTUAL_DERIVATION,
}

CONCEPT_SENSITIVE_RELATIONS = {
    EvidenceRelation.CONSTRUCT_BASIS,
    EvidenceRelation.ARCHITECTURAL_MAPPING_BASIS,
}

CONCEPT_SENSITIVE_CLAIMS = {
    ClaimScope.CONCEPT_SUPPORTED,
    ClaimScope.PROFESSIONAL_REQUIREMENT,
}


def _is_link_item_sensitive(link: QuestionEvidenceLink) -> bool:
    return (
        link.evidence_relation in ITEM_SENSITIVE_RELATIONS
        or link.claim_scope in ITEM_SENSITIVE_CLAIMS
        or link.adaptation_type in ITEM_SENSITIVE_ADAPTATIONS
    )


def _is_link_concept_sensitive(link: QuestionEvidenceLink) -> bool:
    return (
        link.evidence_relation in CONCEPT_SENSITIVE_RELATIONS
        or link.claim_scope in CONCEPT_SENSITIVE_CLAIMS
    )


def _collect_source_permissions(
    request: PublicationValidationRequest,
    selections: tuple[_QuestionContentSelection, ...],
) -> tuple[_IssueDraft, ...]:
    """Collects source usage permission issue drafts for question selections."""
    registry = request.registry
    sources_by_id = {source.id: source for source in registry.sources}
    evidence_links = registry.evidence_links

    evidence_by_revision_id: dict[str, list[QuestionEvidenceLink]] = {}
    for link in evidence_links:
        evidence_by_revision_id.setdefault(link.question_content_revision_id, []).append(link)

    issue_drafts: list[_IssueDraft] = []

    for selection in selections:
        selected_revision = selection.selected_revision
        if selected_revision is None:
            continue

        question_id = selection.question.id
        selected_rev_id = selected_revision.id

        direct_links = evidence_by_revision_id.get(selected_rev_id, [])
        if not direct_links:
            continue

        links_by_source_id: dict[str, list[QuestionEvidenceLink]] = {}
        for link in direct_links:
            for s_id in link.source_ids:
                links_by_source_id.setdefault(s_id, []).append(link)

        for source_id in sorted(links_by_source_id.keys()):
            source = sources_by_id[source_id]

            status = source.usage_permission_status
            if status in (
                UsagePermissionStatus.OPEN,
                UsagePermissionStatus.PERMISSION_GRANTED,
                UsagePermissionStatus.NOT_APPLICABLE,
            ):
                continue

            source_links = links_by_source_id[source_id]
            sorted_link_ids = tuple(sorted(set(link.id for link in source_links)))

            if status is UsagePermissionStatus.PERMISSION_REQUIRED:
                issue_drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.SOURCE_PERMISSION_REQUIRED,
                        severity=PublicationIssueSeverity.ERROR,
                        object_type=PublicationObjectType.SCIENTIFIC_SOURCE,
                        object_id=source.id,
                        question_id=question_id,
                        question_content_revision_id=selected_rev_id,
                        message=(
                            f"Source {source.id!r} ({source.title!r}) referenced "
                            f"by direct evidence links {sorted_link_ids!r} for question "
                            f"{question_id!r} selected revision {selected_rev_id!r} "
                            f"has permission status {status.value!r} "
                            f"(BRIF.AI publication-safety policy rule, "
                            f"not a legal determination)"
                        ),
                        related_object_ids=sorted_link_ids,
                    )
                )
            elif status is UsagePermissionStatus.UNKNOWN:
                has_item = any(_is_link_item_sensitive(link) for link in source_links)
                has_concept = any(_is_link_concept_sensitive(link) for link in source_links)
                has_ambiguous = any(
                    not _is_link_item_sensitive(link) and not _is_link_concept_sensitive(link)
                    for link in source_links
                )

                if has_item or has_ambiguous or not has_concept:
                    issue_drafts.append(
                        _IssueDraft(
                            code=PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_ITEM_USE,
                            severity=PublicationIssueSeverity.ERROR,
                            object_type=PublicationObjectType.SCIENTIFIC_SOURCE,
                            object_id=source.id,
                            question_id=question_id,
                            question_content_revision_id=selected_rev_id,
                            message=(
                                f"Source {source.id!r} ({source.title!r}) referenced "
                                f"by direct evidence links {sorted_link_ids!r} for question "
                                f"{question_id!r} selected revision {selected_rev_id!r} "
                                f"has UNKNOWN permission status for item-sensitive usage "
                                f"(BRIF.AI publication-safety policy boundary)"
                            ),
                            related_object_ids=sorted_link_ids,
                        )
                    )
                else:
                    issue_drafts.append(
                        _IssueDraft(
                            code=PublicationIssueCode.SOURCE_PERMISSION_UNKNOWN_FOR_CONCEPT_USE,
                            severity=PublicationIssueSeverity.WARNING,
                            object_type=PublicationObjectType.SCIENTIFIC_SOURCE,
                            object_id=source.id,
                            question_id=question_id,
                            question_content_revision_id=selected_rev_id,
                            message=(
                                f"Source {source.id!r} ({source.title!r}) referenced "
                                f"by direct evidence links {sorted_link_ids!r} for question "
                                f"{question_id!r} selected revision {selected_rev_id!r} "
                                f"has UNKNOWN permission status for concept-sensitive usage "
                                f"(non-blocking BRIF.AI policy warning)"
                            ),
                            related_object_ids=sorted_link_ids,
                        )
                    )

    return tuple(issue_drafts)
