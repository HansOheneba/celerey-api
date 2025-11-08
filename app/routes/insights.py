from flask import Blueprint, jsonify, request
from app.models import Insights, db

insights_bp = Blueprint("insights_bp", __name__)


@insights_bp.route("/", methods=["GET"])
def get_insights():
    insights = Insights.query.all()
    return jsonify(
        [
            {
                "id": i.id,
                "title": i.title,
                "slug": i.slug,
                "author": i.author,
                "date": i.date.strftime("%Y-%m-%d"),
                "excerpt": i.excerpt,
                "cover_image": i.cover_image,
                "content": i.content,
                "tags": i.tags.split(",") if i.tags else [],
            }
            for i in insights
        ]
    )


@insights_bp.route("/", methods=["POST"])
def add_insight():
    data = request.json
    new_insight = Insights(
        title=data["title"],
        slug=data["slug"],
        author=data["author"],
        excerpt=data["excerpt"],
        cover_image=data.get("cover_image"),
        content=data["content"],
        tags=",".join(data.get("tags", [])),
    )
    db.session.add(new_insight)
    db.session.commit()
    return jsonify({"message": "Insight added successfully"}), 201


@insights_bp.route("/<int:id>", methods=["PUT"])
def update_insight(id):
    insight = Insights.query.get_or_404(id)
    data = request.json
    for key, value in data.items():
        setattr(insight, key, value)
    db.session.commit()
    return jsonify({"message": "Insight updated"})


@insights_bp.route("/<int:id>", methods=["DELETE"])
def delete_insight(id):
    insight = Insights.query.get_or_404(id)
    db.session.delete(insight)
    db.session.commit()
    return jsonify({"message": "Insight deleted"})
