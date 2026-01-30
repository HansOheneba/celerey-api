from flask import Blueprint, jsonify, request, make_response
from app.database import DBHelper
from datetime import datetime
from app.services.email import EmailService
import re
import threading
import json
import time

concierge_bp = Blueprint("concierge_bp", __name__)

# Global list to track active threads
active_email_threads = []

@concierge_bp.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    # Allow specific origins (add your frontend URLs)
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "https://celereyv2.vercel.app",
        "https://celerey-api.vercel.app"
    ]
    
    origin = request.headers.get('Origin')
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
    
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Max-Age', '86400')  # 24 hours
    
    return response

@concierge_bp.route("/", methods=["OPTIONS"])
@concierge_bp.route("/<int:request_id>", methods=["OPTIONS"])
def options_handler(request_id=None):
    """Handle preflight OPTIONS request - FIX THE REDIRECT ISSUE HERE"""
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Max-Age', '86400')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response, 200

email_service = EmailService()

def send_concierge_admin_notification_async(submission_id: int, submission_data: dict):
    """Send admin notification in background thread for concierge requests"""
    if not email_service.enabled:
        return
    
    # Small delay to ensure Flask response is sent first
    time.sleep(0.5)
    
    try:
        result = email_service.send_concierge_notification(submission_data)
        if result.get("ok"):
            print(f"✓ Concierge admin notification sent for submission {submission_id}")
        else:
            print(f"⚠️ Failed to send concierge admin notification for submission {submission_id}: {result.get('error')}")
    except Exception as e:
        print(f"✗ Error in concierge notification thread: {str(e)}")

def cleanup_completed_threads():
    """Clean up completed threads from the global list"""
    global active_email_threads
    active_email_threads = [t for t in active_email_threads if t.is_alive()]

# Helper functions
def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def normalize_email(email):
    return email.strip().lower()

def validate_phone(phone):
    """Basic phone validation"""
    digits = ''.join(filter(str.isdigit, phone))
    return len(digits) >= 10

@concierge_bp.route("", methods=["POST"], strict_slashes=False)
@concierge_bp.route("/", methods=["POST"], strict_slashes=False)
def create_concierge_request():
    """Create a new concierge service request"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "ok": False,
                "error": "VALIDATION_ERROR",
                "details": {"body": "Request body must be valid JSON"}
            }), 400
        
        # Validate contact information
        contact = data.get("contact", {})
        selected_services = data.get("selectedServices", [])
        special_requirements = data.get("specialRequirements", "")
        notes = data.get("notes", "")
        additional_context = data.get("additionalContext", "")
        
        errors = {}
        
        # Required contact fields
        required_fields = ["firstName", "lastName", "email", "phone"]
        for field in required_fields:
            if not contact.get(field):
                errors[f"contact.{field}"] = f"{field} is required"
        
        # Email validation
        if contact.get("email") and not validate_email(contact.get("email")):
            errors["contact.email"] = "Invalid email format"
        
        # Phone validation
        if contact.get("phone") and not validate_phone(contact.get("phone")):
            errors["contact.phone"] = "Invalid phone number"
        
        # At least one service must be selected
        if not selected_services:
            errors["selectedServices"] = "At least one service must be selected"
        
        if errors:
            return jsonify({
                "ok": False,
                "error": "VALIDATION_ERROR",
                "details": errors
            }), 400
        
        # Prepare submission data
        submission_data = {
            "first_name": contact["firstName"].strip(),
            "last_name": contact["lastName"].strip(),
            "email": normalize_email(contact["email"]),
            "phone": contact["phone"].strip(),
            "location": contact.get("location", "").strip(),  # Changed from company to location
            "selected_services": json.dumps(selected_services),
            "special_requirements": special_requirements.strip() if special_requirements else "",
            "notes": notes.strip() if notes else "",
            "additional_context": additional_context.strip() if additional_context else "",
            "source": "concierge_pricing_page",
            "status": "new",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent")
        }
        
        # Insert into database - UPDATED QUERY
        query = """
            INSERT INTO concierge_requests (
                first_name, last_name, email, phone, location,  -- Changed from company to location
                selected_services, special_requirements, notes, additional_context,
                source, status, ip_address, user_agent, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        submission_id = DBHelper.execute_query(
            query,
            (
                submission_data["first_name"],
                submission_data["last_name"],
                submission_data["email"],
                submission_data["phone"],
                submission_data["location"],  # Changed from company to location
                submission_data["selected_services"],
                submission_data["special_requirements"],
                submission_data["notes"],
                submission_data["additional_context"],
                submission_data["source"],
                submission_data["status"],
                submission_data["ip_address"],
                submission_data["user_agent"],
                datetime.now()
            ),
            lastrowid=True
        )
        
        # Add additional data for email notification
        submission_data["id"] = submission_id
        submission_data["selected_services_list"] = selected_services
        submission_data["service_count"] = len(selected_services)
        
        # Send admin notification in background
        if email_service.enabled and email_service.admin_emails:
            thread = threading.Thread(
                target=send_concierge_admin_notification_async,
                args=(submission_id, submission_data),
                name=f"concierge-email-{submission_id}"
            )
            thread.daemon = False  # Keep thread alive until completion
            
            # Clean up old threads before starting new one
            cleanup_completed_threads()
            
            # Add to global tracking
            active_email_threads.append(thread)
            
            thread.start()
            
            # Wait a tiny bit to ensure thread starts (non-blocking)
            time.sleep(0.1)
            
            print(f"Started concierge admin notification for submission {submission_id}")
            print(f"Active email threads: {len([t for t in active_email_threads if t.is_alive()])}")
        else:
            print(f"No email notification sent for concierge submission {submission_id} (service disabled or no recipients)")
        
        return jsonify({
            "ok": True,
            "submissionId": submission_id,
            "message": "Thank you for your concierge request! We'll review your selection and get back to you with a detailed quote."
        }), 201
    
    except Exception as e:
        print(f"Error in create_concierge_request: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong. Please try again."
        }), 500

