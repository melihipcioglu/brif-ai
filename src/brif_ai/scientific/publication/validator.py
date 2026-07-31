"""Full publication validation composition service for Publication Validation v0.

Note:
- Composes structural publication policy collectors in a deterministic sequence.
- Does NOT claim scientific validity on its own.
- Does NOT introduce new issue policies.
- Uses NO network, file I/O, database, LLM, AI scores, random numbers, UUIDs, or system time.
- Does NOT mutate request, catalog, or registry models.
- Uses checked_at and validator_version exactly as provided in request.
- Finalizes all issue drafts globally exactly once using _finalize_issues.
- Does NOT use broad try/except to mask programming errors as validation issues.
"""

from brif_ai.scientific.publication._content import _collect_target_locale_content
from brif_ai.scientific.publication._evaluations import _collect_content_evaluations
from brif_ai.scientific.publication._evidence import _collect_question_evidence
from brif_ai.scientific.publication._issues import _finalize_issues, _IssueDraft
from brif_ai.scientific.publication._permissions import _collect_source_permissions
from brif_ai.scientific.publication._reviews import _collect_expert_reviews
from brif_ai.scientific.publication.models import (
    PublicationValidationReport,
    PublicationValidationRequest,
    QuestionPublicationResult,
)
from brif_ai.scientific.publication.preflight import _collect_publication_preflight


def validate_publication(
    request: PublicationValidationRequest,
) -> PublicationValidationReport:
    """Validate a publication request through all preflight and downstream policy stages."""
    approved_questions, preflight_drafts = _collect_publication_preflight(request)

    can_continue = bool(approved_questions) and not any(
        draft.severity.is_blocking for draft in preflight_drafts
    )

    all_drafts: list[_IssueDraft] = []
    question_results: list[QuestionPublicationResult] = []

    if not can_continue:
        all_drafts.extend(preflight_drafts)
    else:
        selections, content_drafts = _collect_target_locale_content(request, approved_questions)
        evidence_drafts = _collect_question_evidence(request, selections)
        permission_drafts = _collect_source_permissions(request, selections)
        review_drafts = _collect_expert_reviews(request, selections)
        evaluation_drafts = _collect_content_evaluations(request, selections)

        all_drafts.extend(preflight_drafts)
        all_drafts.extend(content_drafts)
        all_drafts.extend(evidence_drafts)
        all_drafts.extend(permission_drafts)
        all_drafts.extend(review_drafts)
        all_drafts.extend(evaluation_drafts)

        final_issues_temp = _finalize_issues(all_drafts)

        selections_by_question_id = {selection.question.id: selection for selection in selections}

        for question in approved_questions:
            selection = selections_by_question_id.get(question.id)
            selected_revision_id = (
                selection.selected_revision.id
                if selection and selection.selected_revision
                else None
            )

            q_issues = [issue for issue in final_issues_temp if issue.question_id == question.id]
            issue_ids = [issue.id for issue in q_issues]
            blocking_issue_ids = [issue.id for issue in q_issues if issue.severity.is_blocking]

            question_results.append(
                QuestionPublicationResult(
                    question_id=question.id,
                    target_locale=request.target_locale,
                    selected_content_revision_id=selected_revision_id,
                    issue_ids=issue_ids,
                    blocking_issue_ids=blocking_issue_ids,
                )
            )

        final_issues = final_issues_temp
        return PublicationValidationReport(
            catalog_id=request.catalog.id,
            catalog_version=request.catalog.catalog_version,
            registry_id=request.registry.id,
            registry_version=request.registry.registry_version,
            target_locale=request.target_locale,
            checked_at=request.checked_at,
            validator_version=request.validator_version,
            question_results=question_results,
            issues=list(final_issues),
        )

    final_issues = _finalize_issues(all_drafts)
    return PublicationValidationReport(
        catalog_id=request.catalog.id,
        catalog_version=request.catalog.catalog_version,
        registry_id=request.registry.id,
        registry_version=request.registry.registry_version,
        target_locale=request.target_locale,
        checked_at=request.checked_at,
        validator_version=request.validator_version,
        question_results=[],
        issues=list(final_issues),
    )
