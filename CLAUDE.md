# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **M&A Research Pipeline** built in Python that identifies and scores specialty tax advisory firms as potential acquisition targets. The system combines data scraping, deduplication, enrichment, scoring, and provides both a REST API and export capabilities.

## Architecture

### Data Flow Pipeline
The system follows a 7-step ETL pipeline orchestrated by `pipeline.py`:

1. **Collect** → Run scrapers to gather raw company data (Google Places, SerpAPI)
2. **Deduplicate** → Merge duplicates using domain-based and fuzzy name matching
3. **Enrich** → Visit company websites to fill in missing data
4. **Score** → Assign 0-1 confidence scores based on thesis fit
5. **Filter** → Apply thesis exclusion rules and size thresholds
6. **Store** → Save to SQLite database with source provenance
7. **Export** → Generate CSV and JSON outputs

### Key Components

- **config.py**: Centralized configuration using `@dataclass` pattern. Contains:
  - `ThesisConfig`: Investment criteria (services, geography, size thresholds)
  - `APIConfig`: API keys loaded from environment
  - `PipelineConfig`: Pipeline behavior (rate limits, dedup thresholds)

- **models.py**: Database layer with SQLite. Uses:
  - `Company` dataclass: Core data model with ~30 fields
  - `Database` class: Connection pooling, upsert logic, provenance tracking
  - Tables: `companies`, `pipeline_runs`, `source_log`

- **dedup.py**: Two-phase deduplication:
  1. Domain-based (most reliable - same website = same company)
  2. Fuzzy name matching (uses SequenceMatcher, configurable threshold)

- **scoring.py**: Weighted confidence scoring (0-1) based on:
  - Service match (35%): Do they offer target services?
  - Data completeness (20%): How many fields populated?
  - Size fit (15%): Meet revenue/employee thresholds?
  - Source quality (15%): Number of confirming sources
  - No exclusions (15%): Red flags or PE-backed status

- **scrapers/**: Pluggable scraper architecture
  - `base.py`: Abstract base class with rate limiting
  - `google_places.py`: Google Places API integration
  - `serp_search.py`: SerpAPI (Google Search) integration

- **enrichers/website.py**: Website scraping to extract missing data

- **server.py**: Flask REST API serving:
  - `/api/companies` - Filtered company list
  - `/api/kpis` - Dashboard analytics
  - `/api/export/{csv,json}` - Data exports
  - `/api/thesis` - Current thesis configuration

## Development Commands

### Running the Pipeline

```bash
# Run full pipeline with API keys
GOOGLE_PLACES_API_KEY=xxx SERPAPI_KEY=yyy python backend/main.py run

# Run in demo mode (seeds with 30 sample companies)
python backend/main.py run

# Export existing data without re-scraping
python backend/main.py export

# Show database statistics
python backend/main.py stats
```

### Running the API Server

```bash
cd backend
python server.py  # Runs on http://localhost:5001

# Auto-seeds demo data if database is empty
```

### Environment Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Create .env from example
cp backend/.env.example backend/.env
# Edit .env and add your API keys
```

## Database

- **Location**: `data/companies.db` (SQLite)
- **Schema**: See `models.py` line 120-214
- **Upsert behavior**: Merges on `(name, state)` unique constraint, preserves non-null fields
- **WAL mode**: Enabled for better concurrent read/write performance
- **Indexes**: On `state`, `primary_service`, `is_excluded`, `estimated_revenue`, `employee_count`

## Configuration & Thesis Management

The investment thesis is defined in `config.py` as a `ThesisConfig` dataclass. To modify search criteria:

1. Edit `THESIS.target_services` - List of service types to search for
2. Edit `THESIS.search_queries` - Search query templates
3. Edit `THESIS.min_revenue` / `THESIS.min_employees` - Size thresholds
4. Edit `THESIS.excluded_primary_services` - Services to exclude
5. Edit `THESIS.priority_metros` - Geographic focus areas

The system is designed to support multiple theses (bonus feature), though currently only one is active.

## Data Sources & Rate Limiting

All scrapers inherit from `BaseScraper` which provides:
- Rate limiting via `time.sleep()` between requests
- Request timeout handling
- Error logging with graceful degradation

Rate limits are configured in `PIPELINE`:
- Google Places: 0.5 req/sec (2s delay)
- SerpAPI: 0.5 req/sec (2s delay)
- Website scraping: 1.0 req/sec (1s delay)

## Scoring Algorithm

Confidence scores are computed in `scoring.py` using weighted components:

- **Service match** (35%): 1.0 if ≥3 services match, 0.9 if 2 match, 0.7 if 1 match
- **Data completeness** (20%): Ratio of filled fields (11 key fields checked)
- **Size fit** (15%): Revenue/employee thresholds from thesis
- **Source quality** (15%): More sources = higher confidence (3+ sources = 1.0)
- **No exclusions** (15%): Penalty for PE-backed (0.3) or flagged for review (0.5)

Modify weights in `scoring.py` WEIGHTS dict if needed.

## Testing & Demo Mode

The system includes a demo mode that seeds 30 realistic companies when no API keys are configured. This is triggered automatically in:
- `main.py run` command (if no API keys)
- `server.py` startup (if database is empty)

Demo data is defined in `main.py` lines 128-863 (`_seed_demo_data` function).

## Common Development Patterns

### Adding a New Scraper

1. Create `backend/scrapers/new_source.py`
2. Inherit from `BaseScraper` in `scrapers/base.py`
3. Implement `scrape()` method returning `list[Company]`
4. Register in `pipeline.py` around line 68-84
5. Add rate limit config to `PIPELINE` in `config.py`

### Modifying the Data Model

1. Update `Company` dataclass in `models.py`
2. Add field to database schema in `_init_schema()` (line 120)
3. Update CSV export field list in `export_to_csv()` (line 385)
4. Run pipeline to recreate database or manually migrate

### Adding New Scoring Factors

1. Add scoring function in `scoring.py` (e.g., `_score_industry()`)
2. Add weight to `WEIGHTS` dict (must sum to 1.0)
3. Add to `score_company()` scores dict
4. Test with demo data to validate

## API Endpoints

Full list in `server.py`:
- `GET /api/companies?service=X&state=Y&min_revenue=Z&search=Q` - Filtered list
- `GET /api/companies/{id}` - Single company with source details
- `GET /api/kpis` - Dashboard summary statistics
- `GET /api/export/csv` - Download CSV export
- `GET /api/export/json` - Download JSON export
- `GET /api/pipeline/runs` - Recent pipeline run logs
- `GET /api/thesis` - Current thesis configuration
- `GET /api/health` - Health check

All endpoints support CORS for frontend integration.
