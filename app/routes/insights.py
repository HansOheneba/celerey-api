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
                    "author": i["author"],
                    "date": DBHelper.format_date(i["date"]),
                    "excerpt": i["excerpt"],
                    "cover_image": i["cover_image"],
                    "content": i["content"],
                    "tags": i["tags"].split(",") if i["tags"] else [],
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@insights_bp.route("/", methods=["POST"])
def add_insight():
    try:
        data = request.json

        # Basic validation
        required_fields = ["title", "slug", "author", "excerpt", "content"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if slug exists
        slug_check = "SELECT id FROM insights WHERE slug = %s"
        existing = DBHelper.execute_query(slug_check, (data["slug"],), fetch_one=True)
        if existing:
            return jsonify({"error": "Slug already exists"}), 400

        insert_query = """
            INSERT INTO insights (title, slug, author, excerpt, cover_image, content, tags, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        tags_str = ",".join(data.get("tags", [])) if data.get("tags") else None

        insight_id = DBHelper.execute_query(
            insert_query,
            (
                data["title"],
                data["slug"],
                data["author"],
                data["excerpt"],
                data.get("cover_image"),
                data["content"],
                tags_str,
                datetime.now(),
            ),
            lastrowid=True,
        )

        return jsonify({"message": "Insight added successfully", "id": insight_id}), 201

    except Exception as e:
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
        update_fields = []
        params = []

        for field in ["title", "slug", "author", "excerpt", "cover_image", "content"]:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])

        if "tags" in data and isinstance(data["tags"], list):
            update_fields.append("tags = %s")
            params.append(",".join(data["tags"]))

        params.append(id)

        update_query = f"UPDATE insights SET {', '.join(update_fields)} WHERE id = %s"
        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Insight updated"}), 200

    except Exception as e:
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
