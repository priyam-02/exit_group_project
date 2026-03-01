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

        logger.info(f"Enriching {company.name} from {company.website}")

        # Track what we extract (for metrics)
        extracted = {
            "linkedin_url": False,
            "revenue": False,
            "employees": False,
            "contact": False,
        }

        base_url = company.website.rstrip("/")
        all_text = ""

        # Phase 1: Extract LinkedIn URL first (before text cleanup removes footers)
        if not company.linkedin_url:
            linkedin_url = self._find_linkedin_url_across_site(base_url)
            if linkedin_url:
                company.linkedin_url = linkedin_url
                extracted["linkedin_url"] = True
                logger.info(f"✓ LinkedIn URL: {linkedin_url}")

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

        # Try LinkedIn enrichment if we have a LinkedIn URL
        # (LinkedIn provides reliable employee count ranges)
        if company.linkedin_url:
            try:
                self._enrich_from_linkedin(company)
            except Exception as e:
                logger.debug(f"LinkedIn enrichment failed for {company.name}: {e}")

        # Convert employee ranges to midpoint estimates (authentic data transformation)
        self._convert_employee_ranges(company)

        # Track what was extracted
        if company.estimated_revenue and not extracted["revenue"]:
            extracted["revenue"] = True
        if company.employee_count and not extracted["employees"]:
            extracted["employees"] = True
        if company.key_contact_name or company.key_contact_email:
            extracted["contact"] = True

        # Log summary
        extracted_fields = [k for k, v in extracted.items() if v]
        if extracted_fields:
            logger.info(f"✓ {company.name}: Extracted {', '.join(extracted_fields)}")
            if company.estimated_revenue:
                logger.debug(f"  Revenue: ${company.estimated_revenue:,} ({company.revenue_source or 'unknown'})")
            if company.employee_count:
                logger.debug(f"  Employees: {company.employee_count} ({company.employee_count_source or 'unknown'})")
            if company.key_contact_name:
                logger.debug(f"  Contact: {company.key_contact_name} - {company.key_contact_title or 'Unknown Title'}")
        else:
            logger.debug(f"✗ {company.name}: No new data extracted")

        return company

    def _fetch_page(self, url: str) -> tuple[Optional[str], Optional[BeautifulSoup]]:
        """Fetch a page and return (text_content, soup) or (None, None)."""
        try:
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code != 200:
                return None, None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract footer text BEFORE removing (often contains employee counts)
            footer_text = ""
            for footer in soup.find_all(["footer", "div"], class_=lambda x: x and "footer" in str(x).lower()):
                footer_text += " " + footer.get_text(separator=" ", strip=True)

            # Remove script and style elements (but keep nav/header/footer for now)
            for element in soup(["script", "style"]):
                element.decompose()

            # Get main text
            text = soup.get_text(separator=" ", strip=True)
            # Clean up whitespace
            text = re.sub(r"\s+", " ", text)

            # Append footer text (it might have employee counts like "© 2024 - 50+ professionals")
            if footer_text:
                text += " " + footer_text

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

        # Pattern 1: Founder narrative (About page style)
        founder_narrative_patterns = [
            r"founded\s+(?:in\s+\d{4}\s+)?by\s+([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)",
            r"([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)\s+founded\s+(?:the\s+)?(?:company|firm)",
            r"under\s+the\s+leadership\s+of\s+([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)",
            r"(?:CEO|President|Founder)[:,]?\s+([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)",
        ]

        for pattern in founder_narrative_patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                # Validate it's a real name (2-4 words)
                name_parts = name.split()
                if 2 <= len(name_parts) <= 4:
                    company.key_contact_name = name
                    company.key_contact_title = "Founder" if "found" in pattern else "CEO"
                    logger.debug(f"Found {company.key_contact_title} from narrative: {name}")
                    return

        # Pattern 2: Look for leadership titles with names
        title_patterns = [
            r"(?:CEO|President|Founder|Managing\s+Partner|Principal|Owner|Managing\s+Director)",
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
                logger.debug(f"Found contact: {company.key_contact_name} - {company.key_contact_title}")
                return

            # Reverse: Title - Name or Title: Name
            match = re.search(
                rf"{pattern}\s*[,\-–:]\s*([A-Z][a-z]+\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]+)",
                text
            )
            if match:
                company.key_contact_name = match.group(1).strip()
                company.key_contact_title = re.search(pattern, match.group(0)).group(0)
                logger.debug(f"Found contact: {company.key_contact_name} - {company.key_contact_title}")
                return

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

        # Email - search all pages, prefer personal emails over generic
        if not company.key_contact_email:
            emails = self._extract_emails_from_page(text, soup)
            if emails:
                company.key_contact_email = emails[0]  # Already sorted by preference

        # Address for city/state if missing
        if not company.state:
            from scrapers.base import BaseScraper
            state = BaseScraper.extract_state_from_address(text)
            if state:
                company.state = state
            city = BaseScraper.extract_city_from_address(text)
            if city:
                company.city = city

        # Extract from schema.org structured data
        if soup:
            self._extract_from_structured_data(company, soup)

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
                logger.debug(f"Extracted revenue: ${company.estimated_revenue:,}")

        # Employee count estimation
        if not company.employee_count:
            company.employee_count = self._estimate_employees(all_text)
            if company.employee_count:
                company.employee_count_source = "website_text_inference"
                logger.debug(f"Extracted employees: {company.employee_count}")

    @staticmethod
    def _estimate_revenue(text: str) -> Optional[int]:
        """
        Try to estimate revenue from website text.
        Looks for patterns like "$X million", "Xm in revenue", etc.
        """
        text_lower = text.lower()

        # Pattern 1: Revenue ranges (e.g., "$5-10M in revenue") - take midpoint
        range_patterns = [
            r"\$(\d+(?:\.\d+)?)\s*-\s*\$?(\d+(?:\.\d+)?)\s*(?:m|million)\s*(?:in\s+)?(?:revenue|sales|annual|turnover)",
            r"revenue\s+(?:of\s+)?\$(\d+(?:\.\d+)?)\s*-\s*\$?(\d+(?:\.\d+)?)\s*(?:m|million)",
            r"(?:generates?|sales)\s+\$(\d+(?:\.\d+)?)\s*-\s*\$?(\d+(?:\.\d+)?)\s*(?:m|million)",
        ]
        for pattern in range_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    low = float(match.group(1))
                    high = float(match.group(2))
                    if 1 <= low <= high <= 500:
                        # Take midpoint of range
                        midpoint = (low + high) / 2
                        return int(midpoint * 1_000_000)
                except (ValueError, IndexError):
                    continue

        # Pattern 2: Direct revenue mentions (expanded patterns)
        direct_patterns = [
            # Standard formats
            r"\$(\d+(?:\.\d+)?)\s*(?:m|million|mn)\s*(?:in\s+)?(?:revenue|sales|billing|annual\s+revenue|turnover)",
            r"revenue\s*(?:of\s+|exceeding\s+|over\s+|:\s*)?\$?(\d+(?:\.\d+)?)\s*(?:m|million|mn)",
            r"(?:annual\s+)?(?:revenue|sales|turnover)\s*(?:of\s+|is\s+|:\s*)?\$?(\d+(?:\.\d+)?)\s*(?:m|million|mn)",
            r"\$(\d+(?:\.\d+)?)\s*(?:m|million|mn)\s+(?:annual\s+)?(?:revenue|sales|firm|business)",
            r"generates?\s+(?:over\s+|approximately\s+)?\$?(\d+(?:\.\d+)?)\s*(?:m|million|mn)\s*(?:in\s+)?(?:revenue|annually|per\s+year)?",
            # Without dollar sign
            r"(?:revenue|sales|turnover)\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:m|million)\s*(?:dollars?)?",
            r"(\d+(?:\.\d+)?)\s*(?:m|million)\s+(?:in\s+)?(?:annual\s+)?(?:revenue|sales)",
            # With "approximately", "over", "exceeding"
            r"(?:approximately|about|around|over|exceeding)\s+\$?(\d+(?:\.\d+)?)\s*(?:m|million)\s*(?:in\s+)?(?:revenue|sales)",
        ]
        for pattern in direct_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    amount = float(match.group(1))
                    if 1 <= amount <= 500:  # Reasonable range in millions
                        return int(amount * 1_000_000)
                except ValueError:
                    continue

        # Pattern 3: Billion-scale revenues
        billion_patterns = [
            r"\$(\d+(?:\.\d+)?)\s*(?:b|billion)\s*(?:in\s+)?(?:revenue|sales|annual|turnover)",
            r"revenue\s*(?:of\s+)?\$?(\d+(?:\.\d+)?)\s*(?:b|billion)",
            r"(\d+(?:\.\d+)?)\s*(?:b|billion)\s+(?:in\s+)?(?:annual\s+)?revenue",
        ]
        for pattern in billion_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    amount = float(match.group(1))
                    if 0.1 <= amount <= 100:  # Reasonable range in billions
                        return int(amount * 1_000_000_000)
                except ValueError:
                    continue

        # Pattern 4: Tax credit amounts processed (rough revenue indicator)
        credit_patterns = [
            r"\$(\d+(?:\.\d+)?)\s*(?:b|billion)\s*(?:in\s+)?(?:credit|tax\s+saving|tax\s+benefit|credits?\s+processed)",
            r"(?:secured|identified|generated|claimed|processed)\s+(?:over\s+)?\$(\d+(?:\.\d+)?)\s*(?:b|billion)\s*(?:in\s+)?(?:credits?|tax\s+benefits?)",
            r"(?:secured|identified|generated|claimed)\s+(?:over\s+)?\$(\d+(?:\.\d+)?)\s*(?:m|million)\s*(?:in\s+)?(?:credits?|tax\s+savings?)",
        ]
        for pattern in credit_patterns:
            match = re.search(pattern, text_lower)
            if match:
                # If they process billions in credits, they're likely $50M+ revenue firm
                # If they process $100M+ in credits, they're likely $10M+ revenue
                try:
                    amount = float(match.group(1))
                    # Check if it's billions or millions
                    context = text_lower[max(0, match.start()-20):min(len(text_lower), match.end()+20)]
                    if "billion" in context or " b " in context:
                        return 50_000_000  # Conservative estimate for billion-dollar processors
                    elif amount > 100:  # $100M+ in credits
                        return 10_000_000  # Likely $10M+ revenue firm
                    elif amount > 20:  # $20M+ in credits
                        return 5_000_000  # Likely $5M+ revenue firm
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

        # Pattern 1: Employee ranges (e.g., "10-20 employees") - take midpoint
        range_patterns = [
            r"(\d+)\s*-\s*(\d+)\s+(?:employees|people|staff|professionals|team\s+members)",
            r"(?:team|staff)\s+(?:of\s+)?(\d+)\s*-\s*(\d+)",
            r"(\d+)\s*-\s*(\d+)\s+(?:person|member)\s+(?:team|firm|company)",
        ]
        for pattern in range_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    low = int(match.group(1))
                    high = int(match.group(2))
                    if 1 <= low <= high <= 10000:
                        # Take midpoint of range
                        return (low + high) // 2
                except (ValueError, IndexError):
                    continue

        # Pattern 2: Exact counts with various phrasings
        exact_patterns = [
            r"(\d+)\+?\s*(?:employees|team\s+members|professionals|consultants|staff|people)",
            r"team\s+of\s+(\d+)\+?(?:\s+(?:professionals|consultants|experts))?",
            r"(?:over|more\s+than|approximately|about)\s+(\d+)\+?\s+(?:employees|people|professionals|staff)",
            r"(\d+)\s*(?:\+|plus)\s*(?:employees|people|professionals|staff|team\s+members)",
            r"staff\s+of\s+(\d+)\+?",
            r"(\d+)\s+(?:experienced|dedicated|skilled)\s+(?:professionals|consultants|tax\s+experts|cpas?|accountants?)",
            r"(?:firm|company|practice)\s+of\s+(\d+)\+?\s+(?:professionals|people|employees)",
            r"(\d+)\s+(?:member|person)\s+(?:team|firm|practice)",
        ]
        for pattern in exact_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    count = int(match.group(1))
                    if 2 <= count <= 10000:  # Reasonable range
                        # If pattern has "+", add 20% to account for "50+" meaning ~60
                        if "+" in match.group(0) or "plus" in match.group(0) or "over" in match.group(0) or "more than" in match.group(0):
                            count = int(count * 1.2)
                        return count
                except ValueError:
                    continue

        return None

    def _find_linkedin_url_across_site(self, base_url: str) -> Optional[str]:
        """
        Search for LinkedIn URL across multiple pages of the website.
        Checks homepage, about page, and contact page for LinkedIn links.
        """
        # Pages most likely to have LinkedIn links (footer/social icons)
        search_paths = ["", "/about", "/about-us", "/contact", "/contact-us"]

        for path in search_paths:
            try:
                url = f"{base_url}{path}"
                # Fetch with raw HTML (don't remove footer/header)
                resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    linkedin_url = self._extract_linkedin_url(soup)
                    if linkedin_url:
                        logger.debug(f"Found LinkedIn URL on {url}")
                        return linkedin_url
            except Exception as e:
                logger.debug(f"Error searching for LinkedIn on {url}: {e}")
                continue

        return None

    @staticmethod
    def _extract_linkedin_url(soup: BeautifulSoup) -> Optional[str]:
        """Extract LinkedIn company page URL from website HTML."""
        if not soup:
            return None

        # Look for LinkedIn links in the page
        for link in soup.find_all("a", href=True):
            href = link["href"]

            # Check for company page
            if "linkedin.com/company/" in href:
                # Clean up the URL (remove query params, tracking codes)
                href = href.split("?")[0].split("#")[0]
                return href.rstrip("/")

            # Check for personal profiles (CEO/founder LinkedIn)
            # We'll use this as fallback to find company
            if "linkedin.com/in/" in href or "linkedin.com/pub/" in href:
                # Clean up the URL
                href = href.split("?")[0].split("#")[0]
                # Only use as last resort (prefer company pages)
                continue

        # Fallback: look for personal profiles if no company page found
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "linkedin.com/in/" in href or "linkedin.com/pub/" in href:
                # Check if it's a founder/CEO profile (often linked prominently)
                link_text = link.get_text(strip=True).lower()
                if any(title in link_text for title in ["ceo", "founder", "president", "owner"]):
                    href = href.split("?")[0].split("#")[0]
                    logger.debug(f"Found LinkedIn profile (founder/CEO): {href}")
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

    def _extract_emails_from_page(self, text: str, soup: BeautifulSoup) -> list[str]:
        """
        Extract emails from page text, prioritizing personal emails over generic ones.
        Returns list of emails sorted by preference (personal first).
        """
        # Find all email addresses
        email_pattern = r"[\w.+-]+@[\w-]+\.[\w.]+"
        all_emails = re.findall(email_pattern, text.lower())

        if not all_emails:
            return []

        # Filter and score emails
        generic_prefixes = [
            "info@", "contact@", "admin@", "support@", "noreply@", "no-reply@",
            "sales@", "marketing@", "hr@", "jobs@", "careers@", "help@",
            "webmaster@", "hello@", "general@", "team@", "office@"
        ]

        personal_indicators = [
            # First name patterns
            r"^[a-z]+@",  # john@
            r"^[a-z]+\.[a-z]+@",  # john.smith@
            r"^[a-z][a-z]+@",  # jsmith@
        ]

        scored_emails = []
        for email in set(all_emails):  # Remove duplicates
            # Skip obvious generic emails
            if any(email.startswith(prefix) for prefix in generic_prefixes):
                continue

            # Score email (higher = more likely to be personal)
            score = 0
            for pattern in personal_indicators:
                if re.match(pattern, email):
                    score += 1

            # Prefer emails with names in them
            if re.match(r"^[a-z]+\.[a-z]+@", email):
                score += 2  # firstname.lastname@ is highly preferred

            scored_emails.append((score, email))

        # Sort by score (highest first) and return emails
        scored_emails.sort(reverse=True, key=lambda x: x[0])
        return [email for score, email in scored_emails if score > 0] or [scored_emails[0][1]] if scored_emails else []

    @staticmethod
    def _convert_employee_ranges(company: Company):
        """
        Convert employee count ranges to midpoint estimates.
        This is authentic data transformation, not synthetic estimation.
        E.g., "11-50 employees" → 30 employees
        """
        # Only convert if we have a range but no exact count
        if company.employee_count_min and company.employee_count_max and not company.employee_count:
            midpoint = (company.employee_count_min + company.employee_count_max) // 2
            company.employee_count = midpoint
            company.employee_count_source = "range_midpoint"
            logger.debug(f"Converted range {company.employee_count_min}-{company.employee_count_max} to midpoint: {midpoint}")

    def _extract_from_structured_data(self, company: Company, soup: BeautifulSoup):
        """Extract data from schema.org structured data (JSON-LD)."""
        if not soup:
            return

        # Look for JSON-LD schema.org markup
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)

                # Handle both single objects and arrays
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # Organization schema
                    if item.get("@type") in ["Organization", "LocalBusiness", "ProfessionalService"]:
                        # Founder name
                        if not company.key_contact_name and "founder" in item:
                            founders = item["founder"]
                            if isinstance(founders, dict) and "name" in founders:
                                company.key_contact_name = founders["name"]
                                company.key_contact_title = "Founder"
                                logger.debug(f"Schema.org: Found founder {company.key_contact_name}")
                            elif isinstance(founders, list) and len(founders) > 0 and "name" in founders[0]:
                                company.key_contact_name = founders[0]["name"]
                                company.key_contact_title = "Founder"
                                logger.debug(f"Schema.org: Found founder {company.key_contact_name}")

                        # Employee count
                        if not company.employee_count and "numberOfEmployees" in item:
                            try:
                                count = int(item["numberOfEmployees"])
                                if 1 <= count <= 10000:
                                    company.employee_count = count
                                    company.employee_count_source = "schema_org"
                                    logger.debug(f"Schema.org: Found {count} employees")
                            except (ValueError, TypeError):
                                pass

                        # Email
                        if not company.key_contact_email and "email" in item:
                            email = item["email"].lower()
                            if not any(prefix in email for prefix in ["info@", "admin@", "support@"]):
                                company.key_contact_email = email
                                logger.debug(f"Schema.org: Found email {email}")

            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.debug(f"Error parsing schema.org data: {e}")
                continue

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
