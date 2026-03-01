"""
Website Enricher.

After initial discovery from Google Places or SerpAPI, this module
visits each company's website to extract additional details:
  - Services offered (more accurate than search query inference)
  - Key contacts / leadership team
  - Company description
  - Employee count hints
  - Revenue indicators
  - PE-backed indicators
  - Year founded

This is the "data enrichment from a second source" bonus item.
"""

import logging
import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from models import Company
from config import PIPELINE

logger = logging.getLogger(__name__)

# Pages to check on each company website
TARGET_PAGES = [
    "",              # Homepage
    "/about",
    "/about-us",
    "/about-us/",
    "/services",
    "/our-services",
    "/team",
    "/our-team",
    "/leadership",
    "/contact",
    "/contact-us",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


class WebsiteEnricher:
    """Enrich company data by scraping their websites."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = PIPELINE.enrichment_timeout

    def enrich(self, company: Company) -> Company:
        """
        Visit the company's website and extract as much data as possible.
        Non-destructive — only fills in fields that are currently empty.
        """
        if not company.website:
            return company

        base_url = company.website.rstrip("/")
        all_text = ""

        for page_path in TARGET_PAGES:
            url = f"{base_url}{page_path}"
            try:
                text, soup = self._fetch_page(url)
                if not text:
                    continue

                all_text += f"\n{text}"

                # Extract data from specific page types
                if page_path in ("", "/about", "/about-us", "/about-us/"):
                    self._extract_about_info(company, text, soup)
                elif page_path in ("/services", "/our-services"):
                    self._extract_services(company, text)
                elif page_path in ("/team", "/our-team", "/leadership"):
                    self._extract_team(company, text, soup)
                elif page_path in ("/contact", "/contact-us"):
                    self._extract_contact(company, text, soup)

            except Exception as e:
                logger.debug(f"Error fetching {url}: {e}")
                continue

        # Run aggregate analysis on all collected text
        if all_text:
            self._analyze_full_text(company, all_text)
            # Add website as a data source
            if "website" not in company.data_sources:
                company.data_sources.append("website")

        # Try to find LinkedIn URL if not already set
        if not company.linkedin_url:
            try:
                # Check homepage for LinkedIn link
                text, soup = self._fetch_page(company.website)
                if soup:
                    linkedin_link = self._extract_linkedin_url(soup)
                    if linkedin_link:
                        company.linkedin_url = linkedin_link
                        logger.debug(f"Found LinkedIn URL for {company.name}: {linkedin_link}")
            except Exception as e:
                logger.debug(f"Error finding LinkedIn URL for {company.name}: {e}")

        # Try LinkedIn enrichment if we have a LinkedIn URL
        # (LinkedIn provides reliable employee count ranges)
        if company.linkedin_url:
            try:
                self._enrich_from_linkedin(company)
            except Exception as e:
                logger.debug(f"LinkedIn enrichment failed for {company.name}: {e}")

        return company

    def _fetch_page(self, url: str) -> tuple[Optional[str], Optional[BeautifulSoup]]:
        """Fetch a page and return (text_content, soup) or (None, None)."""
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                return None, None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            text = soup.get_text(separator=" ", strip=True)
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)

            return text, soup

        except requests.RequestException:
            return None, None

    def _extract_about_info(self, company: Company, text: str, soup: BeautifulSoup):
        """Extract info from About page: description, year founded, etc."""

        # Year founded
        if not company.year_founded:
            patterns = [
                r"(?:founded|established|since|started)\s+(?:in\s+)?(\d{4})",
                r"(\d{4})\s+(?:founded|established)",
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    year = int(match.group(1))
                    if 1950 <= year <= 2025:
                        company.year_founded = year
                        break

        # Description (first substantial paragraph)
        if not company.description:
            # Find meta description or first paragraph
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content"):
                company.description = meta["content"][:500]
            else:
                # Find first substantial paragraph
                for p in soup.find_all("p"):
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 80:
                        company.description = p_text[:500]
                        break

    def _extract_services(self, company: Company, text: str):
        """Extract and classify services from services page."""
        from scrapers.base import BaseScraper

        services = BaseScraper.classify_services(text)
        if services:
            company.services = list(set(company.services + services))
            if not company.primary_service and services:
                company.primary_service = services[0]

    def _extract_team(self, company: Company, text: str, soup: BeautifulSoup):
        """Extract key contact info from team/leadership page."""
        if company.key_contact_name:
            return  # Already have a contact

        # Look for leadership titles
        title_patterns = [
            r"(?:CEO|President|Founder|Managing\s+Partner|Principal|Owner|Director)",
        ]

        # Try to find name-title pairs
        for pattern in title_patterns:
            # Pattern: Name, Title or Name - Title
            match = re.search(
                rf"([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)\s*[,\-–]\s*{pattern}",
                text
            )
            if match:
                company.key_contact_name = match.group(1).strip()
                company.key_contact_title = re.search(pattern, match.group(0)).group(0)
                break

            # Reverse: Title - Name
            match = re.search(
                rf"{pattern}\s*[,\-–:]\s*([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)",
                text
            )
            if match:
                company.key_contact_name = match.group(1).strip()
                company.key_contact_title = re.search(pattern, match.group(0)).group(0)
                break

        # Count team members as a rough employee count indicator
        if not company.employee_count:
            # Count how many names/profiles appear on team page
            # (h3 or h4 elements often contain team member names)
            name_elements = soup.find_all(["h3", "h4"], class_=lambda x: x and "name" in str(x).lower())
            if not name_elements:
                name_elements = soup.find_all(["h3", "h4"])
                # Filter to likely names (2-4 capitalized words)
                name_elements = [
                    el for el in name_elements
                    if re.match(r"^[A-Z][a-z]+(\s+[A-Z]\.?\s+|\s+)[A-Z][a-z]+", el.get_text(strip=True))
                ]
            if len(name_elements) > 2:
                # This is a lower bound — the actual company is likely bigger
                company.employee_count = max(len(name_elements), company.employee_count or 0)
                company.employee_count_source = "website_team_page"

    def _extract_contact(self, company: Company, text: str, soup: BeautifulSoup):
        """Extract contact details from contact page."""

        # Phone number
        if not company.phone:
            from scrapers.base import BaseScraper
            phone_match = re.search(r"(?:\+1[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})", text)
            if phone_match:
                raw = phone_match.group(0)
                company.phone = BaseScraper.normalize_phone(raw)

        # Email
        if not company.key_contact_email:
            email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
            if email_match:
                email = email_match.group(0).lower()
                # Skip generic emails
                if not any(prefix in email for prefix in ["info@", "admin@", "support@", "noreply@"]):
                    company.key_contact_email = email

        # Address for city/state if missing
        if not company.state:
            from scrapers.base import BaseScraper
            state = BaseScraper.extract_state_from_address(text)
            if state:
                company.state = state
            city = BaseScraper.extract_city_from_address(text)
            if city:
                company.city = city

    def _analyze_full_text(self, company: Company, all_text: str):
        """Run aggregate analysis on all text from the website."""
        from scrapers.base import BaseScraper

        # Re-classify services with full text
        services = BaseScraper.classify_services(all_text)
        if services:
            company.services = list(set(company.services + services))
            if not company.primary_service:
                company.primary_service = services[0]

        # Check for exclusions
        exclusion = BaseScraper.check_exclusions(all_text)
        if exclusion:
            company.is_excluded = True
            company.exclusion_reason = exclusion

        # Detect ownership type (only set if not already confirmed)
        if not company.ownership_type:
            ownership = BaseScraper.detect_ownership_type(all_text)
            if ownership:
                company.ownership_type = ownership
                # Also set is_pe_backed flag for backward compatibility
                if ownership == "PE-backed":
                    company.is_pe_backed = True

        # Revenue estimation from text clues
        if not company.estimated_revenue:
            company.estimated_revenue = self._estimate_revenue(all_text)
            if company.estimated_revenue:
                company.revenue_source = "website_text_inference"

        # Employee count estimation
        if not company.employee_count:
            company.employee_count = self._estimate_employees(all_text)
            if company.employee_count:
                company.employee_count_source = "website_text_inference"

    @staticmethod
    def _estimate_revenue(text: str) -> Optional[int]:
        """
        Try to estimate revenue from website text.
        Looks for patterns like "$X million", "Xm in revenue", etc.
        """
        text_lower = text.lower()

        # Direct revenue mentions (expanded patterns)
        patterns = [
            r"\$(\d+(?:\.\d+)?)\s*(?:m|million)\s*(?:in\s+)?(?:revenue|sales|billing|annual\s+revenue)",
            r"revenue\s+(?:of\s+|exceeding\s+|over\s+|:\s*)?\$(\d+(?:\.\d+)?)\s*(?:m|million)",
            r"(\d+(?:\.\d+)?)\s*(?:m|million)\s*(?:dollar)?\s*(?:in\s+)?(?:revenue|firm|business|company)",
            r"annual\s+(?:revenue|sales)\s+(?:of\s+)?\$(\d+(?:\.\d+)?)\s*(?:m|million)",
            r"\$(\d+(?:\.\d+)?)\s*(?:m|million)\s+(?:annual\s+)?(?:revenue|sales)",
            r"generates?\s+(?:over\s+)?\$(\d+(?:\.\d+)?)\s*(?:m|million)\s+(?:in\s+)?(?:revenue|annually)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    amount = float(match.group(1))
                    if 1 <= amount <= 500:  # Reasonable range in millions
                        return int(amount * 1_000_000)
                except ValueError:
                    continue

        # Tax credit amounts processed (rough revenue indicator)
        credit_patterns = [
            r"\$(\d+(?:\.\d+)?)\s*(?:b|billion)\s*(?:in\s+)?(?:credit|tax\s+saving|tax\s+benefit)",
            r"(?:secured|identified|generated)\s+(?:over\s+)?\$(\d+(?:\.\d+)?)\s*(?:m|million)",
        ]
        for pattern in credit_patterns:
            match = re.search(pattern, text_lower)
            if match:
                # If they process billions in credits, they're likely >$10M revenue
                try:
                    amount = float(match.group(1))
                    if "billion" in text_lower[match.start():match.end()+10]:
                        return 50_000_000  # Conservative estimate for billion-dollar processors
                    elif amount > 100:
                        return 10_000_000
                except ValueError:
                    continue

        return None

    @staticmethod
    def _estimate_employees(text: str) -> Optional[int]:
        """
        Try to estimate employee count from website text.
        Looks for patterns like "X employees", "team of X", etc.
        """
        text_lower = text.lower()

        patterns = [
            r"(\d+)\+?\s*(?:employees|team\s+members|professionals|consultants|staff)",
            r"team\s+of\s+(\d+)\+?",
            r"(?:over|more\s+than|approximately)\s+(\d+)\+?\s+(?:employees|people|professionals)",
            r"(\d+)\s*(?:\+|plus)\s*(?:employees|people|professionals|staff)",
            r"staff\s+of\s+(\d+)",
            r"(\d+)\s+experienced\s+(?:professionals|consultants|tax\s+experts)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    count = int(match.group(1))
                    if 2 <= count <= 10000:  # Reasonable range
                        # If pattern has "+", add 20% to account for "50+" meaning ~60
                        if "+" in match.group(0) or "plus" in match.group(0) or "over" in match.group(0):
                            count = int(count * 1.2)
                        return count
                except ValueError:
                    continue

        # Office locations as a proxy (multiple offices = likely > 5 employees)
        office_count = len(re.findall(r"(?:office|location)\s+(?:in|:)", text_lower))
        if office_count >= 3:
            return max(15, office_count * 5)  # Conservative estimate

        return None

    @staticmethod
    def _extract_linkedin_url(soup: BeautifulSoup) -> Optional[str]:
        """Extract LinkedIn company page URL from website."""
        if not soup:
            return None

        # Look for LinkedIn links in the page
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "linkedin.com/company/" in href:
                # Clean up the URL
                if "?" in href:
                    href = href.split("?")[0]
                return href.rstrip("/")

        return None

    def _enrich_from_linkedin(self, company: Company):
        """
        Extract data from LinkedIn company page:
        - Employee count (ranges or exact)
        - Leadership team (CEO, Founder, President)
        - Year founded
        - Company description/tagline
        """
        if not company.linkedin_url:
            return

        try:
            # Fetch LinkedIn page
            text, soup = self._fetch_page(company.linkedin_url)
            if not text:
                return

            text_lower = text.lower()

            # Extract leadership if not already set
            if not company.key_contact_name and soup:
                self._extract_linkedin_leadership(company, text, soup)

            # Extract year founded if not already set
            if not company.year_founded:
                year_match = re.search(r"founded[:\s]+(\d{4})", text_lower)
                if year_match:
                    year = int(year_match.group(1))
                    if 1950 <= year <= 2025:
                        company.year_founded = year
                        logger.debug(f"LinkedIn: {company.name} founded in {year}")

            # Skip employee count if already have data from LinkedIn
            if company.employee_count_source == "linkedin":
                return

            # Pattern 1: "X-Y employees" (range format)
            range_match = re.search(
                r"(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)\s+employees?",
                text_lower
            )
            if range_match:
                low = int(range_match.group(1).replace(',', ''))
                high = int(range_match.group(2).replace(',', ''))
                # Store as range
                company.employee_count_min = low
                company.employee_count_max = high
                company.employee_count_source = "linkedin"
                if "linkedin" not in company.data_sources:
                    company.data_sources.append("linkedin")
                logger.debug(f"LinkedIn: {company.name} has {low}-{high} employees")
                return

            # Pattern 2: "X employees" (exact count)
            exact_match = re.search(
                r"(\d{1,3}(?:,\d{3})*)\s+employees?\s+(?:on\s+)?(?:linkedin)?",
                text_lower
            )
            if exact_match:
                count = int(exact_match.group(1).replace(',', ''))
                if 1 <= count <= 100000:
                    company.employee_count = count
                    company.employee_count_source = "linkedin"
                    if "linkedin" not in company.data_sources:
                        company.data_sources.append("linkedin")
                    logger.debug(f"LinkedIn: {company.name} has {count} employees")
                    return

            # Pattern 3: LinkedIn size categories (fallback)
            size_categories = {
                "1-10": (1, 10),
                "11-50": (11, 50),
                "51-200": (51, 200),
                "201-500": (201, 500),
                "501-1000": (501, 1000),
                "1001-5000": (1001, 5000),
                "5001-10000": (5001, 10000),
                "10000+": (10000, None),  # Open-ended range
            }

            for category, (min_val, max_val) in size_categories.items():
                if category.lower() in text_lower:
                    company.employee_count_min = min_val
                    company.employee_count_max = max_val
                    company.employee_count_source = "linkedin_category"
                    if "linkedin" not in company.data_sources:
                        company.data_sources.append("linkedin")
                    logger.debug(f"LinkedIn: {company.name} category {category} ({min_val}-{max_val or '+'} employees)")
                    return

        except Exception as e:
            logger.debug(f"LinkedIn parsing error for {company.name}: {e}")

    def _extract_linkedin_leadership(self, company: Company, text: str, soup: BeautifulSoup):
        """Extract leadership information from LinkedIn company page."""
        # LinkedIn shows leadership in "People" section with patterns like:
        # "Jane Doe - CEO at Company"
        # "John Smith, Founder & CEO"
        # Look for common executive titles
        leadership_titles = [
            "ceo", "chief executive", "president", "founder", "co-founder",
            "managing partner", "principal", "owner", "managing director"
        ]

        # Pattern 1: "Name - Title at Company" or "Name, Title"
        for title in leadership_titles:
            # Try to find name followed by title
            pattern = rf"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-,]\s*(?:\w+\s+)*{title}"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Validate it looks like a real name (2-4 words, proper capitalization)
                name_parts = name.split()
                if 2 <= len(name_parts) <= 4 and all(p[0].isupper() for p in name_parts):
                    company.key_contact_name = name
                    company.key_contact_title = title.upper() if title in ["ceo"] else title.title()
                    logger.debug(f"LinkedIn: Found {company.key_contact_title} - {name}")
                    return
