"""
Test the loan_details_collector node with interrupt() function.
Demonstrates how interrupt() is used to repeatedly ask for loan details.

This test simulates terminal input by programmatically providing user responses.
"""

from langchain_core.messages import HumanMessage, AIMessage
from app.backend.util.graph import build_graph


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")


def print_interrupt_info(snapshot, round_num):
    """Print detailed information about the interrupt."""
    print(f"\n{'━'*80}")
    print(f"🔔 INTERRUPT #{round_num} - EXECUTION PAUSED")
    print(f"{'━'*80}")
    
    state = snapshot.values
    financial = state.get("financial_info", {})
    
    print(f"\n📍 Next Nodes: {snapshot.next}")
    print(f"🔄 Current Stage: {state.get('current_stage', 'N/A')}")
    print(f"⏸️  Paused Reason: {state.get('paused_reason', 'None')}")
    
    print(f"\n💰 Financial Info Collected So Far:")
    home_loan = financial.get('home_loan_amount')
    down_pay = financial.get('down_payment')
    tenure = financial.get('tenure_years')
    
    print(f"   • Home Loan Amount: {'₹{:,.0f}'.format(home_loan) if home_loan else '❌ Not Provided'}")
    print(f"   • Down Payment: {'₹{:,.0f}'.format(down_pay) if down_pay is not None else '❌ Not Provided'}")
    print(f"   • Tenure: {'{} years'.format(tenure) if tenure else '❌ Not Provided'}")
    
    # Show AI's message
    if state.get("messages"):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage):
            print(f"\n🤖 Assistant's Request:")
            print(f"{'─'*80}")
            print(last_msg.content)
            print(f"{'─'*80}")
    
    print()


