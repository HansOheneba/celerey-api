from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime
import json

plans_bp = Blueprint("plans_bp", __name__, url_prefix="/plans")


# 🟢 Get all plans
@plans_bp.route("/", methods=["GET"])
def get_plans():
    try:
        query = "SELECT * FROM plans ORDER BY price ASC"
        plans = DBHelper.execute_query(query, fetch_all=True)

        result = []
        for plan in plans:
            # Parse JSON features
            features = json.loads(plan["features"]) if plan["features"] else []

            result.append(
                {
                    "id": plan["id"],
                    "name": plan["name"],
                    "description": plan["description"],
                    "tagline": plan["tagline"],  # Add this line
                    "price": float(plan["price"]) if plan["price"] else None,
                    "billing_cycle": plan["billing_cycle"],
                    "features": features,
                    "payment_link": plan["payment_link"],
                    "button_text": plan["button_text"],
                    "popular": bool(plan["popular"]),
                    "created_at": DBHelper.format_datetime(plan["created_at"]),
                    "updated_at": DBHelper.format_datetime(plan["updated_at"]),
                }
            )

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Get a single plan by ID
@plans_bp.route("/<int:id>", methods=["GET"])
def get_plan(id):
    try:
        query = "SELECT * FROM plans WHERE id = %s"
        plan = DBHelper.execute_query(query, (id,), fetch_one=True)

        if not plan:
            return jsonify({"error": "Plan not found"}), 404

        # Parse JSON features
        features = json.loads(plan["features"]) if plan["features"] else []

        return (
            jsonify(
                {
                    "id": plan["id"],
                    "name": plan["name"],
                    "description": plan["description"],
                    "tagline": plan["tagline"],  # Add this line
                    "price": float(plan["price"]) if plan["price"] else None,
                    "billing_cycle": plan["billing_cycle"],
                    "features": features,
                    "payment_link": plan["payment_link"],
                    "button_text": plan["button_text"],
                    "popular": bool(plan["popular"]),
                    "created_at": DBHelper.format_datetime(plan["created_at"]),
                    "updated_at": DBHelper.format_datetime(plan["updated_at"]),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Add a new plan
@plans_bp.route("/", methods=["POST"])
def add_plan():
    try:
        data = request.get_json()

        # Basic validation
        required_fields = [
            "name",
            "description",
            "tagline",
            "price",
            "billing_cycle",
            "features",
        ]  # Updated
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if plan name already exists
        check_query = "SELECT id FROM plans WHERE name = %s"
        existing_plan = DBHelper.execute_query(
            check_query, (data["name"],), fetch_one=True
        )
        if existing_plan:
            return jsonify({"error": "Plan with this name already exists"}), 400

        # Insert new plan
        insert_query = """
            INSERT INTO plans (name, description, tagline, price, billing_cycle, features, 
                             payment_link, button_text, popular, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Convert features list to JSON string
        features_json = json.dumps(data["features"])

        now = datetime.now()

        plan_id = DBHelper.execute_query(
            insert_query,
            (
                data["name"],
                data["description"],
                data["tagline"],  # Add this line
                data["price"],
                data["billing_cycle"],
                features_json,
                data.get("payment_link", ""),
                data.get("button_text", "Get Started"),
                data.get("popular", False),
                now,
                now,
            ),
            lastrowid=True,
        )

        return jsonify({"message": "Plan added successfully", "id": plan_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Update plan
@plans_bp.route("/<int:id>", methods=["PUT"])
def update_plan(id):
    try:
        # Check if plan exists
        check_query = "SELECT id FROM plans WHERE id = %s"
        existing_plan = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing_plan:
            return jsonify({"error": "Plan not found"}), 404

        data = request.get_json()
        update_fields = []
        params = []

        for field in [
            "name",
            "description",
            "tagline",  # Add this line
            "price",
            "billing_cycle",
            "payment_link",
            "button_text",
        ]:
            if field in data:
                update_fields.append(f"{field} = %s")
                params.append(data[field])

        if "features" in data and isinstance(data["features"], list):
            update_fields.append("features = %s")
            params.append(json.dumps(data["features"]))

        if "popular" in data:
            update_fields.append("popular = %s")
            params.append(data["popular"])

        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(id)

        update_query = f"UPDATE plans SET {', '.join(update_fields)} WHERE id = %s"
        DBHelper.execute_query(update_query, params)

        return jsonify({"message": "Plan updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Delete plan (remains the same)
@plans_bp.route("/<int:id>", methods=["DELETE"])
def delete_plan(id):
    try:
        # Check if plan exists
        check_query = "SELECT id FROM plans WHERE id = %s"
        existing_plan = DBHelper.execute_query(check_query, (id,), fetch_one=True)
        if not existing_plan:
            return jsonify({"error": "Plan not found"}), 404

        delete_query = "DELETE FROM plans WHERE id = %s"
        DBHelper.execute_query(delete_query, (id,))

        return jsonify({"message": "Plan deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🟢 Get table schema
@plans_bp.route("/table-schema", methods=["GET"])
def table_schema():
    try:
        query = "DESCRIBE plans"
        schema = DBHelper.execute_query(query, fetch_all=True)
        return jsonify({"schema": schema}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
