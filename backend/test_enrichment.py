#!/usr/bin/env python3
"""
Test website enrichment on individual companies or batches.

Usage:
    # Test single company by URL
    python test_enrichment.py --url https://taxpointadvisors.com

    # Test top N companies from database
    python test_enrichment.py --batch 10

    # Test specific company by name
    python test_enrichment.py --name "Tax Point Advisors"
"""

import argparse
import logging
import sys
from models import Company, Database
from enrichers.website import WebsiteEnricher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_single_url(url: str):
    """Test enrichment on a single URL."""
    logger.info(f"Testing enrichment for: {url}")

    # Create mock company
    company = Company(
        name="Test Company",
        website=url,
        services=[],
        data_sources=[]
    )

    # Enrich
    enricher = WebsiteEnricher()
    enriched = enricher.enrich(company)

    # Display results
    print("\n" + "="*60)
    print(f"ENRICHMENT RESULTS FOR: {url}")
    print("="*60)
    print(f"Name: {enriched.name}")
    print(f"LinkedIn URL: {enriched.linkedin_url or 'NOT FOUND'}")
    print(f"Revenue: ${enriched.estimated_revenue:,} ({enriched.revenue_source})" if enriched.estimated_revenue else "Revenue: NOT FOUND")
    print(f"Employees: {enriched.employee_count} ({enriched.employee_count_source})" if enriched.employee_count else "Employees: NOT FOUND")
    if enriched.employee_count_min and enriched.employee_count_max:
        print(f"  Employee Range: {enriched.employee_count_min}-{enriched.employee_count_max}")
    print(f"Contact: {enriched.key_contact_name} - {enriched.key_contact_title}" if enriched.key_contact_name else "Contact: NOT FOUND")
    print(f"Email: {enriched.key_contact_email}" if enriched.key_contact_email else "Email: NOT FOUND")
    print(f"Ownership: {enriched.ownership_type}" if enriched.ownership_type else "Ownership: NOT FOUND")
    print(f"Description: {enriched.description[:100]}..." if enriched.description else "Description: NOT FOUND")
    print("="*60 + "\n")


def test_batch(count: int = 10):
    """Test enrichment on top N companies from database."""
    logger.info(f"Testing enrichment on top {count} companies")

    db = Database()

    # Get all companies with websites
    all_companies = db.get_all_companies()
    companies_with_websites = [c for c in all_companies if c.website]

    # Sort by confidence score and take top N
    companies_with_websites.sort(key=lambda c: c.confidence_score or 0, reverse=True)
    companies = companies_with_websites[:count]

    if not companies:
        print("No companies found in database")
        return

    enricher = WebsiteEnricher()

    # Track metrics
    metrics = {
        "total": len(companies),
        "linkedin_found": 0,
        "revenue_found": 0,
        "employees_found": 0,
        "contact_found": 0,
    }

    print(f"\nTesting {len(companies)} companies...\n")

    for i, company in enumerate(companies, 1):
        logger.info(f"[{i}/{len(companies)}] Testing {company.name}")

        # Store before state
        before = {
            "linkedin": company.linkedin_url,
            "revenue": company.estimated_revenue,
            "employees": company.employee_count,
            "contact": company.key_contact_name,
        }

        # Enrich
        try:
            enriched = enricher.enrich(company)

            # Track what changed
            if enriched.linkedin_url and not before["linkedin"]:
                metrics["linkedin_found"] += 1
            if enriched.estimated_revenue and not before["revenue"]:
                metrics["revenue_found"] += 1
            if enriched.employee_count and not before["employees"]:
                metrics["employees_found"] += 1
            if enriched.key_contact_name and not before["contact"]:
                metrics["contact_found"] += 1

            # Display result
            print(f"{i}. {company.name}")
            if enriched.linkedin_url and not before["linkedin"]:
                print(f"   ✓ LinkedIn: {enriched.linkedin_url}")
            if enriched.estimated_revenue and not before["revenue"]:
                print(f"   ✓ Revenue: ${enriched.estimated_revenue:,}")
            if enriched.employee_count and not before["employees"]:
                print(f"   ✓ Employees: {enriched.employee_count}")
            if enriched.key_contact_name and not before["contact"]:
                print(f"   ✓ Contact: {enriched.key_contact_name}")

            if not any([
                enriched.linkedin_url and not before["linkedin"],
                enriched.estimated_revenue and not before["revenue"],
                enriched.employee_count and not before["employees"],
                enriched.key_contact_name and not before["contact"],
            ]):
                print(f"   ✗ No new data extracted")

        except Exception as e:
            logger.error(f"Error enriching {company.name}: {e}")
            print(f"   ✗ ERROR: {e}")

    # Display summary
    print("\n" + "="*60)
    print("BATCH ENRICHMENT SUMMARY")
    print("="*60)
    print(f"Companies tested: {metrics['total']}")
    print(f"LinkedIn URLs found: {metrics['linkedin_found']} ({metrics['linkedin_found']/metrics['total']*100:.1f}%)")
    print(f"Revenue extracted: {metrics['revenue_found']} ({metrics['revenue_found']/metrics['total']*100:.1f}%)")
    print(f"Employees extracted: {metrics['employees_found']} ({metrics['employees_found']/metrics['total']*100:.1f}%)")
    print(f"Contacts extracted: {metrics['contact_found']} ({metrics['contact_found']/metrics['total']*100:.1f}%)")
    print("="*60 + "\n")


def test_by_name(name: str):
    """Test enrichment on a specific company by name."""
    logger.info(f"Finding company: {name}")

    db = Database()
    all_companies = db.get_all_companies()

    # Find company by name (case-insensitive partial match)
    company = None
    for c in all_companies:
        if name.lower() in c.name.lower():
            company = c
            break

    if not company:
        print(f"Company not found: {name}")
        return

    if not company.website:
        print(f"Company has no website: {company.name}")
        return

    logger.info(f"Testing {company.name} - {company.website}")

    # Store before state
    print(f"\nBEFORE enrichment:")
    print(f"  LinkedIn: {company.linkedin_url or 'None'}")
    print(f"  Revenue: ${company.estimated_revenue:,}" if company.estimated_revenue else "  Revenue: None")
    print(f"  Employees: {company.employee_count}" if company.employee_count else "  Employees: None")
    print(f"  Contact: {company.key_contact_name}" if company.key_contact_name else "  Contact: None")

    # Enrich
    enricher = WebsiteEnricher()
    enriched = enricher.enrich(company)

    # Display after state
    print(f"\nAFTER enrichment:")
    print(f"  LinkedIn: {enriched.linkedin_url or 'None'}")
    print(f"  Revenue: ${enriched.estimated_revenue:,} ({enriched.revenue_source})" if enriched.estimated_revenue else "  Revenue: None")
    print(f"  Employees: {enriched.employee_count} ({enriched.employee_count_source})" if enriched.employee_count else "  Employees: None")
    print(f"  Contact: {enriched.key_contact_name} - {enriched.key_contact_title}" if enriched.key_contact_name else "  Contact: None")
    print(f"  Email: {enriched.key_contact_email}" if enriched.key_contact_email else "  Email: None")
    print()


def main():
    parser = argparse.ArgumentParser(description="Test website enrichment")
    parser.add_argument("--url", help="Test single company by URL")
    parser.add_argument("--batch", type=int, help="Test top N companies from database")
    parser.add_argument("--name", help="Test specific company by name")

    args = parser.parse_args()

    if args.url:
        test_single_url(args.url)
    elif args.batch:
        test_batch(args.batch)
    elif args.name:
        test_by_name(args.name)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
