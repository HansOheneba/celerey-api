from flask import Blueprint, jsonify, request
from app.database import DBHelper
from datetime import datetime
import re

start_bp = Blueprint("start_bp", __name__, url_prefix="/start")


def validate_email(email):
    """Validate basic email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def normalize_email(email):
    """Normalize email: trim and lowercase"""
    return email.strip().lower()


@start_bp.route("/", methods=["POST"])
def begin_journey():
    """
    Capture lead data from BeginJourneyModal
    
    Accepts frontend field names:
    - firstName
    - lastName
    - email
    - phone
    - timeZone
    - agree (maps to consent_to_contact in DB)
    """
    try:
        data = request.get_json()
        
        if not data:
            return (
                jsonify({
                    "ok": False,
                    "error": "VALIDATION_ERROR",
                    "details": {"body": "Request body must be valid JSON"}
                }),
                400
            )
        
        # Validation
        errors = {}
        
        # Required field checks - using frontend field names
        required_fields = ["firstName", "lastName", "email", "phone", "timeZone", "agree"]
        for field in required_fields:
            if field not in data or data[field] is None:
                errors[field] = f"{field} is required"
            elif isinstance(data[field], str) and not data[field].strip():
                errors[field] = f"{field} cannot be empty"
        
        # Email validation
        if "email" in data and data["email"]:
            email = data["email"].strip()
            if not validate_email(email):
                errors["email"] = "Invalid email format"
        
        # agree must be true (frontend field name)
        if "agree" in data:
            if not isinstance(data.get("agree"), bool):
                errors["agree"] = "agree must be a boolean"
            elif not data["agree"]:
                errors["agree"] = "You must agree to continue"
        
        if errors:
            return (
                jsonify({
                    "ok": False,
                    "error": "VALIDATION_ERROR",
                    "details": errors
                }),
                400
            )
        
        # Prepare data for insertion
        # Keep frontend names for clarity, map to DB column names
        first_name = data["firstName"].strip()
        last_name = data["lastName"].strip()
        email = normalize_email(data["email"])
        phone = data["phone"].strip()
        time_zone = data["timeZone"].strip()
        consent_to_contact = data["agree"]  # Map 'agree' to 'consent_to_contact'
        
        
        # Metadata
        ip_address = request.remote_addr
        user_agent = request.headers.get("User-Agent")
        source = "begin_journey_modal"
        status = "new"
        created_at = datetime.now()
        
        # Insert into database
        # Include optional fields in query even if not used currently
        insert_query = """
            INSERT INTO support_leads (
                first_name, last_name, email, phone,
                time_zone, consent_to_contact,
                offer_id, price_label,
                source, status,
                ip_address, user_agent,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        lead_id = DBHelper.execute_query(
            insert_query,
            (
                first_name,
                last_name,
                email,
                phone,
                time_zone,
                consent_to_contact,
                source,
                status,
                ip_address,
                user_agent,
                created_at
            ),
            lastrowid=True
        )
        
        return (
            jsonify({
                "ok": True,
                "leadId": lead_id,
                "message": "Thanks — we'll reach out via email shortly."
            }),
            201
        )
    
    except Exception as e:
        print(f"Error in begin_journey: {str(e)}")
        return (
            jsonify({
                "ok": False,
                "error": "SERVER_ERROR",
                "message": "Something went wrong. Please try again."
            }),
            500
        )


@start_bp.route("/", methods=["GET"])
def get_all_leads():
    """Get all support leads - returns all fields"""
    try:
        query = """
            SELECT *
            FROM support_leads
            ORDER BY created_at DESC
        """
        
        leads = DBHelper.execute_query(query, fetch_all=True)
        
        formatted_leads = []
        for lead in leads:
            formatted_leads.append({
                "id": lead["id"],
                "firstName": lead["first_name"],
                "lastName": lead["last_name"],
                "email": lead["email"],
                "phone": lead["phone"],
                "timeZone": lead["time_zone"],
                "agree": bool(lead["consent_to_contact"]),  # Map back to frontend name
  
                "source": lead["source"],
                "status": lead["status"],
                "ipAddress": lead["ip_address"],
                "userAgent": lead["user_agent"],
                "internalNotes": lead["internal_notes"],
                "createdAt": DBHelper.format_datetime(lead["created_at"]) if hasattr(DBHelper, 'format_datetime') else str(lead["created_at"])
            })
        
        return jsonify({"ok": True, "leads": formatted_leads}), 200
    
    except Exception as e:
        print(f"Error in get_all_leads: {str(e)}")
        return (
            jsonify({
                "ok": False,
                "error": "SERVER_ERROR",
                "message": "Something went wrong. Please try again."
            }),
            500
        )


@start_bp.route("/<int:lead_id>", methods=["GET"])
def get_lead(lead_id):
    """
    Retrieve a support lead by ID
    Returns fields with frontend naming convention
    """
    try:
        query = """
            SELECT id, first_name, last_name, email, phone,
                   time_zone, consent_to_contact,
                   offer_id, price_label,
                   source, status,
                   ip_address, user_agent,
                   internal_notes,
                   created_at
            FROM support_leads
            WHERE id = %s
        """
        
        lead = DBHelper.execute_query(query, (lead_id,), fetch_one=True)
        
        if not lead:
            return jsonify({"ok": False, "error": "Lead not found"}), 404
        
        return (
            jsonify({
                "ok": True,
                "lead": {
                    "id": lead["id"],
                    "firstName": lead["first_name"],
                    "lastName": lead["last_name"],
                    "email": lead["email"],
                    "phone": lead["phone"],
                    "timeZone": lead["time_zone"],
                    "agree": bool(lead["consent_to_contact"]),  # Frontend field name
                   
                
                    "source": lead["source"],
                    "status": lead["status"],
                    "ipAddress": lead["ip_address"],
                    "userAgent": lead["user_agent"],
                    "internalNotes": lead["internal_notes"],
                    "createdAt": DBHelper.format_datetime(lead["created_at"]) if hasattr(DBHelper, 'format_datetime') else str(lead["created_at"])
                }
            }),
            200
        )
    
    except Exception as e:
        print(f"Error in get_lead: {str(e)}")
        return (
            jsonify({
                "ok": False,
                "error": "SERVER_ERROR",
                "message": "Something went wrong. Please try again."
            }),
            500
        )