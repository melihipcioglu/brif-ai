"""Private content evaluation validation service for publication preflight.

Note:
- This service does NOT conduct user research or psychometric studies.
- Does NOT verify the methodological quality or scientific validity of evaluations.
- participant_count does NOT imply sample adequacy or statistical power.
- Does NOT classify or semantically analyze summary or identified_issues text.
- Does NOT assume the latest conducted_at record supersedes earlier records.
- Does NOT model evaluation supersession, revocation, or replacement.
- Does NOT generate missing user-evaluation, psychometric claim, or target-context requirements.
- Generates only _IssueDraft instances and never constructs PublicationIssue directly.
- Does NOT call _finalize_issues.
- Uses NO network requests, LLM, AI scoring, statistics, or text parsing.
"""

from brif_ai.scientific.models import ContentEvaluationRecord, EvaluationResult
from brif_ai.scientific.publication._content import _QuestionContentSelection
from brif_ai.scientific.publication._issues import _IssueDraft
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationValidationRequest

_MAX_MESSAGE_LENGTH = 1000
_TRUNCATION_SUFFIX = "...[truncated]"


def _bounded_evaluation_message(
    prefix_header: str,
    summary: str,
    identified_issues: list[str],
    extra_note: str | None = None,
) -> str:
    """Build a deterministic evaluation message guaranteed to fit within 1000 characters."""
    parts = [prefix_header]
    if extra_note:
        parts.append(f" Note: {extra_note}")
    parts.append(f" Summary: {summary}")
    if identified_issues:
        issues_str = "; ".join(identified_issues)
        parts.append(f" Issues: {issues_str}")

    full_message = "".join(parts)
    if len(full_message) <= _MAX_MESSAGE_LENGTH:
        return full_message

    allowed_length = _MAX_MESSAGE_LENGTH - len(_TRUNCATION_SUFFIX)
    return full_message[:allowed_length] + _TRUNCATION_SUFFIX


def _collect_content_evaluations(
    request: PublicationValidationRequest,
    selections: tuple[_QuestionContentSelection, ...],
) -> tuple[_IssueDraft, ...]:
    """Collect issue drafts for existing content evaluation records on selected revisions."""
    evaluations_by_revision: dict[str, list[ContentEvaluationRecord]] = {}
    for evaluation in request.registry.evaluations:
        evaluations_by_revision.setdefault(evaluation.question_content_revision_id, []).append(
            evaluation
        )

    drafts: list[_IssueDraft] = []

    for selection in selections:
        if selection.selected_revision is None:
            continue

        selected_rev_id = selection.selected_revision.id
        matching_evaluations = evaluations_by_revision.get(selected_rev_id, [])

        sorted_evaluations = sorted(matching_evaluations, key=lambda e: e.id)

        for evaluation in sorted_evaluations:
            question_id = selection.question.id
            rev_id = selected_rev_id
            eval_type = evaluation.evaluation_type.value

            if evaluation.result is EvaluationResult.REVISION_REQUIRED:
                header = (
                    f"Content evaluation '{evaluation.id}' ({eval_type}) "
                    f"for question '{question_id}' revision '{rev_id}' [{evaluation.locale}] "
                    f"resulted in REVISION_REQUIRED."
                )
                msg = _bounded_evaluation_message(
                    header, evaluation.summary, evaluation.identified_issues
                )
                drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.EVALUATION_REVISION_REQUIRED,
                        severity=PublicationIssueSeverity.ERROR,
                        object_type=PublicationObjectType.CONTENT_EVALUATION_RECORD,
                        object_id=evaluation.id,
                        question_id=question_id,
                        question_content_revision_id=rev_id,
                        related_object_ids=(),
                        message=msg,
                    )
                )
            elif evaluation.result is EvaluationResult.PASSED_WITH_NOTES:
                header = (
                    f"Content evaluation '{evaluation.id}' ({eval_type}) "
                    f"for question '{question_id}' revision '{rev_id}' [{evaluation.locale}] "
                    f"passed with notes."
                )
                msg = _bounded_evaluation_message(
                    header, evaluation.summary, evaluation.identified_issues
                )
                drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.EVALUATION_PASSED_WITH_NOTES,
                        severity=PublicationIssueSeverity.WARNING,
                        object_type=PublicationObjectType.CONTENT_EVALUATION_RECORD,
                        object_id=evaluation.id,
                        question_id=question_id,
                        question_content_revision_id=rev_id,
                        related_object_ids=(),
                        message=msg,
                    )
                )
            elif evaluation.result is EvaluationResult.INCONCLUSIVE:
                header = (
                    f"Content evaluation '{evaluation.id}' ({eval_type}) "
                    f"for question '{question_id}' revision '{rev_id}' [{evaluation.locale}] "
                    f"is INCONCLUSIVE."
                )
                msg = _bounded_evaluation_message(
                    header, evaluation.summary, evaluation.identified_issues
                )
                drafts.append(
                    _IssueDraft(
                        code=PublicationIssueCode.EVALUATION_INCONCLUSIVE,
                        severity=PublicationIssueSeverity.WARNING,
                        object_type=PublicationObjectType.CONTENT_EVALUATION_RECORD,
                        object_id=evaluation.id,
                        question_id=question_id,
                        question_content_revision_id=rev_id,
                        related_object_ids=(),
                        message=msg,
                    )
                )
            elif evaluation.result is EvaluationResult.PASSED:
                if evaluation.identified_issues:
                    header = (
                        f"Content evaluation '{evaluation.id}' ({eval_type}) "
                        f"for question '{question_id}' revision '{rev_id}' [{evaluation.locale}] "
                        f"is stored as PASSED."
                    )
                    note = (
                        "Registry result is stored as PASSED, but structured identified_issues "
                        "list is not empty. BRIF.AI v0 publication-safety policy surfaces this as "
                        "a non-blocking passed-with-notes warning. This operation does not alter "
                        "the evaluation result."
                    )
                    msg = _bounded_evaluation_message(
                        header, evaluation.summary, evaluation.identified_issues, extra_note=note
                    )
                    drafts.append(
                        _IssueDraft(
                            code=PublicationIssueCode.EVALUATION_PASSED_WITH_NOTES,
                            severity=PublicationIssueSeverity.WARNING,
                            object_type=PublicationObjectType.CONTENT_EVALUATION_RECORD,
                            object_id=evaluation.id,
                            question_id=question_id,
                            question_content_revision_id=rev_id,
                            related_object_ids=(),
                            message=msg,
                        )
                    )

    return tuple(drafts)
