"""Target locale content selection service for Publication Validation v0.

Scope and Boundaries:
---------------------
- Bu aşama yalnız hedef locale için APPROVED içerik revizyonu seçer.
- Bilimsel geçerlik iddiası üretmez.
- Evidence yeterliliğini kontrol etmez.
- Kaynak kullanım iznini kontrol etmez.
- Uzman review veya evaluation kontrol etmez.
- Dilsel kalitenin iyi olduğunu varsaymaz.
- Başka locale’e fallback yapmaz.
- PublicationIssue veya PublicationValidationReport üretmez.
- source_metadata, AI confidence ve evidence score kullanmaz.
"""

from __future__ import annotations

from dataclasses import dataclass

from brif_ai.conversation.models import QuestionDefinition
from brif_ai.scientific.models import ContentRevisionStatus, QuestionContentRevision
from brif_ai.scientific.publication._issues import _IssueDraft
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationValidationRequest


@dataclass(frozen=True, slots=True)
class _QuestionContentSelection:
    """Selection record linking an approved question to its target locale content revision."""

    question: QuestionDefinition
    selected_revision: QuestionContentRevision | None


def _collect_target_locale_content(
    request: PublicationValidationRequest,
    approved_questions: tuple[QuestionDefinition, ...],
) -> tuple[
    tuple[_QuestionContentSelection, ...],
    tuple[_IssueDraft, ...],
]:
    """Selects APPROVED content revisions for approved questions in target locale
    and collects issue drafts.
    """
    target_locale = request.target_locale
    revisions = request.registry.question_content_revisions

    selections: list[_QuestionContentSelection] = []
    issue_drafts: list[_IssueDraft] = []

    for question in approved_questions:
        approved_revision: QuestionContentRevision | None = None
        target_locale_revision_ids: list[str] = []

        for rev in revisions:
            if rev.question_id == question.id and rev.locale == target_locale:
                target_locale_revision_ids.append(rev.id)
                if rev.status is ContentRevisionStatus.APPROVED:
                    approved_revision = rev

        if approved_revision is None:
            sorted_related_ids = tuple(sorted(target_locale_revision_ids))
            selections.append(
                _QuestionContentSelection(
                    question=question,
                    selected_revision=None,
                )
            )
            issue_drafts.append(
                _IssueDraft(
                    code=PublicationIssueCode.APPROVED_CONTENT_REVISION_MISSING,
                    severity=PublicationIssueSeverity.ERROR,
                    object_type=PublicationObjectType.QUESTION_DEFINITION,
                    object_id=question.id,
                    question_id=question.id,
                    question_content_revision_id=None,
                    message=(
                        f"Approved content revision missing for question {question.id!r} "
                        f"in target locale {target_locale!r}"
                    ),
                    related_object_ids=sorted_related_ids,
                )
            )
        else:
            selections.append(
                _QuestionContentSelection(
                    question=question,
                    selected_revision=approved_revision,
                )
            )
            if approved_revision.content_key != question.content_key:
                issue_drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.CONTENT_KEY_MISMATCH,
                        severity=PublicationIssueSeverity.ERROR,
                        object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
                        object_id=approved_revision.id,
                        question_id=question.id,
                        question_content_revision_id=approved_revision.id,
                        message=(
                            f"Question {question.id!r} content_key {question.content_key!r} "
                            f"does not match revision {approved_revision.id!r} "
                            f"content_key {approved_revision.content_key!r}"
                        ),
                        related_object_ids=(question.id,),
                    )
                )

    return tuple(selections), tuple(issue_drafts)
