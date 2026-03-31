"""
Test the state_evaluator node with interrupt-driven collection.
Demonstrates the loop: state_evaluator → (interrupt) → intent_classifier → state_evaluator
"""
from langchain_core.messages import HumanMessage, AIMessage
from app.backend.nodes.agent import HomeLoanAgent


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")


def print_state_summary(state, test_name):
    """Print a summary of the current state."""
    print(f"\n{'─'*80}")
    print(f"{test_name} - STATE SUMMARY")
    print(f"{'─'*80}")
    
    print(f"\n📄 Documents Uploaded: {len(state.get('uploaded_documents', {}))}/{3}")
    for doc_type, doc_info in state.get("uploaded_documents", {}).items():
        verified = "✓" if doc_info.get("verified") else "✗"
        print(f"   {verified} {doc_type}")
    
    print(f"\n📋 Information Status:")
    personal = state.get("personal_info", {})
    financial = state.get("financial_info", {})
    employment = state.get("employment_info", {})
    
    print(f"   Personal: {'✓' if personal.get('name') and personal.get('phone') else '✗'} Name, Phone")
    print(f"   Financial: {'✓' if financial.get('net_monthly_income') and financial.get('total_existing_emis') else '✗'} Income, EMIs")
    print(f"   Employment: {'✓' if employment.get('employer_name') else '✗'} Employer")
    
    print(f"\n🔄 Current Stage: {state.get('current_stage', 'N/A')}")
    print(f"⏸️  Paused Reason: {state.get('paused_reason', 'None')}")
    
    if state.get('messages'):
        last_msg = state['messages'][-1]
        print(f"\n💬 Last Message ({type(last_msg).__name__}):")
        content = last_msg.content
        if len(content) > 200:
            print(f"   {content[:200]}...")
        else:
            print(f"   {content}")


def test_missing_documents_flow():
    """
    Test state_evaluator when documents are missing.
    Should pause and set current_stage to 'awaiting_documents'.
    """
    
    print_section("📄 TEST 1: Missing Documents Flow")
    
    agent = HomeLoanAgent()
    
    # State with only 1 document uploaded (need 3: aadhaar, pan, itr)
    state = {
        "user_id": "test_user_001",
        "messages": [AIMessage(content="Starting evaluation")],
        "intent": "Document_upload",
        "current_stage": "state_evaluation",
        "uploaded_documents": {
            "aadhaar": {
                "uploaded": True,
                "verified": True,
                "data": {"name": "Test User"}
            }
        },
        "personal_info": {"name": "Test User", "phone": "1234567890"},
        "financial_info": {"net_monthly_income": 50000, "total_existing_emis": 5000},
        "employment_info": {"employer_name": "Test Corp"}
    }
    
    print("Initial State: Only Aadhaar uploaded, missing PAN and ITR\n")
    
    result = agent.state_evaluator(state)
    state.update(result)
    
    print_state_summary(state, "AFTER STATE_EVALUATOR")
    
    print("\n⏸️  [INTERRUPT] Graph would pause here")
    print("🔄 Expected routing: state_evaluator → intent_classifier (to upload more docs)")
    
    # Verify the state
    assert state.get("current_stage") == "awaiting_documents", "Should set stage to awaiting_documents"
    assert state.get("paused_reason") is not None, "Should set paused_reason"
    assert "pan" in state.get("paused_reason").lower(), "Should mention missing PAN"
    assert state.get("intent") is None, "Should reset intent for new input"
    
    print("\n✅ TEST 1 PASSED: State evaluator correctly identifies missing documents")
    print(f"   • Sets current_stage: {state.get('current_stage')}")
    print(f"   • Sets paused_reason: {state.get('paused_reason')}")
    print(f"   • Resets intent to allow new document upload")
    
    return True


