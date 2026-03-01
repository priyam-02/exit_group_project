"""
Configuration for the M&A Thesis Research Pipeline.

All thesis parameters, API keys, and pipeline settings are centralized here.
This makes it easy to swap in a different thesis later (bonus feature).
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class ThesisConfig:
    """
    Defines the M&A investment thesis criteria.
    Designed to be swappable for the "custom thesis" bonus feature.
    """
    name: str = "Specialty Tax Advisory Services"
    description: str = (
        "Find privately held specialty tax firms across the Continental US "
        "that provide one or more of: R&D Tax Credits, Cost Segregation, "
        "Work Opportunity Tax Credits (WOTC), Sales & Use Tax consulting."
    )

    # Target services (used for search queries and classification)
    target_services: list = field(default_factory=lambda: [
        "R&D Tax Credits",
        "Cost Segregation",
        "Work Opportunity Tax Credits",  # WOTC
        "Sales & Use Tax",
    ])

    # Search query templates — these get expanded with geographic modifiers
    search_queries: list = field(default_factory=lambda: [
        "R&D tax credit consulting firm",
        "cost segregation study company",
        "cost segregation consulting",
        "WOTC tax credit services",
        "work opportunity tax credit consulting",
        "sales and use tax consulting firm",
        "specialty tax advisory firm",
        "R&D tax credit company",
        "engineering-based tax study firm",
        "sales tax consulting services",
    ])

    # Size thresholds
    min_revenue: int = 3_000_000       # $3M
    min_employees: int = 5

    # Geography
    geography: str = "Continental United States"

    # Ownership filters
    ownership_filter: str = "privately held"
    exclude_union: bool = True

    # Exclusions
    excluded_primary_services: list = field(default_factory=lambda: [
        "Employee Retention Credit",
        "ERC",
        "Property Tax",              # Exclusively property tax
    ])

    # States to search (Continental US — excludes AK, HI, territories)
    target_states: list = field(default_factory=lambda: [
        "AL", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
        "DC",
    ])

    # Major metro areas for focused searching (higher density of tax firms)
    priority_metros: list = field(default_factory=lambda: [
        "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
        "Phoenix, AZ", "Philadelphia, PA", "San Antonio, TX", "San Diego, CA",
        "Dallas, TX", "Austin, TX", "San Jose, CA", "Jacksonville, FL",
        "San Francisco, CA", "Charlotte, NC", "Indianapolis, IN",
        "Seattle, WA", "Denver, CO", "Nashville, TN", "Atlanta, GA",
        "Boston, MA", "Miami, FL", "Minneapolis, MN", "Tampa, FL",
        "Portland, OR", "St. Louis, MO", "Pittsburgh, PA", "Cincinnati, OH",
        "Kansas City, MO", "Columbus, OH", "Cleveland, OH", "Salt Lake City, UT",
        "Detroit, MI", "Milwaukee, WI", "Raleigh, NC", "Richmond, VA",
    ])


@dataclass
class APIConfig:
    """API keys and endpoints. Loaded from environment variables."""

    # Google Places API
    google_places_api_key: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
    google_places_base_url: str = "https://maps.googleapis.com/maps/api/place"

    # SerpAPI (for Google search results)
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")
    serpapi_base_url: str = "https://serpapi.com/search"

    # OpenAI / Claude API for classification (optional enrichment)
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")  # or "openai"


@dataclass
class PipelineConfig:
    """Pipeline behavior settings."""

    # Database
    db_path: str = os.getenv("DB_PATH", "data/companies.db")

    # Rate limiting (requests per second)
    rate_limit_google: float = 0.5      # 2 sec between Google API calls
    rate_limit_scraping: float = 1.0    # 1 sec between web scrape requests
    rate_limit_serp: float = 0.5        # 2 sec between SerpAPI calls

    # Deduplication
    dedup_similarity_threshold: float = 0.85  # Fuzzy match threshold for names

    # Pipeline
    max_results_per_query: int = 20     # Max results per search query
    max_total_companies: int = 100      # Hard cap to avoid runaway scraping
    enrichment_timeout: int = 10        # Seconds before timing out on a website

    # Output
    output_dir: str = "data"
    export_csv: bool = True
    export_json: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: str = "data/pipeline.log"


# ── Singleton instances ──────────────────────────────────────────────────────

THESIS = ThesisConfig()
APIS = APIConfig()
PIPELINE = PipelineConfig()
