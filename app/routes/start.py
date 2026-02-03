from flask import Blueprint, jsonify, request, make_response
from app.database import DBHelper
from datetime import datetime
from app.services.email import EmailService
import re
import threading
import uuid

start_bp = Blueprint("start_bp", __name__)

def add_cors_headers(response):
    """Add CORS headers to response"""
    origin = request.headers.get("Origin", "")
    allowed_origins = [
        "http://localhost:3000",
        "https://celereyv2.vercel.app",
        "https://celerey-api.vercel.app"
    ]
    
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = request.headers.get("Access-Control-Request-Headers", "Content-Type, Authorization, X-Requested-With")
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response

@start_bp.before_request
def handle_preflight():
    """Handle preflight OPTIONS requests"""
    if request.method == 'OPTIONS':
        response = make_response('', 204)
        return add_cors_headers(response)

@start_bp.after_request
def after_request(response):
    """Apply CORS headers to all responses"""
    return add_cors_headers(response)

email_service = EmailService()

def send_admin_notification(lead_id: int, user_data: dict):
    """Send admin notification synchronously"""
    if not email_service.enabled:
        print(f"Email service disabled for user {user_data.get('id')}")
        return
    
    try:
        # Format user data for lead notification
        lead_data = {
            "id": lead_id,
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "email": user_data.get("email"),
            "phone": user_data.get("phone"),
            "time_zone": user_data.get("time_zone"),
            "user_id": user_data.get("id")
        }
        
        result = email_service.send_lead_notification(lead_data)
        if result.get("ok"):
            print(f"✓ Admin notification sent for user {user_data.get('id')}")
        else:
            print(f"⚠️  Failed to send admin notification: {result.get('error')}")
    except Exception as e:
        print(f"✗ Error sending lead notification: {str(e)}")

# Helper functions
def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def normalize_email(email):
    return email.strip().lower()