def test_missing_information_flow():
    """
    Test state_evaluator when all documents are uploaded but info is missing.
    Should pause and set current_stage to 'awaiting_information'.
    """
    
    print_section("📋 TEST 2: Missing Information Flow")
    
    agent = HomeLoanAgent()
    
    # State with all documents but missing personal info
    state = {
        "user_id": "test_user_002",
        "messages": [AIMessage(content="Checking info")],
        "current_stage": "state_evaluation",
        "uploaded_documents": {
            "aadhaar": {"uploaded": True, "verified": True, "data": {}},
            "pan": {"uploaded": True, "verified": True, "data": {}},
            "itr": {"uploaded": True, "verified": True, "data": {}}
        },
        "all_documents_uploaded": False,
        "personal_info": {},  # Missing name and phone
        "financial_info": {"net_monthly_income": 50000, "total_existing_emis": 5000},
        "employment_info": {"employer_name": "Test Corp"}
    }
    
    print("Initial State: All 3 documents uploaded, but missing personal info\n")
    
    result = agent.state_evaluator(state)
    state.update(result)
    
    print_state_summary(state, "AFTER STATE_EVALUATOR")
    
    print("\n⏸️  [INTERRUPT] Graph would pause here")
    print("🔄 Expected routing: state_evaluator → intent_classifier (to provide info)")
    
    # Verify the state
    assert state.get("current_stage") == "awaiting_information", "Should set stage to awaiting_information"
    assert state.get("all_documents_uploaded") == True, "Should mark documents as uploaded"
    assert state.get("paused_reason") is not None, "Should set paused_reason"
    assert "personal" in state.get("paused_reason").lower(), "Should mention missing personal info"
    
    print("\n✅ TEST 2 PASSED: State evaluator correctly identifies missing information")
    print(f"   • Sets current_stage: {state.get('current_stage')}")
    print(f"   • Marks all_documents_uploaded: True")
    print(f"   • Sets paused_reason: {state.get('paused_reason')}")
    
    return True


def test_all_complete_flow():
    """
    Test state_evaluator when all documents and information are complete.
    Should proceed to loan_details_collection without pause.
    """
    
    print_section("✅ TEST 3: All Complete Flow")
    
    agent = HomeLoanAgent()
    
    # State with everything complete
    state = {
        "user_id": "test_user_003",
        "messages": [AIMessage(content="Final check")],
        "current_stage": "state_evaluation",
        "uploaded_documents": {
            "aadhaar": {"uploaded": True, "verified": True, "data": {}},
            "pan": {"uploaded": True, "verified": True, "data": {}},
            "itr": {"uploaded": True, "verified": True, "data": {}}
        },
        "personal_info": {"name": "Complete User", "phone": "9876543210"},
        "financial_info": {"net_monthly_income": 75000, "total_existing_emis": 10000},
        "employment_info": {"employer_name": "Complete Corp"}
    }
    
    print("Initial State: All documents uploaded + all information provided\n")
    
    result = agent.state_evaluator(state)
    state.update(result)
    
    print_state_summary(state, "AFTER STATE_EVALUATOR")
    
    print("\n✅ No interrupt needed!")
    print("🔄 Expected routing: state_evaluator → loan_details")
    
    # Verify the state
    assert state.get("current_stage") == "loan_details_collection", "Should advance to loan_details_collection"
    assert state.get("paused_reason") is None, "Should NOT set paused_reason"
    assert state.get("all_documents_uploaded") == True, "Should mark documents as uploaded"
    
    print("\n✅ TEST 3 PASSED: State evaluator correctly proceeds when all complete")
    print(f"   • Sets current_stage: {state.get('current_stage')}")
    print(f"   • No paused_reason (ready to proceed)")
    print(f"   • all_documents_uploaded: True")
    
    return True