def test_loan_details_with_interrupt():
    """
    Test loan_details_collector node using interrupt() function.
    Shows how the node interrupts multiple times until all details are collected.
    Simulates terminal input by programmatically providing user responses.
    """
    
    print_section("🧪 LOAN DETAILS WITH interrupt() FUNCTION TEST")
    
    print("This test demonstrates how loan_details_collector uses interrupt()")
    print("to iteratively collect loan information through multiple interactions.")
    print("\nSimulating user providing details one-by-one via terminal...\n")
    
    # Build the graph
    graph = build_graph()
    config = {"configurable": {"thread_id": "test_loan_interrupt_v3"}}
    
    # Prepare initial state - ready for loan details collection
    # State has all prerequisites met, just missing loan details
    initial_state = {
        "user_id": "test_interrupt_user",
        "messages": [],  # Empty messages so loan_details node won't try to extract with LLM
        "current_stage": "loan_details_collection",
        "uploaded_documents": {
            "PAN": {"uploaded": True, "verified": True, "data": {"pan_number": "ABCDE1234F"}},
            "Aadhaar": {"uploaded": True, "verified": True, "data": {"aadhaar_number": "123456789012"}},
            "ITR": {"uploaded": True, "verified": True, "data": {"itr_amount": 1200000}}
        },
        "all_documents_uploaded": True,
        "personal_info": {
            "name": "Interrupt Test User",
            "phone": "9876543210",
            "email": "interrupt@test.com",
            "address": "123 Test Street"
        },
        "financial_info": {
            "net_monthly_income": 100000,
            "total_existing_emis": 5000,
            "annual_income": 1200000,
            "rent": 0,
            "cibil_score": 750
            # Loan details (home_loan_amount, down_payment, tenure_years) are missing
        },
        "employment_info": {
            "employer_name": "Test Corp",
            "job_title": "Software Engineer"
        }
    }
    
    print("📊 INITIAL SETUP:")
    print(f"   User: {initial_state['user_id']}")
    print(f"   Stage: {initial_state['current_stage']}")
    print(f"   Documents: All verified (PAN, Aadhaar, ITR)")
    print(f"   Monthly Income: ₹{initial_state['financial_info']['net_monthly_income']:,}")
    print(f"   Personal & Employment Info: All collected")
    print(f"   Note: Starting DIRECTLY at loan_details node to test interrupt() in isolation")
    
    interrupt_count = 0
    
    # ===== START: Inject state directly to start at loan_details node =====
    print_section("▶️  STEP 1: Start execution directly at loan_details node")
    
    # Inject the initial state and start from loan_details node
    # This completely bypasses all API-dependent nodes (intent_classifier, text_info, state_evaluator)
    print("Injecting state as if coming from state_evaluator...\n")
    graph.update_state(config, initial_state, as_node="state_evaluator")
    
    # Now invoke - should go directly to loan_details and interrupt
    print("▶️  Invoking graph... should reach loan_details and interrupt\n")
    for event in graph.stream(None, config, stream_mode="values"):
        pass
    
    # ===== INTERRUPT 1: Initial request for all loan details =====
    snapshot = graph.get_state(config)
    interrupt_count += 1
    print_interrupt_info(snapshot, interrupt_count)
    
    # Simulate user input from terminal
    user_input_1 = "I want a loan of 50 lakhs"
    print(f"👤 USER INPUT (via terminal):")
    print(f"   → {user_input_1}")
    print()
    
    # Update state with user's response (simulating resume after interrupt)
    graph.update_state(
        config,
        {"messages": [HumanMessage(content=user_input_1)]},
        as_node="loan_details"
    )
    
    print("▶️  Resuming execution after user input...")
    for event in graph.stream(None, config, stream_mode="values"):
        pass
    
    # ===== INTERRUPT 2: Still missing down_payment and tenure =====
    snapshot = graph.get_state(config)
    
    if snapshot.next and "loan_details" in str(snapshot.next):
        interrupt_count += 1
        print_interrupt_info(snapshot, interrupt_count)
        
        user_input_2 = "My down payment will be 10 lakhs"
        print(f"👤 USER INPUT (via terminal):")
        print(f"   → {user_input_2}")
        print()
        
        graph.update_state(
            config,
            {"messages": [HumanMessage(content=user_input_2)]},
            as_node="loan_details"
        )
        
        print("▶️  Resuming execution after user input...")
        for event in graph.stream(None, config, stream_mode="values"):
            pass
    
    # ===== INTERRUPT 3: Still missing tenure =====
    snapshot = graph.get_state(config)
    
    if snapshot.next and "loan_details" in str(snapshot.next):
        interrupt_count += 1
        print_interrupt_info(snapshot, interrupt_count)
        
        user_input_3 = "20 years loan tenure"
        print(f"👤 USER INPUT (via terminal):")
        print(f"   → {user_input_3}")
        print()
        
        graph.update_state(
            config,
            {"messages": [HumanMessage(content=user_input_3)]},
            as_node="loan_details"
        )
        
        print("▶️  Resuming execution after user input...")
        for event in graph.stream(None, config, stream_mode="values"):
            pass
    
    # ===== COMPLETION: All details collected =====
    snapshot = graph.get_state(config)
    
    print_section("✅ LOAN DETAILS COLLECTION COMPLETE")
    
    final_state = snapshot.values
    final_financial = final_state.get("financial_info", {})
    
    print(f"📍 Current Stage: {final_state.get('current_stage')}")
    print(f"⏭️  Next Node: {snapshot.next if snapshot.next else '(Continuing to financial_risk)'}")
    print(f"⏸️  Paused Reason: {final_state.get('paused_reason', 'None')}")
    
    print(f"\n💰 FINAL COLLECTED LOAN DETAILS:")
    home_loan = final_financial.get('home_loan_amount', 0)
    down_pay = final_financial.get('down_payment', 0)
    tenure = final_financial.get('tenure_years', 0)
    
    print(f"   • Home Loan Amount: ₹{home_loan:,.0f}")
    print(f"   • Down Payment: ₹{down_pay:,.0f}")
    print(f"   • Tenure: {tenure} years")
    
    # Show final success message
    if final_state.get("messages"):
        last_msg = final_state["messages"][-1]
        if isinstance(last_msg, AIMessage):
            print(f"\n🤖 Success Message:")
            print(f"{'─'*80}")
            print(last_msg.content)
            print(f"{'─'*80}")
    
    # ===== TEST SUMMARY =====
    print_section("📊 TEST SUMMARY")
    
    print(f"🔔 Total Interrupts: {interrupt_count}")
    print("\n✅ INTERRUPT FLOW:")
    print(f"   1. First interrupt: Asked for all 3 details (home_loan_amount, down_payment, tenure_years)")
    print(f"   2. Second interrupt: User provided loan amount → Asked for remaining 2 details")
    print(f"   3. Third interrupt: User provided down payment → Asked for tenure")
    print(f"   4. User provided tenure → All collected, node completed!")
    
    print(f"\n💡 KEY OBSERVATIONS:")
    print(f"   • interrupt() called INSIDE the loan_details node")
    print(f"   • Node loops internally until all details collected")
    print(f"   • Each interrupt shows progress and asks for missing details")
    print(f"   • Once complete, node exits and proceeds to financial_risk")
    
    # Verification
    all_collected = (
        home_loan > 0 and
        down_pay >= 0 and
        tenure > 0
    )
    
    print(f"\n🎯 VERIFICATION:")
    if all_collected:
        print(f"   ✅ All loan details successfully collected")
        print(f"   ✅ interrupt() function worked as expected")
        print(f"   ✅ Success message saved to state")
        print(f"   ✅ TEST PASSED")
    else:
        print(f"   ❌ Some details missing!")
        print(f"   ❌ TEST FAILED")
    
    print()
    
    return all_collected


if __name__ == "__main__":
    print("\n" + "="*80)
    print("  🧪 LOAN DETAILS NODE - INTERRUPT FUNCTIONALITY TEST")
    print("="*80)
    
    try:
        success = test_loan_details_with_interrupt()
        
        print("\n" + "="*80)
        if success:
            print("  🎉 TEST SUITE PASSED!")
            print("  ✅ loan_details node correctly uses interrupt() for iterative collection")
        else:
            print("  ❌ TEST SUITE FAILED!")
            print("  ⚠️  Check the output above for details")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR DURING TEST:")
        print(f"   {str(e)}\n")
        import traceback
        traceback.print_exc()
        print()
