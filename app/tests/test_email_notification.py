"""
Test case for email_notification node in HomeLoanAgent.
Prompts user for email in terminal, stores in state['personal_info']['email'],
then runs only the email_notification node and prints the result.
"""

from app.backend.nodes.agent import HomeLoanAgent
from app.backend.schema.state import ApplicationState


def test_email_notification():
    print("=" * 60)
    print("EMAIL NOTIFICATION NODE TEST")
    print("=" * 60)
    agent = HomeLoanAgent()
    
    # Prompt user for email
    print("\n📧 Please provide your email for testing...")
    user_email = input("Enter your email address for notification test: ").strip()
    
    if not user_email:
        print("❌ No email provided. Test aborted.")
        return
    
    print(f"✓ Email set to: {user_email}")
    print("\n🔄 Executing email_notification node...\n")
    
    # Build minimal state
    state = ApplicationState(
        user_id="test_user_123",
        personal_info={
            "name": "Test User",
            "email": user_email
        },
        financial_info={
            "home_loan_amount": 5000000,
            "down_payment": 1000000,
            "tenure_years": 20
        },
        employment_info={
            "employer_name": "TestCorp",
            "employment_type": "Salaried"
        },
        financial_metrics={
            "ltv_ratio": 80.0,
            "foir_ratio": 40.0,
            "cibil_score": 750
        },
        emi_details={
            "monthly_emi": 43200.0,
            "annual_interest_rate": 8.5,
            "total_interest_payable": 5300000.0,
            "total_amount_payable": 10300000.0
        },
        messages=[],
        current_stage="email_notification",
        application_saved=True,
        email_sent=False,
        paused_reason=None,
        retry_count=0
    )
    result = agent.email_notification(state)
    
    print("\n" + "=" * 60)
    print("EMAIL NOTIFICATION NODE OUTPUT")
    print("=" * 60)
    for msg in result["messages"]:
        print(msg.content)
    print("\n" + "-" * 60)
    print(f"Email sent status: {result.get('email_sent')}")
    print(f"Current stage: {result.get('current_stage')}")
    print("=" * 60)
    
    if not result.get("email_sent"):
        print("\n💡 TROUBLESHOOTING:")
        print("   If email was not sent, check the following:")
        print("   1. SMTP_EMAIL and SMTP_PASSWORD are set in config.py")
        print("   2. Gmail App Password is used (not regular password)")
        print("   3. Gmail account has 2FA enabled")
        print("   4. Network connection is available")
    else:
        print(f"\n✅ SUCCESS: Email sent to {user_email}")
        print("   Check your inbox (and spam folder)!")

if __name__ == "__main__":
    test_email_notification()