@start_bp.route("", methods=["POST"])
def begin_journey():
    """Create a new user and support lead"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "ok": False,
                "error": "VALIDATION_ERROR",
                "details": {"body": "Request body must be valid JSON"}
            }), 400
        
        # Basic validation
        errors = {}
        required = ["firstName", "lastName", "email", "phone", "timeZone", "agree"]
        
        for field in required:
            if not data.get(field):
                errors[field] = f"{field} is required"
        
        if "email" in data and data["email"] and not validate_email(data["email"]):
            errors["email"] = "Invalid email format"
        
        if errors:
            return jsonify({
                "ok": False,
                "error": "VALIDATION_ERROR",
                "details": errors
            }), 400
        
        # Generate UUID for user
        user_uuid = str(uuid.uuid4())
        normalized_email = normalize_email(data["email"])
        now = datetime.now()
        
        # Check if user already exists by email
        user_check_query = "SELECT id FROM users WHERE email = %s"
        existing_user = DBHelper.execute_query(user_check_query, (normalized_email,), fetch_one=True)
        
        if existing_user:
            # User exists, return their ID
            user_id = existing_user["id"]
            print(f"User already exists with ID: {user_id}")
        else:
            # Create new user
            user_data = {
                "id": user_uuid,
                "first_name": data["firstName"].strip(),
                "last_name": data["lastName"].strip(),
                "email": normalized_email,
                "phone": data["phone"].strip(),
                "time_zone": data["timeZone"].strip(),
                "consent_to_contact": bool(data["agree"]),
                "has_paid": 0,
                "created_at": now
            }
            
            # Insert into users table
            user_query = """
                INSERT INTO users (
                    id, first_name, last_name, email, phone,
                    time_zone, consent_to_contact, has_paid, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            user_id = DBHelper.execute_query(
                user_query,
                (
                    user_data["id"],
                    user_data["first_name"],
                    user_data["last_name"],
                    user_data["email"],
                    user_data["phone"],
                    user_data["time_zone"],
                    user_data["consent_to_contact"],
                    user_data["has_paid"],
                    user_data["created_at"]
                ),
                lastrowid=False  # We're using UUID, not auto-increment
            )
            
            if not user_id:
                user_id = user_uuid
            
            print(f"✓ Created new user with ID: {user_id}")
        
        # Also create support lead record (for legacy compatibility)
        lead_data = {
            "first_name": data["firstName"].strip(),
            "last_name": data["lastName"].strip(),
            "email": normalized_email,
            "phone": data["phone"].strip(),
            "time_zone": data["timeZone"].strip(),
            "consent_to_contact": bool(data["agree"]),
            "source": "begin_journey_modal",
            "status": "new",
            "user_id": user_id,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent")
        }
        
        lead_query = """
            INSERT INTO support_leads (
                first_name, last_name, email, phone,
                time_zone, consent_to_contact,
                source, status, user_id,
                ip_address, user_agent,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        lead_id = DBHelper.execute_query(
            lead_query,
            (
                lead_data["first_name"],
                lead_data["last_name"],
                lead_data["email"],
                lead_data["phone"],
                lead_data["time_zone"],
                lead_data["consent_to_contact"],
                lead_data["source"],
                lead_data["status"],
                lead_data["user_id"],
                lead_data["ip_address"],
                lead_data["user_agent"],
                now
            ),
            lastrowid=True
        )
        
        # Send admin notification
        if email_service.enabled and email_service.admin_emails:
            print(f"Sending admin notification for user {user_id}")
            
            try:
                # Combine user and lead data for notification
                notification_data = {
                    **lead_data,
                    "id": lead_id,
                    "user_id": user_id
                }
                
                result = email_service.send_lead_notification(notification_data)
                if result.get("ok"):
                    print(f"✓ Admin notification sent for user {user_id}")
                else:
                    print(f"⚠️ Failed to send admin notification: {result.get('error')}")
                    
            except Exception as e:
                print(f"✗ Email error: {str(e)}")
        else:
            print(f"No email notification sent (service disabled or no recipients)")
        
        return jsonify({
            "ok": True,
            "userId": user_id,
            "leadId": lead_id,
            "message": "Thanks — we'll reach out via email shortly."
        }), 201
    
    except Exception as e:
        print(f"Error in begin_journey: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong. Please try again."
        }), 500


@start_bp.route("", methods=["GET"])
def get_all_leads():
    """Get all leads"""
    try:
        query = "SELECT * FROM support_leads ORDER BY created_at DESC"
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
                "agree": bool(lead["consent_to_contact"]),
                "source": lead["source"],
                "status": lead["status"],
                "createdAt": str(lead["created_at"])
            })
        
        return jsonify({
            "ok": True,
            "leads": formatted_leads,
            "count": len(formatted_leads)
        }), 200
    
    except Exception as e:
        print(f"Error in get_all_leads: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong."
        }), 500

@start_bp.route("/<int:lead_id>", methods=["GET"])
def get_lead(lead_id):
    """Get a single lead"""
    try:
        query = "SELECT * FROM support_leads WHERE id = %s"
        lead = DBHelper.execute_query(query, (lead_id,), fetch_one=True)
        
        if not lead:
            return jsonify({"ok": False, "error": "Lead not found"}), 404
        
        return jsonify({
            "ok": True,
            "lead": {
                "id": lead["id"],
                "firstName": lead["first_name"],
                "lastName": lead["last_name"],
                "email": lead["email"],
                "phone": lead["phone"],
                "timeZone": lead["time_zone"],
                "agree": bool(lead["consent_to_contact"]),
                "source": lead["source"],
                "status": lead["status"],
                "createdAt": str(lead["created_at"])
            }
        }), 200
    
    except Exception as e:
        print(f"Error in get_lead: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong."
        }), 500
    
@start_bp.route("", methods=["OPTIONS"])
def options_root():
    """Handle preflight OPTIONS request"""
    response = make_response('', 204)
    return add_cors_headers(response)