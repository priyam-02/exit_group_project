"""
Confidence Scorer.

Assigns a 0-1 confidence score to each company based on how well
it matches the M&A thesis criteria. This helps the dashboard
surface the best targets at the top.

Scoring factors:
  - Service match (are they in our target services?)
  - Data completeness (how many fields do we have?)
  - Size indicators (revenue/employee thresholds)
  - Source reliability (multiple sources = higher confidence)
  - Exclusion checks (penalty for flagged items)
"""

import logging
from models import Company
from config import THESIS

logger = logging.getLogger(__name__)

# Weight allocation (must sum to 1.0)
WEIGHTS = {
    "service_match": 0.35,     # Most important — do they offer target services?
    "data_completeness": 0.20, # How much do we know about them?
    "size_fit": 0.15,          # Do they meet size thresholds?
    "source_quality": 0.15,    # How many sources confirm this company?
    "no_exclusions": 0.15,     # Are there any red flags?
}


def score_company(company: Company) -> float:
    """
    Compute a confidence score from 0 to 1.
    Higher = better match to the thesis.
    """
    scores = {
        "service_match": _score_service_match(company),
        "data_completeness": _score_completeness(company),
        "size_fit": _score_size(company),
        "source_quality": _score_sources(company),
        "no_exclusions": _score_exclusions(company),
    }

    total = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)

    logger.debug(
        f"Score for '{company.name}': {total:.2f} "
        f"(service={scores['service_match']:.2f}, "
        f"complete={scores['data_completeness']:.2f}, "
        f"size={scores['size_fit']:.2f}, "
        f"source={scores['source_quality']:.2f}, "
        f"excl={scores['no_exclusions']:.2f})"
    )

    return round(total, 3)


def score_all(companies: list[Company]) -> list[Company]:
    """Score all companies and attach the confidence_score field."""
    for company in companies:
        company.confidence_score = score_company(company)
    return companies


# ── Individual Scoring Functions ─────────────────────────────────────────────

def _score_service_match(company: Company) -> float:
    """Score based on matching thesis target services."""
    if not company.services:
        return 0.2  # We don't know yet — some base score

    target_set = set(THESIS.target_services)
    matched = set(company.services) & target_set

    if len(matched) >= 3:
        return 1.0
    elif len(matched) == 2:
        return 0.9
    elif len(matched) == 1:
        return 0.7
    else:
        # Has services but none match our targets
        return 0.1


def _score_completeness(company: Company) -> float:
    """Score based on data field coverage."""
    # Check if we have employee data (exact count OR range)
    has_employee_data = (
        company.employee_count is not None or
        company.employee_count_min is not None or
        company.employee_count_max is not None
    )

    fields = [
        company.name,
        company.city,
        company.state,
        company.website,
        company.services,
        company.estimated_revenue,
        has_employee_data,  # Count as filled if we have any employee data
        company.ownership_type,
        company.key_contact_name,
        company.phone,
        company.description,
    ]

    filled = sum(1 for f in fields if f)
    return filled / len(fields)


def _score_size(company: Company) -> float:
    """Score based on size threshold fit."""
    score = 0.5  # Neutral if we don't have size data

    has_revenue = company.estimated_revenue is not None
    has_employees = company.employee_count is not None or company.employee_count_min is not None

    if has_revenue:
        if company.estimated_revenue >= THESIS.min_revenue:
            score = 1.0
        elif company.estimated_revenue >= THESIS.min_revenue * 0.5:
            score = 0.6  # Close to threshold
        else:
            score = 0.2  # Too small

    if has_employees:
        # Use exact count if available, otherwise use range max (conservative estimate)
        count = company.employee_count
        if count is None and company.employee_count_max is not None:
            count = company.employee_count_max  # Use upper bound of range
        elif count is None and company.employee_count_min is not None:
            count = company.employee_count_min  # Use lower bound if no max

        if count and count >= THESIS.min_employees:
            score = max(score, 0.8)
        elif count and count >= 3:
            score = max(score, 0.5)
        elif count:
            score = min(score, 0.3)

    return score


def _score_sources(company: Company) -> float:
    """Score based on number and quality of data sources."""
    source_count = len(company.data_sources)

    if source_count >= 3:
        return 1.0
    elif source_count == 2:
        return 0.8
    elif source_count == 1:
        return 0.5
    else:
        return 0.2


def _score_exclusions(company: Company) -> float:
    """Score penalty for exclusion flags."""
    if company.is_excluded:
        return 0.0
    if company.is_pe_backed:
        return 0.3  # PE-backed companies are less attractive for this thesis
    if company.needs_review:
        return 0.5
    return 1.0