@concierge_bp.route("/", methods=["GET"])
def get_all_concierge_requests():
    """Get all concierge requests"""
    try:
        query = "SELECT * FROM concierge_requests ORDER BY created_at DESC"
        requests = DBHelper.execute_query(query, fetch_all=True)
        
        formatted_requests = []
        for req in requests:
            # Parse JSON services if they exist
            selected_services = []
            if req.get("selected_services"):
                try:
                    selected_services = json.loads(req["selected_services"])
                except json.JSONDecodeError:
                    selected_services = []
            
            formatted_requests.append({
                "id": req["id"],
                "firstName": req["first_name"],
                "lastName": req["last_name"],
                "email": req["email"],
                "phone": req["phone"],
                "location": req["location"],  # Changed from company to location
                "selectedServices": selected_services,
                "specialRequirements": req["special_requirements"],
                "notes": req["notes"],
                "additionalContext": req["additional_context"],
                "source": req["source"],
                "status": req["status"],
                "serviceCount": len(selected_services),
                "createdAt": str(req["created_at"])
            })
        
        return jsonify({
            "ok": True,
            "requests": formatted_requests,
            "count": len(formatted_requests)
        }), 200
    
    except Exception as e:
        print(f"Error in get_all_concierge_requests: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong."
        }), 500

@concierge_bp.route("/<int:request_id>", methods=["GET"])
def get_concierge_request(request_id):
    """Get a single concierge request"""
    try:
        query = "SELECT * FROM concierge_requests WHERE id = %s"
        request_data = DBHelper.execute_query(query, (request_id,), fetch_one=True)
        
        if not request_data:
            return jsonify({"ok": False, "error": "Request not found"}), 404
        
        # Parse JSON services if they exist
        selected_services = []
        if request_data.get("selected_services"):
            try:
                selected_services = json.loads(request_data["selected_services"])
            except json.JSONDecodeError:
                selected_services = []
        
        return jsonify({
            "ok": True,
            "request": {
                "id": request_data["id"],
                "firstName": request_data["first_name"],
                "lastName": request_data["last_name"],
                "email": request_data["email"],
                "phone": request_data["phone"],
                "location": request_data["location"],  # Changed from company to location
                "selectedServices": selected_services,
                "specialRequirements": request_data["special_requirements"],
                "notes": request_data["notes"],
                "additionalContext": request_data["additional_context"],
                "source": request_data["source"],
                "status": request_data["status"],
                "createdAt": str(request_data["created_at"])
            }
        }), 200
    
    except Exception as e:
        print(f"Error in get_concierge_request: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong."
        }), 500