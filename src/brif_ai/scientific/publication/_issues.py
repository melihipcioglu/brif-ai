"""Private publication issue draft and deterministic finalization helpers for BRIF.AI v0.

Global Issue Identification Boundary:
-------------------------------------
- Validation stages should produce `_IssueDraft` records whenever possible.
- The complete `validate_publication` service must aggregate drafts from all stages,
  deduplicate and sort them globally, and call `_finalize_issues` exactly once.
- Independently numbered `PublicationIssue` lists from separate stages must not
  be concatenated directly.
- This module is internal private infrastructure; it is not a public API or user contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from brif_ai.scientific.publication.common import (
    PublicationIssueCode,
    PublicationIssueSeverity,
    PublicationObjectType,
)
from brif_ai.scientific.publication.models import PublicationIssue

_SEVERITY_ORDER: dict[PublicationIssueSeverity, int] = {
    PublicationIssueSeverity.CRITICAL: 0,
    PublicationIssueSeverity.ERROR: 1,
    PublicationIssueSeverity.WARNING: 2,
    PublicationIssueSeverity.INFO: 3,
}


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


def _finalize_issues(
    drafts: list[_IssueDraft] | tuple[_IssueDraft, ...],
) -> tuple[PublicationIssue, ...]:
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
