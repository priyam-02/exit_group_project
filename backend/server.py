"""
Flask API Server.

Serves company data to the dashboard frontend via REST endpoints.
Also provides endpoints for triggering pipeline runs and exports.
"""

import os
import sys
import json
import logging
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PIPELINE, THESIS
from models import Database

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the frontend

logger = logging.getLogger(__name__)

db = Database()


# ── Company Endpoints ────────────────────────────────────────────────────────

@app.route("/api/companies", methods=["GET"])
def get_companies():
    """
    Get all companies with optional filtering.
    Query params:
      - service: Filter by service type
      - state: Filter by state
      - min_revenue: Minimum revenue
      - min_employees: Minimum employees
      - include_excluded: Include excluded companies (default: false)
      - search: Text search across name/description
    """
    include_excluded = request.args.get("include_excluded", "false").lower() == "true"

    conn = db._get_conn()
    try:
        query = "SELECT * FROM companies WHERE 1=1"
        params = []

        if not include_excluded:
            query += " AND is_excluded = 0"

        # Service filter
        service = request.args.get("service")
        if service:
            query += " AND (services LIKE ? OR primary_service = ?)"
            params.extend([f"%{service}%", service])

        # State filter
        state = request.args.get("state")
        if state:
            query += " AND state = ?"
            params.append(state.upper())

        # Revenue filter
        min_revenue = request.args.get("min_revenue")
        if min_revenue:
            query += " AND estimated_revenue >= ?"
            params.append(int(min_revenue))

        # Employee filter (checks exact count OR range max)
        min_employees = request.args.get("min_employees")
        if min_employees:
            query += " AND (employee_count >= ? OR employee_count_max >= ?)"
            params.extend([int(min_employees), int(min_employees)])

        # Text search
        search = request.args.get("search")
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Sort
        sort_by = request.args.get("sort_by", "confidence_score")
        sort_dir = request.args.get("sort_dir", "DESC")
        allowed_sorts = {
            "name", "state", "estimated_revenue", "employee_count",
            "confidence_score", "primary_service", "google_rating"
        }
        if sort_by in allowed_sorts:
            query += f" ORDER BY {sort_by} {sort_dir} NULLS LAST"
        else:
            query += " ORDER BY confidence_score DESC"

        rows = conn.execute(query, params).fetchall()

        companies = []
        for row in rows:
            company = dict(row)
            company["services"] = json.loads(company.get("services") or "[]")
            company["data_sources"] = json.loads(company.get("data_sources") or "[]")
            company["source_urls"] = json.loads(company.get("source_urls") or "[]")
            companies.append(company)

        return jsonify({"companies": companies, "total": len(companies)})

    finally:
        conn.close()


@app.route("/api/companies/<int:company_id>", methods=["GET"])
def get_company(company_id):
    """Get a single company by ID with full details."""
    conn = db._get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone()

        if not row:
            return jsonify({"error": "Company not found"}), 404

        company = dict(row)
        company["services"] = json.loads(company.get("services") or "[]")
        company["data_sources"] = json.loads(company.get("data_sources") or "[]")
        company["source_urls"] = json.loads(company.get("source_urls") or "[]")

        # Get source logs for this company
        sources = conn.execute(
            "SELECT * FROM source_log WHERE company_id = ?", (company_id,)
        ).fetchall()
        company["source_details"] = [dict(s) for s in sources]

        return jsonify(company)

    finally:
        conn.close()


# ── KPI / Analytics Endpoints ────────────────────────────────────────────────

