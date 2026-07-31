"""Expert and language review validation service for Publication Validation v0.

Scope and Boundaries:
---------------------
- Bu servis gerçek uzmanlık veya bilimsel yeterlilik değerlendirmesi yapmaz.
- Reviewer kimliğini, uzmanlığını, imzasını veya yetkisini doğrulamaz.
- reviewer_reference ve reviewer_role yalnız registry metadata değerleridir.
- İnceleme metinlerini otomatik sınıflandırmaz.
- reviewed_at değerine bakarak "en yeni review geçerlidir" varsayımı yapmaz.
- Review supersession, revocation veya replacement mekanizması uygulamaz.
- evidence_link_ids boş listesinin revision-level review kabul edilmesi
  repository invariantı değil, BRIF.AI v0 yorumlama politikasıdır.
- CULTURAL_ADAPTATION review gereksinimi minimum v0 kapsamında uygulanmaz.
- PublicationIssue veya PublicationValidationReport üretmez.
- Yalnız _IssueDraft üretir.
- _finalize_issues çağırmaz.
- Ağ, veritabanı, UUID, random, hash, LLM veya AI score kullanmaz.
"""

from __future__ import annotations

from brif_ai.scientific.models import (
    AdaptationType,
    ExpertReviewRecord,
    QuestionEvidenceLink,
    ReviewArea,
    ReviewDecision,
)
from brif_ai.scientific.publication._content import _QuestionContentSelection
from brif_ai.scientific.publication._issues import _IssueDraft
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationValidationRequest

TRANSLATION_SENSITIVE_ADAPTATIONS = {
    AdaptationType.DIRECT_TRANSLATION,
    AdaptationType.FORWARD_BACK_TRANSLATION,
}


def _collect_expert_reviews(
    request: PublicationValidationRequest,
    selections: tuple[_QuestionContentSelection, ...],
) -> tuple[_IssueDraft, ...]:
    """Collects expert and language review issue drafts for question selections."""
    registry = request.registry
    reviews = registry.expert_reviews
    evidence_links = registry.evidence_links

    reviews_by_revision_id: dict[str, list[ExpertReviewRecord]] = {}
    for review in reviews:
        reviews_by_revision_id.setdefault(review.question_content_revision_id, []).append(review)

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

        current_reviews = reviews_by_revision_id.get(selected_rev_id, [])
        sorted_reviews = sorted(current_reviews, key=lambda r: r.id)

        # 1. Evaluate negative review decisions (REJECTED / CHANGES_REQUESTED)
        for review in sorted_reviews:
            sorted_link_ids = tuple(sorted(set(review.evidence_link_ids)))

            if review.decision is ReviewDecision.REJECTED:
                issue_drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.REVIEW_REJECTED,
                        severity=PublicationIssueSeverity.ERROR,
                        object_type=PublicationObjectType.EXPERT_REVIEW_RECORD,
                        object_id=review.id,
                        question_id=question_id,
                        question_content_revision_id=selected_rev_id,
                        message=(
                            f"Expert review {review.id!r} (area {review.review_area.value!r}, "
                            f"reviewer {review.reviewer_reference!r} [{review.reviewer_role!r}]) "
                            f"REJECTED selected revision {selected_rev_id!r} "
                            f"for question {question_id!r}: {review.rationale!r}"
                        ),
                        related_object_ids=sorted_link_ids,
                    )
                )
            elif review.decision is ReviewDecision.CHANGES_REQUESTED:
                issue_drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.REVIEW_CHANGES_REQUESTED,
                        severity=PublicationIssueSeverity.ERROR,
                        object_type=PublicationObjectType.EXPERT_REVIEW_RECORD,
                        object_id=review.id,
                        question_id=question_id,
                        question_content_revision_id=selected_rev_id,
                        message=(
                            f"Expert review {review.id!r} (area {review.review_area.value!r}, "
                            f"reviewer {review.reviewer_reference!r} [{review.reviewer_role!r}]) "
                            f"requested changes for selected revision {selected_rev_id!r} "
                            f"for question {question_id!r}: {review.required_changes!r}"
                        ),
                        related_object_ids=sorted_link_ids,
                    )
                )

        # 2. Evaluate language review coverage for translation-sensitive evidence
        direct_links = evidence_by_revision_id.get(selected_rev_id, [])
        translation_links = [
            link
            for link in direct_links
            if link.adaptation_type in TRANSLATION_SENSITIVE_ADAPTATIONS
        ]

        if translation_links:
            all_translation_ids = {link.id for link in translation_links}
            approved_language_reviews = [
                r
                for r in sorted_reviews
                if r.review_area is ReviewArea.LANGUAGE_AND_COMPREHENSION
                and r.decision is ReviewDecision.APPROVED
            ]

            covered_translation_ids: set[str] = set()
            for rev in approved_language_reviews:
                if not rev.evidence_link_ids:
                    covered_translation_ids.update(all_translation_ids)
                else:
                    covered_translation_ids.update(
                        link_id
                        for link_id in rev.evidence_link_ids
                        if link_id in all_translation_ids
                    )

            uncovered_ids = all_translation_ids - covered_translation_ids
            if uncovered_ids:
                sorted_uncovered = tuple(sorted(uncovered_ids))
                issue_drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.TRANSLATED_ITEM_WITHOUT_LANGUAGE_REVIEW,
                        severity=PublicationIssueSeverity.ERROR,
                        object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
                        object_id=selected_rev_id,
                        question_id=question_id,
                        question_content_revision_id=selected_rev_id,
                        message=(
                            f"Question {question_id!r} selected revision {selected_rev_id!r} "
                            f"(locale {selected_revision.locale!r}) has uncovered translation "
                            f"evidence links {sorted_uncovered!r} missing approved "
                            f"{ReviewArea.LANGUAGE_AND_COMPREHENSION.value!r} review"
                        ),
                        related_object_ids=sorted_uncovered,
                    )
                )

    return tuple(issue_drafts)
