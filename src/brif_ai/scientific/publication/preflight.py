"""Publication validation preflight service for BRIF.AI v0.

Preflight checks:
- Verifies catalog and registry binding (catalog id and version).
- Selects approved questions from the catalog, sorted deterministically.
- Verifies that all registry question content revisions refer to known catalog questions.
- Verifies that all registry construct output target IDs refer to known catalog information targets.

Scope and Boundaries:
---------------------
- Preflight yalnız katalog ve registry bağını ve temel dış referansları doğrular.
- Bir sorunun bilimsel olarak valide olduğunu söylemez.
- Soru içeriği seçmez.
- Evidence yeterliliğini kontrol etmez.
- Kaynak kullanım iznini kontrol etmez.
- Uzman review veya pilot değerlendirmesini kontrol etmez.
- PublicationValidationReport üretmez.
- AI confidence veya evidence score kullanmaz.
- source_metadata alanını okumaz.
"""

from __future__ import annotations

from dataclasses import dataclass

from brif_ai.conversation.models import QuestionDefinition, QuestionStatus
from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import (
    PublicationIssue,
    PublicationValidationRequest,
)

_SEVERITY_ORDER: dict[PublicationIssueSeverity, int] = {
    PublicationIssueSeverity.CRITICAL: 0,
    PublicationIssueSeverity.ERROR: 1,
    PublicationIssueSeverity.WARNING: 2,
    PublicationIssueSeverity.INFO: 3,
}


@dataclass(frozen=True, slots=True)
class PublicationPreflightResult:
    """Internal preflight validation phase result for Publication Validation v0."""

    approved_questions: tuple[QuestionDefinition, ...]
    issues: tuple[PublicationIssue, ...]

    @property
    def can_continue(self) -> bool:
        return len(self.approved_questions) > 0 and not any(issue.blocking for issue in self.issues)


@dataclass(frozen=True, slots=True)
class _IssueDraft:
    code: PublicationIssueCode
    severity: PublicationIssueSeverity
    object_type: PublicationObjectType
    object_id: str
    question_id: str | None = None
    question_content_revision_id: str | None = None
    message: str = ""
    related_object_ids: tuple[str, ...] = ()


def _issue_draft_sort_key(
    draft: _IssueDraft,
) -> tuple[int, tuple[int, str], tuple[int, str], str, str]:
    return (
        _SEVERITY_ORDER[draft.severity],
        (0, "") if draft.question_id is None else (1, draft.question_id),
        (0, "")
        if draft.question_content_revision_id is None
        else (1, draft.question_content_revision_id),
        draft.code.value,
        draft.object_id,
    )


def _finalize_issues(drafts: list[_IssueDraft]) -> tuple[PublicationIssue, ...]:
    seen_keys: set[tuple[object, ...]] = set()
    deduped_drafts: list[_IssueDraft] = []
    for draft in drafts:
        key = (
            draft.code,
            draft.object_id,
            draft.question_id,
            draft.question_content_revision_id,
            draft.related_object_ids,
        )
        if key not in seen_keys:
            seen_keys.add(key)
            deduped_drafts.append(draft)

    sorted_drafts = sorted(deduped_drafts, key=_issue_draft_sort_key)

    issues: list[PublicationIssue] = []
    for index, draft in enumerate(sorted_drafts, start=1):
        issue_id = f"publication_issue_{index:04d}"
        issues.append(
            PublicationIssue(
                id=issue_id,
                code=draft.code,
                severity=draft.severity,
                object_type=draft.object_type,
                object_id=draft.object_id,
                question_id=draft.question_id,
                question_content_revision_id=draft.question_content_revision_id,
                message=draft.message,
                related_object_ids=list(draft.related_object_ids),
            )
        )
    return tuple(issues)


