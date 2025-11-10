from flask import Blueprint, jsonify, request
from app.models import Advisors, db
from datetime import datetime

advisors_bp = Blueprint("advisors_bp", __name__, url_prefix="/advisors")


# 🟢 Get all advisors
@advisors_bp.route("/", methods=["GET"])
def get_advisors():
    advisors = Advisors.query.order_by(Advisors.name.asc()).all()
    return (
        jsonify(
            [
                {
                    "id": a.id,
                    "slug": a.slug,
                    "name": a.name,
                    "title": a.title,
                    "bio": a.bio,
                    "experience": a.experience,
                    "expertise": a.expertise.split(",") if a.expertise else [],
                    "image": a.image,
                    "created_at": (
                        a.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        if a.created_at
                        else None
                    ),
                    "updated_at": (
                        a.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                        if a.updated_at
                        else None
                    ),
                }
                for a in advisors
            ]
        ),
        200,
    )


# 🟢 Get a single advisor by slug
@advisors_bp.route("/<string:slug>", methods=["GET"])
def get_advisor(slug):
    advisor = Advisors.query.filter_by(slug=slug).first_or_404()
    return (
        jsonify(
            {
                "id": advisor.id,
                "slug": advisor.slug,
                "name": advisor.name,
                "title": advisor.title,
                "bio": advisor.bio,
                "experience": advisor.experience,
                "expertise": advisor.expertise.split(",") if advisor.expertise else [],
                "image": advisor.image,
                "created_at": (
                    advisor.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if advisor.created_at
                    else None
                ),
                "updated_at": (
                    advisor.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if advisor.updated_at
                    else None
                ),
            }
        ),
        200,
    )


# 🟢 Get a single advisor by ID
@advisors_bp.route("/id/<int:id>", methods=["GET"])
def get_advisor_by_id(id):
    advisor = Advisors.query.get_or_404(id)
    return (
        jsonify(
            {
                "id": advisor.id,
                "slug": advisor.slug,
                "name": advisor.name,
                "title": advisor.title,
                "bio": advisor.bio,
                "experience": advisor.experience,
                "expertise": advisor.expertise.split(",") if advisor.expertise else [],
                "image": advisor.image,
                "created_at": (
                    advisor.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if advisor.created_at
                    else None
                ),
                "updated_at": (
                    advisor.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if advisor.updated_at
                    else None
                ),
            }
        ),
        200,
    )


# 🟢 Add a new advisor
@advisors_bp.route("/", methods=["POST"])
def add_advisor():
    data = request.get_json()

    # Basic validation
    required_fields = ["slug", "name", "title", "bio", "experience"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Check if slug already exists
    existing_advisor = Advisors.query.filter_by(slug=data["slug"]).first()
    if existing_advisor:
        return jsonify({"error": "Advisor with this slug already exists"}), 400

    new_advisor = Advisors(
        slug=data["slug"],
        name=data["name"],
        title=data["title"],
        bio=data["bio"],
        experience=data["experience"],
        expertise=",".join(data.get("expertise", [])),
        image=data.get("image"),
    )

    db.session.add(new_advisor)
    db.session.commit()

    return jsonify({"message": "Advisor added successfully", "id": new_advisor.id}), 201



@advisors_bp.route("/<int:id>", methods=["PUT"])
def update_advisor(id):
    advisor = Advisors.query.get_or_404(id)
    data = request.get_json()

    for field in [
        "slug",
        "name",
        "title",
        "bio",
        "experience",
        "image",
    ]:
        if field in data:
            setattr(advisor, field, data[field])

    if "expertise" in data and isinstance(data["expertise"], list):
        advisor.expertise = ",".join(data["expertise"])

    db.session.commit()
    return jsonify({"message": "Advisor updated successfully"}), 200



@advisors_bp.route("/<int:id>", methods=["DELETE"])
def delete_advisor(id):
    advisor = Advisors.query.get_or_404(id)
    db.session.delete(advisor)
    db.session.commit()
    return jsonify({"message": "Advisor deleted successfully"}), 200
