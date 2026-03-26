"""
Email Service Module

Handles email notifications for the Home Loan Application System.
Sends professional application summary emails to applicants using Gmail SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple
from app.static.config import SMTP_HOST, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD


def send_application_summary_email(
    recipient_email: str,
    applicant_name: str,
    user_id: str,
    personal_info: Dict[str, Any],
    financial_info: Dict[str, Any],
    financial_metrics: Dict[str, Any],
    emi_details: Dict[str, Any]
) -> Tuple[str, bool]:
    """
    Send a professional application summary email to the applicant.
    
    Args:
        recipient_email: Email address of the recipient
        applicant_name: Name of the applicant
        user_id: Application/User ID
        personal_info: Personal information dictionary
        financial_info: Financial information dictionary
        financial_metrics: Financial risk metrics dictionary
        emi_details: EMI calculation details dictionary
        
    Returns:
        Tuple of (status_message, success_boolean)
    """
    
    # Validate email configuration
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return ("⚠️ Email: SMTP not configured. Notification skipped.", False)
    
    # Extract data for email
    monthly_emi = emi_details.get("monthly_emi", 0)
    loan_amount = financial_info.get("home_loan_amount", 0)
    down_payment = financial_info.get("down_payment", 0)
    tenure = financial_info.get("tenure_years", 0)
    total_interest = emi_details.get("total_interest_payable", 0)
    total_payable = emi_details.get("total_amount_payable", 0)
    ltv = financial_metrics.get("ltv_ratio", 0)
    foir = financial_metrics.get("foir_ratio", 0)
    cibil = financial_metrics.get("cibil_score", 0)
    interest_rate = emi_details.get("annual_interest_rate", 0)
    
    # Build HTML email body
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; max-width: 650px; margin: auto;">
        <div style="background: linear-gradient(135deg, #1a73e8, #0d47a1); padding: 25px; text-align: center; border-radius: 8px 8px 0 0;">
            <h1 style="color: white; margin: 0;">🏠 Home Loan Application</h1>
            <p style="color: #e0e0e0; margin: 5px 0 0;">Application Summary & Confirmation</p>
        </div>
        
        <div style="padding: 25px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
            <p>Dear <strong>{applicant_name}</strong>,</p>
            <p>Thank you for submitting your home loan application. Here is a summary of your application details:</p>
            
            <h3 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px;">📋 Application Details</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Application ID</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{user_id}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Applicant Name</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{applicant_name}</td></tr>
            </table>
            
            <h3 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px;">💰 Loan & EMI Details</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Loan Amount</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">₹{loan_amount:,.2f}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Down Payment</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">₹{down_payment:,.2f}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Tenure</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{tenure} years</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Interest Rate</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{interest_rate}% p.a.</td></tr>
                <tr style="background: #e8f5e9;"><td style="padding: 10px; font-size: 16px;"><strong>Monthly EMI</strong></td>
                    <td style="padding: 10px; font-size: 16px; color: #2e7d32;"><strong>₹{monthly_emi:,.2f}</strong></td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Total Interest</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">₹{total_interest:,.2f}</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Total Payable</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">₹{total_payable:,.2f}</td></tr>
            </table>
            
            <h3 style="color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 5px;">📊 Risk Assessment</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>LTV Ratio</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{ltv:.2f}%</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>FOIR</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{foir:.2f}%</td></tr>
                <tr><td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>CIBIL Score</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #eee;">{cibil}</td></tr>
            </table>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 6px; border-left: 4px solid #ff9800; margin-bottom: 20px;">
                <p style="margin: 0;"><strong> Next Steps:</strong></p>
                <ul style="margin: 8px 0 0; padding-left: 20px;">
                    <li>Our team will review your application within 2-3 business days.</li>
                    <li>You may be contacted for additional documentation.</li>
                    <li>Final approval is subject to property valuation and verification.</li>
                </ul>
            </div>
            
            <p style="color: #666; font-size: 12px; text-align: center; margin-top: 25px; border-top: 1px solid #eee; padding-top: 15px;">
                This is an auto-generated email from the Home Loan Application System.<br>
                Please do not reply to this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        # Create email message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"🏠 Home Loan Application Received - {applicant_name} ({user_id})"
        message["From"] = SMTP_EMAIL
        message["To"] = recipient_email
        
        message.attach(MIMEText(html_body, "html"))
        
        # Send email via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(message)
        
        return (f"✅ Email: Application summary sent to {recipient_email}", True)
        
    except smtplib.SMTPAuthenticationError:
        return ("⚠️ Email: SMTP authentication failed. Check credentials in config.", False)
    except Exception as e:
        return (f"❌ Email: Failed to send - {str(e)}", False)
