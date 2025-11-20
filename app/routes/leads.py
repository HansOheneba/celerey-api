from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime

leads_bp = Blueprint("leads_bp", __name__, url_prefix="/leads")


@leads_bp.route("/", methods=["GET"])
def get_leads():
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        offset = (page - 1) * per_page

        base_query = "FROM leads"
        count_query = "SELECT COUNT(*) as total " + base_query
        select_query = "SELECT * " + base_query

        # Optional filter by source
        source = request.args.get("source")
        params = []
        if source in ["newsletter", "wealth_scan", "contact_form"]:
            where_clause = " WHERE source = %s"
            base_query += where_clause
            count_query += where_clause
            select_query += where_clause
            params.append(source)

        total_result = DBHelper.execute_query(count_query, params, fetch_one=True)
        total = total_result["total"] if total_result else 0

        select_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        leads = DBHelper.execute_query(select_query, params, fetch_all=True)

        return (
            jsonify(
                {
                    "leads": [
                        {
                            "id": lead["id"],
                            "email": lead["email"],
                            "source": lead["source"],
                            "created_at": DBHelper.format_datetime(lead["created_at"]),
                        }
                        for lead in leads
                    ],
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                    "current_page": page,
                    "per_page": per_page,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@leads_bp.route("/", methods=["POST"])
def add_lead():
    try:
        data = request.get_json()

        if "email" not in data or not data["email"]:
            return jsonify({"error": "Missing email"}), 400

        if "@" not in data["email"]:
            return jsonify({"error": "Invalid email format"}), 400

        source = data.get("source", "newsletter")
        if source not in ["newsletter", "wealth_scan", "contact_form"]:
            return jsonify({"error": "Invalid source"}), 400

        insert_query = """
            INSERT INTO leads (email, source, created_at)
            VALUES (%s, %s, %s)
        """

        now = datetime.now()

        lead_id = DBHelper.execute_query(
            insert_query, (data["email"], source, now), lastrowid=True
        )

        return jsonify({"message": "Lead added successfully", "id": lead_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
