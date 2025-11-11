from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime

podcasts_bp = Blueprint("podcasts_bp", __name__, url_prefix="/podcasts")


@podcasts_bp.route("/", methods=["GET"])
def get_podcasts():
    try:
        query = "SELECT * FROM podcasts ORDER BY date DESC"
        podcasts = DBHelper.execute_query(query, fetch_all=True)

        result = []
        for p in podcasts:
            result.append(
                {
                    "id": p["id"],
                    "slug": p["slug"],
                    "title": p["title"],
                    "host": p["host"],
                    "duration": p["duration"],
                    "date": DBHelper.format_date(p["date"]),
                    "image": p["image"],
                    "description": p["description"],
                    "spotify_link": p["spotify_link"],
                    "spotify_embed_url": p["spotify_embed_url"],
                    "tags": p["tags"].split(",") if p["tags"] else [],
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@podcasts_bp.route("/<int:id>", methods=["GET"])
def get_podcast(id):
    try:
        query = "SELECT * FROM podcasts WHERE id = %s"
        podcast = DBHelper.execute_query(query, (id,), fetch_one=True)

        if not podcast:
            return jsonify({"error": "Podcast not found"}), 404

        return (
            jsonify(
                {
                    "id": podcast["id"],
                    "slug": podcast["slug"],
                    "title": podcast["title"],
                    "host": podcast["host"],
                    "duration": podcast["duration"],
                    "date": DBHelper.format_date(podcast["date"]),
                    "image": podcast["image"],
                    "description": podcast["description"],
                    "spotify_link": podcast["spotify_link"],
                    "spotify_embed_url": podcast["spotify_embed_url"],
                    "tags": podcast["tags"].split(",") if podcast["tags"] else [],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@podcasts_bp.route("/", methods=["POST"])
def add_podcast():
    try:
        data = request.get_json()

        # Basic validation
        required_fields = ["slug", "title"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if slug exists
        slug_check = "SELECT id FROM podcasts WHERE slug = %s"
        existing = DBHelper.execute_query(slug_check, (data["slug"],), fetch_one=True)
        if existing:
            return jsonify({"error": "Slug already exists"}), 400

        insert_query = """
            INSERT INTO podcasts (slug, title, host, duration, date, image, description, spotify_link, spotify_embed_url, tags)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Parse date if provided
        podcast_date = None
        if data.get("date"):
            try:
                podcast_date = DBHelper.parse_date(data["date"])
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        tags_str = ",".join(data.get("tags", [])) if data.get("tags") else None

        podcast_id = DBHelper.execute_query(
            insert_query,
            (
                data["slug"],
                data["title"],
                data.get("host"),
                data.get("duration"),
                podcast_date,
                data.get("image"),
                data.get("description"),
                data.get("spotify_link"),
                data.get("spotify_embed_url"),
                tags_str,
            ),
            lastrowid=True,
        )

        return jsonify({"message": "Podcast added successfully", "id": podcast_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@podcasts_bp.route("/<int:id>", methods=["PUT"])
def update_podcast(id):
    try:
        # Check if podcast exists
        check_query = "SELECT id FROM podcasts WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Podcast not found"}), 404

        data = request.get_json()
        update_fields = []
        params = []

        for field in [
            "slug",
            "title",
            "host",
            "duration",
            "image",
            "description",
            "spotify_link",
            "spotify_embed_url",
        ]:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])

        if "tags" in data and isinstance(data["tags"], list):
            update_fields.append("tags = %s")
            params.append(",".join(data["tags"]))

        if "date" in data and data["date"]:
            try:
                podcast_date = DBHelper.parse_date(data["date"])
                update_fields.append("date = %s")
                params.append(podcast_date)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        params.append(id)

        update_query = f"UPDATE podcasts SET {', '.join(update_fields)} WHERE id = %s"
        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Podcast updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@podcasts_bp.route("/<int:id>", methods=["DELETE"])
def delete_podcast(id):
    try:
        # Check if podcast exists
        check_query = "SELECT id FROM podcasts WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing:
            return jsonify({"error": "Podcast not found"}), 404

        delete_query = "DELETE FROM podcasts WHERE id = %s"
        DBHelper.execute_query(delete_query, (id,))

        return jsonify({"message": "Podcast deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
