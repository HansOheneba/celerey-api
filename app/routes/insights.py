from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime

insights_bp = Blueprint("insights_bp", __name__)


@insights_bp.route("/", methods=["GET"])
def get_insights():
    try:
        query = "SELECT * FROM insights ORDER BY date DESC"
        insights = DBHelper.execute_query(query, fetch_all=True)

        result = []
        for i in insights:
            result.append(
                {
                    "id": i["id"],
                    "title": i["title"],
                    "slug": i["slug"],
                    "date": DBHelper.format_date(i["date"]),
                    "cover_image": i["cover_image"],
                    "content": i["content"],
                    "tags": i["tags"].split(",") if i["tags"] else [],
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@insights_bp.route("/<int:id>", methods=["GET"])
def get_insight(id):
    try:
        query = "SELECT * FROM insights WHERE id = %s"
        insight = DBHelper.execute_query(query, (id,), fetch_one=True)

        if not insight:
            return jsonify({"error": "Insight not found"}), 404

        result = {
            "id": insight["id"],
            "title": insight["title"],
            "slug": insight["slug"],
            "date": DBHelper.format_date(insight["date"]),
            "cover_image": insight["cover_image"],
            "content": insight["content"],
            "tags": insight["tags"].split(",") if insight["tags"] else [],
        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@insights_bp.route("/", methods=["POST"])
def add_insight():
    try:
        data = request.json
        print("Received data:", data)  # Debug log

        # Basic validation
        required_fields = ["title", "slug", "content"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if slug exists
        slug_check = "SELECT id FROM insights WHERE slug = %s"
        existing = DBHelper.execute_query(slug_check, (data["slug"],), fetch_one=True)
        if existing:
            return jsonify({"error": "Slug already exists"}), 400

        insert_query = """
            INSERT INTO insights (title, slug, cover_image, content, tags, date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Handle tags - convert list to comma-separated string
        tags_str = ",".join(data.get("tags", [])) if data.get("tags") else None

        insight_id = DBHelper.execute_query(
            insert_query,
            (
                data["title"],
                data["slug"],
                data.get("coverImage"),  # Note: React sends coverImage
                data["content"],
                tags_str,
                datetime.now(),
            ),
            lastrowid=True,
        )

        return jsonify({"message": "Insight added successfully", "id": insight_id}), 201

    except Exception as e:
        print("Error:", str(e))  # Debug log
        return jsonify({"error": str(e)}), 500


@insights_bp.route("/<int:id>", methods=["PUT"])
def update_insight(id):
    try:
        # Check if insight exists
        check_query = "SELECT id FROM insights WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Insight not found"}), 404

        data = request.json
        print("Update data received:", data)  # Debug log

        # Check if slug is being updated and if it already exists (excluding current post)
        if "slug" in data:
            slug_check = "SELECT id FROM insights WHERE slug = %s AND id != %s"
            slug_exists = DBHelper.execute_query(
                slug_check, (data["slug"], id), fetch_one=True
            )
            if slug_exists:
                return jsonify({"error": "Slug already exists"}), 400

        update_fields = []
        params = []

        # Map React field names to database column names
        field_mapping = {
            "title": "title",
            "slug": "slug",
            "coverImage": "cover_image",  # Map React field to DB field
            "content": "content",
        }

        for react_field, db_field in field_mapping.items():
            if react_field in data:
                update_fields.append(f"{db_field} = %s")
                params.append(data[react_field])

        # Handle tags
        if "tags" in data and isinstance(data["tags"], list):
            update_fields.append("tags = %s")
            params.append(",".join(data["tags"]))

        # Add updated timestamp
        update_fields.append("date = %s")
        params.append(datetime.now())

        params.append(id)

        update_query = f"UPDATE insights SET {', '.join(update_fields)} WHERE id = %s"
        print("Update query:", update_query)  # Debug log
        print("Update params:", params)  # Debug log

        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Insight updated successfully"}), 200

    except Exception as e:
        print("Update error:", str(e))  # Debug log
        return jsonify({"error": str(e)}), 500


@insights_bp.route("/<int:id>", methods=["DELETE"])
def delete_insight(id):
    try:
        # Check if insight exists
        check_query = "SELECT id FROM insights WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Insight not found"}), 404

        delete_query = "DELETE FROM insights WHERE id = %s"
        DBHelper.execute_query(delete_query, (id,))

        return jsonify({"message": "Insight deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