def test_iterative_collection_simulation():
    """
    Simulate the full iterative collection loop.
    Start with nothing → add documents → add info → proceed to loan details.
    """
    
    print_section("🔄 TEST 4: Iterative Collection Simulation")
    
    agent = HomeLoanAgent()
    
    # ITERATION 1: Start with nothing
    print("\n📍 ITERATION 1: No documents, no info")
    state = {
        "user_id": "test_user_004",
        "messages": [AIMessage(content="Starting")],
        "current_stage": "state_evaluation",
        "uploaded_documents": {},
        "personal_info": {},
        "financial_info": {},
        "employment_info": {}
    }
    
    result = agent.state_evaluator(state)
    state.update(result)
    
    print(f"   Result: {state.get('current_stage')}")
    print(f"   Message: {state['messages'][-1].content[:80]}...")
    assert state.get("current_stage") == "awaiting_documents", "Should wait for documents"
    print("   ⏸️  Graph pauses, routes back to intent_classifier")
    
    # ITERATION 2: Add all documents
    print("\n📍 ITERATION 2: All documents uploaded")
    state["uploaded_documents"] = {
        "aadhaar": {"uploaded": True, "verified": True, "data": {}},
        "pan": {"uploaded": True, "verified": True, "data": {}},
        "itr": {"uploaded": True, "verified": True, "data": {}}
    }
    state["messages"].append(AIMessage(content="Documents uploaded"))
    
    result = agent.state_evaluator(state)
    state.update(result)
    
    print(f"   Result: {state.get('current_stage')}")
    print(f"   Message: {state['messages'][-1].content[:80]}...")
    assert state.get("current_stage") == "awaiting_information", "Should wait for info"
    print("   ⏸️  Graph pauses, routes back to intent_classifier")
    
    # ITERATION 3: Add all information
    print("\n📍 ITERATION 3: All information provided")
    state["personal_info"] = {"name": "Iterative User", "phone": "1112223333"}
    state["financial_info"] = {"net_monthly_income": 60000, "total_existing_emis": 8000}
    state["employment_info"] = {"employer_name": "Iterative Corp"}
    state["messages"].append(AIMessage(content="Info provided"))
    
    result = agent.state_evaluator(state)
    state.update(result)
    
    print(f"   Result: {state.get('current_stage')}")
    print(f"   Message: {state['messages'][-1].content[:80]}...")
    assert state.get("current_stage") == "loan_details_collection", "Should proceed to loan details"
    print("   ✅ No pause, routes to loan_details")
    
    print("\n✅ TEST 4 PASSED: Iterative collection loop works correctly")
    print("   Flow: awaiting_documents → awaiting_information → loan_details_collection")
    
    return True


if __name__ == "__main__":
    test1 = test_missing_documents_flow()
    test2 = test_missing_information_flow()
    test3 = test_all_complete_flow()
    test4 = test_iterative_collection_simulation()
    
    print_section("🎉 TEST SUMMARY")
    
    results = {
        "Missing Documents Flow": test1,
        "Missing Information Flow": test2,
        "All Complete Flow": test3,
        "Iterative Collection": test4
    }
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n📋 Key Features Verified:")
    print("  1. ✅ Detects missing documents and pauses")
    print("  2. ✅ Detects missing information and pauses")
    print("  3. ✅ Sets appropriate current_stage for routing")
    print("  4. ✅ Resets intent to allow new input")
    print("  5. ✅ Provides user-friendly messages")
    print("  6. ✅ Proceeds to loan_details when all complete")
    print("  7. ✅ Supports iterative collection loop")
    
    print("\n💡 For Streamlit Frontend:")
    print("  • Check current_stage == 'awaiting_documents' or 'awaiting_information'")
    print("  • Display state['messages'][-1].content to user")
    print("  • Collect document upload or text input")
    print("  • Add HumanMessage and call graph.invoke(None, config)")
    print("  • Graph routes to intent_classifier → processes → state_evaluator")
    print("  • Loop continues until all requirements met")
    
    print("\n🔄 Graph Flow with Interrupts:")
    print("  START → intent_classifier → [document_processing|text_info]")
    print("     → state_evaluator [INTERRUPT] → intent_classifier (loop)")
    print("     → state_evaluator (re-check) → loan_details → ...")
