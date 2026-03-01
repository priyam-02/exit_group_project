#!/usr/bin/env python3
"""
Main entry point for the M&A Research Pipeline.

Usage:
    # Run the full pipeline
    python main.py run

    # Run with specific API keys
    GOOGLE_PLACES_API_KEY=xxx SERPAPI_KEY=yyy python main.py run

    # Export data only (skip scraping)
    python main.py export

    # Show pipeline stats
    python main.py stats
"""

import argparse
import logging
import os
import sys

# Ensure the backend directory is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PIPELINE, APIS
from pipeline import Pipeline
from models import Database


def setup_logging():
    """Configure logging to both console and file."""
    os.makedirs(os.path.dirname(PIPELINE.log_file), exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, PIPELINE.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(PIPELINE.log_file, mode="a"),
        ],
    )


def cmd_run(args):
    """Run the full data pipeline."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Validate API keys
    has_google = bool(APIS.google_places_api_key)
    has_serp = bool(APIS.serpapi_key)

    if not has_google and not has_serp:
        logger.error(
            "⚠️  No API keys configured!\n"
            "  Set at least one of:\n"
            "    GOOGLE_PLACES_API_KEY - Google Places API key\n"
            "    SERPAPI_KEY           - SerpAPI key\n"
            "\n"
            "  Example:\n"
            "    GOOGLE_PLACES_API_KEY=xxx SERPAPI_KEY=yyy python main.py run\n"
        )
        sys.exit(1)

    logger.info("API Keys configured:")
    logger.info(f"  Google Places: {'✓' if has_google else '✗'}")
    logger.info(f"  SerpAPI:       {'✓' if has_serp else '✗'}")

    pipeline = Pipeline()
    pipeline.run()


def cmd_export(args):
    """Export existing database to CSV/JSON."""
    setup_logging()
    logger = logging.getLogger(__name__)

    db = Database()
    count = db.get_company_count()
    logger.info(f"Database has {count} active companies")

    os.makedirs(PIPELINE.output_dir, exist_ok=True)

    csv_path = os.path.join(PIPELINE.output_dir, "companies.csv")
    db.export_to_csv(csv_path)
    logger.info(f"Exported CSV: {csv_path}")

    json_path = os.path.join(PIPELINE.output_dir, "companies.json")
    db.export_to_json(json_path)
    logger.info(f"Exported JSON: {json_path}")


def cmd_stats(args):
    """Show database statistics."""
    setup_logging()
    db = Database()

    total = db.get_company_count(include_excluded=True)
    active = db.get_company_count(include_excluded=False)
    by_state = db.get_companies_by_state()
    by_service = db.get_companies_by_service()

    print(f"\n{'='*50}")
    print(f"DATABASE STATISTICS")
    print(f"{'='*50}")
    print(f"Total companies:  {total}")
    print(f"Active targets:   {active}")
    print(f"Excluded:         {total - active}")

    if by_service:
        print(f"\nBy Service:")
        for service, count in by_service.items():
            print(f"  {service}: {count}")

    if by_state:
        print(f"\nBy State (top 10):")
        for state, count in list(by_state.items())[:10]:
            print(f"  {state}: {count}")

    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(
        description="M&A Thesis Research Pipeline — The Exit Group"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.set_defaults(func=cmd_run)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data to CSV/JSON")
    export_parser.set_defaults(func=cmd_export)

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
