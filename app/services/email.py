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
                    {"name": "source", "value": lead_data.get("source", "begin_journey")}  # FIXED THIS LINE
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
    
    def send_concierge_notification(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification about new concierge request to admin team
        
        Args:
            submission_data: Dictionary containing concierge request information
        
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
            subject = f"Concierge Request: {submission_data.get('first_name', 'New')} {submission_data.get('last_name', 'Request')}"
            
            # Get services list
            services_list = submission_data.get("selected_services_list", [])
            services_html = self._create_services_html(services_list)
            services_text = self._create_services_text(services_list)
            
            # Send email via Resend
            response = resend.Emails.send({
                "from": f"Celerey Concierge <{self.from_email}>",
                "to": self.admin_emails,
                "subject": subject,
                "html": self._create_concierge_html_email(submission_data, services_html),
                "text": self._create_concierge_text_email(submission_data, services_text),
                "reply_to": submission_data.get("email"),
                "tags": [
                    {"name": "category", "value": "concierge-notification"},
                    {"name": "source", "value": submission_data.get("source", "concierge_pricing")},
                    {"name": "service_count", "value": str(submission_data.get("service_count", 0))}
                ]
            })
            
            print(f"✓ Concierge admin notification sent. ID: {response.get('id')}")
            return {"ok": True, "email_id": response.get("id")}
            
        except Exception as e:
            print(f"✗ Failed to send concierge notification: {str(e)}")
            return {"ok": False, "error": str(e)}

    def _create_services_html(self, services_list: List[Dict]) -> str:
        """Create HTML for services list"""
        if not services_list:
            return "<p>No services selected</p>"
        
        html = "<div style='margin: 15px 0;'>"
        html += "<h4 style='margin-bottom: 10px; color: #495057;'>Selected Services:</h4>"
        html += "<ul style='margin: 10px 0; padding-left: 20px;'>"
        
        for idx, service in enumerate(services_list, 1):
            service_id = service.get('id', 'N/A')
            service_name = service.get('name', 'Unknown Service')
            pricing_type = service.get('pricingType', '')
            
            html += f"""
            <li style='margin-bottom: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px;'>
                <div style='font-weight: 600;'>{service_name}</div>
                <div style='font-size: 12px; color: #6c757d;'>
                    ID: {service_id}
                    {f'• Type: {pricing_type}' if pricing_type else ''}
                </div>
            </li>
            """
        
        html += "</ul></div>"
        return html

    def _create_services_text(self, services_list: List[Dict]) -> str:
        """Create plain text for services list"""
        if not services_list:
            return "Services Requested: None\n"
        
        text = "Services Requested:\n"
        for idx, service in enumerate(services_list, 1):
            service_id = service.get('id', 'N/A')
            service_name = service.get('name', 'Unknown Service')
            pricing_type = service.get('pricingType', '')
            
            text += f"  {idx}. {service_name} (ID: {service_id})"
            if pricing_type:
                text += f" [{pricing_type}]"
            text += "\n"
        
        return text

    def _create_concierge_html_email(self, submission_data: Dict[str, Any], services_html: str) -> str:
        """Create HTML email for concierge admin notification"""
        special_req = submission_data.get("special_requirements", "").strip()
        notes = submission_data.get("notes", "").strip()
        addl_context = submission_data.get("additional_context", "").strip()
        
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
                .info-box {{ background: white; padding: 15px; border-radius: 6px; margin-bottom: 15px; border-left: 4px solid #1B1856; }}
                .field {{ margin-bottom: 10px; }}
                .field-label {{ font-weight: 600; color: #495057; display: block; margin-bottom: 3px; font-size: 14px; }}
                .field-value {{ color: #333; }}
                .actions {{ text-align: center; margin-top: 25px; }}
                .button {{ display: inline-block; background: #1B1856; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: 500; }}
                .service-count {{ display: inline-block; background: #1B1856; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0; display: flex; align-items: center;">
                        New Concierge Request
                        <span class="service-count">{submission_data.get('service_count', 0)} services</span>
                    </h2>
                    <p style="margin: 5px 0 0; opacity: 0.9;">Custom Advisory Service Inquiry</p>
                </div>
                
                <div class="content">
                    <div class="info-box">
                        <h3 style="margin-top: 0; margin-bottom: 15px; color: #1B1856; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                            Client Information
                        </h3>
                        
                        <div class="field">
                            <span class="field-label">Full Name:</span>
                            <span class="field-value">{submission_data.get('first_name')} {submission_data.get('last_name')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">Email:</span>
                            <span class="field-value">
                                <a href="mailto:{submission_data.get('email')}" style="color: #1B1856; text-decoration: none;">
                                    {submission_data.get('email')}
                                </a>
                            </span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">Phone:</span>
                            <span class="field-value">{submission_data.get('phone')}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">Company:</span>
                            <span class="field-value">{submission_data.get('company') or 'Not specified'}</span>
                        </div>
                        
                        <div class="field">
                            <span class="field-label">Submitted:</span>
                            <span class="field-value">{submission_data.get('created_at', 'Just now')}</span>
                        </div>
                    </div>
                    
                    <!-- Services Section -->
                    <div class="info-box">
                        <h3 style="margin-top: 0; margin-bottom: 15px; color: #1B1856; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">
                            Service Selection
                        </h3>
                        {services_html}
                    </div>
                    
                    <!-- Additional Information Section -->
                    {self._get_additional_info_html(submission_data)}
                    
                    <div class="actions">
                        <a href="mailto:{submission_data.get('email')}?subject=Re: Your Celerey Concierge Request&body=Hi {submission_data.get('first_name')},%0D%0A%0D%0A" 
                           class="button">
                            Reply to Client
                        </a>
                    </div>
                    
                    <p style="text-align: center; margin-top: 25px; font-size: 12px; color: #6c757d; border-top: 1px solid #dee2e6; padding-top: 15px;">
                        Request ID: CR-{submission_data.get('id', 'N/A'):04d} • Submitted via Concierge Pricing Page • {submission_data.get('source', 'web')}
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def _get_additional_info_html(self, submission_data: Dict[str, Any]) -> str:
        """Get HTML for additional information if available"""
        special_req = submission_data.get("special_requirements", "").strip()
        notes = submission_data.get("notes", "").strip()
        addl_context = submission_data.get("additional_context", "").strip()
        
        if not special_req and not notes and not addl_context:
            return ""
        
        html = '<div class="info-box">'
        html += '<h3 style="margin-top: 0; margin-bottom: 15px; color: #1B1856; border-bottom: 1px solid #dee2e6; padding-bottom: 8px;">'
        html += 'Additional Information'
        html += '</h3>'
        
        if special_req:
            html += f"""
            <div class="field">
                <span class="field-label">Special Requirements:</span>
                <div class="field-value" style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; font-size: 14px;">
                    {special_req}
                </div>
            </div>
            """
        
        if notes:
            html += f"""
            <div class="field">
                <span class="field-label">Notes:</span>
                <div class="field-value" style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; font-size: 14px;">
                    {notes}
                </div>
            </div>
            """
        
        if addl_context:
            html += f"""
            <div class="field">
                <span class="field-label">Additional Context:</span>
                <div class="field-value" style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; font-size: 14px;">
                    {addl_context}
                </div>
            </div>
            """
        
        html += '</div>'
        return html

    def _create_concierge_text_email(self, submission_data: Dict[str, Any], services_text: str) -> str:
        """Create plain text email for concierge admin notification"""
        special_req = submission_data.get("special_requirements", "").strip()
        notes = submission_data.get("notes", "").strip()
        addl_context = submission_data.get("additional_context", "").strip()
        
        text = f"""
NEW CONCIERGE REQUEST - CUSTOM ADVISORY INQUIRY
{'='*50}

CLIENT INFORMATION:
Name:     {submission_data.get('first_name')} {submission_data.get('last_name')}
Email:    {submission_data.get('email')}
Phone:    {submission_data.get('phone')}
Company:  {submission_data.get('company') or 'Not specified'}
Submitted: {submission_data.get('created_at', 'Just now')}

{services_text}
"""
        
        # Add additional information sections
        additional_sections = []
        
        if special_req:
            additional_sections.append(f"SPECIAL REQUIREMENTS:\n{submission_data.get('special_requirements')}")
        
        if notes:
            additional_sections.append(f"NOTES:\n{submission_data.get('notes')}")
        
        if addl_context:
            additional_sections.append(f"ADDITIONAL CONTEXT:\n{submission_data.get('additional_context')}")
        
        if additional_sections:
            text += "\nADDITIONAL INFORMATION:\n"
            text += "-" * 30 + "\n"
            text += "\n\n".join(additional_sections)
            text += "\n"
        
        text += f"""
{'='*50}
Request ID: CR-{submission_data.get('id', 'N/A'):04d}
Submitted via: {submission_data.get('source', 'concierge_pricing_page')}
Services Selected: {submission_data.get('service_count', 0)}

Reply to: {submission_data.get('email')}
"""
        
        return text