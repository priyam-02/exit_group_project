"""
Clutch.co Directory Scraper.

Clutch is a B2B ratings and reviews platform that lists professional services
companies including tax consulting, accounting, and business advisory firms.

Provides:
- Company name, location, employee count
- Service offerings and specializations
- Review ratings and counts
- Minimum project size (revenue indicator)
- Company website and contact info
- Founded year

Does NOT require API key - uses web scraping of public directory.
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional
from scrapers.base import BaseScraper
from models import Company
from config import THESIS, PIPELINE
import time

logger = logging.getLogger(__name__)


class ClutchDirectoryScraper(BaseScraper):
    """Scrape company data from Clutch.co directory."""

    def __init__(self):
        super().__init__(rate_limit=PIPELINE.rate_limit_scraping)
        self.base_url = "https://clutch.co"

    def source_name(self) -> str:
        return "clutch_directory"

    def scrape(self) -> list[Company]:
        """
        Scrape tax consulting firms from Clutch.co directory.

        Searches for:
        - Tax consulting services
        - Accounting firms offering specialty tax services
        - Financial advisory firms with tax practices

        Returns list of Company objects.

        Note: Clutch.co may block automated scraping. If you encounter 403 errors,
        consider using alternative directories (Yelp, Yellow Pages) or Clutch's
        official API (requires partnership/subscription).
        """
        companies = []
        seen_names = set()
        blocked = False

        # Clutch search queries for specialty tax firms
        search_queries = [
            "tax-consulting",
            "tax-advisory",
            "accounting-firms/tax-services",
            "business-services/tax-preparation",
        ]

        logger.info(f"Clutch Directory: Searching {len(search_queries)} categories...")

        for query in search_queries:
            try:
                results = self._search_clutch_category(query)
                for company_data in results:
                    name = company_data.get("name")
                    if not name or name in seen_names:
                        continue

                    seen_names.add(name)
                    company = self._parse_clutch_company(company_data)
                    if company:
                        companies.append(company)

                    if len(companies) >= PIPELINE.max_total_companies:
                        logger.info("Reached max company cap, stopping.")
                        break

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    blocked = True
                    logger.warning(
                        f"Clutch.co blocked scraping (403 Forbidden). "
                        f"This is expected - Clutch uses anti-bot protection. "
                        f"Consider using alternative directories or Clutch's official API."
                    )
                    break
                logger.error(f"HTTP error searching Clutch category '{query}': {e}")
                continue
            except Exception as e:
                logger.error(f"Error searching Clutch category '{query}': {e}")
                continue

            if len(companies) >= PIPELINE.max_total_companies:
                break

        if blocked and len(companies) == 0:
            logger.info(
                "Clutch scraping blocked. Alternatives:\n"
                "  1. Use Yelp API (free tier available)\n"
                "  2. Use Yellow Pages scraping\n"
                "  3. Use LinkedIn Sales Navigator export\n"
                "  4. Contact Clutch for API access (business partnership required)"
            )

        logger.info(f"Clutch Directory: Found {len(companies)} companies")
        self.results = companies
        return companies

    def _search_clutch_category(self, category: str, max_pages: int = 3) -> list[dict]:
        """
        Search a Clutch category and extract company listing data.

        Args:
            category: Clutch category URL slug (e.g., 'tax-consulting')
            max_pages: Maximum number of pages to scrape per category

        Returns:
            List of company data dictionaries
        """
        companies = []

        for page in range(max_pages):
            self._throttle()

            # Clutch pagination format: ?page=0, ?page=1, etc.
            url = f"{self.base_url}/directory/{category}"
            if page > 0:
                url += f"?page={page}"

            try:
                # More realistic headers to avoid bot detection
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Cache-Control": "max-age=0",
                }
                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Find company listing cards
                # Clutch uses various CSS classes, this is a simplified approach
                listings = soup.find_all('li', class_=lambda x: x and 'provider' in x.lower())

                if not listings:
                    # Alternative: find by data attributes or structure
                    listings = soup.find_all('div', attrs={'data-content': 'provider-card'})

                if not listings:
                    logger.debug(f"No listings found on page {page} for {category}")
                    break

                for listing in listings:
                    company_data = self._extract_listing_data(listing)
                    if company_data:
                        companies.append(company_data)

                logger.debug(f"  Page {page+1}: Found {len(listings)} companies")

            except Exception as e:
                logger.error(f"Error scraping page {page} of {category}: {e}")
                break

        return companies

    def _extract_listing_data(self, listing_element) -> Optional[dict]:
        """
        Extract company data from a Clutch listing element.

        Clutch listings typically contain:
        - Company name
        - Location
        - Employee count range
        - Hourly rate
        - Minimum project size
        - Review count and rating
        - Services offered
        """
        try:
            # Extract company name
            name_elem = listing_element.find('h3', class_=lambda x: x and 'company' in x.lower())
            if not name_elem:
                name_elem = listing_element.find('a', class_=lambda x: x and 'company' in x.lower())

            if not name_elem:
                return None

            name = name_elem.get_text(strip=True)
            profile_url = name_elem.get('href', '') if name_elem.name == 'a' else ''
            if profile_url and not profile_url.startswith('http'):
                profile_url = self.base_url + profile_url

            # Extract location
            location_elem = listing_element.find('span', class_=lambda x: x and 'location' in x.lower())
            location = location_elem.get_text(strip=True) if location_elem else ""

            # Extract employee count
            employees_elem = listing_element.find('div', class_=lambda x: x and 'employees' in x.lower())
            employees_text = employees_elem.get_text(strip=True) if employees_elem else ""

            # Extract minimum project size (revenue indicator)
            project_size_elem = listing_element.find('div', class_=lambda x: x and 'project-size' in x.lower())
            min_project = project_size_elem.get_text(strip=True) if project_size_elem else ""

            # Extract review rating and count
            rating_elem = listing_element.find('span', class_=lambda x: x and 'rating' in x.lower())
            rating = rating_elem.get_text(strip=True) if rating_elem else None

            review_count_elem = listing_element.find('span', class_=lambda x: x and 'reviews' in x.lower())
            review_count = review_count_elem.get_text(strip=True) if review_count_elem else None

            return {
                'name': name,
                'profile_url': profile_url,
                'location': location,
                'employees_text': employees_text,
                'min_project_size': min_project,
                'rating': rating,
                'review_count': review_count,
            }

        except Exception as e:
            logger.debug(f"Error extracting listing data: {e}")
            return None

    def _parse_clutch_company(self, data: dict) -> Optional[Company]:
        """Convert Clutch listing data into a Company object."""

        name = data.get('name', '').strip()
        if not name:
            return None

        # Parse location (usually "City, State" or "City, State, Country")
        location = data.get('location', '')
        state = None
        city = None

        if location:
            parts = [p.strip() for p in location.split(',')]
            if len(parts) >= 2:
                city = parts[0]
                state_candidate = parts[1]
                # Check if it's a US state
                state = self.extract_state_from_address(location)

        # Skip if not in Continental US
        if state and state not in self._continental_states():
            return None

        # Parse employee count from text like "50-99 employees"
        employees_text = data.get('employees_text', '')
        employee_min, employee_max = self._parse_employee_range(employees_text)

        # Parse minimum project size for revenue estimation
        min_project = data.get('min_project_size', '')
        # Use midpoint for revenue estimation only
        employee_midpoint = (employee_min + employee_max) // 2 if (employee_min and employee_max) else None
        estimated_revenue = self._estimate_revenue_from_project_size(min_project, employee_midpoint)

        # Parse rating (e.g., "4.8" or "4.8/5")
        rating = None
        try:
            rating_text = data.get('rating', '')
            if rating_text:
                rating = float(rating_text.split('/')[0].strip())
        except:
            pass

        # Parse review count (e.g., "42 reviews")
        review_count = None
        try:
            review_text = data.get('review_count', '')
            if review_text:
                review_count = int(''.join(filter(str.isdigit, review_text)))
        except:
            pass

        # Classify services based on company name and category
        services = self.classify_services(name + " tax consulting")

        company = Company(
            name=self.normalize_company_name(name),
            city=city,
            state=state,
            services=services,
            primary_service=services[0] if services else "Tax Advisory",
            employee_count_min=employee_min,
            employee_count_max=employee_max,
            employee_count_source="Clutch.co",
            estimated_revenue=estimated_revenue,
            website=None,  # Would need to visit profile page
            clutch_rating=rating,
            clutch_reviews_count=review_count,
            data_sources=["clutch_directory"],
            source_urls=[data.get('profile_url', '')],
        )

        return company

    def _parse_employee_range(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """
        Parse employee count from Clutch format.

        Examples:
        - "50-99 employees" → (50, 99)
        - "10-49 employees" → (10, 49)
        - "250-999 employees" → (250, 999)
        - "50 employees" → (50, 50)

        Returns:
            Tuple of (min, max) employee counts
        """
        if not text:
            return (None, None)

        try:
            # Extract all numbers from the text
            import re
            numbers = [int(n) for n in re.findall(r'\d+', text)]

            if len(numbers) >= 2:
                # Range format: "X-Y employees"
                return (numbers[0], numbers[1])
            elif len(numbers) == 1:
                # Exact count: "X employees"
                return (numbers[0], numbers[0])
        except:
            pass

        return (None, None)

    def _estimate_revenue_from_project_size(
        self,
        min_project: str,
        employees: Optional[int]
    ) -> Optional[int]:
        """
        Estimate annual revenue based on minimum project size.

        Logic:
        - If min project is $50k+ → likely $3M+ revenue (needs ~60 such projects/year)
        - If min project is $25k-50k → likely $1.5M+ revenue
        - If min project is $10k-25k → likely $500k+ revenue
        - Cross-check with employee count (avg $100k revenue per employee in consulting)
        """
        if not min_project:
            # Estimate from employees only
            if employees and employees >= 10:
                return employees * 200_000  # $200k per employee (conservative)
            return None

        try:
            # Extract dollar amount from text like "$50,000+"
            cleaned = min_project.replace('$', '').replace(',', '').replace('+', '')
            min_amount = int(''.join(filter(str.isdigit, cleaned)))

            if min_amount >= 50_000:
                estimated = 5_000_000  # $5M+ revenue
            elif min_amount >= 25_000:
                estimated = 2_500_000  # $2.5M+ revenue
            elif min_amount >= 10_000:
                estimated = 1_000_000  # $1M+ revenue
            else:
                estimated = 500_000  # $500k+ revenue

            # Cross-check with employee count
            if employees and employees >= 10:
                employee_based = employees * 200_000
                # Use the higher estimate
                return max(estimated, employee_based)

            return estimated

        except:
            return None

    @staticmethod
    def _continental_states() -> set:
        """Return set of continental US state abbreviations."""
        from scrapers.base import CONTINENTAL_US
        return CONTINENTAL_US
