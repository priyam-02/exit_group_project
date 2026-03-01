"""
Database layer for the M&A Research Pipeline.

Uses SQLite for portability (no external DB setup needed).
Schema is designed around the fields specified in the assessment:
  - Company name, location, website, services, revenue, employee count,
    ownership type, key contacts, and data source provenance.
"""

import sqlite3
import json
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
from config import PIPELINE


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Company:
    """Represents a single company/acquisition target."""

    # Core identity
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None

    # Services (stored as JSON array in DB)
    services: list = field(default_factory=list)
    primary_service: Optional[str] = None

    # Size indicators
    estimated_revenue: Optional[int] = None          # In dollars
    revenue_source: Optional[str] = None             # Where we got the estimate
    employee_count: Optional[int] = None             # Exact count (if known)
    employee_count_min: Optional[int] = None         # Range minimum (e.g., 11 from "11-50")
    employee_count_max: Optional[int] = None         # Range maximum (e.g., 50 from "11-50")
    employee_count_source: Optional[str] = None

    # Ownership
    ownership_type: Optional[str] = None             # private, PE-backed, franchise, etc.
    is_pe_backed: Optional[bool] = None

    # Contacts
    key_contact_name: Optional[str] = None
    key_contact_title: Optional[str] = None
    key_contact_email: Optional[str] = None
    key_contact_phone: Optional[str] = None

    # Data provenance
    data_sources: list = field(default_factory=list)  # e.g., ["google_places", "website"]
    source_urls: list = field(default_factory=list)    # Original URLs where found

    # Metadata
    description: Optional[str] = None
    year_founded: Optional[int] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    google_place_id: Optional[str] = None
    google_rating: Optional[float] = None
    google_reviews_count: Optional[int] = None
    linkedin_url: Optional[str] = None
    clutch_rating: Optional[float] = None
    clutch_reviews_count: Optional[int] = None

    # Pipeline metadata
    confidence_score: Optional[float] = None   # 0-1, how confident we are this fits thesis
    is_excluded: bool = False                  # Flagged for exclusion (ERC, property tax, etc.)
    exclusion_reason: Optional[str] = None
    needs_review: bool = False                 # Flagged for manual review
    notes: Optional[str] = None

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for DB insertion."""
        d = asdict(self)
        d["services"] = json.dumps(d["services"])
        d["data_sources"] = json.dumps(d["data_sources"])
        d["source_urls"] = json.dumps(d["source_urls"])
        if d["created_at"] is None:
            d["created_at"] = datetime.utcnow().isoformat()
        d["updated_at"] = datetime.utcnow().isoformat()
        return d

    @classmethod
    def from_row(cls, row: dict) -> "Company":
        """Create Company from a DB row (sqlite3.Row)."""
        d = dict(row)
        d["services"] = json.loads(d.get("services") or "[]")
        d["data_sources"] = json.loads(d.get("data_sources") or "[]")
        d["source_urls"] = json.loads(d.get("source_urls") or "[]")
        # Remove 'id' if present since it's not in the dataclass
        d.pop("id", None)
        return cls(**d)


# ── Database Manager ─────────────────────────────────────────────────────────

class Database:
    """SQLite database manager with connection pooling."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or PIPELINE.db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- Core identity
                    name TEXT NOT NULL,
                    city TEXT,
                    state TEXT,
                    website TEXT,

                    -- Services
                    services TEXT DEFAULT '[]',        -- JSON array
                    primary_service TEXT,

                    -- Size
                    estimated_revenue INTEGER,
                    revenue_source TEXT,
                    employee_count INTEGER,
                    employee_count_min INTEGER,
                    employee_count_max INTEGER,
                    employee_count_source TEXT,

                    -- Ownership
                    ownership_type TEXT,  -- Only set when confirmed from reliable source
                    is_pe_backed BOOLEAN DEFAULT 0,

                    -- Contacts
                    key_contact_name TEXT,
                    key_contact_title TEXT,
                    key_contact_email TEXT,
                    key_contact_phone TEXT,

                    -- Data provenance
                    data_sources TEXT DEFAULT '[]',    -- JSON array
                    source_urls TEXT DEFAULT '[]',     -- JSON array

                    -- Metadata
                    description TEXT,
                    year_founded INTEGER,
                    phone TEXT,
                    address TEXT,
                    google_place_id TEXT,
                    google_rating REAL,
                    google_reviews_count INTEGER,
                    linkedin_url TEXT,
                    clutch_rating REAL,
                    clutch_reviews_count INTEGER,

                    -- Pipeline metadata
                    confidence_score REAL,
                    is_excluded BOOLEAN DEFAULT 0,
                    exclusion_reason TEXT,
                    needs_review BOOLEAN DEFAULT 0,
                    notes TEXT,

                    -- Timestamps
                    created_at TEXT,
                    updated_at TEXT,

                    -- Unique constraint for dedup
                    UNIQUE(name, state)
                );

                -- Indexes for common queries
                CREATE INDEX IF NOT EXISTS idx_companies_state ON companies(state);
                CREATE INDEX IF NOT EXISTS idx_companies_service ON companies(primary_service);
                CREATE INDEX IF NOT EXISTS idx_companies_excluded ON companies(is_excluded);
                CREATE INDEX IF NOT EXISTS idx_companies_revenue ON companies(estimated_revenue);
                CREATE INDEX IF NOT EXISTS idx_companies_employees ON companies(employee_count);
                CREATE INDEX IF NOT EXISTS idx_companies_employees_min ON companies(employee_count_min);
                CREATE INDEX IF NOT EXISTS idx_companies_employees_max ON companies(employee_count_max);

                -- Pipeline run log — tracks each pipeline execution
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    thesis_name TEXT,
                    status TEXT DEFAULT 'running',       -- running, completed, failed
                    companies_found INTEGER DEFAULT 0,
                    companies_after_dedup INTEGER DEFAULT 0,
                    companies_excluded INTEGER DEFAULT 0,
                    error_message TEXT,
                    config_snapshot TEXT                  -- JSON of thesis config used
                );

                -- Source tracking — which sources yielded which companies
                CREATE TABLE IF NOT EXISTS source_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER,
                    source_type TEXT,              -- google_places, serp, directory, website
                    source_query TEXT,             -- The query that found this company
                    source_url TEXT,
                    raw_data TEXT,                 -- JSON of raw API/scrape response
                    scraped_at TEXT,
                    FOREIGN KEY (company_id) REFERENCES companies(id)
                );
            """)
            conn.commit()
        finally:
            conn.close()

    def upsert_company(self, company: Company) -> int:
        """
        Insert or update a company. On conflict (same name + state),
        merge new data into existing record without overwriting non-null fields.
        Returns the company ID.
        """
        conn = self._get_conn()
        try:
            data = company.to_dict()

            # Check if company already exists
            existing = conn.execute(
                "SELECT * FROM companies WHERE name = ? AND state = ?",
                (data["name"], data["state"])
            ).fetchone()

            if existing:
                # Merge: update only fields that are currently NULL in DB
                # but have values in the new data
                existing_dict = dict(existing)
                updates = {}
                for key, new_val in data.items():
                    if key in ("id", "created_at"):
                        continue
                    old_val = existing_dict.get(key)

                    # For JSON fields, merge lists
                    if key in ("services", "data_sources", "source_urls"):
                        old_list = json.loads(old_val or "[]")
                        new_list = json.loads(new_val or "[]")
                        merged = list(set(old_list + new_list))
                        updates[key] = json.dumps(merged)
                    # For scalar fields, prefer new non-null value if old is null
                    elif old_val is None and new_val is not None:
                        updates[key] = new_val
                    # Always update the timestamp
                    elif key == "updated_at":
                        updates[key] = new_val

                if updates:
                    set_clause = ", ".join(f"{k} = ?" for k in updates)
                    values = list(updates.values())
                    conn.execute(
                        f"UPDATE companies SET {set_clause} WHERE id = ?",
                        values + [existing_dict["id"]]
                    )
                    conn.commit()
                return existing_dict["id"]

            else:
                # Insert new company
                columns = ", ".join(data.keys())
                placeholders = ", ".join("?" for _ in data)
                cursor = conn.execute(
                    f"INSERT INTO companies ({columns}) VALUES ({placeholders})",
                    list(data.values())
                )
                conn.commit()
                return cursor.lastrowid

        finally:
            conn.close()

    def log_source(self, company_id: int, source_type: str,
                   query: str = None, url: str = None, raw_data: dict = None):
        """Log where a company was found for data provenance."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO source_log
                   (company_id, source_type, source_query, source_url, raw_data, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (company_id, source_type, query, url,
                 json.dumps(raw_data) if raw_data else None,
                 datetime.utcnow().isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_all_companies(self, include_excluded: bool = False) -> list:
        """Get all companies, optionally including excluded ones."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM companies"
            if not include_excluded:
                query += " WHERE is_excluded = 0"
            query += " ORDER BY confidence_score DESC, name ASC"
            rows = conn.execute(query).fetchall()
            return [Company.from_row(row) for row in rows]
        finally:
            conn.close()

    def get_company_count(self, include_excluded: bool = False) -> int:
        """Quick count of companies."""
        conn = self._get_conn()
        try:
            query = "SELECT COUNT(*) FROM companies"
            if not include_excluded:
                query += " WHERE is_excluded = 0"
            return conn.execute(query).fetchone()[0]
        finally:
            conn.close()

    def get_companies_by_state(self) -> dict:
        """Get company count grouped by state."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT state, COUNT(*) as count FROM companies
                   WHERE is_excluded = 0 AND state IS NOT NULL
                   GROUP BY state ORDER BY count DESC"""
            ).fetchall()
            return {row["state"]: row["count"] for row in rows}
        finally:
            conn.close()

    def get_companies_by_service(self) -> dict:
        """Get company count grouped by primary service."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT primary_service, COUNT(*) as count FROM companies
                   WHERE is_excluded = 0 AND primary_service IS NOT NULL
                   GROUP BY primary_service ORDER BY count DESC"""
            ).fetchall()
            return {row["primary_service"]: row["count"] for row in rows}
        finally:
            conn.close()

    def start_pipeline_run(self, thesis_name: str, config_snapshot: dict) -> int:
        """Log the start of a pipeline run."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO pipeline_runs (started_at, thesis_name, config_snapshot)
                   VALUES (?, ?, ?)""",
                (datetime.utcnow().isoformat(), thesis_name, json.dumps(config_snapshot))
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def finish_pipeline_run(self, run_id: int, status: str,
                            found: int, after_dedup: int, excluded: int,
                            error: str = None):
        """Log the completion of a pipeline run."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE pipeline_runs SET
                   finished_at = ?, status = ?, companies_found = ?,
                   companies_after_dedup = ?, companies_excluded = ?, error_message = ?
                   WHERE id = ?""",
                (datetime.utcnow().isoformat(), status, found,
                 after_dedup, excluded, error, run_id)
            )
            conn.commit()
        finally:
            conn.close()

    def export_to_csv(self, filepath: str):
        """Export all non-excluded companies to CSV."""
        import csv
        companies = self.get_all_companies(include_excluded=False)
        if not companies:
            return

        fieldnames = [
            "name", "city", "state", "website", "services", "primary_service",
            "estimated_revenue", "employee_count", "employee_count_min", "employee_count_max",
            "ownership_type", "is_pe_backed",
            "key_contact_name", "key_contact_title", "phone",
            "year_founded", "google_rating", "confidence_score",
            "data_sources", "description"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for c in companies:
                row = asdict(c)
                # Convert lists to readable strings for CSV
                row["services"] = "; ".join(row["services"])
                row["data_sources"] = "; ".join(row["data_sources"])
                writer.writerow(row)

    def export_to_json(self, filepath: str):
        """Export all non-excluded companies to JSON."""
        companies = self.get_all_companies(include_excluded=False)
        data = [asdict(c) for c in companies]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
