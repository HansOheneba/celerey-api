from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime

contact_bp = Blueprint("contact_bp", __name__, url_prefix="/contact")


@contact_bp.route("/messages", methods=["GET"])
def get_contact_messages():
    try:
        # Query parameters
        status = request.args.get("status")
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        offset = (page - 1) * per_page

        # Base query
        base_query = "FROM contact_messages"
        count_query = "SELECT COUNT(*) as total " + base_query
        select_query = "SELECT * " + base_query

        params = []
        if status and status in ["new", "read", "replied"]:
            where_clause = " WHERE status = %s"
            base_query += where_clause
            count_query += where_clause
            select_query += where_clause
            params.append(status)

        # Get total count
        total_result = DBHelper.execute_query(count_query, params, fetch_one=True)
        total = total_result["total"] if total_result else 0

        # Get paginated results
        select_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        messages = DBHelper.execute_query(select_query, params, fetch_all=True)

        return (
            jsonify(
                {
                    "messages": [
                        {
                            "id": msg["id"],
                            "full_name": msg["full_name"],
                            "email": msg["email"],
                            "subject": msg["subject"],
                            "message": msg["message"],
                            "status": msg["status"],
                            "created_at": DBHelper.format_datetime(msg["created_at"]),
                            "updated_at": DBHelper.format_datetime(msg["updated_at"]),
                        }
                        for msg in messages
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


@contact_bp.route("/messages/<int:id>", methods=["GET"])
def get_contact_message(id):
    try:
        query = "SELECT * FROM contact_messages WHERE id = %s"
        message = DBHelper.execute_query(query, (id,), fetch_one=True)

        if not message:
            return jsonify({"error": "Message not found"}), 404

        return (
            jsonify(
                {
                    "id": message["id"],
                    "full_name": message["full_name"],
                    "email": message["email"],
                    "subject": message["subject"],
                    "message": message["message"],
                    "status": message["status"],
                    "created_at": DBHelper.format_datetime(message["created_at"]),
                    "updated_at": DBHelper.format_datetime(message["updated_at"]),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@contact_bp.route("/messages", methods=["POST"])
def submit_contact_message():
    try:
        data = request.get_json()

        # Basic validation
        required_fields = ["full_name", "email", "message"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Email validation
        if "@" not in data["email"]:
            return jsonify({"error": "Invalid email format"}), 400

        insert_query = """
            INSERT INTO contact_messages (full_name, email, subject, message, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        now = datetime.now()
        message_id = DBHelper.execute_query(
            insert_query,
            (
                data["full_name"],
                data["email"],
                data.get("subject", ""),
                data["message"],
                "new",
                now,
                now,
            ),
            lastrowid=True,
        )

        return (
            jsonify(
                {"message": "Contact message submitted successfully", "id": message_id}
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@contact_bp.route("/messages/<int:id>/status", methods=["PUT"])
def update_message_status(id):
    try:
        # Check if message exists
        check_query = "SELECT id FROM contact_messages WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Message not found"}), 404

        data = request.get_json()
        if "status" not in data:
            return jsonify({"error": "Missing status field"}), 400

        new_status = data["status"]
        if new_status not in ["new", "read", "replied"]:
            return (
                jsonify(
                    {"error": "Invalid status. Must be 'new', 'read', or 'replied'"}
                ),
                400,
            )

        update_query = (
            "UPDATE contact_messages SET status = %s, updated_at = %s WHERE id = %s"
        )
        DBHelper.execute_query(update_query, (new_status, datetime.now(), id))

        return (
            jsonify(
                {"message": f"Message status updated to '{new_status}' successfully"}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@contact_bp.route("/messages/<int:id>", methods=["PUT"])
def update_contact_message(id):
    try:
        # Check if message exists
        check_query = "SELECT id FROM contact_messages WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Message not found"}), 404

        data = request.get_json()
        update_fields = []
        params = []

        for field in ["full_name", "email", "subject", "message", "status"]:
            if field in data:
                if field == "status" and data[field] not in ["new", "read", "replied"]:
                    return jsonify({"error": "Invalid status value"}), 400
                update_fields.append(f"{field} = %s")
                params.append(data[field])

        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(id)

        update_query = (
            f"UPDATE contact_messages SET {', '.join(update_fields)} WHERE id = %s"
        )
        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Contact message updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@contact_bp.route("/messages/<int:id>", methods=["DELETE"])
def delete_contact_message(id):
    try:
        # Check if message exists
        check_query = "SELECT id FROM contact_messages WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Message not found"}), 404

        delete_query = "DELETE FROM contact_messages WHERE id = %s"
        DBHelper.execute_query(delete_query, (id,))

        return jsonify({"message": "Contact message deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@contact_bp.route("/stats", methods=["GET"])
def get_contact_stats():
    try:
        total_query = "SELECT COUNT(*) as total FROM contact_messages"
        total_result = DBHelper.execute_query(total_query, fetch_one=True)

        new_query = (
            "SELECT COUNT(*) as count FROM contact_messages WHERE status = 'new'"
        )
        new_result = DBHelper.execute_query(new_query, fetch_one=True)

        read_query = (
            "SELECT COUNT(*) as count FROM contact_messages WHERE status = 'read'"
        )
        read_result = DBHelper.execute_query(read_query, fetch_one=True)

        replied_query = (
            "SELECT COUNT(*) as count FROM contact_messages WHERE status = 'replied'"
        )
        replied_result = DBHelper.execute_query(replied_query, fetch_one=True)

        return (
            jsonify(
                {
                    "total_messages": total_result["total"] if total_result else 0,
                    "new_messages": new_result["count"] if new_result else 0,
                    "read_messages": read_result["count"] if read_result else 0,
                    "replied_messages": (
                        replied_result["count"] if replied_result else 0
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
