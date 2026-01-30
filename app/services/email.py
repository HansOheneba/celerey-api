import os
import resend
from dotenv import load_dotenv
from typing import Dict, Any, List
from datetime import datetime
from dateutil import parser
from zoneinfo import ZoneInfo 

# Load environment variables
load_dotenv()


def format_datetime_readable(dt_value: Any, tz_name: str = "Africa/Accra") -> str:
    """
    Accepts datetime | ISO string | None and returns a readable string:
    "Fri, 30 Jan 2026, 14:05 (Africa/Accra)"
    """
    if not dt_value:
        # fallback to "now"
        dt = datetime.now(tz=ZoneInfo(tz_name))
    elif isinstance(dt_value, datetime):
        dt = dt_value
        # If naive, assume UTC then convert (adjust if your DB stores local time)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        dt = dt.astimezone(ZoneInfo(tz_name))
    elif isinstance(dt_value, str):
        # parse ISO or common datetime strings
        dt = parser.parse(dt_value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        dt = dt.astimezone(ZoneInfo(tz_name))
    else:
        # unknown type
        dt = datetime.now(tz=ZoneInfo(tz_name))

    return dt.strftime("%a, %d %b %Y, %H:%M") + f" ({tz_name})"

class EmailService:
    """Email service for sending admin notifications via Resend"""
    
    def __init__(self):
        """Initialize Resend with API key"""
        self.api_key = os.getenv("RESEND_API_KEY")
        
        # Warn but don't crash if API key is missing
        if not self.api_key:
            print("⚠️  RESEND_API_KEY not set. Email notifications will be disabled.")
            self.enabled = False
            return
        
        resend.api_key = self.api_key
        self.enabled = True
        
        # Email configuration
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "notifications@celerey.co")
        
        # Get admin emails from environment
        admin_emails = os.getenv("ADMIN_NOTIFICATION_EMAILS", "")
        self.admin_emails = [email.strip() for email in admin_emails.split(",") if email.strip()]
        
        if not self.admin_emails:
            print("⚠️  ADMIN_NOTIFICATION_EMAILS not set. No recipients configured.")
    
    def send_lead_notification(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification about new lead to admin team
        
        Args:
            lead_data: Dictionary containing lead information
        
        Returns:
            Response from Resend API or error info
        """
        # Check if email service is enabled
        if not self.enabled:
            return {"ok": False, "error": "Email service disabled - missing API key"}
        
        # Check if we have recipients
        if not self.admin_emails:
            return {"ok": False, "error": "No admin recipients configured"}
        
        try:
            # Create email content
            subject = f"New Lead: {lead_data.get('first_name', 'New')} {lead_data.get('last_name', 'Lead')}"
            
            # Send email via Resend
            response = resend.Emails.send({
                "from": f"Celerey Leads <{self.from_email}>",
                "to": self.admin_emails,
                "subject": subject,
                "html": self._create_html_email(lead_data),
                "text": self._create_text_email(lead_data),
                "reply_to": lead_data.get("email"),
                "tags": [
                    {"name": "category", "value": "lead-notification"},
                    {"name": "source", "value": lead_data.get("source", "begin_journey")}
                ]
            })
            
            print(f"✓ Admin notification sent. ID: {response.get('id')}")
            return {"ok": True, "email_id": response.get("id")}
            
        except Exception as e:
            print(f"✗ Failed to send admin notification: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def _create_html_email(self, lead_data: Dict[str, Any]) -> str:
        """Create clean HTML email for admin notification"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1B1856; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 8px 8px; }}
                .lead-info {{ background: white; padding: 15px; border-radius: 6px; margin-bottom: 15px; }}
                .field {{ margin-bottom: 8px; }}
                .field-label {{ font-weight: 600; color: #495057; }}
                .actions {{ text-align: center; margin-top: 20px; }}
                .button {{ display: inline-block; background: #1B1856; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">New Lead Alert</h2>
                    <p style="margin: 5px 0 0; opacity: 0.9;">Begin Journey Modal Submission</p>
                </div>
                
                <div class="content">
                    <div class="lead-info">
                        <h3 style="margin-top: 0; color: #1B1856;">Lead Details</h3>
                        
                        <div class="field">
                            <span class="field-label"> Name:</span>
                            <span>{lead_data.get('first_name')} {lead_data.get('last_name')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label"> Email:</span>
                            <span><a href="mailto:{lead_data.get('email')}">{lead_data.get('email')}</a></span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label"> Phone:</span>
                            <span>{lead_data.get('phone')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label"> Time Zone:</span>
                            <span>{lead_data.get('time_zone')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label"> Submitted:</span>
                            <span>{lead_data.get('created_at', 'Just now')}</span>
                        </div>
                    </div>
                    
                    <div class="actions">
                        <a href="mailto:{lead_data.get('email')}" class="button">Reply to Lead</a>
                    </div>
                    
                    <p style="text-align: center; margin-top: 20px; font-size: 12px; color: #6c757d;">
                        Lead ID: {lead_data.get('id', 'N/A')} • Sent by Celerey Lead System
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _create_text_email(self, lead_data: Dict[str, Any]) -> str:
        """Create plain text email for admin notification"""
        return f"""
NEW LEAD ALERT

Name: {lead_data.get('first_name')} {lead_data.get('last_name')}
Email: {lead_data.get('email')}
Phone: {lead_data.get('phone')}
Time Zone: {lead_data.get('time_zone')}
Submitted: {lead_data.get('created_at', 'Just now')}
Source: Begin Journey Modal

Lead ID: {lead_data.get('id', 'N/A')}

Reply to: {lead_data.get('email')}
        """