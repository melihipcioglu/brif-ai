"""Shared enums and constrained text types for scientific content v0.

LanguageCode and LocaleCode use simple regex checks for v0. They are not full
BCP-47 validators.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Annotated

from pydantic import StringConstraints

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:  # pragma: no cover - Python 3.10 local tooling compatibility

    class StrEnum(str, Enum):  # noqa: UP042
        pass


LanguageCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=3, pattern=r"^[a-z]{2,3}$"),
]
LocaleCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=6,
        pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$",
    ),
]


class SourceType(StrEnum):
    PEER_REVIEWED_ARTICLE = "PEER_REVIEWED_ARTICLE"
    SYSTEMATIC_REVIEW = "SYSTEMATIC_REVIEW"
    BOOK = "BOOK"
    BOOK_CHAPTER = "BOOK_CHAPTER"
    VALIDATED_INSTRUMENT = "VALIDATED_INSTRUMENT"
    STANDARD = "STANDARD"
    PROFESSIONAL_GUIDE = "PROFESSIONAL_GUIDE"
    THESIS = "THESIS"
    EXPERT_CONSENSUS_DOCUMENT = "EXPERT_CONSENSUS_DOCUMENT"
    OTHER = "OTHER"


class IdentifierType(StrEnum):
    DOI = "DOI"
    ISBN = "ISBN"
    URL = "URL"
    STANDARD_NUMBER = "STANDARD_NUMBER"
    OTHER = "OTHER"
    NONE = "NONE"


class UsagePermissionStatus(StrEnum):
    OPEN = "OPEN"
    PERMISSION_GRANTED = "PERMISSION_GRANTED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class ContentRevisionStatus(StrEnum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class EvidenceRelation(StrEnum):
    CONSTRUCT_BASIS = "CONSTRUCT_BASIS"
    QUESTION_WORDING_BASIS = "QUESTION_WORDING_BASIS"
    RESPONSE_FORMAT_BASIS = "RESPONSE_FORMAT_BASIS"
    ARCHITECTURAL_MAPPING_BASIS = "ARCHITECTURAL_MAPPING_BASIS"
    RISK_OR_SCREENING_BASIS = "RISK_OR_SCREENING_BASIS"


class ClaimScope(StrEnum):
    CONCEPT_SUPPORTED = "CONCEPT_SUPPORTED"
    QUESTION_DERIVED = "QUESTION_DERIVED"
    ITEM_ADAPTED = "ITEM_ADAPTED"
    VALIDATED_ITEM = "VALIDATED_ITEM"
    PROFESSIONAL_REQUIREMENT = "PROFESSIONAL_REQUIREMENT"
    EXPERT_AUTHORED = "EXPERT_AUTHORED"


class AdaptationType(StrEnum):
    ORIGINAL = "ORIGINAL"
    DIRECT_TRANSLATION = "DIRECT_TRANSLATION"
    FORWARD_BACK_TRANSLATION = "FORWARD_BACK_TRANSLATION"
    CULTURAL_ADAPTATION = "CULTURAL_ADAPTATION"
    CONCEPTUAL_DERIVATION = "CONCEPTUAL_DERIVATION"
    EXPERT_AUTHORED = "EXPERT_AUTHORED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ReviewArea(StrEnum):
    ARCHITECTURAL_PROGRAMMING = "ARCHITECTURAL_PROGRAMMING"
    ENVIRONMENTAL_PSYCHOLOGY = "ENVIRONMENTAL_PSYCHOLOGY"
    ACCESSIBILITY = "ACCESSIBILITY"
    RESEARCH_METHODS = "RESEARCH_METHODS"
    LANGUAGE_AND_COMPREHENSION = "LANGUAGE_AND_COMPREHENSION"
    ETHICS_AND_PRIVACY = "ETHICS_AND_PRIVACY"
    DOMAIN_SPECIFIC = "DOMAIN_SPECIFIC"


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REJECTED = "REJECTED"


class EvaluationType(StrEnum):
    COGNITIVE_INTERVIEW = "COGNITIVE_INTERVIEW"
    PILOT_INTERVIEW = "PILOT_INTERVIEW"
    READABILITY_REVIEW = "READABILITY_REVIEW"
    EXPERT_PANEL = "EXPERT_PANEL"
    USABILITY_TEST = "USABILITY_TEST"
    PSYCHOMETRIC_STUDY = "PSYCHOMETRIC_STUDY"


class EvaluationResult(StrEnum):
    PASSED = "PASSED"
    PASSED_WITH_NOTES = "PASSED_WITH_NOTES"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    INCONCLUSIVE = "INCONCLUSIVE"
