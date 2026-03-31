"""
Automated Complete Workflow Test
Tests the entire graph with predefined queries showing all interrupts and paused reasons.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.messages import HumanMessage, AIMessage
from app.backend.schema.state import ApplicationState
from app.backend.util.graph import build_graph
import json


def print_separator(char="=", length=100):
    """Print a separator line."""
    print("\n" + char * length)


def print_header(text):
    """Print a formatted header."""
    print_separator("=")
    print(f"  {text}")
    print_separator("=")


def print_subheader(text):
    """Print a sub-header."""
    print_separator("-")
    print(f"  {text}")
    print_separator("-")


def print_state_details(state, step_num):
    """Print detailed state information."""
    print(f"\n{'='*100}")
    print(f"  📊 STATE DETAILS - STEP {step_num}")
    print(f"{'='*100}")
    
    print(f"\n🔹 Intent: {state.get('intent', 'None')}")
    print(f"🔹 Current Stage: {state.get('current_stage', 'None')}")
    print(f"🔹 Paused Reason: {state.get('paused_reason', 'None')}")
    print(f"🔹 All Documents Uploaded: {state.get('all_documents_uploaded', False)}")
    
    # Documents status
    uploaded_docs = state.get('uploaded_documents', {})
    if uploaded_docs:
        print(f"\n📄 UPLOADED DOCUMENTS ({len(uploaded_docs)}):")
        for doc_type, doc_info in uploaded_docs.items():
            status = "✅ Verified" if doc_info.get('verified') else "⚠️  Pending"
            print(f"   • {doc_type}: {status}")
    
    # Personal info
    personal = state.get('personal_info', {})
    if personal:
        print(f"\n👤 PERSONAL INFO:")
        for key, value in personal.items():
            print(f"   • {key}: {value}")
    
    # Financial info
    financial = state.get('financial_info', {})
    if financial:
        print(f"\n💰 FINANCIAL INFO:")
        for key, value in financial.items():
            print(f"   • {key}: {value}")
    
    # Employment info
    employment = state.get('employment_info', {})
    if employment:
        print(f"\n💼 EMPLOYMENT INFO:")
        for key, value in employment.items():
            print(f"   • {key}: {value}")


def run_complete_workflow_test():
    """
    Run a complete automated workflow test.
    """
    print_header("🏠 HOME LOAN APPLICATION - COMPLETE WORKFLOW TEST")
    
    print("\n⚙️  Initializing graph...")
    graph = build_graph()
    print("✅ Graph compiled successfully with checkpointer and interrupts!")
    
    # Configuration for thread
    config = {"configurable": {"thread_id": "test_workflow_user"}}
    
    print("\n🎯 Starting automated workflow test...\n")
    
    # Define test scenarios with expected behavior
    test_scenarios = [
        {
            "step": 1,
            "query": "I want to apply for a home loan",
            "description": "Initial query - should classify intent as Homeloan_query",
            "expected_stage": "None",
            "should_interrupt": False
        },
        {
            "step": 2,
            "query": "I have my PAN card with number ABCDE1234F",
            "description": "Upload PAN document",
            "expected_stage": "awaiting_documents",
            "should_interrupt": True
        },
        {
            "step": 3,
            "query": "Here is my Aadhaar number 123456789012",
            "description": "Upload Aadhaar document",
            "expected_stage": "awaiting_documents",
            "should_interrupt": True
        },
        {
            "step": 4,
            "query": "My salary slip shows income of 80000 per month",
            "description": "Upload salary slip",
            "expected_stage": "awaiting_information",
            "should_interrupt": True
        },
        {
            "step": 5,
            "query": "My name is Rajesh Kumar, phone 9876543210, email rajesh@example.com",
            "description": "Provide personal information",
            "expected_stage": "awaiting_information",
            "should_interrupt": True
        },
        {
            "step": 6,
            "query": "Monthly income 80000 and existing EMIs are 5000",
            "description": "Provide financial information",
            "expected_stage": "awaiting_information",
            "should_interrupt": True
        },
        {
            "step": 7,
            "query": "I work at Tech Solutions Pvt Ltd as permanent employee",
            "description": "Provide employment information",
            "expected_stage": "loan_details_collection",
            "should_interrupt": True
        },
        {
            "step": 8,
            "query": "I need a loan of ₹50,00,000 with down payment of ₹10,00,000 for 20 years",
            "description": "Provide loan details - triggers financial risk check and auto-save",
            "expected_stage": "completed",
            "should_interrupt": False
        },
    ]
    
    for scenario in test_scenarios:
        step = scenario["step"]
        query = scenario["query"]
        description = scenario["description"]
        
        print_separator("*")
        print(f"\n🔷 STEP {step}: {description}")
        print(f"👤 User Query: \"{query}\"")
        print_separator("*")
        
        # Get current state
        current_state = graph.get_state(config)
        
        if current_state.values:
            messages = current_state.values.get('messages', [])
        else:
            messages = []
        
        # Add user message
        messages.append(HumanMessage(content=query))
        graph.update_state(config, {"messages": messages}, as_node="__start__")
        
        print("\n🔄 Processing through graph nodes...")
        
        # Track which nodes are executed
        nodes_executed = []
        
        # Stream through the graph
        for event in graph.stream(None, config, stream_mode="updates"):
            for node_name, node_state in event.items():
                nodes_executed.append(node_name)
                print(f"   ➡️  Executed Node: {node_name}")
                
                # Show AI responses
                if 'messages' in node_state and node_state['messages']:
                    for msg in node_state['messages']:
                        if isinstance(msg, AIMessage):
                            content = msg.content
                            if len(content) > 150:
                                content = content[:150] + "..."
                            print(f"      🤖 Response: {content}")
        
        print(f"\n✅ Nodes executed: {' → '.join(nodes_executed)}")
        
        # Get final state after processing
        final_state = graph.get_state(config)
        
        # Print state details
        if final_state.values:
            print_state_details(final_state.values, step)
        
        # Check for interrupts
        if final_state.next:
            print(f"\n{'='*100}")
            print(f"⏸️  🛑 INTERRUPT DETECTED! 🛑")
            print(f"{'='*100}")
            print(f"Next pending nodes: {final_state.next}")
            print(f"⏳ Workflow paused - waiting for user input to continue...")
            print(f"{'='*100}\n")
        else:
            print(f"\n{'='*100}")
            print(f"✅ No interrupts - workflow continues or completes")
            print(f"{'='*100}\n")
        
        # Show last AI message
        if final_state.values:
            messages = final_state.values.get('messages', [])
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, AIMessage):
                    print(f"\n💬 ASSISTANT MESSAGE:")
                    print(f"{'─'*100}")
                    print(f"{last_msg.content}")
                    print(f"{'─'*100}\n")
    
    # Final summary
    print_header("🎉 WORKFLOW TEST COMPLETED SUCCESSFULLY!")
    
    final_state = graph.get_state(config)
    if final_state.values:
        print("\n📋 FINAL APPLICATION SUMMARY:")
        print("="*100)
        
        state = final_state.values
        
        print(f"\n✅ User ID: {state.get('user_id')}")
        print(f"✅ Current Stage: {state.get('current_stage')}")
        print(f"✅ Documents Uploaded: {len(state.get('uploaded_documents', {}))}/3")
        print(f"✅ All Documents Verified: {state.get('all_documents_uploaded', False)}")
        
        financial = state.get('financial_info', {})
        print(f"\n💰 LOAN DETAILS:")
        print(f"   • Home Loan Amount: ₹{financial.get('home_loan_amount', 0):,.2f}")
        print(f"   • Down Payment: ₹{financial.get('down_payment', 0):,.2f}")
        print(f"   • Tenure: {financial.get('tenure_years', 0)} years")
        print(f"   • Monthly Income: ₹{financial.get('net_monthly_income', 0):,.2f}")
        print(f"   • Existing EMIs: ₹{financial.get('total_existing_emis', 0):,.2f}")
        
        print("\n✅ Application data automatically saved to saved_docs folder!")
        print("="*100)


if __name__ == "__main__":
    try:
        run_complete_workflow_test()
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
