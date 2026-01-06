from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime

services_bp = Blueprint("services_bp", __name__, url_prefix="/services")


@services_bp.route("/", methods=["GET"])
def get_services():
    try:
        query = """
            SELECT * FROM services
            WHERE active = TRUE
            ORDER BY price ASC
        """
        services = DBHelper.execute_query(query, fetch_all=True)

        result = []
        for service in services:
            result.append(
                {
                    "id": service["id"],
                    "name": service["name"],
                    "description": service["description"],
                    "price": float(service["price"]),
                    "duration": service["duration"],
                    "payment_link": service["payment_link"],
                    "active": bool(service["active"]),
                    "created_at": DBHelper.format_datetime(service["created_at"]),
                    "updated_at": DBHelper.format_datetime(service["updated_at"]),
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@services_bp.route("/<int:id>", methods=["GET"])
def get_service(id):
    try:
        query = "SELECT * FROM services WHERE id = %s"
        service = DBHelper.execute_query(query, (id,), fetch_one=True)

        if not service:
            return jsonify({"error": "Service not found"}), 404

        return (
            jsonify(
                {
                    "id": service["id"],
                    "name": service["name"],
                    "description": service["description"],
                    "price": float(service["price"]),
                    "duration": service["duration"],
                    "payment_link": service["payment_link"],
                    "active": bool(service["active"]),
                    "created_at": DBHelper.format_datetime(service["created_at"]),
                    "updated_at": DBHelper.format_datetime(service["updated_at"]),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@services_bp.route("/", methods=["POST"])
def add_service():
    try:
        data = request.get_json()

        required_fields = ["name", "description", "price"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        check_query = "SELECT id FROM services WHERE name = %s"
        existing = DBHelper.execute_query(check_query, (data["name"],), fetch_one=True)
        if existing:
            return jsonify({"error": "Service with this name already exists"}), 400

        insert_query = """
            INSERT INTO services (
              name, description, price, duration,
              payment_link, active, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        now = datetime.now()

        service_id = DBHelper.execute_query(
            insert_query,
            (
                data["name"],
                data["description"],
                data["price"],
                data.get("duration"),
                data.get("payment_link", ""),
                data.get("active", True),
                now,
                now,
            ),
            lastrowid=True,
        )

        return jsonify({"message": "Service added successfully", "id": service_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@services_bp.route("/<int:id>", methods=["PUT"])
def update_service(id):
    try:
        check_query = "SELECT id FROM services WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)

        if not existing:
            return jsonify({"error": "Service not found"}), 404

        data = request.get_json()
        update_fields = []
        params = []

        for field in [
            "name",
            "description",
            "price",
            "duration",
            "payment_link",
            "active",
        ]:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])

        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(id)

        update_query = f"""
            UPDATE services
            SET {', '.join(update_fields)}
            WHERE id = %s
        """

        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Service updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@services_bp.route("/<int:id>", methods=["DELETE"])
def delete_service(id):
    try:
        check_query = "SELECT id FROM services WHERE id = %s"
        existing = DBHelper.execute_query(check_query, (id,), fetch_one=True)

        if not existing:
            return jsonify({"error": "Service not found"}), 404

        delete_query = """
            UPDATE services
            SET active = FALSE, updated_at = %s
            WHERE id = %s
        """

        DBHelper.execute_query(delete_query, (datetime.now(), id))

        return jsonify({"message": "Service deactivated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