def run_publication_preflight(
    request: PublicationValidationRequest,
) -> PublicationPreflightResult:
    """Executes preflight checks on a publication validation request.

    Preflight yalnız katalog ve registry bağını ve temel dış referansları doğrular.
    - Bir sorunun bilimsel olarak valide olduğunu söylemez.
    - Soru içeriği seçmez.
    - Evidence yeterliliğini kontrol etmez.
    - Kaynak kullanım iznini kontrol etmez.
    - Uzman review veya pilot değerlendirmesini kontrol etmez.
    - PublicationValidationReport üretmez.
    - AI confidence veya evidence score kullanmaz.
    - source_metadata alanını okumaz.
    """
    catalog = request.catalog
    registry = request.registry

    binding_issues: list[_IssueDraft] = []
    if registry.question_catalog_id != catalog.id:
        binding_issues.append(
            _IssueDraft(
                code=PublicationIssueCode.REGISTRY_CATALOG_ID_MISMATCH,
                severity=PublicationIssueSeverity.CRITICAL,
                object_type=PublicationObjectType.SCIENTIFIC_CONTENT_REGISTRY,
                object_id=registry.id,
                question_id=None,
                question_content_revision_id=None,
                message=(
                    f"Registry question_catalog_id {registry.question_catalog_id!r} "
                    f"does not match catalog id {catalog.id!r}"
                ),
                related_object_ids=(catalog.id, registry.question_catalog_id),
            )
        )

    if registry.question_catalog_version != catalog.catalog_version:
        binding_issues.append(
            _IssueDraft(
                code=PublicationIssueCode.REGISTRY_CATALOG_VERSION_MISMATCH,
                severity=PublicationIssueSeverity.CRITICAL,
                object_type=PublicationObjectType.SCIENTIFIC_CONTENT_REGISTRY,
                object_id=registry.id,
                question_id=None,
                question_content_revision_id=None,
                message=(
                    f"Registry question_catalog_version {registry.question_catalog_version!r} "
                    f"does not match catalog catalog_version {catalog.catalog_version!r}"
                ),
                related_object_ids=(),
            )
        )

    if binding_issues:
        return PublicationPreflightResult(
            approved_questions=(),
            issues=_finalize_issues(binding_issues),
        )

    issue_drafts: list[_IssueDraft] = []

    # 1. Approved Question Selection
    approved_questions_list = [q for q in catalog.questions if q.status is QuestionStatus.APPROVED]
    approved_questions_list.sort(key=lambda q: (q.display_order, q.id))

    if not approved_questions_list:
        issue_drafts.append(
            _IssueDraft(
                code=PublicationIssueCode.NO_APPROVED_QUESTIONS,
                severity=PublicationIssueSeverity.ERROR,
                object_type=PublicationObjectType.QUESTION_CATALOG,
                object_id=catalog.id,
                question_id=None,
                question_content_revision_id=None,
                message=f"Question catalog {catalog.id!r} contains no APPROVED questions",
                related_object_ids=(),
            )
        )

    # 2. Registry Question Reference Check
    catalog_question_ids = {q.id for q in catalog.questions}
    for revision in registry.question_content_revisions:
        if revision.question_id not in catalog_question_ids:
            issue_drafts.append(
                _IssueDraft(
                    code=PublicationIssueCode.REGISTRY_QUESTION_NOT_FOUND_IN_CATALOG,
                    severity=PublicationIssueSeverity.CRITICAL,
                    object_type=PublicationObjectType.QUESTION_CONTENT_REVISION,
                    object_id=revision.id,
                    question_id=revision.question_id,
                    question_content_revision_id=revision.id,
                    message=(
                        f"Question content revision {revision.id!r} references question_id "
                        f"{revision.question_id!r} which is not found in catalog {catalog.id!r}"
                    ),
                    related_object_ids=(catalog.id,),
                )
            )

    # 3. Construct Output Target Check
    catalog_target_ids = {t.id for t in catalog.information_targets}
    for construct in registry.constructs:
        unknown_targets = [
            t_id for t_id in construct.expected_output_target_ids if t_id not in catalog_target_ids
        ]
        if unknown_targets:
            sorted_unknown_targets = tuple(sorted(set(unknown_targets)))
            unknown_str = ", ".join(sorted_unknown_targets)
            issue_drafts.append(
                _IssueDraft(
                    code=PublicationIssueCode.CONSTRUCT_OUTPUT_TARGET_NOT_FOUND,
                    severity=PublicationIssueSeverity.ERROR,
                    object_type=PublicationObjectType.CONSTRUCT_DEFINITION,
                    object_id=construct.id,
                    question_id=None,
                    question_content_revision_id=None,
                    message=(
                        f"Construct {construct.id!r} references unknown output target IDs: "
                        f"{unknown_str}"
                    ),
                    related_object_ids=sorted_unknown_targets,
                )
            )

    final_issues = _finalize_issues(issue_drafts)
    return PublicationPreflightResult(
        approved_questions=tuple(approved_questions_list),
        issues=final_issues,
    )
