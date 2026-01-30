-- Create support_leads table for lead capture from BeginJourneyModal
CREATE TABLE IF NOT EXISTS support_leads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    time_zone VARCHAR(100) NOT NULL,
    consent_to_contact BOOLEAN NOT NULL DEFAULT TRUE,
    offer_id VARCHAR(255),
    price_label VARCHAR(255),
    source VARCHAR(100) NOT NULL DEFAULT 'begin_journey_modal',
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    ip_address VARCHAR(45),
    user_agent TEXT,
    internal_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
