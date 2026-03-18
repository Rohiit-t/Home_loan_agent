"""
Configuration file for Home Loan Application System.

Contains all configuration parameters including mandatory documents,
financial thresholds, and application settings.
"""

# Document Configuration
MANDATORY_DOCS = ["pan", "aadhaar", "itr"]

# Financial Risk Assessment Thresholds
LTV_THRESHOLD = 80.0
FOIR_THRESHOLD = 50.0 
MIN_CIBIL = 700

# Application Settings
DEFAULT_TEMPERATURE = 0.4  # Default LLM temperature for queries
STRUCTURED_TEMPERATURE = 0.0  # Temperature for structured outputs

# EMI Calculation
DEFAULT_INTEREST_RATE = 8.5  # Annual interest rate in %

# Email Notification (Gmail SMTP)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "spidyshubham1@gmail.com" 
SMTP_PASSWORD = "tgps ovyv spqj iygo"

# Database Configuration (Neon DB - Serverless PostgreSQL)
DATABASE_URL = "postgresql://Rohit:npg_6cLbnUAMQCB1@ep-rough-fire-a1mim3e6.ap-southeast-1.aws.neon.tech/Home_loan_data?sslmode=require&channel_binding=require"