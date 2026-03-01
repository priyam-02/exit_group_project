"""
Base scraper class with shared functionality:
  - Rate limiting
  - Error handling / retries
  - Logging
  - Common data normalization
"""

import time
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional
from models import Company


logger = logging.getLogger(__name__)


# ── US State Mapping ─────────────────────────────────────────────────────────

STATE_ABBREV = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}

ABBREV_TO_STATE = {v: k.title() for k, v in STATE_ABBREV.items()}

CONTINENTAL_US = set(STATE_ABBREV.values()) - {"AK", "HI"}


class BaseScraper(ABC):
    """Abstract base class for all data scrapers."""

    def __init__(self, rate_limit: float = 1.0):
        """
        Args:
            rate_limit: Minimum seconds between requests.
        """
        self.rate_limit = rate_limit
        self._last_request_time = 0
        self.results: list[Company] = []

    def _throttle(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    @abstractmethod
    def scrape(self) -> list[Company]:
        """Run the scraper and return a list of Company objects."""
        pass

    @abstractmethod
    def source_name(self) -> str:
        """Return a human-readable name for this data source."""
        pass

    # ── Shared Normalization Utilities ────────────────────────────────────

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Clean and normalize a company name."""
        if not name:
            return ""

        # Remove common suffixes for matching (but keep original for display)
        name = name.strip()
        # Remove extra whitespace
        name = re.sub(r"\s+", " ", name)
        return name

    @staticmethod
    def normalize_state(state_str: str) -> Optional[str]:
        """Convert state name or abbreviation to 2-letter code."""
        if not state_str:
            return None

        state_str = state_str.strip()

        # Already an abbreviation
        if len(state_str) == 2 and state_str.upper() in CONTINENTAL_US:
            return state_str.upper()

        # Full state name
        lower = state_str.lower()
        if lower in STATE_ABBREV:
            return STATE_ABBREV[lower]

        return None

    @staticmethod
    def normalize_website(url: str) -> Optional[str]:
        """Clean and normalize a website URL."""
        if not url:
            return None

        url = url.strip().lower()
        # Remove trailing slashes
        url = url.rstrip("/")
        # Ensure https
        if not url.startswith("http"):
            url = "https://" + url
        # Remove www. for consistency
        url = re.sub(r"https?://(www\.)?", "https://", url)

        return url

    @staticmethod
    def normalize_phone(phone: str) -> Optional[str]:
        """Normalize phone number to standard format."""
        if not phone:
            return None
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == "1":
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        return phone.strip()

    @staticmethod
    def extract_state_from_address(address: str) -> Optional[str]:
        """Try to extract state abbreviation from a full address string."""
        if not address:
            return None

        # Pattern: City, ST ZIP or City, ST
        match = re.search(r",\s*([A-Z]{2})\s*\d{0,5}", address)
        if match:
            state = match.group(1)
            if state in CONTINENTAL_US:
                return state

        # Try full state names
        for state_name, abbrev in STATE_ABBREV.items():
            if state_name in address.lower():
                return abbrev

        return None

    @staticmethod
    def extract_city_from_address(address: str) -> Optional[str]:
        """Try to extract city from a full address string."""
        if not address:
            return None

        # Pattern: ..., City, ST ZIP
        match = re.search(r"(?:.*,\s*)?([A-Za-z\s]+),\s*[A-Z]{2}", address)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def classify_services(text: str) -> list[str]:
        """
        Detect which thesis services are mentioned in a text blob.
        Returns list of matching service names.
        """
        if not text:
            return []

        text_lower = text.lower()
        services = []

        # R&D Tax Credits
        rd_patterns = [
            r"r\s*&\s*d\s+tax", r"r&d\s+credit", r"research\s+and\s+development\s+tax",
            r"research\s+tax\s+credit", r"r&d\s+incentive",
        ]
        if any(re.search(p, text_lower) for p in rd_patterns):
            services.append("R&D Tax Credits")

        # Cost Segregation
        cs_patterns = [
            r"cost\s+seg", r"cost\s+segregation", r"engineering.based\s+tax\s+stud",
        ]
        if any(re.search(p, text_lower) for p in cs_patterns):
            services.append("Cost Segregation")

        # WOTC
        wotc_patterns = [
            r"wotc", r"work\s+opportunity\s+tax", r"work\s+opportunity\s+credit",
        ]
        if any(re.search(p, text_lower) for p in wotc_patterns):
            services.append("Work Opportunity Tax Credits")

        # Sales & Use Tax
        sut_patterns = [
            r"sales\s+(?:&|and)\s+use\s+tax", r"sales\s+tax\s+consult",
            r"use\s+tax\s+consult", r"sales\s+tax\s+advisory",
            r"indirect\s+tax\s+consult",
        ]
        if any(re.search(p, text_lower) for p in sut_patterns):
            services.append("Sales & Use Tax")

        return services

    @staticmethod
    def check_exclusions(text: str) -> Optional[str]:
        """
        Check if text suggests the company should be excluded.
        Returns exclusion reason or None.
        """
        if not text:
            return None

        text_lower = text.lower()

        # ERC-focused companies
        erc_patterns = [
            r"employee\s+retention\s+credit",
            r"\berc\b.*(?:speciali|focus|primary|only)",
            r"(?:speciali|focus|primary|only).*\berc\b",
        ]
        for p in erc_patterns:
            if re.search(p, text_lower):
                return "Primary service appears to be Employee Retention Credit (ERC)"

        # Property tax exclusive
        prop_patterns = [
            r"property\s+tax.*(?:only|exclusive|speciali|focus)",
            r"(?:only|exclusive|speciali|focus).*property\s+tax",
        ]
        for p in prop_patterns:
            if re.search(p, text_lower):
                return "Exclusively focused on Property Tax consulting"

        return None

    @staticmethod
    def detect_pe_backed(text: str) -> bool:
        """Check if text suggests company is PE-backed."""
        if not text:
            return False

        text_lower = text.lower()
        pe_patterns = [
            r"private\s+equity", r"pe.backed", r"portfolio\s+company",
            r"backed\s+by.*capital", r"backed\s+by.*partners",
            r"acquired\s+by.*capital", r"acquired\s+by.*partners",
        ]
        return any(re.search(p, text_lower) for p in pe_patterns)

    @staticmethod
    def detect_ownership_type(text: str) -> Optional[str]:
        """
        Detect ownership type from website text.
        Returns one of: "PE-backed", "Family-owned", "Corporate-owned", "Franchise", "Independent", or None.
        Priority order: PE-backed > Corporate-owned > Family-owned > Franchise > Independent
        """
        if not text:
            return None

        text_lower = text.lower()

        # PE-backed (highest priority - most important for M&A)
        pe_patterns = [
            r"private\s+equity", r"pe[\s\-]backed", r"portfolio\s+company",
            r"backed\s+by\s+\w+\s+capital", r"backed\s+by\s+\w+\s+partners",
            r"acquired\s+by\s+\w+\s+capital", r"acquired\s+by\s+\w+\s+partners",
            r"investment\s+by\s+\w+\s+capital", r"partnered\s+with\s+\w+\s+capital",
        ]
        if any(re.search(p, text_lower) for p in pe_patterns):
            return "PE-backed"

        # Corporate-owned (subsidiary of larger company)
        corporate_patterns = [
            r"subsidiary\s+of", r"division\s+of", r"part\s+of\s+\w+\s+(?:corporation|corp|inc)",
            r"owned\s+by\s+\w+\s+(?:corporation|corp|inc)", r"acquired\s+by\s+(?!.*(?:capital|partners))\w+\s+(?:corporation|corp|inc)",
            r"a\s+\w+\s+company",  # e.g., "A Deloitte company"
        ]
        if any(re.search(p, text_lower) for p in corporate_patterns):
            return "Corporate-owned"

        # Family-owned (family business indicators)
        family_patterns = [
            r"family[\s\-]owned", r"family[\s\-]business", r"family[\s\-]run",
            r"founded\s+by\s+the\s+\w+\s+family", r"(?:second|third|fourth)\s+generation",
            r"family\s+tradition", r"family\s+company",
        ]
        if any(re.search(p, text_lower) for p in family_patterns):
            return "Family-owned"

        # Franchise
        franchise_patterns = [
            r"franchise", r"franchisee", r"licensed\s+operator",
            r"franchised\s+location", r"independently\s+franchised",
        ]
        if any(re.search(p, text_lower) for p in franchise_patterns):
            return "Franchise"

        # Independent (locally owned, independently operated)
        independent_patterns = [
            r"independently\s+owned", r"locally\s+owned", r"independent\s+(?:firm|company|business)",
            r"privately\s+held", r"woman[\s\-]owned", r"minority[\s\-]owned",
            r"veteran[\s\-]owned", r"employee[\s\-]owned",
        ]
        if any(re.search(p, text_lower) for p in independent_patterns):
            return "Independent"

        return None
