from flask import Blueprint, jsonify, request, make_response
from app.database import DBHelper
from datetime import datetime
from app.services.email import EmailService
import re
import threading

start_bp = Blueprint("start_bp", __name__)

def add_cors_headers(response):
    """Add CORS headers to response"""
    origin = request.headers.get("Origin", "")
    allowed_origins = {
        "http://localhost:3000",
        "https://https://celereyv2.vercel.app/",
    }
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Max-Age"] = "3600"
    response.headers["Access-Control-Allow-Credentials"] = "true"
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

def send_admin_notification(lead_id: int, lead_data: dict):
    """Send admin notification synchronously"""
    if not email_service.enabled:
        print(f"Email service disabled for lead {lead_id}")
        return
    
    try:
        result = email_service.send_lead_notification(lead_data)
        if result.get("ok"):
            print(f"✓ Admin notification sent for lead {lead_id}")
        else:
            print(f"⚠️  Failed to send admin notification for lead {lead_id}: {result.get('error')}")
    except Exception as e:
        print(f"✗ Error sending lead notification: {str(e)}")

# Helper functions
def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def normalize_email(email):
    return email.strip().lower()

@start_bp.route("/", methods=["POST"])
def begin_journey():
    """Create a new lead"""
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
        
        # Prepare data
        lead_data = {
            "first_name": data["firstName"].strip(),
            "last_name": data["lastName"].strip(),
            "email": normalize_email(data["email"]),
            "phone": data["phone"].strip(),
            "time_zone": data["timeZone"].strip(),
            "consent_to_contact": data["agree"],
            "source": "begin_journey_modal",
            "status": "new",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent")
        }
        
        # Insert into database
        query = """
            INSERT INTO support_leads (
                first_name, last_name, email, phone,
                time_zone, consent_to_contact,
                source, status,
                ip_address, user_agent,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        lead_id = DBHelper.execute_query(
            query,
            (
                lead_data["first_name"],
                lead_data["last_name"],
                lead_data["email"],
                lead_data["phone"],
                lead_data["time_zone"],
                lead_data["consent_to_contact"],
                lead_data["source"],
                lead_data["status"],
                lead_data["ip_address"],
                lead_data["user_agent"],
                datetime.now()
            ),
            lastrowid=True
        )
        
        # Add ID to lead data for email notification
        lead_data["id"] = lead_id
        
        # Send admin notification synchronously (but fast)
        if email_service.enabled and email_service.admin_emails:
            print(f"Sending admin notification for lead {lead_id}")
            
            # Try synchronous sending first
            try:
                result = email_service.send_lead_notification(lead_data)
                if result.get("ok"):
                    print(f"✓ Admin notification sent synchronously for lead {lead_id}")
                else:
                    print(f"⚠️ Failed to send admin notification for lead {lead_id}: {result.get('error')}")
                    
                    # If sync fails, try async as fallback
                    thread = threading.Thread(
                        target=send_admin_notification,
                        args=(lead_id, lead_data),
                        daemon=False
                    )
                    thread.start()
                    print(f"Fallback: Started async notification for lead {lead_id}")
                    
            except Exception as e:
                print(f"✗ Sync email error, trying async: {str(e)}")
                # Fall back to async
                thread = threading.Thread(
                    target=send_admin_notification,
                    args=(lead_id, lead_data),
                    daemon=False
                )
                thread.start()
        else:
            print(f"No email notification sent for lead {lead_id} (service disabled or no recipients)")
        
        return jsonify({
            "ok": True,
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

@start_bp.route("/", methods=["GET"])
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
    
@start_bp.route("/", methods=["OPTIONS"])
def options_root():
    """Handle preflight OPTIONS request"""
    response = make_response('', 204)
    return add_cors_headers(response)