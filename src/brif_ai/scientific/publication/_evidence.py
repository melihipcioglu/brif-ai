"""Question evidence link validation service for Publication Validation v0.

Scope and Boundaries:
---------------------
- Bu aşama yalnız seçilmiş içerik revizyonunda evidence link bulunup bulunmadığını kontrol eder.
- Bilimsel geçerliliğin kalitesini veya yeterliliğini kanıtlamaz.
- Kaynak kullanım iznini kontrol etmez.
- Uzman review, language review, user evaluation veya psikometrik destek kontrol etmez.
- Registry model invariantlarını tekrar etmez.
- PublicationIssue veya PublicationValidationReport üretmez.
- Yalnız _IssueDraft üretir.
- AI confidence, evidence score veya source_metadata kullanmaz.
"""

from __future__ import annotations

from brif_ai.scientific.publication._content import _QuestionContentSelection
from brif_ai.scientific.publication._issues import _IssueDraft
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationValidationRequest


def _collect_question_evidence(
    request: PublicationValidationRequest,
    selections: tuple[_QuestionContentSelection, ...],
) -> tuple[_IssueDraft, ...]:
    """Collects evidence link issue drafts for question content selections."""
    registry = request.registry
    target_locale = request.target_locale
    evidence_links = registry.evidence_links
    revisions = registry.question_content_revisions

    evidence_by_revision_id: dict[str, list[str]] = {}
    for link in evidence_links:
        evidence_by_revision_id.setdefault(link.question_content_revision_id, []).append(link.id)

    revisions_by_question_locale: dict[tuple[str, str], list[str]] = {}
    for rev in revisions:
        revisions_by_question_locale.setdefault((rev.question_id, rev.locale), []).append(rev.id)

    issue_drafts: list[_IssueDraft] = []

    for selection in selections:
        selected_revision = selection.selected_revision
        if selected_revision is None:
            continue

        question_id = selection.question.id
        selected_rev_id = selected_revision.id

        direct_evidence_link_ids = evidence_by_revision_id.get(selected_rev_id, [])
        if direct_evidence_link_ids:
            continue

        other_rev_ids = [
            r_id
            for r_id in revisions_by_question_locale.get((question_id, target_locale), [])
            if r_id != selected_rev_id
        ]

        evidence_bearing_other_rev_ids: list[str] = []
        other_evidence_link_ids: list[str] = []
        for r_id in other_rev_ids:
            link_ids = evidence_by_revision_id.get(r_id, [])
            if link_ids:
                evidence_bearing_other_rev_ids.append(r_id)
                other_evidence_link_ids.extend(link_ids)

        if other_evidence_link_ids:
            sorted_other_rev_ids = tuple(sorted(set(evidence_bearing_other_rev_ids)))
            sorted_other_link_ids = tuple(sorted(set(other_evidence_link_ids)))
            issue_drafts.append(
                _IssueDraft(
                    code=PublicationIssueCode.EVIDENCE_FOR_DIFFERENT_REVISION,
                    severity=PublicationIssueSeverity.ERROR,
                    object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
                    object_id=selected_rev_id,
                    question_id=question_id,
                    question_content_revision_id=selected_rev_id,
                    message=(
                        f"Question {question_id!r} selected content revision {selected_rev_id!r} "
                        f"has no direct evidence link in target locale {target_locale!r}, "
                        f"but evidence links {sorted_other_link_ids!r} exist for other revision(s) "
                        f"{sorted_other_rev_ids!r}"
                    ),
                    related_object_ids=sorted_other_link_ids,
                )
            )
        else:
            issue_drafts.append(
                _IssueDraft(
                    code=PublicationIssueCode.EVIDENCE_LINK_MISSING,
                    severity=PublicationIssueSeverity.ERROR,
                    object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
                    object_id=selected_rev_id,
                    question_id=question_id,
                    question_content_revision_id=selected_rev_id,
                    message=(
                        f"Evidence link missing for question {question_id!r} "
                        f"selected content revision {selected_rev_id!r} "
                        f"in target locale {target_locale!r}"
                    ),
                    related_object_ids=(question_id,),
                )
            )

    return tuple(issue_drafts)
