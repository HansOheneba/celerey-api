from flask import Blueprint, jsonify, request, make_response
from app.database import DBHelper
from datetime import datetime
from app.services.email import EmailService
import re
import threading
import time

start_bp = Blueprint("start_bp", __name__)

# Global list to track active threads
active_lead_threads = []

@start_bp.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

email_service = EmailService()

def send_admin_notification_async(lead_id: int, lead_data: dict):
    """Send admin notification in background thread"""
    if not email_service.enabled:
        return
    
    # Small delay to ensure Flask response is sent first
    time.sleep(0.5)
    
    try:
        result = email_service.send_lead_notification(lead_data)
        if result.get("ok"):
            print(f"✓ Admin notification sent for lead {lead_id}")
        else:
            print(f"⚠️  Failed to send admin notification for lead {lead_id}: {result.get('error')}")
    except Exception as e:
        print(f"✗ Error in notification thread: {str(e)}")

def cleanup_completed_threads():
    """Clean up completed threads from the global list"""
    global active_lead_threads
    active_lead_threads = [t for t in active_lead_threads if t.is_alive()]

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
        
        # Send admin notification in background
        if email_service.enabled and email_service.admin_emails:
            thread = threading.Thread(
                target=send_admin_notification_async,
                args=(lead_id, lead_data),
                name=f"lead-email-{lead_id}"
            )
            thread.daemon = False  # Keep thread alive until completion
            
            # Clean up old threads before starting new one
            cleanup_completed_threads()
            
            # Add to global tracking
            active_lead_threads.append(thread)
            
            thread.start()
            
            # Wait a tiny bit to ensure thread starts (non-blocking)
            time.sleep(0.1)
            
            print(f"Started admin notification for lead {lead_id}")
            print(f"Active lead threads: {len([t for t in active_lead_threads if t.is_alive()])}")
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
    return make_response(("", 200))