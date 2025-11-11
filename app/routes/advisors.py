from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime

advisors_bp = Blueprint("advisors_bp", __name__, url_prefix="/advisors")


# 🟢 Get all advisors
@advisors_bp.route("/", methods=["GET"])
def get_advisors():
    try:
        query = "SELECT * FROM advisors ORDER BY name ASC"
        advisors = DBHelper.execute_query(query, fetch_all=True)

        result = []
        for advisor in advisors:
            result.append(
                {
                    "id": advisor["id"],
                    "slug": advisor["slug"],
                    "name": advisor["name"],
                    "title": advisor["title"],
                    "bio": advisor["bio"],
                    "experience": advisor["experience"],
                    "expertise": (
                        advisor["expertise"].split(",") if advisor["expertise"] else []
                    ),
                    "image": advisor["image"],
                    "created_at": DBHelper.format_datetime(advisor["created_at"]),
                    "updated_at": DBHelper.format_datetime(advisor["updated_at"]),
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Get a single advisor by slug
@advisors_bp.route("/<string:slug>", methods=["GET"])
def get_advisor(slug):
    try:
        query = "SELECT * FROM advisors WHERE slug = %s"
        advisor = DBHelper.execute_query(query, (slug,), fetch_one=True)

        if not advisor:
            return jsonify({"error": "Advisor not found"}), 404

        return (
            jsonify(
                {
                    "id": advisor["id"],
                    "slug": advisor["slug"],
                    "name": advisor["name"],
                    "title": advisor["title"],
                    "bio": advisor["bio"],
                    "experience": advisor["experience"],
                    "expertise": (
                        advisor["expertise"].split(",") if advisor["expertise"] else []
                    ),
                    "image": advisor["image"],
                    "created_at": DBHelper.format_datetime(advisor["created_at"]),
                    "updated_at": DBHelper.format_datetime(advisor["updated_at"]),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Add a new advisor
@advisors_bp.route("/", methods=["POST"])
def add_advisor():
    try:
        data = request.get_json()

        # Basic validation
        required_fields = ["slug", "name", "title", "bio", "experience"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if slug already exists
        check_query = "SELECT id FROM advisors WHERE slug = %s"
        existing_advisor = DBHelper.execute_query(
            check_query, (data["slug"],), fetch_one=True
        )
        if existing_advisor:
            return jsonify({"error": "Advisor with this slug already exists"}), 400

        # Insert new advisor
        insert_query = """
            INSERT INTO advisors (slug, name, title, bio, experience, expertise, image, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        expertise_str = (
            ",".join(data.get("expertise", [])) if data.get("expertise") else None
        )
        now = datetime.now()

        advisor_id = DBHelper.execute_query(
            insert_query,
            (
                data["slug"],
                data["name"],
                data["title"],
                data["bio"],
                data["experience"],
                expertise_str,
                data.get("image"),
                now,
                now,
            ),
            lastrowid=True,
        )

        return jsonify({"message": "Advisor added successfully", "id": advisor_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Update advisor
@advisors_bp.route("/<int:id>", methods=["PUT"])
def update_advisor(id):
    try:
        # Check if advisor exists
        check_query = "SELECT id FROM advisors WHERE id = %s"
        existing_advisor = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing_advisor:
            return jsonify({"error": "Advisor not found"}), 404

        data = request.get_json()
        update_fields = []
        params = []

        for field in ["slug", "name", "title", "bio", "experience", "image"]:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])

        if "expertise" in data and isinstance(data["expertise"], list):
            update_fields.append("expertise = %s")
            params.append(",".join(data["expertise"]))

        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(id)

        update_query = f"UPDATE advisors SET {', '.join(update_fields)} WHERE id = %s"
        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Advisor updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Delete advisor
@advisors_bp.route("/<int:id>", methods=["DELETE"])
def delete_advisor(id):
    try:
        # Check if advisor exists
        check_query = "SELECT id FROM advisors WHERE id = %s"
        existing_advisor = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing_advisor:
            return jsonify({"error": "Advisor not found"}), 404

        delete_query = "DELETE FROM advisors WHERE id = %s"
        DBHelper.execute_query(delete_query, (id,))

        return jsonify({"message": "Advisor deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@advisors_bp.route("/table-schema", methods=["GET"])
def table_schema():
    try:
        query = "DESCRIBE advisors"
        schema = DBHelper.execute_query(query, fetch_all=True)
        return jsonify({"schema": schema}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
