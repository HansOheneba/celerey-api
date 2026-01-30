from app.services.email import EmailService

def test_email():
    """Test email notification"""
    service = EmailService()
    
    if not service.enabled:
        print("Email service is disabled (no API key)")
        return
    
    if not service.admin_emails:
        print("No admin recipients configured")
        return
    
    test_lead = {
        "id": 999,
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "time_zone": "America/New_York",
        "created_at": "2024-01-30 10:00:00"
    }
    
    print(f"Sending test email to: {service.admin_emails}")
    result = service.send_lead_notification(test_lead)
    print(f"Result: {result}")

if __name__ == "__main__":
    test_email()