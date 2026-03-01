"""
Google Places API Scraper.

Uses the Places API Text Search to find specialty tax firms
across major US metros. This is the primary structured data source
because it provides: name, address, phone, website, rating, and place_id
which can be used for further detail lookups.

Requires GOOGLE_PLACES_API_KEY environment variable.
"""

import logging
import requests
from typing import Optional
from scrapers.base import BaseScraper
from models import Company
from config import THESIS, APIS, PIPELINE

logger = logging.getLogger(__name__)


class GooglePlacesScraper(BaseScraper):
    """Scrape company data from Google Places API."""

    def __init__(self):
        super().__init__(rate_limit=PIPELINE.rate_limit_google)
        self.api_key = APIS.google_places_api_key
        self.base_url = APIS.google_places_base_url

        if not self.api_key:
            logger.warning(
                "GOOGLE_PLACES_API_KEY not set. Google Places scraper will be skipped."
            )

    def source_name(self) -> str:
        return "google_places"

    def scrape(self) -> list[Company]:
        """
        Run text searches across priority metros and service-specific queries.
        Returns list of Company objects.
        """
        if not self.api_key:
            logger.warning("Skipping Google Places — no API key")
            return []

        companies = []
        seen_place_ids = set()
        service_counts = {
            "R&D Tax Credits": 0,
            "Cost Segregation": 0,
            "Work Opportunity Tax Credits": 0,
            "Sales & Use Tax": 0,
        }

        # Build search combinations: query × metro
        search_combos = self._build_search_matrix()
        total = len(search_combos)

        logger.info(f"Google Places: Running {total} search queries (randomized for balanced coverage)...")

        for i, (query, location) in enumerate(search_combos):
            logger.info(f"  [{i+1}/{total}] Searching: '{query}' near '{location}'")

            try:
                results = self._text_search(query, location)
                for place in results:
                    place_id = place.get("place_id")
                    if place_id in seen_place_ids:
                        continue
                    seen_place_ids.add(place_id)

                    company = self._parse_place(place, query)
                    if company:
                        companies.append(company)
                        # Track service distribution
                        for service in company.services:
                            if service in service_counts:
                                service_counts[service] += 1

                    if len(companies) >= PIPELINE.max_total_companies:
                        logger.info("Reached max company cap, stopping.")
                        break

            except Exception as e:
                logger.error(f"Error on query '{query}' near '{location}': {e}")
                continue

            if len(companies) >= PIPELINE.max_total_companies:
                break

        logger.info(f"Google Places: Found {len(companies)} unique companies")
        logger.info(f"  Service distribution: R&D={service_counts['R&D Tax Credits']}, "
                   f"CostSeg={service_counts['Cost Segregation']}, "
                   f"WOTC={service_counts['Work Opportunity Tax Credits']}, "
                   f"SUT={service_counts['Sales & Use Tax']}")
        self.results = companies
        return companies

    def _build_search_matrix(self) -> list[tuple[str, str]]:
        """
        Build a matrix of (search_query, location) pairs.
        We search each thesis query in a subset of priority metros.
        Focused on quality over quantity - targeting 30-80 strong companies.

        IMPORTANT: Queries are randomized to ensure all services get coverage
        before hitting the company cap (not just R&D and Cost Seg).
        """
        import random

        combos = []

        # Top 10 metros with highest concentration of tax consulting firms
        top_metros = [
            "New York, NY",
            "Los Angeles, CA",
            "Chicago, IL",
            "Houston, TX",
            "San Francisco, CA",
            "Dallas, TX",
            "Atlanta, GA",
            "Boston, MA",
            "Philadelphia, PA",
            "Seattle, WA",
        ]

        # Most targeted queries for specialty tax firms
        focused_queries = [
            "R&D tax credit consulting",
            "cost segregation company",
            "specialty tax advisory firm",
            "WOTC tax credit services",
            "sales and use tax consulting",
        ]

        # 5 queries × 10 metros = 50 focused searches
        for query in focused_queries:
            for metro in top_metros:
                combos.append((query, metro))

        # Randomize order to ensure balanced service coverage
        # (prevents R&D/Cost Seg from dominating before hitting company cap)
        random.shuffle(combos)

        return combos

    def _text_search(self, query: str, location: str) -> list[dict]:
        """
        Execute a Places API Text Search.
        Returns list of place results.
        """
        self._throttle()

        url = f"{self.base_url}/textsearch/json"
        params = {
            "query": f"{query} {location}",
            "key": self.api_key,
            "type": "accounting",  # Broad type for tax consulting
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            logger.warning(f"Places API status: {data.get('status')} - {data.get('error_message', '')}")
            return []

        results = data.get("results", [])

        # Handle pagination (next_page_token) for up to 20 results per query
        next_token = data.get("next_page_token")
        if next_token and len(results) < PIPELINE.max_results_per_query:
            self._throttle()  # Google requires a short delay before using next_page_token
            import time
            time.sleep(2)  # Google-specific delay for page token validity

            params_next = {"pagetoken": next_token, "key": self.api_key}
            try:
                resp2 = requests.get(url, params=params_next, timeout=15)
                resp2.raise_for_status()
                data2 = resp2.json()
                if data2.get("status") == "OK":
                    results.extend(data2.get("results", []))
            except Exception as e:
                logger.debug(f"Pagination failed: {e}")

        return results[:PIPELINE.max_results_per_query]

    def get_place_details(self, place_id: str) -> Optional[dict]:
        """
        Get detailed information for a specific place.
        Includes website, phone, reviews, hours, etc.
        """
        self._throttle()

        url = f"{self.base_url}/details/json"
        params = {
            "place_id": place_id,
            "key": self.api_key,
            "fields": (
                "name,formatted_address,formatted_phone_number,website,"
                "url,rating,user_ratings_total,business_status,"
                "opening_hours,types,editorial_summary"
            ),
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data.get("status") == "OK":
                return data.get("result", {})
        except Exception as e:
            logger.error(f"Place details error for {place_id}: {e}")

        return None

    def _parse_place(self, place: dict, search_query: str) -> Optional[Company]:
        """Convert a Google Places result into a Company object."""

        name = place.get("name", "").strip()
        if not name:
            return None

        address = place.get("formatted_address", "")
        state = self.extract_state_from_address(address)
        city = self.extract_city_from_address(address)

        # Skip if not in Continental US
        if state and state not in ("AK", "HI") and state not in self._continental_states():
            return None

        # Classify services based on the search query that found this company
        # (We'll do deeper classification during enrichment from their website)
        services = self.classify_services(name + " " + search_query)

        company = Company(
            name=self.normalize_company_name(name),
            city=city,
            state=state,
            address=address,
            services=services,
            primary_service=services[0] if services else None,
            phone=self.normalize_phone(place.get("formatted_phone_number", "")),
            google_place_id=place.get("place_id"),
            google_rating=place.get("rating"),
            google_reviews_count=place.get("user_ratings_total"),
            data_sources=["google_places"],
            source_urls=[place.get("url", "")],
            # ownership_type left as None - only set when confirmed from reliable source
        )

        return company

    @staticmethod
    def _continental_states() -> set:
        """Return set of continental US state abbreviations."""
        from scrapers.base import CONTINENTAL_US
        return CONTINENTAL_US

    def enrich_with_details(self, company: Company) -> Company:
        """
        Call Place Details API to get website, phone, etc.
        for a company that already has a google_place_id.
        """
        if not company.google_place_id:
            return company

        details = self.get_place_details(company.google_place_id)
        if not details:
            return company

        if not company.website:
            company.website = self.normalize_website(details.get("website", ""))

        if not company.phone:
            company.phone = self.normalize_phone(
                details.get("formatted_phone_number", "")
            )

        if not company.address:
            company.address = details.get("formatted_address", "")
            if not company.state:
                company.state = self.extract_state_from_address(company.address)
            if not company.city:
                company.city = self.extract_city_from_address(company.address)

        # Update rating if available
        if details.get("rating"):
            company.google_rating = details["rating"]
        if details.get("user_ratings_total"):
            company.google_reviews_count = details["user_ratings_total"]

        # Check editorial summary for service classification
        summary = details.get("editorial_summary", {}).get("overview", "")
        if summary:
            company.description = summary
            more_services = self.classify_services(summary)
            company.services = list(set(company.services + more_services))

        return company
