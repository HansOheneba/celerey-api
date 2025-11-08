from flask import Blueprint, jsonify, request
from app.models import Podcasts, db
from datetime import datetime

podcasts_bp = Blueprint("podcasts_bp", __name__, url_prefix="/podcasts")


# 🟢 Get all podcasts
@podcasts_bp.route("/", methods=["GET"])
def get_podcasts():
    podcasts = Podcasts.query.order_by(Podcasts.date.desc()).all()
    return (
        jsonify(
            [
                {
                    "id": p.id,
                    "slug": p.slug,
                    "title": p.title,
                    "host": p.host,
                    "duration": p.duration,
                    "date": p.date.strftime("%Y-%m-%d") if p.date else None,
                    "image": p.image,
                    "description": p.description,
                    "spotify_link": p.spotify_link,
                    "spotify_embed_url": p.spotify_embed_url,
                    "tags": p.tags.split(",") if p.tags else [],
                }
                for p in podcasts
            ]
        ),
        200,
    )


# 🟢 Get a single podcast by ID
@podcasts_bp.route("/<int:id>", methods=["GET"])
def get_podcast(id):
    podcast = Podcasts.query.get_or_404(id)
    return (
        jsonify(
            {
                "id": podcast.id,
                "slug": podcast.slug,
                "title": podcast.title,
                "host": podcast.host,
                "duration": podcast.duration,
                "date": podcast.date.strftime("%Y-%m-%d") if podcast.date else None,
                "image": podcast.image,
                "description": podcast.description,
                "spotify_link": podcast.spotify_link,
                "spotify_embed_url": podcast.spotify_embed_url,
                "transcript": podcast.transcript,
                "tags": podcast.tags.split(",") if podcast.tags else [],
            }
        ),
        200,
    )


# 🟢 Add a new podcast
@podcasts_bp.route("/", methods=["POST"])
def add_podcast():
    data = request.get_json()

    # Basic validation
    required_fields = ["slug", "title"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    new_podcast = Podcasts(
        slug=data["slug"],
        title=data["title"],
        host=data.get("host"),
        duration=data.get("duration"),
        date=(
            datetime.strptime(data.get("date"), "%Y-%m-%d")
            if data.get("date")
            else None
        ),
        image=data.get("image"),
        description=data.get("description"),
        spotify_link=data.get("spotify_link"),
        spotify_embed_url=data.get("spotify_embed_url"),
        transcript=data.get("transcript"),
        tags=",".join(data.get("tags", [])),
    )

    db.session.add(new_podcast)
    db.session.commit()

    return jsonify({"message": "Podcast added successfully", "id": new_podcast.id}), 201


# 🟢 Update existing podcast
@podcasts_bp.route("/<int:id>", methods=["PUT"])
def update_podcast(id):
    podcast = Podcasts.query.get_or_404(id)
    data = request.get_json()

    # Update fields safely
    for field in [
        "slug",
        "title",
        "host",
        "duration",
        "image",
        "description",
        "spotify_link",
        "spotify_embed_url",
        "transcript",
        "tags",
    ]:
        if field in data:
            value = data[field]
            if field == "tags" and isinstance(value, list):
                value = ",".join(value)
            setattr(podcast, field, value)

    if "date" in data and data["date"]:
        try:
            podcast.date = datetime.strptime(data["date"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    db.session.commit()
    return jsonify({"message": "Podcast updated successfully"}), 200


# 🟢 Delete a podcast
@podcasts_bp.route("/<int:id>", methods=["DELETE"])
def delete_podcast(id):
    podcast = Podcasts.query.get_or_404(id)
    db.session.delete(podcast)
    db.session.commit()
    return jsonify({"message": "Podcast deleted successfully"}), 200