@app.route("/api/kpis", methods=["GET"])
def get_kpis():
    """
    Get summary KPI data for the dashboard header cards.
    Returns total count, service breakdown, state breakdown, etc.
    """
    conn = db._get_conn()
    try:
        # Total active companies
        total = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE is_excluded = 0"
        ).fetchone()[0]

        # Total excluded
        excluded = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE is_excluded = 1"
        ).fetchone()[0]

        # By service type
        services_raw = conn.execute("""
            SELECT services FROM companies WHERE is_excluded = 0
        """).fetchall()

        service_counts = {}
        for row in services_raw:
            for service in json.loads(row["services"] or "[]"):
                service_counts[service] = service_counts.get(service, 0) + 1

        # By state
        state_counts = conn.execute("""
            SELECT state, COUNT(*) as count FROM companies
            WHERE is_excluded = 0 AND state IS NOT NULL
            GROUP BY state ORDER BY count DESC
        """).fetchall()

        # Revenue stats
        revenue_stats = conn.execute("""
            SELECT
                COUNT(*) as with_revenue,
                AVG(estimated_revenue) as avg_revenue,
                MIN(estimated_revenue) as min_revenue,
                MAX(estimated_revenue) as max_revenue,
                SUM(estimated_revenue) as total_revenue
            FROM companies
            WHERE is_excluded = 0 AND estimated_revenue IS NOT NULL
        """).fetchone()

        # Employee stats
        employee_stats = conn.execute("""
            SELECT
                COUNT(*) as with_employees,
                AVG(employee_count) as avg_employees,
                MIN(employee_count) as min_employees,
                MAX(employee_count) as max_employees
            FROM companies
            WHERE is_excluded = 0 AND employee_count IS NOT NULL
        """).fetchone()

        # Ownership breakdown
        ownership = conn.execute("""
            SELECT ownership_type, COUNT(*) as count FROM companies
            WHERE is_excluded = 0 AND ownership_type IS NOT NULL
            GROUP BY ownership_type ORDER BY count DESC
        """).fetchall()

        # Companies with identified ownership
        with_ownership = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE is_excluded = 0 AND ownership_type IS NOT NULL"
        ).fetchone()[0]

        # PE-backed count
        pe_backed = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE is_pe_backed = 1"
        ).fetchone()[0]

        # With website
        with_website = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE is_excluded = 0 AND website IS NOT NULL"
        ).fetchone()[0]

        # With contact
        with_contact = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE is_excluded = 0 AND key_contact_name IS NOT NULL"
        ).fetchone()[0]

        # Needs review
        needs_review = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE needs_review = 1"
        ).fetchone()[0]

        # Average confidence score
        avg_confidence = conn.execute(
            "SELECT AVG(confidence_score) FROM companies WHERE is_excluded = 0"
        ).fetchone()[0]

        return jsonify({
            "total_companies": total,
            "excluded_companies": excluded,
            "service_distribution": service_counts,
            "state_distribution": {row["state"]: row["count"] for row in state_counts},
            "revenue": {
                "companies_with_data": dict(revenue_stats)["with_revenue"] or 0,
                "average": round(dict(revenue_stats)["avg_revenue"] or 0),
                "min": dict(revenue_stats)["min_revenue"],
                "max": dict(revenue_stats)["max_revenue"],
                "total": dict(revenue_stats)["total_revenue"],
            },
            "employees": {
                "companies_with_data": dict(employee_stats)["with_employees"] or 0,
                "average": round(dict(employee_stats)["avg_employees"] or 0),
                "min": dict(employee_stats)["min_employees"],
                "max": dict(employee_stats)["max_employees"],
            },
            "ownership_breakdown": {row["ownership_type"]: row["count"] for row in ownership},
            "companies_with_ownership": with_ownership,
            "pe_backed_count": pe_backed,
            "with_website": with_website,
            "with_contact": with_contact,
            "needs_review": needs_review,
            "avg_confidence_score": round(avg_confidence or 0, 3),
        })

    finally:
        conn.close()


# ── Export Endpoints ─────────────────────────────────────────────────────────

@app.route("/api/export/csv", methods=["GET"])
def export_csv():
    """Download the company list as CSV."""
    filepath = os.path.join(PIPELINE.output_dir, "companies_export.csv")
    db.export_to_csv(filepath)
    return send_file(
        filepath,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"exit_group_targets_{THESIS.name.replace(' ', '_')}.csv"
    )


@app.route("/api/export/json", methods=["GET"])
def export_json():
    """Download the company list as JSON."""
    filepath = os.path.join(PIPELINE.output_dir, "companies_export.json")
    db.export_to_json(filepath)
    return send_file(
        filepath,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"exit_group_targets_{THESIS.name.replace(' ', '_')}.json"
    )


# ── Pipeline Status ──────────────────────────────────────────────────────────

@app.route("/api/pipeline/runs", methods=["GET"])
def get_pipeline_runs():
    """Get recent pipeline run logs."""
    conn = db._get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 10"
        ).fetchall()
        return jsonify({"runs": [dict(r) for r in rows]})
    finally:
        conn.close()


@app.route("/api/thesis", methods=["GET"])
def get_thesis():
    """Get the current thesis configuration."""
    return jsonify({
        "name": THESIS.name,
        "description": THESIS.description,
        "target_services": THESIS.target_services,
        "min_revenue": THESIS.min_revenue,
        "min_employees": THESIS.min_employees,
        "geography": THESIS.geography,
        "ownership_filter": THESIS.ownership_filter,
        "excluded_services": THESIS.excluded_primary_services,
    })


# ── Health Check ─────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "database": PIPELINE.db_path,
        "company_count": db.get_company_count(),
    })


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5001, debug=True)
