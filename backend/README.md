# M&A Research Pipeline - Backend

> **Python ETL pipeline and REST API for specialty tax advisory firm discovery**

**Technology:** Python 3.9+, Flask, SQLite, BeautifulSoup
**API:** 8 REST endpoints on port 5001
**Database:** SQLite with WAL mode
**Pipeline:** 7-step ETL process

See [../README.md](../README.md) for project overview.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Pipeline Commands](#pipeline-commands)
5. [API Reference](#api-reference)
6. [Database Schema](#database-schema)
7. [Thesis Configuration](#thesis-configuration)
8. [Data Sources](#data-sources)
9. [Scoring Algorithm](#scoring-algorithm)
10. [Deduplication Logic](#deduplication-logic)
11. [Development Guide](#development-guide)
12. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Configure (optional - works without keys in demo mode)
cp .env.example .env
# Edit .env to add API keys

# Run pipeline
python main.py run

# Start API server
python server.py

# API available at http://localhost:5001
```

---

## Installation

### Prerequisites

- **Python 3.9 or higher**
- **pip** package manager
- **(Optional)** Virtual environment (recommended)
- **(Optional)** Google Places API key
- **(Optional)** SerpAPI key

> **Note:** The system works in demo mode without API keys, seeding 30 sample companies.

### Step-by-Step Setup

#### 1. Create Virtual Environment (Recommended)

```bash
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

#### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `flask==3.1.0` - Web framework for REST API
- `flask-cors==5.0.1` - CORS support for frontend
- `requests==2.32.3` - HTTP library for API calls
- `beautifulsoup4==4.12.3` - HTML parsing for web scraping
- `pandas==2.2.3` - Data export to CSV
- `python-dotenv==1.0.1` - Environment variable management

#### 3. Create Environment File

```bash
cp .env.example .env
```

#### 4. Configure API Keys (Optional for Demo Mode)

Edit `.env`:

```bash
# Google Places API Key
GOOGLE_PLACES_API_KEY=your_google_key_here

# SerpAPI Key
SERPAPI_KEY=your_serpapi_key_here

# Database path
DB_PATH=data/companies.db
```

**Getting API Keys:**
- **Google Places:** [Get key](https://console.cloud.google.com/apis/credentials) - Enable "Places API"
- **SerpAPI:** [Get key](https://serpapi.com/)

#### 5. Verify Installation

```bash
python -c "import flask; import requests; import bs4; print('✓ All dependencies installed')"
```

---

## Configuration

Configuration is managed via two mechanisms:

### 1. Environment Variables (`.env`)

Runtime configuration for API keys and paths:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_PLACES_API_KEY` | No | `""` | Google Places API key |
| `SERPAPI_KEY` | No | `""` | SerpAPI key |
| `DB_PATH` | No | `data/companies.db` | SQLite database path |

**Demo Mode:** If API keys are not provided, the system automatically seeds 30 sample companies for testing.

### 2. Investment Thesis (`config.py`)

Business logic configuration for the M&A thesis:

```python
# backend/config.py

@dataclass
class ThesisConfig:
    # Target service types
    target_services = [
        "R&D Tax Credits",
        "Cost Segregation",
        "Work Opportunity Tax Credits",
        "Sales & Use Tax",
    ]

    # Size thresholds
    min_revenue = 3_000_000  # $3M
    min_employees = 5

    # Geography
    target_states = ["CA", "NY", "TX", "FL", ...]  # Continental US

    # Exclusions
    excluded_primary_services = [
        "Employee Retention Credit",
        "Property Tax",
    ]

    # Priority metros for focused searching
    priority_metros = [
        "New York, NY",
        "Los Angeles, CA",
        "Chicago, IL",
        # ... 30+ metros
    ]
```

**To modify the thesis:** Edit `config.py` and re-run the pipeline.

---

## Pipeline Commands

The pipeline is controlled via `main.py` CLI:

### Run Full Pipeline

```bash
python main.py run
```

**What it does:**
1. Runs all scrapers (Google Places, Clutch, SerpAPI if keys provided)
2. Deduplicates companies (domain-based + fuzzy matching)
3. Enriches missing data (website scraping, LinkedIn, state filings)
4. Scores all companies (confidence scores 0-1)
5. Applies filters (excludes PE-backed, below thresholds)
6. Saves to database
7. Exports to CSV and JSON

**Demo Mode:** If no API keys are configured, seeds 30 sample companies instead.

**Output:**
- Database: `data/companies.db`
- CSV Export: `data/companies_export.csv`
- JSON Export: `data/companies_export.json`
- Logs: `data/pipeline.log`

### Export Only (No Scraping)

```bash
python main.py export
```

Exports existing database to CSV and JSON without running scrapers.

### Database Statistics

```bash
python main.py stats
```

Shows:
- Total companies in database
- Count by state
- Count by service type
- Average confidence score
- PE-backed count
- Excluded count

**Example Output:**
```
=== Database Statistics ===
Total companies: 127
Active (not excluded): 98
Excluded: 29
Average confidence score: 0.73

Top 5 states:
  CA: 24
  NY: 18
  TX: 15
  FL: 12
  IL: 10

Services breakdown:
  R&D Tax Credits: 45
  Cost Segregation: 38
  Sales & Use Tax: 28
  Work Opportunity Tax Credits: 16
```

---

## API Reference

The Flask API serves company data to the frontend and supports programmatic access.

**Base URL:** `http://localhost:5001`
**CORS:** Enabled for all origins

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/companies` | Get filtered company list |
| `GET` | `/api/companies/{id}` | Get single company details |
| `GET` | `/api/kpis` | Get dashboard KPI metrics |
| `GET` | `/api/export/csv` | Download CSV export |
| `GET` | `/api/export/json` | Download JSON export |
| `GET` | `/api/pipeline/runs` | Get pipeline run history |
| `GET` | `/api/thesis` | Get current thesis configuration |
| `GET` | `/api/health` | Health check |

---

### GET /api/companies

Get all companies with optional filtering.

**Query Parameters:**

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `service` | string | Filter by service type | `R&D Credits` |
| `state` | string | Filter by state (2-letter code) | `CA` |
| `min_revenue` | integer | Minimum revenue in dollars | `5000000` |
| `min_employees` | integer | Minimum employee count | `10` |
| `search` | string | Text search (name, description) | `TaxAdvisors` |
| `sort_by` | string | Sort column | `confidence_score` |
| `sort_dir` | string | Sort direction | `DESC` or `ASC` |
| `include_excluded` | boolean | Include excluded companies | `false` |

**Allowed sort_by values:** `name`, `state`, `estimated_revenue`, `employee_count`, `confidence_score`, `primary_service`, `google_rating`

**Example Request:**

```bash
# Get companies in California with R&D Credits service
curl "http://localhost:5001/api/companies?service=R%26D+Credits&state=CA"

# Get companies with minimum $5M revenue, sorted by score
curl "http://localhost:5001/api/companies?min_revenue=5000000&sort_by=confidence_score&sort_dir=DESC"

# Search for "TaxAdvisors" in any field
curl "http://localhost:5001/api/companies?search=TaxAdvisors"
```

**Response:**

```json
{
  "companies": [
    {
      "id": 1,
      "name": "TaxAdvisors LLC",
      "city": "San Francisco",
      "state": "CA",
      "website": "https://taxadvisors.com",
      "services": ["R&D Tax Credits", "Cost Segregation"],
      "primary_service": "R&D Tax Credits",
      "estimated_revenue": 5000000,
      "employee_count": 25,
      "ownership_type": "independent",
      "is_pe_backed": false,
      "confidence_score": 0.87,
      "data_sources": ["google_places", "website", "linkedin"],
      "source_urls": ["https://...", "https://..."],
      "phone": "(415) 555-0123",
      "address": "123 Market St, San Francisco, CA 94102",
      "google_rating": 4.5,
      "description": "Specialty tax consulting for R&D credits...",
      "is_excluded": false,
      "created_at": "2026-03-01T10:30:00",
      "updated_at": "2026-03-01T10:30:00"
    }
  ],
  "total": 42
}
```

---

### GET /api/companies/{id}

Get a single company by ID with full details including source provenance.

**Path Parameters:**
- `id` (integer) - Company ID

**Example Request:**

```bash
curl "http://localhost:5001/api/companies/1"
```

**Response:**

```json
{
  "id": 1,
  "name": "TaxAdvisors LLC",
  "city": "San Francisco",
  "state": "CA",
  "website": "https://taxadvisors.com",
  "services": ["R&D Tax Credits", "Cost Segregation"],
  "primary_service": "R&D Tax Credits",
  "estimated_revenue": 5000000,
  "revenue_source": "website",
  "employee_count": 25,
  "employee_count_source": "linkedin",
  "ownership_type": "independent",
  "is_pe_backed": false,
  "key_contact_name": "John Smith",
  "key_contact_title": "CEO",
  "key_contact_email": "john@taxadvisors.com",
  "confidence_score": 0.87,
  "data_sources": ["google_places", "website", "linkedin"],
  "source_urls": ["https://...", "https://..."],
  "source_details": [
    {
      "id": 1,
      "company_id": 1,
      "source_name": "google_places",
      "field_name": "phone",
      "value": "(415) 555-0123",
      "timestamp": "2026-03-01T10:30:00",
      "source_url": "https://maps.google.com/..."
    },
    {
      "id": 2,
      "company_id": 1,
      "source_name": "website",
      "field_name": "services",
      "value": "[\"R&D Tax Credits\", \"Cost Segregation\"]",
      "timestamp": "2026-03-01T10:31:00",
      "source_url": "https://taxadvisors.com"
    }
  ],
  "is_excluded": false,
  "created_at": "2026-03-01T10:30:00",
  "updated_at": "2026-03-01T10:30:00"
}
```

---

### GET /api/kpis

Get summary KPI data for the dashboard.

**Example Request:**

```bash
curl "http://localhost:5001/api/kpis"
```

**Response:**

```json
{
  "total_companies": 127,
  "active_companies": 98,
  "excluded_companies": 29,
  "avg_confidence_score": 0.73,
  "avg_revenue": 4250000,
  "ownership_identified_pct": 78.5,
  "companies_with_ownership": 99,
  "pe_backed_count": 12,
  "states_covered": 35,
  "top_service": "R&D Tax Credits",
  "service_breakdown": {
    "R&D Tax Credits": 45,
    "Cost Segregation": 38,
    "Sales & Use Tax": 28,
    "Work Opportunity Tax Credits": 16
  },
  "state_breakdown": {
    "CA": 24,
    "NY": 18,
    "TX": 15,
    "FL": 12,
    "IL": 10
  }
}
```

---

### GET /api/export/csv

Download CSV export of all companies.

**Example Request:**

```bash
curl "http://localhost:5001/api/export/csv" -o companies.csv
```

**Response:**
- **Content-Type:** `text/csv`
- **Filename:** `companies_export.csv`

**CSV Columns:**
- id, name, city, state, website, services, primary_service, estimated_revenue, employee_count, ownership_type, is_pe_backed, key_contact_name, key_contact_title, key_contact_email, phone, address, confidence_score, data_sources, is_excluded, exclusion_reason, created_at, updated_at

---

### GET /api/export/json

Download JSON export of all companies.

**Example Request:**

```bash
curl "http://localhost:5001/api/export/json" -o companies.json
```

**Response:**
- **Content-Type:** `application/json`
- **Filename:** `companies_export.json`

**JSON Structure:**

```json
{
  "export_date": "2026-03-01T14:30:00",
  "total_companies": 127,
  "companies": [
    { /* full company object */ },
    { /* full company object */ }
  ]
}
```

---

### GET /api/pipeline/runs

Get recent pipeline execution history.

**Example Request:**

```bash
curl "http://localhost:5001/api/pipeline/runs"
```

**Response:**

```json
{
  "runs": [
    {
      "id": 3,
      "started_at": "2026-03-01T10:00:00",
      "finished_at": "2026-03-01T10:15:00",
      "status": "completed",
      "companies_collected": 150,
      "companies_deduplicated": 127,
      "companies_scored": 127,
      "error_message": null
    },
    {
      "id": 2,
      "started_at": "2026-02-28T09:00:00",
      "finished_at": "2026-02-28T09:12:00",
      "status": "completed",
      "companies_collected": 145,
      "companies_deduplicated": 120,
      "companies_scored": 120,
      "error_message": null
    }
  ]
}
```

---

### GET /api/thesis

Get current investment thesis configuration.

**Example Request:**

```bash
curl "http://localhost:5001/api/thesis"
```

**Response:**

```json
{
  "name": "Specialty Tax Advisory Services",
  "description": "Find privately held specialty tax firms...",
  "target_services": [
    "R&D Tax Credits",
    "Cost Segregation",
    "Work Opportunity Tax Credits",
    "Sales & Use Tax"
  ],
  "min_revenue": 3000000,
  "min_employees": 5,
  "excluded_primary_services": [
    "Employee Retention Credit",
    "Property Tax"
  ],
  "geography": "Continental United States",
  "target_states": ["CA", "NY", "TX", ...]
}
```

---

### GET /api/health

Health check endpoint.

**Example Request:**

```bash
curl "http://localhost:5001/api/health"
```

**Response:**

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2026-03-01T14:30:00"
}
```

---

## Database Schema

The SQLite database contains 3 tables with WAL (Write-Ahead Logging) enabled for concurrent access.

**Location:** `data/companies.db`

### Table: companies

Primary table storing company data.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | INTEGER | No | Primary key (auto-increment) |
| `name` | TEXT | No | Company name |
| `city` | TEXT | Yes | City |
| `state` | TEXT | Yes | 2-letter state code |
| `website` | TEXT | Yes | Company website URL |
| `services` | TEXT | Yes | JSON array of service types |
| `primary_service` | TEXT | Yes | Main service offered |
| `estimated_revenue` | INTEGER | Yes | Revenue in dollars |
| `revenue_source` | TEXT | Yes | Source of revenue estimate |
| `employee_count` | INTEGER | Yes | Exact employee count |
| `employee_count_min` | INTEGER | Yes | Employee range minimum |
| `employee_count_max` | INTEGER | Yes | Employee range maximum |
| `employee_count_source` | TEXT | Yes | Source of employee data |
| `ownership_type` | TEXT | Yes | Type: `independent`, `pe_backed`, `franchise`, `corporate`, `family_owned` |
| `is_pe_backed` | BOOLEAN | Yes | Private equity backed flag |
| `key_contact_name` | TEXT | Yes | Primary contact name |
| `key_contact_title` | TEXT | Yes | Primary contact title |
| `key_contact_email` | TEXT | Yes | Primary contact email |
| `key_contact_phone` | TEXT | Yes | Primary contact phone |
| `data_sources` | TEXT | Yes | JSON array of source names |
| `source_urls` | TEXT | Yes | JSON array of source URLs |
| `description` | TEXT | Yes | Company description |
| `year_founded` | INTEGER | Yes | Year founded |
| `phone` | TEXT | Yes | Main phone number |
| `address` | TEXT | Yes | Full address |
| `google_place_id` | TEXT | Yes | Google Places ID |
| `google_rating` | REAL | Yes | Google rating (0-5) |
| `google_reviews_count` | INTEGER | Yes | Google review count |
| `linkedin_url` | TEXT | Yes | LinkedIn company URL |
| `clutch_rating` | REAL | Yes | Clutch rating (0-5) |
| `clutch_reviews_count` | INTEGER | Yes | Clutch review count |
| `confidence_score` | REAL | Yes | Confidence score (0-1) |
| `is_excluded` | BOOLEAN | No | Exclusion flag (default: 0) |
| `exclusion_reason` | TEXT | Yes | Reason for exclusion |
| `needs_review` | BOOLEAN | No | Manual review flag (default: 0) |
| `notes` | TEXT | Yes | Internal notes |
| `created_at` | TEXT | Yes | Creation timestamp (ISO 8601) |
| `updated_at` | TEXT | Yes | Last update timestamp (ISO 8601) |

**Constraints:**
- `UNIQUE(name, state)` - Prevents duplicate companies

**Indexes:**
- `idx_companies_state` on `state`
- `idx_companies_service` on `primary_service`
- `idx_companies_excluded` on `is_excluded`
- `idx_companies_revenue` on `estimated_revenue`
- `idx_companies_employees` on `employee_count`
- `idx_companies_employees_min` on `employee_count_min`
- `idx_companies_employees_max` on `employee_count_max`

### Table: pipeline_runs

Tracks each pipeline execution.

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | INTEGER | No | Primary key |
| `started_at` | TEXT | No | Start timestamp |
| `finished_at` | TEXT | Yes | End timestamp |
| `status` | TEXT | Yes | `running`, `completed`, `failed` |
| `companies_collected` | INTEGER | Yes | Count after collection |
| `companies_deduplicated` | INTEGER | Yes | Count after dedup |
| `companies_scored` | INTEGER | Yes | Count after scoring |
| `error_message` | TEXT | Yes | Error details if failed |

### Table: source_log

Data provenance tracking (source of each field).

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | INTEGER | No | Primary key |
| `company_id` | INTEGER | No | Foreign key to companies |
| `source_name` | TEXT | No | Source identifier (e.g., `google_places`) |
| `field_name` | TEXT | No | Field that was populated |
| `value` | TEXT | Yes | Value that was set |
| `timestamp` | TEXT | No | When this was recorded |
| `source_url` | TEXT | Yes | Original URL |

**Foreign Key:** `company_id` references `companies(id)`

---

## Thesis Configuration

The investment thesis drives the entire pipeline. Edit `config.py` to customize:

### Target Services

```python
target_services = [
    "R&D Tax Credits",
    "Cost Segregation",
    "Work Opportunity Tax Credits",
    "Sales & Use Tax",
]
```

Add or remove services to focus on different tax specialties.

### Size Thresholds

```python
min_revenue = 3_000_000  # $3M
min_employees = 5
```

Companies below these thresholds are flagged for exclusion.

### Geography

```python
target_states = [
    "AL", "AZ", "AR", "CA", "CO", ... # Continental US
]

priority_metros = [
    "New York, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    # ... 30+ major metros
]
```

Scrapers focus on `priority_metros` for higher-quality results.

### Exclusions

```python
excluded_primary_services = [
    "Employee Retention Credit",  # Not a target service
    "Property Tax",               # Exclusively property tax
]
```

Companies with these primary services are automatically excluded.

---

## Data Sources

The pipeline collects data from 5+ sources:

### 1. Google Places API
- **Requires:** `GOOGLE_PLACES_API_KEY`
- **Provides:** Location, phone, rating, hours, place_id
- **Rate Limit:** 0.5 req/sec (2s delay)
- **Implementation:** `scrapers/google_places.py`

### 2. SerpAPI (Google Search)
- **Requires:** `SERPAPI_KEY`
- **Provides:** Company websites, descriptions from search results
- **Rate Limit:** 0.5 req/sec (2s delay)
- **Implementation:** `scrapers/serp_search.py`

### 3. Clutch.co Directory
- **Requires:** None (public scraping)
- **Provides:** B2B service provider listings, ratings, employee counts
- **Rate Limit:** 1.0 req/sec (1s delay)
- **Implementation:** `scrapers/clutch_directory.py`

### 4. Website Scraping (Enhanced - 7 Major Improvements)
- **Requires:** None
- **Provides:** Services, revenue, ownership, key contacts, LinkedIn URLs, employee counts
- **Rate Limit:** 1.0 req/sec (1s delay)
- **Implementation:** `enrichers/website.py` (805 lines)

**Recent Enhancements (March 2026):**
1. **LinkedIn URL extraction** - Searches 5 pages instead of 1 (30-50% discovery rate)
2. **Revenue patterns** - 20+ new patterns including ranges and tax credit inference (25-35% coverage)
3. **Employee patterns** - 15+ patterns including qualitative firm descriptions (35-45% coverage)
4. **Smart contact extraction** - Email filtering and Schema.org JSON-LD parsing (20-30% coverage)
5. **Employee range conversion** - LinkedIn ranges to midpoint estimates
6. **Text extraction improvements** - Preserves footer text for pattern matching
7. **Enhanced logging** - Tracks extraction success rates per field

**Expected Coverage Improvements:**
- Revenue: 0% → 25-35% (37-52 companies from 149)
- Employees: 9.6% → 35-45% (52-67 companies from 149)
- Contacts: 1.8% → 20-30% (30-45 companies from 149)
- LinkedIn URLs: 0% → 30-50% (45-75 companies from 149)

See [ENRICHMENT_IMPROVEMENTS.md](../ENRICHMENT_IMPROVEMENTS.md) for detailed documentation of improvements.
See [DATA_SOURCES.md](DATA_SOURCES.md) for comprehensive data source documentation.

#### Enhanced Extraction Patterns (March 2026)

**Revenue Extraction (20+ patterns) - `website.py:340-430`:**
- Revenue ranges: "$5-10M in revenue" → $7.5M (midpoint)
- Flexible phrasings: "revenues of $5M", "turnover of $5 million"
- Billion-scale: "$1.2 billion" → $1,200,000,000
- Tax credit inference: "$100M+ credits processed" → implies $10M+ revenue firm
- Without dollar signs: "revenue 5 million dollars"

**Example patterns matched:**
```
- "$5M in annual revenue"
- "revenues of approximately $10 million"
- "$5-10M revenue range"
- "processed over $50M in R&D tax credits" (infers $5M+ revenue)
- "turnover: 3.5 million dollars"
```

**Employee Extraction (15+ patterns) - `website.py:440-520`:**
- Employee ranges: "10-20 employees" → 15 (midpoint)
- Qualitative descriptions:
  - "small/boutique firm" → 8 employees
  - "mid-sized firm" → 25 employees
  - "large/full-service firm" → 75 employees
- Partner counting: "5 partners" → 25 employees (partners × 5 heuristic)
- Multiple phrasings: "team of 50", "over 30 professionals"
- Office counting: 3+ offices → minimum 15 employees

**Example patterns matched:**
```
- "team of 25 professionals"
- "11-50 employees" (from LinkedIn)
- "boutique tax firm" → 8 employees
- "5 partners and their teams" → 25 employees
- "offices in 3 states" → 15 employees minimum
```

**Contact Extraction - `website.py:265-310`:**
- Email extraction from ALL pages (not just contact page)
- Smart filtering: skips generic (info@, sales@, hr@), prefers personal (john.smith@)
- Founder narrative extraction: "Founded by John Smith"
- Schema.org structured data parsing (JSON-LD)

**LinkedIn URL Extraction - `website.py:102-144`:**
- Searches 5 pages: homepage, /about, /about-us, /contact, /contact-us
- Supports both company pages and personal profiles
- Extracts before footer removal (previously missed)
- CEO/founder profile detection

**Employee Range Conversion - `website.py:575-588`:**
- Converts LinkedIn ranges to midpoint estimates
- Example: "11-50 employees" → 30 employees
- Marks source as "range_midpoint" for transparency

**Testing:** Use `test_enrichment.py` to validate extraction on specific companies

---

## Scoring Algorithm

Companies are scored 0-1 based on how well they match the investment thesis.

### Scoring Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| **Service Match** | 35% | Do they offer target services? |
| **Data Completeness** | 20% | How many fields are populated? |
| **Size Fit** | 15% | Meet revenue/employee thresholds? |
| **Source Quality** | 15% | How many sources confirm this? |
| **No Exclusions** | 15% | Any red flags? |

**Total:** 100%

### Service Match (35%)

```python
if matched_services >= 3:
    score = 1.0  # Offer 3+ target services
elif matched_services == 2:
    score = 0.9  # Offer 2 target services
elif matched_services == 1:
    score = 0.7  # Offer 1 target service
else:
    score = 0.1  # No target services
```

### Data Completeness (20%)

Checks 11 key fields:
- name, city, state, website
- services, employee_count (or range)
- estimated_revenue, ownership_type
- phone, description

```python
score = filled_fields / 11
```

### Size Fit (15%)

```python
if revenue >= min_revenue AND employees >= min_employees:
    score = 1.0
elif revenue >= min_revenue OR employees >= min_employees:
    score = 0.5  # Meets one threshold
else:
    score = 0.0  # Below both thresholds
```

### Source Quality (15%)

```python
source_count = len(data_sources)
if source_count >= 3:
    score = 1.0
elif source_count == 2:
    score = 0.6
elif source_count == 1:
    score = 0.3
else:
    score = 0.0
```

### No Exclusions (15%)

```python
if is_pe_backed:
    score = 0.3  # PE-backed penalty
elif needs_review:
    score = 0.5  # Flagged for review
else:
    score = 1.0  # No issues
```

### Final Score

```python
total_score = (
    service_match * 0.35 +
    data_completeness * 0.20 +
    size_fit * 0.15 +
    source_quality * 0.15 +
    no_exclusions * 0.15
)
```

**Implementation:** [`scoring.py`](scoring.py)

To modify weights, edit `WEIGHTS` dict in `scoring.py` (must sum to 1.0).

---

## Deduplication Logic

Deduplication runs in two phases to merge duplicate companies:

### Phase 1: Domain-Based Matching

Companies with the same website domain are considered duplicates.

```python
# Same website = same company
"taxadvisors.com" == "taxadvisors.com" → MERGE
```

**Confidence:** High (website is a strong unique identifier)

### Phase 2: Fuzzy Name Matching

Companies with similar names in the same state are checked for duplicates.

```python
from difflib import SequenceMatcher

threshold = 0.80  # 80% similarity

similarity = SequenceMatcher(None, name1, name2).ratio()
if similarity >= threshold and state1 == state2:
    # Potential duplicate → MERGE
```

**Examples:**
- "TaxAdvisors LLC" vs "Tax Advisors, LLC" → 95% similarity → MERGE
- "Smith Tax Group" vs "Smith Tax Solutions" → 70% similarity → KEEP SEPARATE

**Implementation:** [`dedup.py`](dedup.py)

**Configuration:** Edit `PIPELINE.dedup_name_threshold` in `config.py` to adjust sensitivity.

### Merge Strategy

When duplicates are found:
1. Keep the company with the highest confidence score as primary
2. Merge all non-null fields from duplicates
3. Combine `data_sources` and `source_urls` arrays
4. Preserve all source provenance in `source_log`

---

## Development Guide

### Adding a New Scraper

1. **Create scraper file:**

```python
# scrapers/new_source.py

from scrapers.base import BaseScraper
from models import Company

class NewSourceScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="new_source", rate_limit=1.0)

    def scrape(self, query: str = None) -> list[Company]:
        """Scrape companies from the new source."""
        companies = []

        # Implement scraping logic here
        # ...

        return companies
```

2. **Register in pipeline:**

```python
# pipeline.py

from scrapers.new_source import NewSourceScraper

def collect(run_id: str) -> list[Company]:
    scrapers = [
        GooglePlacesScraper(),
        ClutchScraper(),
        NewSourceScraper(),  # Add here
    ]
    # ...
```

3. **Add rate limit config:**

```python
# config.py

@dataclass
class PipelineConfig:
    rate_limits = {
        "google_places": 2.0,
        "clutch": 1.0,
        "new_source": 1.5,  # Add here
    }
```

### Adding a New Enricher

Similar to scrapers, enrichers fill in missing data:

```python
# enrichers/new_enricher.py

def enrich_from_new_source(company: Company) -> Company:
    """Enrich company data from new source."""
    if company.website:
        # Fetch and parse data
        # Update company fields
        # Add to data_sources
        pass
    return company
```

Register in `pipeline.py` `enrich()` function.

### Testing Enrichment

Use `test_enrichment.py` to validate enrichment improvements before running the full pipeline:

**Test single company by URL:**
```bash
python test_enrichment.py --url https://taxpointadvisors.com
```

**Test batch of companies from database:**
```bash
python test_enrichment.py --batch 10  # Test top 10 companies
```

**Test specific company by name:**
```bash
python test_enrichment.py --name "Tax Point Advisors"
```

**Expected output:**
- LinkedIn URLs found: 30-50% of companies
- Revenue extracted: 25-35% of companies
- Employees extracted: 35-45% of companies
- Contacts extracted: 20-30% of companies

**View enrichment logs:**
```bash
tail -f data/pipeline.log | grep "Enriching\|Extracted"
```

See [ENRICHMENT_IMPROVEMENTS.md](../ENRICHMENT_IMPROVEMENTS.md) for detailed documentation of all 7 improvements.

### Modifying Scoring Algorithm

Edit `scoring.py`:

1. **Change weights:**

```python
WEIGHTS = {
    "service_match": 0.40,      # Increase from 0.35
    "data_completeness": 0.20,
    "size_fit": 0.15,
    "source_quality": 0.15,
    "no_exclusions": 0.10,      # Decrease from 0.15
}
```

2. **Add new scoring factor:**

```python
def _score_industry(company: Company) -> float:
    """Score based on industry classification."""
    # Implementation
    return score

WEIGHTS = {
    "service_match": 0.30,
    "data_completeness": 0.20,
    "size_fit": 0.15,
    "source_quality": 0.15,
    "no_exclusions": 0.10,
    "industry": 0.10,  # New factor
}

def score_company(company: Company) -> float:
    scores = {
        # ... existing factors
        "industry": _score_industry(company),  # Add here
    }
    # ...
```

---

## Troubleshooting

### API Errors

**Issue:** `ModuleNotFoundError: No module named 'flask'`

**Solution:**
```bash
pip install -r requirements.txt
```

**Issue:** `Address already in use: port 5001`

**Solution:**
```bash
# Find and kill process on port 5001
lsof -ti:5001 | xargs kill -9

# Or use different port
PORT=5002 python server.py
```

### Database Issues

**Issue:** `sqlite3.OperationalError: database is locked`

**Solution:**
```bash
# Close all connections
# WAL mode should prevent this, but if it occurs:
rm data/companies.db-wal
rm data/companies.db-shm
```

**Issue:** Database is empty after running pipeline

**Solution:**
```bash
# Check logs
tail -f data/pipeline.log

# Verify demo mode ran
# Should see: "Demo mode: Seeding 30 sample companies"

# Check stats
python main.py stats
```

### Pipeline Failures

**Issue:** Scraper errors or rate limit exceeded

**Solution:**
```bash
# Check API keys in .env
cat .env

# Increase rate limits in config.py
# Change from 1.0 to 2.0 seconds

# Check logs for specific errors
tail -n 100 data/pipeline.log | grep ERROR
```

**Issue:** ImportError or circular imports

**Solution:**
```bash
# Ensure you're in the backend directory
cd backend

# Run from backend directory
python main.py run
```

### General Issues

**Issue:** Python version too old

**Solution:**
```bash
# Check version
python --version  # Need 3.9+

# Use python3 explicitly
python3 main.py run
```

**Issue:** Permission denied when writing to database

**Solution:**
```bash
# Create data directory
mkdir -p data

# Fix permissions
chmod 755 data
```

---

## Additional Resources

- **[Project README](../README.md)** - Project overview and quick start
- **[Frontend README](../frontend/README.md)** - Dashboard documentation
- **[DATA_SOURCES.md](DATA_SOURCES.md)** - Comprehensive data source guide
- **[Enrichment Improvements](../ENRICHMENT_IMPROVEMENTS.md)** - Detailed documentation of 7 extraction enhancements
- **[Test Enrichment](test_enrichment.py)** - Testing script for enrichment pipeline
- **[CLAUDE.md](../CLAUDE.md)** - Internal developer guide

---

**Questions?** Check [../README.md](../README.md#troubleshooting) for common issues or review the logs at `data/pipeline.log`.
