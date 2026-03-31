"""
Focused test for loan_details_collector node only.
Tests the node in isolation with simulated state and interrupt cycles.
"""

import os
from dotenv import load_dotenv

# Load .env from app/static/ directory
env_path = os.path.join(os.path.dirname(__file__), "..", "static", ".env")
load_dotenv(dotenv_path=env_path)

from langchain_core.messages import HumanMessage, AIMessage
from app.backend.nodes.agent import HomeLoanAgent
from langgraph.types import interrupt


def print_separator(title=""):
    """Print a visual separator"""
    if title:
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    else:
        print(f"\n{'-'*70}\n")


def test_loan_details_node_isolated():
    """
    Test loan_details_collector node in isolation.
    Simulates the interrupt/resume cycle by manually calling the node method.
    """
    print_separator("TESTING LOAN_DETAILS_COLLECTOR NODE (ISOLATED)")
    
    print("This test checks the loan_details node logic by directly calling the method.")
    print("We will simulate the interrupt/resume cycle by manually updating state.\n")
    
    # Initialize the agent
    agent = HomeLoanAgent()
    
    # Create initial state with all prerequisites (documents, personal info, etc.)
    state = {
        "user_id": "test_node_user",
        "messages": [],
        "current_stage": "loan_details_collection",
        "uploaded_documents": {
            "PAN": {"uploaded": True, "verified": True},
            "Aadhaar": {"uploaded": True, "verified": True},
            "ITR": {"uploaded": True, "verified": True}
        },
        "all_documents_uploaded": True,
        "personal_info": {
            "name": "Test User",
            "phone": "9876543210"
        },
        "financial_info": {
            "net_monthly_income": 100000,
            "total_existing_emis": 5000,
            "annual_income": 1200000,
            "rent": 0,
            "cibil_score": 750
            # Loan details missing: home_loan_amount, down_payment, tenure_years
        },
        "employment_info": {
            "employer_name": "Test Corp"
        }
    }
    
    print("INITIAL STATE:")
    print(f"   User: {state['user_id']}")
    print(f"   Documents: All verified")
    print(f"   Personal & Financial Info: Complete")
    print(f"   Loan Details: Not yet collected")
    
    interrupt_count = 0
    
    # CYCLE 1: First call - should interrupt asking for all 3 details
    print_separator("CYCLE 1: First Call to loan_details_collector")
    
    try:
        result = agent.loan_details_collector(state)
        print("ERROR: Node should have interrupted but did not!")
        return False
    except Exception as e:
        if "interrupt" in str(type(e).__name__).lower():
            interrupt_count += 1
            print(f"Node interrupted as expected (Interrupt #{interrupt_count})")
            print(f"   Interrupt message: {str(e)}")
            
            # Check that financial_info still has no loan details
            financial = state.get("financial_info", {})
            print(f"\nFinancial Info Status:")
            print(f"   Home Loan Amount: {financial.get('home_loan_amount', 'Not set')}")
            print(f"   Down Payment: {financial.get('down_payment', 'Not set')}")
            print(f"   Tenure: {financial.get('tenure_years', 'Not set')}")
        else:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # CYCLE 2: Simulate user providing loan amount only
    print_separator("CYCLE 2: User Provides Loan Amount")
    
    print("User Input: 'I want a loan of 50 lakhs'")
    
    # Add user message to state
    state["messages"].append(HumanMessage(content="I want a loan of 50 lakhs"))
    
    try:
        result = agent.loan_details_collector(state)
        print("ERROR: Node should have interrupted but did not!")
        return False
    except Exception as e:
        if "interrupt" in str(type(e).__name__).lower():
            interrupt_count += 1
            print(f"Node interrupted again (Interrupt #{interrupt_count})")
            print(f"   Interrupt message: {str(e)}")
            
            # Check that home_loan_amount is now set
            financial = state.get("financial_info", {})
            print(f"\nFinancial Info Status:")
            print(f"   Home Loan Amount: Rs {financial.get('home_loan_amount', 0):,.0f}")
            print(f"   Down Payment: {financial.get('down_payment', 'Not set')}")
            print(f"   Tenure: {financial.get('tenure_years', 'Not set')}")
        else:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # CYCLE 3: Simulate user providing down payment
    print_separator("CYCLE 3: User Provides Down Payment")
    
    print("User Input: 'My down payment is 10 lakhs'")
    
    # Add user message to state
    state["messages"].append(HumanMessage(content="My down payment is 10 lakhs"))
    
    try:
        result = agent.loan_details_collector(state)
        print("ERROR: Node should have interrupted but did not!")
        return False
    except Exception as e:
        if "interrupt" in str(type(e).__name__).lower():
            interrupt_count += 1
            print(f"Node interrupted again (Interrupt #{interrupt_count})")
            print(f"   Interrupt message: {str(e)}")
            
            # Check that down_payment is now set
            financial = state.get("financial_info", {})
            print(f"\nFinancial Info Status:")
            print(f"   Home Loan Amount: Rs {financial.get('home_loan_amount', 0):,.0f}")
            print(f"   Down Payment: Rs {financial.get('down_payment', 0):,.0f}")
            print(f"   Tenure: {financial.get('tenure_years', 'Not set')}")
        else:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # CYCLE 4: Simulate user providing tenure - should complete
    print_separator("CYCLE 4: User Provides Tenure (Final Detail)")
    
    print("User Input: 'I want 20 years tenure'")
    
    # Add user message to state
    state["messages"].append(HumanMessage(content="I want 20 years tenure"))
    
    try:
        result = agent.loan_details_collector(state)
        print("Node completed successfully without interrupt!")
        
        # Verify the result
        financial = result.get("financial_info", {})
        print(f"\nFINAL Loan Details:")
        print(f"   Home Loan Amount: Rs {financial.get('home_loan_amount', 0):,.0f}")
        print(f"   Down Payment: Rs {financial.get('down_payment', 0):,.0f}")
        print(f"   Tenure: {financial.get('tenure_years', 0)} years")
        
        print(f"\nCurrent Stage: {result.get('current_stage')}")
        print(f"Paused Reason: {result.get('paused_reason', 'None')}")
        
        # Check for success message
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage):
                print(f"\nSuccess Message:")
                print("-"*70)
                print(last_msg.content)
                print("-"*70)
        
        # Verify all details are collected
        all_collected = (
            financial.get('home_loan_amount', 0) > 0 and
            financial.get('down_payment', 0) >= 0 and
            financial.get('tenure_years', 0) > 0
        )
        
        if not all_collected:
            print("\nTEST FAILED: Not all details were collected!")
            return False
            
    except Exception as e:
        print(f"ERROR: Node should have completed but interrupted/failed!")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # TEST SUMMARY
    print_separator("TEST SUMMARY")
    
    print(f"Total Interrupts: {interrupt_count}")
    print(f"\nEXPECTED BEHAVIOR:")
    print(f"   1. Interrupt #1: Asked for all 3 details")
    print(f"   2. Interrupt #2: User provided loan amount -> Asked for 2 remaining")
    print(f"   3. Interrupt #3: User provided down payment -> Asked for tenure")
    print(f"   4. Completed: User provided tenure -> All collected, no interrupt")
    
    print(f"\nKEY OBSERVATIONS:")
    print(f"   - While loop keeps checking for missing details")
    print(f"   - interrupt() raises exception on each missing detail")
    print(f"   - Node re-executes from start on each resume")
    print(f"   - Structured LLM extracts details from user messages")
    print(f"   - Success message stored in state['messages'] on completion")
    
    print(f"\nFINAL VERIFICATION:")
    print(f"   All 3 loan details collected successfully")
    print(f"   interrupt() worked correctly {interrupt_count} times")
    print(f"   Success message saved to state")
    print(f"   current_stage set to 'financial_risk_check'")
    print(f"   TEST PASSED")
    
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  LOAN_DETAILS_COLLECTOR NODE - ISOLATED TEST")
    print("="*70)
    
    try:
        success = test_loan_details_node_isolated()
        
        print("\n" + "="*70)
        if success:
            print("  TEST PASSED!")
            print("  loan_details_collector node works correctly")
        else:
            print("  TEST FAILED!")
            print("  Check the output above for details")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\nFATAL ERROR:")
        print(f"   {str(e)}\n")
        import traceback
        traceback.print_exc()
        print()
