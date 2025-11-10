from flask import Blueprint, jsonify, request
from app.models import ContactMessage, db
from datetime import datetime

contact_bp = Blueprint("contact_bp", __name__, url_prefix="/contact")


# 🟢 Get all contact messages (with filtering and pagination)
@contact_bp.route("/messages", methods=["GET"])
def get_contact_messages():
    # Query parameters
    status = request.args.get("status")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    # Base query
    query = ContactMessage.query

    # Filter by status if provided
    if status and status in ["new", "read", "replied"]:
        query = query.filter_by(status=status)

    # Order by latest first and paginate
    messages = query.order_by(ContactMessage.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return (
        jsonify(
            {
                "messages": [
                    {
                        "id": msg.id,
                        "full_name": msg.full_name,
                        "email": msg.email,
                        "subject": msg.subject,
                        "message": msg.message,
                        "status": msg.status,
                        "created_at": (
                            msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                            if msg.created_at
                            else None
                        ),
                        "updated_at": (
                            msg.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                            if msg.updated_at
                            else None
                        ),
                    }
                    for msg in messages.items
                ],
                "total": messages.total,
                "pages": messages.pages,
                "current_page": page,
                "per_page": per_page,
            }
        ),
        200,
    )


# 🟢 Get a single contact message by ID
@contact_bp.route("/messages/<int:id>", methods=["GET"])
def get_contact_message(id):
    message = ContactMessage.query.get_or_404(id)
    return (
        jsonify(
            {
                "id": message.id,
                "full_name": message.full_name,
                "email": message.email,
                "subject": message.subject,
                "message": message.message,
                "status": message.status,
                "created_at": (
                    message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if message.created_at
                    else None
                ),
                "updated_at": (
                    message.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                    if message.updated_at
                    else None
                ),
            }
        ),
        200,
    )


# 🟢 Submit a new contact message
@contact_bp.route("/messages", methods=["POST"])
def submit_contact_message():
    data = request.get_json()

    # Basic validation
    required_fields = ["full_name", "email", "message"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Email validation
    if "@" not in data["email"]:
        return jsonify({"error": "Invalid email format"}), 400

    new_message = ContactMessage(
        full_name=data["full_name"],
        email=data["email"],
        subject=data.get("subject", ""),
        message=data["message"],
        status="new",  # Always set to 'new' for new submissions
    )

    db.session.add(new_message)
    db.session.commit()

    return (
        jsonify(
            {"message": "Contact message submitted successfully", "id": new_message.id}
        ),
        201,
    )


# 🟢 Update message status
@contact_bp.route("/messages/<int:id>/status", methods=["PUT"])
def update_message_status(id):
    message = ContactMessage.query.get_or_404(id)
    data = request.get_json()

    if "status" not in data:
        return jsonify({"error": "Missing status field"}), 400

    new_status = data["status"]
    if new_status not in ["new", "read", "replied"]:
        return (
            jsonify({"error": "Invalid status. Must be 'new', 'read', or 'replied'"}),
            400,
        )

    message.status = new_status
    db.session.commit()

    return (
        jsonify({"message": f"Message status updated to '{new_status}' successfully"}),
        200,
    )


# 🟢 Update entire message
@contact_bp.route("/messages/<int:id>", methods=["PUT"])
def update_contact_message(id):
    message = ContactMessage.query.get_or_404(id)
    data = request.get_json()

    # Update fields safely
    for field in ["full_name", "email", "subject", "message", "status"]:
        if field in data:
            if field == "status" and data[field] not in ["new", "read", "replied"]:
                return jsonify({"error": "Invalid status value"}), 400
            setattr(message, field, data[field])

    db.session.commit()
    return jsonify({"message": "Contact message updated successfully"}), 200


# 🟢 Delete a contact message
@contact_bp.route("/messages/<int:id>", methods=["DELETE"])
def delete_contact_message(id):
    message = ContactMessage.query.get_or_404(id)
    db.session.delete(message)
    db.session.commit()
    return jsonify({"message": "Contact message deleted successfully"}), 200


# 🟢 Get message statistics
@contact_bp.route("/stats", methods=["GET"])
def get_contact_stats():
    total_messages = ContactMessage.query.count()
    new_messages = ContactMessage.query.filter_by(status="new").count()
    read_messages = ContactMessage.query.filter_by(status="read").count()
    replied_messages = ContactMessage.query.filter_by(status="replied").count()

    return (
        jsonify(
            {
                "total_messages": total_messages,
                "new_messages": new_messages,
                "read_messages": read_messages,
                "replied_messages": replied_messages,
            }
        ),
        200,
    )
