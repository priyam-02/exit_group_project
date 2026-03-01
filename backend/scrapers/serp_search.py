"""
SerpAPI Scraper — Google Search Results.

Uses SerpAPI to get structured Google search results for thesis-related queries.
This catches companies that might not show up in Google Places (e.g., companies
that rank for "R&D tax credit consulting" but aren't listed as a Place).

Also captures organic search results from industry directories, association pages,
and "top X firms" listicles, which are great for discovery.

Requires SERPAPI_KEY environment variable.
"""

import logging
import re
import requests
from urllib.parse import urlparse
from typing import Optional
from scrapers.base import BaseScraper
from models import Company
from config import THESIS, APIS, PIPELINE

logger = logging.getLogger(__name__)


class SerpScraper(BaseScraper):
    """Scrape company data from Google Search via SerpAPI."""

    def __init__(self):
        super().__init__(rate_limit=PIPELINE.rate_limit_serp)
        self.api_key = APIS.serpapi_key
        self.base_url = APIS.serpapi_base_url

        if not self.api_key:
            logger.warning("SERPAPI_KEY not set. SerpAPI scraper will be skipped.")

    def source_name(self) -> str:
        return "serp_search"

    def scrape(self) -> list[Company]:
        """
        Run targeted Google searches for specialty tax firms.
        Parses both organic results and local pack results.
        """
        if not self.api_key:
            logger.warning("Skipping SerpAPI — no API key")
            return []

        companies = []
        seen_domains = set()

        queries = self._build_queries()
        total = len(queries)

        logger.info(f"SerpAPI: Running {total} search queries...")

        for i, query in enumerate(queries):
            logger.info(f"  [{i+1}/{total}] Searching: '{query}'")

            try:
                results = self._search(query)

                # Parse organic results
                for result in results.get("organic_results", []):
                    company = self._parse_organic_result(result, query)
                    if company and company.website:
                        domain = urlparse(company.website).netloc
                        if domain not in seen_domains:
                            seen_domains.add(domain)
                            companies.append(company)

                # Parse local pack (map results)
                for result in results.get("local_results", []):
                    company = self._parse_local_result(result, query)
                    if company:
                        companies.append(company)

            except Exception as e:
                logger.error(f"SerpAPI error on '{query}': {e}")
                continue

            if len(companies) >= PIPELINE.max_total_companies:
                break

        logger.info(f"SerpAPI: Found {len(companies)} companies")
        self.results = companies
        return companies

    def _build_queries(self) -> list[str]:
        """Build search queries optimized for finding niche tax firms."""
        queries = []

        # Direct firm-finding queries
        service_queries = [
            '"R&D tax credit" consulting firm',
            '"cost segregation" consulting company',
            '"WOTC" tax credit services company',
            '"sales and use tax" consulting firm',
            "specialty tax advisory firm private",
            '"R&D tax credit" firm -jobs -careers',
            '"cost segregation" company -jobs -hiring',
            '"work opportunity tax credit" consulting',
            "top R&D tax credit firms United States",
            "best cost segregation companies",
            "WOTC service providers list",
            "sales and use tax advisory firms",
            "specialty tax consulting companies list",
            "R&D tax credit companies directory",
            '"cost segregation" study firms directory',
            "engineering based tax study companies",
        ]
        queries.extend(service_queries)

        # State-specific searches for high-density states
        key_states = [
            "Texas",
            "California",
            "New York",
            "Florida",
            "Illinois",
            "Ohio",
            "Georgia",
            "North Carolina",
            "New Jersey",
            "Pennsylvania",
        ]
        for state in key_states:
            queries.append(f"R&D tax credit consulting firms {state}")
            queries.append(f"cost segregation companies {state}")

        # Industry directory / list queries
        directory_queries = [
            "list of R&D tax credit companies",
            "ACSS member directory cost segregation",
            "specialty tax firms directory",
            "R&D tax credit providers association",
        ]
        queries.extend(directory_queries)

        return queries

    def _search(self, query: str) -> dict:
        """Execute a SerpAPI search."""
        self._throttle()

        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": 10,
            "gl": "us",
            "hl": "en",
        }

        response = requests.get(self.base_url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        # Handle error responses from SerpAPI
        if isinstance(data, str):
            raise ValueError(f"SerpAPI returned string instead of dict: {data}")
        if "error" in data:
            raise ValueError(f"SerpAPI error: {data.get('error')}")

        return data

    def _parse_organic_result(self, result: dict, query: str) -> Optional[Company]:
        """Parse an organic search result into a Company."""
        title = result.get("title", "")
        link = result.get("link", "")
        snippet = result.get("snippet", "")

        if not title or not link:
            return None

        # Skip non-company pages (news, job boards, Wikipedia, etc.)
        skip_domains = [
            "linkedin.com",
            "indeed.com",
            "glassdoor.com",
            "wikipedia.org",
            "yelp.com",
            "bbb.org",
            "youtube.com",
            "facebook.com",
            "twitter.com",
            "reddit.com",
            "irs.gov",
            "investopedia.com",
            "forbes.com",
            "bloomberg.com",
        ]
        domain = urlparse(link).netloc.lower()
        if any(skip in domain for skip in skip_domains):
            return None

        # Skip obvious non-company pages
        if any(
            kw in link.lower() for kw in ["/blog/", "/article/", "/news/", "/wiki/"]
        ):
            return None

        # Try to extract company name from title
        company_name = self._extract_company_name(title)
        if not company_name:
            return None

        # Classify services from title + snippet
        full_text = f"{title} {snippet}"
        services = self.classify_services(full_text)

        # Check exclusions
        exclusion = self.check_exclusions(full_text)

        is_pe = self.detect_pe_backed(full_text)

        company = Company(
            name=self.normalize_company_name(company_name),
            website=self.normalize_website(link),
            services=services,
            primary_service=services[0] if services else None,
            description=snippet[:500] if snippet else None,
            data_sources=["serp_search"],
            source_urls=[link],
            ownership_type="PE-backed" if is_pe else None,  # Only set when confirmed
            is_excluded=bool(exclusion),
            exclusion_reason=exclusion,
            is_pe_backed=is_pe,
        )

        return company

    def _parse_local_result(self, result: dict, query: str) -> Optional[Company]:
        """Parse a local pack (maps) result into a Company."""
        name = result.get("title", "")
        if not name:
            return None

        address = result.get("address", "")
        state = self.extract_state_from_address(address)
        city = self.extract_city_from_address(address)

        services = self.classify_services(name + " " + query)

        company = Company(
            name=self.normalize_company_name(name),
            city=city,
            state=state,
            address=address,
            phone=self.normalize_phone(result.get("phone", "")),
            google_rating=result.get("rating"),
            google_reviews_count=result.get("reviews"),
            services=services,
            primary_service=services[0] if services else None,
            data_sources=["serp_local"],
            # ownership_type left as None - only set when confirmed
        )

        return company

    @staticmethod
    def _extract_company_name(title: str) -> Optional[str]:
        """
        Try to extract a company name from a search result title.
        Handles patterns like "Company Name | Service", "Company Name - Tagline", etc.
        """
        if not title:
            return None

        # Split on common separators
        separators = [" | ", " - ", " – ", " — ", " :: ", " // "]
        name = title
        for sep in separators:
            if sep in name:
                name = name.split(sep)[0]
                break

        # Remove generic suffixes
        generic = [
            "LLC",
            "Inc",
            "Inc.",
            "Corp",
            "Corp.",
            "LLP",
            "PLLC",
            "& Associates",
            "& Company",
            "Group",
            "Services",
            "Home",
            "About Us",
            "Contact",
        ]
        for g in generic:
            name = re.sub(rf"\s*{re.escape(g)}\s*$", "", name, flags=re.IGNORECASE)

        name = name.strip()
        if len(name) < 3 or len(name) > 100:
            return None

        return name
