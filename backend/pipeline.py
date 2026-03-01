"""
Pipeline Orchestrator.

This is the main entry point for the data collection pipeline.
It coordinates the scraping, deduplication, enrichment, scoring,
and storage steps in sequence.

Pipeline flow:
  1. Collect → Run all scrapers to gather raw company data
  2. Deduplicate → Merge duplicate records
  3. Enrich → Visit websites to fill in missing fields
  4. Score → Assign confidence scores
  5. Filter → Apply thesis exclusions and size thresholds
  6. Store → Save to database
  7. Export → CSV and JSON exports
"""

import logging
import sys
import os
from datetime import datetime
from dataclasses import asdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import THESIS, PIPELINE
from models import Database, Company
from scrapers.google_places import GooglePlacesScraper
from scrapers.serp_search import SerpScraper
from enrichers.website import WebsiteEnricher
from dedup import deduplicate
from scoring import score_all

logger = logging.getLogger(__name__)


class Pipeline:
    """Main pipeline orchestrator."""

    def __init__(self):
        self.db = Database()
        self.stats = {
            "raw_count": 0,
            "after_dedup": 0,
            "after_enrichment": 0,
            "excluded": 0,
            "final_count": 0,
        }

    def run(self):
        """Execute the full pipeline."""
        run_id = self.db.start_pipeline_run(
            thesis_name=THESIS.name,
            config_snapshot=asdict(THESIS)
        )

        try:
            logger.info("=" * 60)
            logger.info(f"Pipeline started: {THESIS.name}")
            logger.info(f"Target services: {THESIS.target_services}")
            logger.info("=" * 60)

            # ── Step 1: Collect ──────────────────────────────────────────
            logger.info("\n📡 STEP 1: Collecting data from sources...")
            all_companies = []

            # Google Places API - 50 focused queries across top 10 metros
            try:
                google_scraper = GooglePlacesScraper()
                google_results = google_scraper.scrape()
                logger.info(f"  → Google Places: {len(google_results)} companies")
                all_companies.extend(google_results)
            except Exception as e:
                logger.error(f"  ✗ Google Places failed: {e}")

            # Clutch Directory - B2B directory for professional services
            try:
                from scrapers.clutch_directory import ClutchDirectoryScraper
                clutch_scraper = ClutchDirectoryScraper()
                clutch_results = clutch_scraper.scrape()
                logger.info(f"  → Clutch Directory: {len(clutch_results)} companies")
                all_companies.extend(clutch_results)
            except Exception as e:
                logger.error(f"  ✗ Clutch Directory failed: {e}")

            # SerpAPI (Google Search) - Temporarily disabled
            # Using only Google Places for focused, high-quality results
            # try:
            #     serp_scraper = SerpScraper()
            #     serp_results = serp_scraper.scrape()
            #     logger.info(f"  → SerpAPI: {len(serp_results)} companies")
            #     all_companies.extend(serp_results)
            # except Exception as e:
            #     logger.error(f"  ✗ SerpAPI failed: {e}")
            logger.info("  → SerpAPI: Disabled (using Google Places only)")

            self.stats["raw_count"] = len(all_companies)
            logger.info(f"\n  Total raw results: {len(all_companies)}")

            if not all_companies:
                logger.warning("No companies found from any source. Exiting.")
                self.db.finish_pipeline_run(
                    run_id, "completed", 0, 0, 0, "No companies found"
                )
                return

            # ── Step 2: Deduplicate ──────────────────────────────────────
            logger.info("\n🔄 STEP 2: Deduplicating records...")
            companies = deduplicate(all_companies)
            self.stats["after_dedup"] = len(companies)
            logger.info(f"  → After dedup: {len(companies)} companies")

            # ── Step 3: Enrich ───────────────────────────────────────────
            logger.info("\n🔍 STEP 3: Enriching from company websites...")

            # First: Get website URLs from Google Places Details API
            logger.info("  → Fetching website URLs from Google Places...")
            google_scraper_for_details = GooglePlacesScraper()
            for company in companies:
                if company.google_place_id and not company.website:
                    try:
                        google_scraper_for_details.enrich_with_details(company)
                    except Exception as e:
                        logger.debug(f"  Google detail enrichment failed for {company.name}: {e}")

            websites_found = sum(1 for c in companies if c.website)
            logger.info(f"  → Found {websites_found} websites")

            # Then: Visit those websites for deeper enrichment
            logger.info("  → Visiting websites for enrichment...")
            enricher = WebsiteEnricher()
            enriched_count = 0

            for i, company in enumerate(companies):
                if company.website:
                    logger.info(
                        f"  [{i+1}/{len(companies)}] Enriching: {company.name} "
                        f"({company.website})"
                    )
                    try:
                        enricher.enrich(company)
                        enriched_count += 1
                    except Exception as e:
                        logger.debug(f"  Enrichment failed for {company.name}: {e}")

            self.stats["after_enrichment"] = len(companies)
            logger.info(f"  → Enriched {enriched_count} companies from websites")

            # ── Step 4: Score ────────────────────────────────────────────
            logger.info("\n📊 STEP 4: Scoring companies...")
            companies = score_all(companies)
            companies.sort(key=lambda c: c.confidence_score or 0, reverse=True)

            # ── Step 5: Filter ───────────────────────────────────────────
            logger.info("\n🏷️  STEP 5: Applying thesis filters...")
            excluded = [c for c in companies if c.is_excluded]
            active = [c for c in companies if not c.is_excluded]

            # Flag companies that don't have any target services
            for c in active:
                if not c.services:
                    c.needs_review = True

            self.stats["excluded"] = len(excluded)
            self.stats["final_count"] = len(active)

            logger.info(f"  → Excluded: {len(excluded)} companies")
            for c in excluded:
                logger.info(f"    - {c.name}: {c.exclusion_reason}")

            logger.info(f"  → Active targets: {len(active)} companies")

            # ── Step 6: Store ────────────────────────────────────────────
            logger.info("\n💾 STEP 6: Saving to database...")
            # Save all companies (including excluded, flagged as such)
            for company in companies:
                company_id = self.db.upsert_company(company)
                # Log source provenance
                for source in company.data_sources:
                    self.db.log_source(
                        company_id, source,
                        url=company.source_urls[0] if company.source_urls else None
                    )

            logger.info(f"  → Saved {len(companies)} companies to database")

            # ── Step 7: Export ───────────────────────────────────────────
            logger.info("\n📁 STEP 7: Exporting data...")
            os.makedirs(PIPELINE.output_dir, exist_ok=True)

            if PIPELINE.export_csv:
                csv_path = os.path.join(PIPELINE.output_dir, "companies.csv")
                self.db.export_to_csv(csv_path)
                logger.info(f"  → Exported CSV: {csv_path}")

            if PIPELINE.export_json:
                json_path = os.path.join(PIPELINE.output_dir, "companies.json")
                self.db.export_to_json(json_path)
                logger.info(f"  → Exported JSON: {json_path}")

            # ── Done ─────────────────────────────────────────────────────
            self.db.finish_pipeline_run(
                run_id, "completed",
                self.stats["raw_count"],
                self.stats["after_dedup"],
                self.stats["excluded"]
            )

            self._print_summary(active)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.db.finish_pipeline_run(run_id, "failed", 0, 0, 0, str(e))
            raise

    def _print_summary(self, active_companies: list[Company]):
        """Print a summary of pipeline results."""
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Raw results collected:  {self.stats['raw_count']}")
        logger.info(f"  After deduplication:    {self.stats['after_dedup']}")
        logger.info(f"  Excluded:               {self.stats['excluded']}")
        logger.info(f"  Final active targets:   {self.stats['final_count']}")

        # Service distribution
        service_counts = {}
        for c in active_companies:
            for s in c.services:
                service_counts[s] = service_counts.get(s, 0) + 1
        if service_counts:
            logger.info("\n  Service Distribution:")
            for service, count in sorted(service_counts.items(), key=lambda x: -x[1]):
                logger.info(f"    {service}: {count}")

        # State distribution (top 10)
        state_counts = {}
        for c in active_companies:
            if c.state:
                state_counts[c.state] = state_counts.get(c.state, 0) + 1
        if state_counts:
            logger.info("\n  Top States:")
            for state, count in sorted(state_counts.items(), key=lambda x: -x[1])[:10]:
                logger.info(f"    {state}: {count}")

        # Data quality metrics
        with_website = sum(1 for c in active_companies if c.website)
        with_revenue = sum(1 for c in active_companies if c.estimated_revenue)
        with_employees = sum(1 for c in active_companies if c.employee_count)
        with_contact = sum(1 for c in active_companies if c.key_contact_name)
        total = len(active_companies) or 1

        logger.info("\n  Data Coverage:")
        logger.info(f"    With website:   {with_website}/{total} ({with_website/total*100:.0f}%)")
        logger.info(f"    With revenue:   {with_revenue}/{total} ({with_revenue/total*100:.0f}%)")
        logger.info(f"    With employees: {with_employees}/{total} ({with_employees/total*100:.0f}%)")
        logger.info(f"    With contact:   {with_contact}/{total} ({with_contact/total*100:.0f}%)")

        logger.info("\n" + "=" * 60)
        logger.info(f"Database: {PIPELINE.db_path}")
        logger.info(f"CSV Export: {PIPELINE.output_dir}/companies.csv")
        logger.info(f"JSON Export: {PIPELINE.output_dir}/companies.json")
        logger.info("=" * 60)
