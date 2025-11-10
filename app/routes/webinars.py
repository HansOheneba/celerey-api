from flask import Blueprint, jsonify, request
from app.models import Webinar, WebinarRegistration, db
from datetime import datetime
import json

webinars_bp = Blueprint("webinars_bp", __name__, url_prefix="/webinars")


# 🟢 Get active webinar
@webinars_bp.route("/active", methods=["GET"])
def get_active_webinar():
    webinar = Webinar.query.filter_by(is_active=True).first()

    if not webinar:
        return jsonify({"error": "No active webinar found"}), 404

    return (
        jsonify(
            {
                "id": webinar.id,
                "title": webinar.title,
                "subtitle": webinar.subtitle,
                "description": webinar.description,
                "date": webinar.date.strftime("%Y-%m-%d %H:%M:%S"),
                "formatted_date": webinar.date.strftime(
                    "%A, %d %B %Y at %H:%M hrs GMT"
                ),
                "speakers": webinar.speakers or [],
                "expectations": webinar.expectations or [],
                "attendees": webinar.attendees or [],
            }
        ),
        200,
    )


# 🟢 Register for webinar
@webinars_bp.route("/register", methods=["POST"])
def register_for_webinar():
    data = request.get_json()

    # Basic validation
    if not data.get("email"):
        return jsonify({"error": "Email is required"}), 400

    # Check if webinar exists
    webinar = Webinar.query.filter_by(is_active=True).first()
    if not webinar:
        return jsonify({"error": "No active webinar found"}), 404

    # Check if already registered
    existing_registration = WebinarRegistration.query.filter_by(
        email=data["email"]
    ).first()
    if existing_registration:
        return jsonify({"error": "Email already registered"}), 400

    new_registration = WebinarRegistration(
        email=data["email"], full_name=data.get("full_name", ""), status="pending"
    )

    db.session.add(new_registration)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Successfully registered for webinar",
                "id": new_registration.id,
            }
        ),
        201,
    )


# 🟢 Admin: Create or update webinar
@webinars_bp.route("/", methods=["POST", "PUT"])
def manage_webinar():
    data = request.get_json()

    # Basic validation
    required_fields = ["title", "date"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Check if webinar already exists
    webinar = Webinar.query.filter_by(is_active=True).first()

    if request.method == "POST" and webinar:
        return jsonify({"error": "Webinar already exists. Use PUT to update."}), 400

    if request.method == "PUT" and not webinar:
        return jsonify({"error": "No webinar found to update"}), 404

    if request.method == "POST":
        webinar = Webinar()

    # Update fields
    webinar.title = data["title"]
    webinar.subtitle = data.get("subtitle")
    webinar.description = data.get("description")
    webinar.date = datetime.strptime(data["date"], "%Y-%m-%d %H:%M:%S")
    webinar.speakers = data.get("speakers", [])
    webinar.expectations = data.get("expectations", [])
    webinar.attendees = data.get("attendees", [])
    webinar.is_active = True

    if request.method == "POST":
        db.session.add(webinar)

    db.session.commit()

    return jsonify({"message": "Webinar saved successfully", "id": webinar.id}), (
        200 if request.method == "PUT" else 201
    )


# 🟢 Admin: Get webinar registrations
@webinars_bp.route("/registrations", methods=["GET"])
def get_webinar_registrations():
    status_filter = request.args.get("status")
    query = WebinarRegistration.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    registrations = query.order_by(WebinarRegistration.created_at.desc()).all()

    return (
        jsonify(
            [
                {
                    "id": reg.id,
                    "email": reg.email,
                    "full_name": reg.full_name,
                    "status": reg.status,
                    "created_at": reg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "invited_at": (
                        reg.invited_at.strftime("%Y-%m-%d %H:%M:%S")
                        if reg.invited_at
                        else None
                    ),
                }
                for reg in registrations
            ]
        ),
        200,
    )


# 🟢 Admin: Update registration status
@webinars_bp.route("/registrations/<int:registration_id>", methods=["PUT"])
def update_registration_status(registration_id):
    registration = WebinarRegistration.query.get_or_404(registration_id)
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

    registration.status = data["status"]

    if data["status"] == "invited":
        registration.invited_at = datetime.utcnow()

    db.session.commit()

    return jsonify({"message": "Registration status updated successfully"}), 200


# 🟢 Admin: Get webinar stats
@webinars_bp.route("/stats", methods=["GET"])
def get_webinar_stats():
    stats = {
        "total_registrations": WebinarRegistration.query.count(),
        "pending": WebinarRegistration.query.filter_by(status="pending").count(),
        "invited": WebinarRegistration.query.filter_by(status="invited").count(),
        "attended": WebinarRegistration.query.filter_by(status="attended").count(),
        "cancelled": WebinarRegistration.query.filter_by(status="cancelled").count(),
    }

    return jsonify(stats), 200


# 🟢 Admin: Delete registration
@webinars_bp.route("/registrations/<int:registration_id>", methods=["DELETE"])
def delete_registration(registration_id):
    registration = WebinarRegistration.query.get_or_404(registration_id)
    db.session.delete(registration)
    db.session.commit()
    return jsonify({"message": "Registration deleted successfully"}), 200
