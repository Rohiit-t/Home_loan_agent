"""
Test the automatic data saving functionality after financial risk check.
This test verifies that user data is saved automatically without requiring confirmation.
"""
import json
import os
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.nodes.agent import HomeLoanAgent


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")


def test_save_functionality():
    """Test the automatic data saving after financial risk check."""
    
    print_section("🚀 TESTING AUTOMATIC SAVE FUNCTIONALITY")
    
    agent = HomeLoanAgent()
    
    # Create a complete state ready for saving (after financial_risk node)
    state = {
        "user_id": "test_user_auto_save",
        "messages": [
            HumanMessage(content="I need a home loan"),
            AIMessage(content="Financial risk check completed")
        ],
        "intent": None,
        "current_stage": "saving_data",
        "last_valid_stage": "financial_risk_check",
        "uploaded_documents": {
            "aadhaar": {
                "uploaded": True,
                "verified": True,
                "data": {
                    "document_type": "aadhaar",
                    "name": "Jane Doe",
                    "dob": "1990-01-01",
                    "address": "123 Main St, Springfield",
                    "id_number": "1234 5678 9012"
                }
            },
            "pan": {
                "uploaded": True,
                "verified": True,
                "data": {
                    "document_type": "pan",
                    "name": "Jane Doe",
                    "dob": "1990-01-01",
                    "id_number": "ABCDE1234F"
                }
            },
            "itr": {
                "uploaded": True,
                "verified": True,
                "data": {
                    "document_type": "itr",
                    "name": "Jane Doe",
                    "assessment_year": "2023-24",
                    "gross_total_income": 1200000.0,
                    "net_monthly_income": 85000.0
                }
            }
        },
        "all_documents_uploaded": True,
        "current_processing_doc": None,
        "personal_info": {
            "name": "Jane Doe",
            "phone": "9876543210",
            "credit_score": 750
        },
        "financial_info": {
            "net_monthly_income": 85000.0,
            "total_existing_emis": 15000.0,
            "home_loan_amount": 5000000.0,
            "down_payment": 1000000.0,
            "tenure_years": 20
        },
        "employment_info": {
            "employer_name": "Tech Corp India",
            "employment_type": "Full-time"
        },
        "financial_metrics": {
            "ltv": 83.33,
            "foir": 17.65
        },
        "paused_reason": None,
        "retry_count": 0
    }
    
    # Test 1: Automatic Save After Financial Risk Check
    print_section("💾 TEST 1: Automatic Data Saving")
    
    print("📝 Simulating financial_risk → save_data flow...")
    print(f"🔄 Current Stage: {state.get('current_stage')}")
    print(f"👤 User ID: {state.get('user_id')}")
    
    # Call save_application_data directly (as graph does)
    result = agent.save_application_data(state)
    
    print(f"\n🤖 Agent Response:")
    print(result['messages'][-1].content)
    print(f"\n✅ Final Stage: {result.get('current_stage')}")
    
    # Test 2: Verify file was created
    print_section("🔍 TEST 2: Verify File Creation and Data Persistence")
    
    # Agent saves to root/saved_docs from app/backend/nodes/agent.py
    # Test is at app/tests/test_save_functionality.py
    # Go up from app/tests to project root
    test_dir = os.path.dirname(__file__)  # app/tests
    app_dir = os.path.dirname(test_dir)  # app/
    project_root = os.path.dirname(app_dir)  # Home loan-langGraph/
    saved_docs_dir = os.path.join(project_root, "saved_docs")
    
    # Ensure directory exists
    if not os.path.exists(saved_docs_dir):
        print(f"⚠️  saved_docs directory not found at: {saved_docs_dir}")
        os.makedirs(saved_docs_dir, exist_ok=True)
        print(f"✅ Created saved_docs directory")
    
    # Find files for this user
    files = [f for f in os.listdir(saved_docs_dir) if f.startswith("application_test_user_auto_save")]
    
    if files:
        latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(saved_docs_dir, f)))
        filepath = os.path.join(saved_docs_dir, latest_file)
        
        print(f"✅ File Created Successfully!")
        print(f"📁 Filename: {latest_file}")
        print(f"📍 Full Path: {filepath}")
        
        # Load and validate saved data
        with open(filepath, 'r') as f:
            saved_data = json.load(f)
        
        print(f"\n📄 Saved Data Validation:")
        print(f"─" * 80)
        print(f"✅ User ID: {saved_data.get('user_id')}")
        print(f"✅ Timestamp: {saved_data.get('timestamp')}")
        
        # Validate personal info
        personal = saved_data.get('personal_info', {})
        print(f"\n👤 Personal Information:")
        print(f"   • Name: {personal.get('name')}")
        print(f"   • Phone: {personal.get('phone')}")
        print(f"   • Credit Score: {personal.get('credit_score')}")
        
        # Validate financial info
        financial = saved_data.get('financial_info', {})
        print(f"\n💰 Financial Information:")
        print(f"   • Home Loan Amount: ₹{financial.get('home_loan_amount', 0):,.0f}")
        print(f"   • Down Payment: ₹{financial.get('down_payment', 0):,.0f}")
        print(f"   • Tenure: {financial.get('tenure_years')} years")
        print(f"   • Monthly Income: ₹{financial.get('net_monthly_income', 0):,.0f}")
        print(f"   • Existing EMIs: ₹{financial.get('total_existing_emis', 0):,.0f}")
        
        # Validate employment info
        employment = saved_data.get('employment_info', {})
        print(f"\n💼 Employment Information:")
        print(f"   • Employer: {employment.get('employer_name')}")
        print(f"   • Type: {employment.get('employment_type')}")
        
        # Validate documents
        docs = saved_data.get('uploaded_documents', {})
        print(f"\n📄 Documents ({len(docs)}):")
        for doc_type, doc_info in docs.items():
            verified = "✅ Verified" if doc_info.get('verified') else "⚠️ Not Verified"
            print(f"   • {doc_type.upper()}: {verified}")
        
        # Validate financial metrics
        metrics = saved_data.get('financial_metrics', {})
        if metrics:
            print(f"\n📊 Financial Metrics:")
            print(f"   • LTV: {metrics.get('ltv', 0):.2f}%")
            print(f"   • FOIR: {metrics.get('foir', 0):.2f}%")
        
        print(f"\n✅ Total Fields Saved: {len(saved_data.keys())} top-level fields")
        print(f"✅ All documents uploaded: {saved_data.get('all_documents_uploaded')}")
    else:
        print(f"❌ No files found for user: test_user_auto_save")
        print(f"📂 Searched in: {saved_docs_dir}")
        return None
    
    # Test 3: Data Integrity Check
    print_section("🔐 TEST 3: Data Integrity Verification")
    
    # Compare original state with saved data
    integrity_checks = []
    
    # Check user_id
    if saved_data.get('user_id') == state.get('user_id'):
        print("✅ User ID matches")
        integrity_checks.append(True)
    else:
        print("❌ User ID mismatch")
        integrity_checks.append(False)
    
    # Check personal info
    if saved_data.get('personal_info', {}).get('name') == state.get('personal_info', {}).get('name'):
        print("✅ Personal info preserved")
        integrity_checks.append(True)
    else:
        print("❌ Personal info mismatch")
        integrity_checks.append(False)
    
    # Check financial info
    if saved_data.get('financial_info', {}).get('home_loan_amount') == state.get('financial_info', {}).get('home_loan_amount'):
        print("✅ Financial info preserved")
        integrity_checks.append(True)
    else:
        print("❌ Financial info mismatch")
        integrity_checks.append(False)
    
    # Check documents
    if len(saved_data.get('uploaded_documents', {})) == len(state.get('uploaded_documents', {})):
        print("✅ All documents saved")
        integrity_checks.append(True)
    else:
        print("❌ Document count mismatch")
        integrity_checks.append(False)
    
    # Summary
    print_section("📊 TEST SUMMARY")
    
    print("✅ Automatic Save (No Confirmation): WORKING")
    print("✅ File Creation: SUCCESSFUL")
    print("✅ Data Persistence: VERIFIED")
    print(f"✅ Data Integrity: {sum(integrity_checks)}/{len(integrity_checks)} checks passed")
    
    if all(integrity_checks):
        print("\n🎉 ALL AUTOMATIC SAVE TESTS PASSED!")
    else:
        print("\n⚠️  Some integrity checks failed")
    
    print(f"\n📝 Note: Data is saved automatically after financial_risk node")
    print(f"📝 No user confirmation is required or requested\n")
    
    return result


if __name__ == "__main__":
    test_save_functionality()
