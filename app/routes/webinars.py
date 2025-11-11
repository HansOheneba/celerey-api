from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime
import json

webinars_bp = Blueprint("webinars_bp", __name__, url_prefix="/webinars")


@webinars_bp.route("/active", methods=["GET"])
def get_active_webinar():
    try:
        query = "SELECT * FROM webinars WHERE is_active = TRUE LIMIT 1"
        webinar = DBHelper.execute_query(query, fetch_one=True)

        if not webinar:
            return jsonify({"error": "No active webinar found"}), 404

        # Parse JSON fields
        speakers = json.loads(webinar["speakers"]) if webinar["speakers"] else []
        expectations = (
            json.loads(webinar["expectations"]) if webinar["expectations"] else []
        )
        attendees = json.loads(webinar["attendees"]) if webinar["attendees"] else []

        return (
            jsonify(
                {
                    "id": webinar["id"],
                    "title": webinar["title"],
                    "subtitle": webinar["subtitle"],
                    "description": webinar["description"],
                    "date": DBHelper.format_datetime(webinar["date"]),
                    "formatted_date": webinar["date"].strftime(
                        "%A, %d %B %Y at %H:%M hrs GMT"
                    ),
                    "speakers": speakers,
                    "expectations": expectations,
                    "attendees": attendees,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@webinars_bp.route("/register", methods=["POST"])
def register_for_webinar():
    try:
        data = request.get_json()

        # Basic validation
        if not data.get("email"):
            return jsonify({"error": "Email is required"}), 400

        # Check if webinar exists
        webinar_query = "SELECT id FROM webinars WHERE is_active = TRUE LIMIT 1"
        webinar = DBHelper.execute_query(webinar_query, fetch_one=True)
        if not webinar:
            return jsonify({"error": "No active webinar found"}), 404

        # Check if already registered
        existing_query = "SELECT id FROM webinar_registrations WHERE email = %s"
        existing_registration = DBHelper.execute_query(
            existing_query, (data["email"],), fetch_one=True
        )
        if existing_registration:
            return jsonify({"error": "Email already registered"}), 400

        insert_query = """
            INSERT INTO webinar_registrations (email, full_name, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
        """

        now = datetime.now()
        registration_id = DBHelper.execute_query(
            insert_query,
            (data["email"], data.get("full_name", ""), "pending", now, now),
            lastrowid=True,
        )

        return (
            jsonify(
                {
                    "message": "Successfully registered for webinar",
                    "id": registration_id,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@webinars_bp.route("/", methods=["POST", "PUT"])
def manage_webinar():
    try:
        data = request.get_json()

        # Basic validation
        required_fields = ["title", "date"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if webinar already exists
        existing_query = "SELECT id FROM webinars WHERE is_active = TRUE LIMIT 1"
        webinar = DBHelper.execute_query(existing_query, fetch_one=True)

        if request.method == "POST" and webinar:
            return jsonify({"error": "Webinar already exists. Use PUT to update."}), 400

        if request.method == "PUT" and not webinar:
            return jsonify({"error": "No webinar found to update"}), 404

        # Prepare data
        webinar_date = DBHelper.parse_datetime(data["date"])
        speakers_json = json.dumps(data.get("speakers", []))
        expectations_json = json.dumps(data.get("expectations", []))
        attendees_json = json.dumps(data.get("attendees", []))

        if request.method == "POST":
            insert_query = """
                INSERT INTO webinars (title, subtitle, description, date, speakers, expectations, attendees, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            now = datetime.now()
            webinar_id = DBHelper.execute_query(
                insert_query,
                (
                    data["title"],
                    data.get("subtitle"),
                    data.get("description"),
                    webinar_date,
                    speakers_json,
                    expectations_json,
                    attendees_json,
                    True,
                    now,
                    now,
                ),
                lastrowid=True,
            )
            return (
                jsonify({"message": "Webinar saved successfully", "id": webinar_id}),
                201,
            )

        else:  # PUT
            update_query = """
                UPDATE webinars 
                SET title = %s, subtitle = %s, description = %s, date = %s, speakers = %s, 
                    expectations = %s, attendees = %s, updated_at = %s 
                WHERE is_active = TRUE
            """
            DBHelper.execute_query(
                update_query,
                (
                    data["title"],
                    data.get("subtitle"),
                    data.get("description"),
                    webinar_date,
                    speakers_json,
                    expectations_json,
                    attendees_json,
                    datetime.now(),
                ),
            )
            return jsonify({"message": "Webinar updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@webinars_bp.route("/registrations", methods=["GET"])
def get_webinar_registrations():
    try:
        status_filter = request.args.get("status")

        base_query = "SELECT * FROM webinar_registrations"
        if status_filter:
            query = base_query + " WHERE status = %s ORDER BY created_at DESC"
            registrations = DBHelper.execute_query(
                query, (status_filter,), fetch_all=True
            )
        else:
            query = base_query + " ORDER BY created_at DESC"
            registrations = DBHelper.execute_query(query, fetch_all=True)

        result = []
        for reg in registrations:
            result.append(
                {
                    "id": reg["id"],
                    "email": reg["email"],
                    "full_name": reg["full_name"],
                    "status": reg["status"],
                    "created_at": DBHelper.format_datetime(reg["created_at"]),
                    "invited_at": (
                        DBHelper.format_datetime(reg["invited_at"])
                        if reg["invited_at"]
                        else None
                    ),
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@webinars_bp.route("/registrations/<int:registration_id>", methods=["PUT"])
def update_registration_status(registration_id):
    try:
        # Check if registration exists
        check_query = "SELECT id FROM webinar_registrations WHERE id = %s"
        existing = DBHelper.execute_query(
            check_query, (registration_id,), fetch_one=True
        )
        if not existing:
            return jsonify({"error": "Registration not found"}), 404

        data = request.get_json()
        if "status" not in data:
            return jsonify({"error": "Status is required"}), 400

        valid_statuses = ["pending", "invited", "attended", "cancelled"]
        if data["status"] not in valid_statuses:
            return (
                jsonify(
                    {
                        "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                    }
                ),
                400,
            )

        # Set invited_at if status is 'invited'
        invited_at = datetime.now() if data["status"] == "invited" else None

        if invited_at:
            update_query = "UPDATE webinar_registrations SET status = %s, invited_at = %s, updated_at = %s WHERE id = %s"
            DBHelper.execute_query(
                update_query,
                (data["status"], invited_at, datetime.now(), registration_id),
            )
        else:
            update_query = "UPDATE webinar_registrations SET status = %s, updated_at = %s WHERE id = %s"
            DBHelper.execute_query(
                update_query, (data["status"], datetime.now(), registration_id)
            )

        return jsonify({"message": "Registration status updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@webinars_bp.route("/stats", methods=["GET"])
def get_webinar_stats():
    try:
        total_query = "SELECT COUNT(*) as count FROM webinar_registrations"
        total_result = DBHelper.execute_query(total_query, fetch_one=True)

        pending_query = "SELECT COUNT(*) as count FROM webinar_registrations WHERE status = 'pending'"
        pending_result = DBHelper.execute_query(pending_query, fetch_one=True)

        invited_query = "SELECT COUNT(*) as count FROM webinar_registrations WHERE status = 'invited'"
        invited_result = DBHelper.execute_query(invited_query, fetch_one=True)

        attended_query = "SELECT COUNT(*) as count FROM webinar_registrations WHERE status = 'attended'"
        attended_result = DBHelper.execute_query(attended_query, fetch_one=True)

        cancelled_query = "SELECT COUNT(*) as count FROM webinar_registrations WHERE status = 'cancelled'"
        cancelled_result = DBHelper.execute_query(cancelled_query, fetch_one=True)

        stats = {
            "total_registrations": total_result["count"] if total_result else 0,
            "pending": pending_result["count"] if pending_result else 0,
            "invited": invited_result["count"] if invited_result else 0,
            "attended": attended_result["count"] if attended_result else 0,
            "cancelled": cancelled_result["count"] if cancelled_result else 0,
        }

        return jsonify(stats), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@webinars_bp.route("/registrations/<int:registration_id>", methods=["DELETE"])
def delete_registration(registration_id):
    try:
        # Check if registration exists
        check_query = "SELECT id FROM webinar_registrations WHERE id = %s"
        existing = DBHelper.execute_query(
            check_query, (registration_id,), fetch_one=True
        )
        if not existing:
            return jsonify({"error": "Registration not found"}), 404

        delete_query = "DELETE FROM webinar_registrations WHERE id = %s"
        DBHelper.execute_query(delete_query, (registration_id,))

        return jsonify({"message": "Registration deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
