"""
Deduplication Engine.

Companies can appear across multiple data sources with slightly
different names, addresses, or other details. This module handles:
  1. Exact dedup (same name + state)
  2. Fuzzy name matching (handles typos, abbreviations, etc.)
  3. Domain-based dedup (same website = same company)
  4. Merging data from duplicate records

Uses both exact matching and fuzzy string similarity to catch:
  - "Acme Tax LLC" vs "Acme Tax"
  - "R&D Credit Co." vs "R and D Credit Company"
"""

import re
import logging
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import urlparse
from models import Company
from config import PIPELINE

logger = logging.getLogger(__name__)


def deduplicate(companies: list[Company]) -> list[Company]:
    """
    Main deduplication function.
    Takes a list of companies and returns a deduplicated list,
    merging data from duplicates into the best record.
    """
    if not companies:
        return []

    logger.info(f"Deduplication: Starting with {len(companies)} companies")

    # Phase 1: Domain-based dedup (most reliable)
    companies = _dedup_by_domain(companies)
    logger.info(f"  After domain dedup: {len(companies)}")

    # Phase 2: Fuzzy name + state dedup
    companies = _dedup_by_name(companies)
    logger.info(f"  After name dedup: {len(companies)}")

    logger.info(f"Deduplication: Final count = {len(companies)}")
    return companies


def _dedup_by_domain(companies: list[Company]) -> list[Company]:
    """Merge companies that share the same website domain."""
    domain_map: dict[str, Company] = {}
    no_domain: list[Company] = []

    for company in companies:
        domain = _extract_domain(company.website)
        if not domain:
            no_domain.append(company)
            continue

        if domain in domain_map:
            # Merge into existing record
            domain_map[domain] = _merge_companies(domain_map[domain], company)
        else:
            domain_map[domain] = company

    return list(domain_map.values()) + no_domain


def _dedup_by_name(companies: list[Company]) -> list[Company]:
    """Merge companies with similar names in the same state."""
    threshold = PIPELINE.dedup_similarity_threshold
    result: list[Company] = []
    used = set()

    for i, c1 in enumerate(companies):
        if i in used:
            continue

        best = c1
        for j, c2 in enumerate(companies[i + 1:], start=i + 1):
            if j in used:
                continue

            # Must be in the same state (or at least one has no state)
            if c1.state and c2.state and c1.state != c2.state:
                continue

            # Compare normalized names
            sim = _name_similarity(c1.name, c2.name)
            if sim >= threshold:
                logger.debug(f"  Merging: '{c1.name}' ≈ '{c2.name}' (sim={sim:.2f})")
                best = _merge_companies(best, c2)
                used.add(j)

        result.append(best)
        used.add(i)

    return result


def _name_similarity(name1: str, name2: str) -> float:
    """
    Compute similarity between two company names.
    Uses normalized forms and SequenceMatcher.
    """
    n1 = _normalize_for_comparison(name1)
    n2 = _normalize_for_comparison(name2)

    if not n1 or not n2:
        return 0.0

    # Exact match after normalization
    if n1 == n2:
        return 1.0

    # SequenceMatcher ratio
    return SequenceMatcher(None, n1, n2).ratio()


def _normalize_for_comparison(name: str) -> str:
    """
    Normalize a company name for comparison purposes.
    Strips suffixes, lowercases, removes punctuation.
    """
    if not name:
        return ""

    name = name.lower().strip()

    # Remove common business suffixes
    suffixes = [
        r"\bllc\b", r"\bllp\b", r"\binc\.?\b", r"\bcorp\.?\b",
        r"\bpllc\b", r"\bco\.?\b", r"\bltd\.?\b", r"\bpc\b",
        r"\bpa\b", r"\bgroup\b", r"\bservices\b", r"\bconsulting\b",
        r"\badvisors?\b", r"\bassociates?\b", r"\b& company\b",
        r"\bcompany\b", r"\binternational\b",
    ]
    for suffix in suffixes:
        name = re.sub(suffix, "", name)

    # Normalize "and" / "&"
    name = name.replace("&", "and")

    # Remove punctuation
    name = re.sub(r"[^\w\s]", "", name)

    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()

    return name


def _extract_domain(url: Optional[str]) -> Optional[str]:
    """Extract the root domain from a URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Remove www prefix
        domain = re.sub(r"^www\.", "", domain.lower())
        return domain if domain else None
    except Exception:
        return None


def _merge_companies(primary: Company, secondary: Company) -> Company:
    """
    Merge two company records, preferring data from the primary.
    For list fields (services, data_sources), we union them.
    For scalar fields, we keep primary's value unless it's None.
    """
    # Merge list fields
    primary.services = list(set(primary.services + secondary.services))
    primary.data_sources = list(set(primary.data_sources + secondary.data_sources))
    primary.source_urls = list(set(primary.source_urls + secondary.source_urls))

    # Merge scalar fields — fill gaps from secondary
    if not primary.city and secondary.city:
        primary.city = secondary.city
    if not primary.state and secondary.state:
        primary.state = secondary.state
    if not primary.website and secondary.website:
        primary.website = secondary.website
    if not primary.phone and secondary.phone:
        primary.phone = secondary.phone
    if not primary.address and secondary.address:
        primary.address = secondary.address
    if not primary.estimated_revenue and secondary.estimated_revenue:
        primary.estimated_revenue = secondary.estimated_revenue
        primary.revenue_source = secondary.revenue_source
    if not primary.employee_count and secondary.employee_count:
        primary.employee_count = secondary.employee_count
        primary.employee_count_source = secondary.employee_count_source
    if not primary.ownership_type and secondary.ownership_type:
        primary.ownership_type = secondary.ownership_type
    if not primary.key_contact_name and secondary.key_contact_name:
        primary.key_contact_name = secondary.key_contact_name
        primary.key_contact_title = secondary.key_contact_title
    if not primary.google_place_id and secondary.google_place_id:
        primary.google_place_id = secondary.google_place_id
    if not primary.google_rating and secondary.google_rating:
        primary.google_rating = secondary.google_rating
    if not primary.google_reviews_count and secondary.google_reviews_count:
        primary.google_reviews_count = secondary.google_reviews_count
    if not primary.description and secondary.description:
        primary.description = secondary.description
    if not primary.year_founded and secondary.year_founded:
        primary.year_founded = secondary.year_founded
    if not primary.linkedin_url and secondary.linkedin_url:
        primary.linkedin_url = secondary.linkedin_url
    if not primary.primary_service and secondary.primary_service:
        primary.primary_service = secondary.primary_service

    # PE-backed flag: if either says yes, mark it
    if secondary.is_pe_backed:
        primary.is_pe_backed = True
        primary.ownership_type = "PE-backed"

    # Exclusion: if either is excluded, mark it
    if secondary.is_excluded:
        primary.is_excluded = True
        if not primary.exclusion_reason:
            primary.exclusion_reason = secondary.exclusion_reason

    # Confidence: take the higher score
    if secondary.confidence_score and (
        not primary.confidence_score or secondary.confidence_score > primary.confidence_score
    ):
        primary.confidence_score = secondary.confidence_score

    return primary
