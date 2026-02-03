from flask import Blueprint, jsonify, request, make_response
from app.database import DBHelper
from datetime import datetime
import os
import stripe
from functools import wraps

billing_bp = Blueprint("billing_bp", __name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://celereyv2.vercel.app")

# Add CORS headers (following your pattern)
@billing_bp.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses"""
    # Allow specific origins (matching your existing setup)
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
    response.headers.add('Access-Control-Max-Age', '86400')
    
    return response

# Helper decorator for validating user_id
def require_user_id(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.args.get('user_id') or request.json.get('user_id') if request.is_json else None
        
        if not user_id:
            return jsonify({
                "ok": False,
                "error": "MISSING_USER_ID",
                "message": "User ID is required"
            }), 400
        
        # Verify user exists
        user_query = "SELECT id FROM users WHERE id = %s"
        user = DBHelper.execute_query(user_query, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                "ok": False,
                "error": "USER_NOT_FOUND",
                "message": "User does not exist"
            }), 404
            
        return f(user_id, *args, **kwargs)
    return decorated_function

@billing_bp.route("/checkout", methods=["POST", "OPTIONS"])
def create_checkout_session():
    """Create a Stripe Checkout session"""
    if request.method == "OPTIONS":
        return make_response(("", 200))
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "ok": False,
                "error": "VALIDATION_ERROR",
                "details": {"body": "Request body must be valid JSON"}
            }), 400
        
        user_id = data.get("user_id")
        
        if not user_id:
            return jsonify({
                "ok": False,
                "error": "VALIDATION_ERROR",
                "details": {"user_id": "User ID is required"}
            }), 400
        
        # Verify user exists
        user_query = "SELECT id, email, has_paid FROM users WHERE id = %s"
        user = DBHelper.execute_query(user_query, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                "ok": False,
                "error": "USER_NOT_FOUND",
                "message": "User does not exist"
            }), 404
        
        # Check if user already paid
        if user.get("has_paid"):
            return jsonify({
                "ok": False,
                "error": "ALREADY_PAID",
                "message": "User already has access"
            }), 400
        
        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": STRIPE_PRICE_ID,
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/payment/cancel",
            metadata={
                "user_id": str(user_id)
            },
            customer_email=user.get("email"),  # Pre-fill email if available
            expires_at=int((datetime.now().timestamp() + 3600)),  # 1 hour expiry
        )
        
        return jsonify({
            "ok": True,
            "sessionId": checkout_session.id,
            "url": checkout_session.url,
            "expires_at": checkout_session.expires_at
        }), 200
        
    except stripe.error.StripeError as e:
        print(f"Stripe error in create_checkout_session: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "STRIPE_ERROR",
            "message": "Payment service error"
        }), 500
    except Exception as e:
        print(f"Error in create_checkout_session: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong. Please try again."
        }), 500

@billing_bp.route("/webhook", methods=["POST"])
def handle_webhook():
    """Handle Stripe webhook events"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header:
        return jsonify({"ok": False, "error": "Missing Stripe-Signature header"}), 400
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        print(f"Webhook error: Invalid payload - {str(e)}")
        return jsonify({"ok": False, "error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Webhook error: Invalid signature - {str(e)}")
        return jsonify({"ok": False, "error": "Invalid signature"}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Only process paid sessions
        if session.get('payment_status') != 'paid':
            print(f"Ignoring unpaid session: {session.get('id')}")
            return jsonify({"ok": True, "message": "Session not paid, ignoring"}), 200
        
        user_id = session.get('metadata', {}).get('user_id')
        
        if not user_id:
            print(f"No user_id in session metadata: {session.get('id')}")
            return jsonify({"ok": False, "error": "Missing user_id in metadata"}), 400
        
        # Check if user already marked as paid (idempotency)
        check_query = """
            SELECT has_paid, stripe_latest_session_id 
            FROM users 
            WHERE id = %s
        """
        existing_user = DBHelper.execute_query(check_query, (user_id,), fetch_one=True)
        
        if existing_user and existing_user.get('has_paid'):
            # Check if this is the same session ID
            if existing_user.get('stripe_latest_session_id') == session.get('id'):
                print(f"Payment already processed for user {user_id}, session {session.get('id')}")
                return jsonify({"ok": True, "message": "Already processed"}), 200
        
        try:
            # Update user with payment details
            update_query = """
                UPDATE users 
                SET 
                    has_paid = 1,
                    paid_at = %s,
                    stripe_customer_id = %s,
                    stripe_latest_session_id = %s,
                    stripe_latest_payment_intent_id = %s
                WHERE id = %s
            """
            
            DBHelper.execute_query(
                update_query,
                (
                    datetime.now(),
                    session.get('customer'),
                    session.get('id'),
                    session.get('payment_intent'),
                    user_id
                )
            )
            
            print(f"✓ Payment processed for user {user_id}, session {session.get('id')}")
            
            return jsonify({
                "ok": True,
                "message": "Payment processed successfully",
                "user_id": user_id
            }), 200
            
        except Exception as e:
            print(f"Error updating user payment status: {str(e)}")
            return jsonify({
                "ok": False,
                "error": "DATABASE_ERROR",
                "message": "Failed to update user"
            }), 500
    
    elif event['type'] == 'checkout.session.expired':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        print(f"Checkout session expired for user {user_id}: {session.get('id')}")
        
        # You could optionally clear any pending state here
        return jsonify({"ok": True, "message": "Session expired noted"}), 200
    
    # Return success for other event types
    return jsonify({"ok": True, "message": "Event received"}), 200

@billing_bp.route("/access", methods=["GET", "OPTIONS"])
@require_user_id
def check_access(user_id):
    """Check if user has paid access"""
    if request.method == "OPTIONS":
        return make_response(("", 200))
    
    try:
        # Always read from database (not Stripe)
        query = """
            SELECT 
                has_paid,
                paid_at,
                stripe_latest_session_id
            FROM users 
            WHERE id = %s
        """
        
        user = DBHelper.execute_query(query, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                "ok": False,
                "error": "USER_NOT_FOUND",
                "message": "User does not exist"
            }), 404
        
        return jsonify({
            "ok": True,
            "paid": bool(user.get('has_paid')),
            "paid_at": str(user.get('paid_at')) if user.get('paid_at') else None,
            "session_id": user.get('stripe_latest_session_id')
        }), 200
        
    except Exception as e:
        print(f"Error in check_access: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR",
            "message": "Something went wrong."
        }), 500

@billing_bp.route("/status", methods=["GET", "OPTIONS"])
@require_user_id
def get_payment_status(user_id):
    """Get detailed payment status"""
    if request.method == "OPTIONS":
        return make_response(("", 200))
    
    try:
        query = """
            SELECT 
                has_paid,
                paid_at,
                stripe_customer_id,
                stripe_latest_session_id,
                stripe_latest_payment_intent_id,
                created_at
            FROM users 
            WHERE id = %s
        """
        
        user = DBHelper.execute_query(query, (user_id,), fetch_one=True)
        
        if not user:
            return jsonify({
                "ok": False,
                "error": "USER_NOT_FOUND"
            }), 404
        
        return jsonify({
            "ok": True,
            "user": {
                "id": user_id,
                "has_paid": bool(user.get('has_paid')),
                "paid_at": str(user.get('paid_at')) if user.get('paid_at') else None,
                "stripe_customer_id": user.get('stripe_customer_id'),
                "stripe_session_id": user.get('stripe_latest_session_id'),
                "stripe_payment_intent_id": user.get('stripe_latest_payment_intent_id'),
                "created_at": str(user.get('created_at')) if user.get('created_at') else None
            }
        }), 200
        
    except Exception as e:
        print(f"Error in get_payment_status: {str(e)}")
        return jsonify({
            "ok": False,
            "error": "SERVER_ERROR"
        }), 500