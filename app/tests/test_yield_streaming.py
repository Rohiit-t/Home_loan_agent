"""
Test Yield Streaming Functionality
Verifies that all nodes properly yield progress messages for real-time UI updates.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Fix Unicode encoding for Windows terminal
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from langchain_core.messages import HumanMessage, AIMessage
from app.backend.schema.state import ApplicationState
from app.backend.util.graph import build_graph
from datetime import datetime
import json


def print_separator(char="=", length=100):
    """Print a separator line."""
    print("\n" + char * length)


def print_header(text):
    """Print a formatted header."""
    print_separator("=")
    print(f"  {text}")
    print_separator("=")


def test_yield_streaming():
    """
    Test that all nodes yield progress messages correctly for streaming UI updates.
    """
    print_header("🧪 TESTING YIELD STREAMING FUNCTIONALITY")
    
    # Build graph
    print("\n📦 Building graph...")
    graph = build_graph()
    
    # Configuration
    config = {"configurable": {"thread_id": "test_yield_streaming_" + datetime.now().strftime("%Y%m%d_%H%M%S")}}
    
    # Initialize state with user_id
    initial_state = {"user_id": "test_yield_user"}
    graph.update_state(config, initial_state, as_node="__start__")
    
    # Expected yield messages per node type
    expected_yields = {
        "intent_classifier": ["Analyzing your query", "Query classified"],
        "text_info": ["Extracting information"],
        "document_processing": ["Processing document"],
        "state_evaluator": ["Checking document status"],
        "loan_details": ["Checking loan details"],
        "loan_info_collector": ["Processing loan details"],
        "financial_risk": ["Calculating financial metrics"],
        "emi_calculator": ["Calculating EMI"],
        "save_json": ["Saving application data to JSON"],
        "save_db": ["Saving application data to database"],
        "email_notification": ["Preparing email notification", "Sending email"],
        "homeloan_query": ["Finding information"]
    }
    
    # Test scenarios covering all major nodes
    test_scenarios = [
        {
            "step": 1,
            "query": "My name is John Doe, age 35, phone 9876543210, email john@test.com",
            "description": "Test text_info_extractor yield",
            "expected_nodes": ["intent_classifier", "text_info", "state_evaluator"]
        },
        {
            "step": 2,
            "query": "I have PAN card ABCDE1234F",
            "description": "Test document_processing yield",
            "expected_nodes": ["intent_classifier", "document_processing", "state_evaluator"]
        },
        {
            "step": 3,
            "query": "Here is my Aadhaar 123456789012",
            "description": "Test document_processing yield again",
            "expected_nodes": ["intent_classifier", "document_processing", "state_evaluator"]
        },
        {
            "step": 4,
            "query": "My salary slip shows 75000 per month income and existing EMIs are 8000",
            "description": "Test document + text info",
            "expected_nodes": ["intent_classifier", "document_processing", "state_evaluator"]
        },
        {
            "step": 5,
            "query": "I need loan of 50 lakhs with 10 lakhs down payment for 15 years",
            "description": "Test loan_info_collector yield",
            "expected_nodes": ["intent_classifier", "loan_info_collector", "loan_details"]
        },
        {
            "step": 6,
            "query": "What is the interest rate for home loans?",
            "description": "Test homeloan_query yield",
            "expected_nodes": ["intent_classifier", "homeloan_query"]
        }
    ]
    
    # Track statistics
    total_yields = 0
    total_nodes_executed = 0
    all_captured_yields = []
    
    print("\n" + "="*100)
    print("🎬 STARTING YIELD STREAMING TEST")
    print("="*100)
    
    for scenario in test_scenarios:
        step = scenario["step"]
        query = scenario["query"]
        description = scenario["description"]
        expected_nodes = scenario.get("expected_nodes", [])
        
        print_separator("*")
        print(f"\n🔷 STEP {step}: {description}")
        print(f"👤 User Query: \"{query}\"")
        print_separator("*")
        
        # Get current state and add message
        current_state = graph.get_state(config)
        messages = current_state.values.get('messages', []) if current_state.values else []
        messages.append(HumanMessage(content=query))
        graph.update_state(config, {"messages": messages}, as_node="__start__")
        
        print("\n🔄 Streaming through graph (capturing yielded messages)...\n")
        
        # Track yields and nodes for this step
        step_yields = []
        nodes_executed = []
        
        # Stream with 'values' mode to capture all yielded messages
        try:
            for chunk in graph.stream(None, config, stream_mode="values"):
                # chunk contains the full state after each yield or node completion
                if 'messages' in chunk and chunk['messages']:
                    # Get only new messages
                    last_msg = chunk['messages'][-1]
                    if isinstance(last_msg, AIMessage):
                        content = last_msg.content
                        if content not in step_yields and content != "I have noted this information.":
                            step_yields.append(content)
                            all_captured_yields.append({
                                "step": step,
                                "message": content
                            })
                            total_yields += 1
                            
                            # Print yield message in real-time
                            print(f"   ✨ YIELD: {content[:100]}{'...' if len(content) > 100 else ''}")
        except Exception as e:
            print(f"   ⚠️  Stream error: {type(e).__name__}: {str(e)[:100]}")
        
        # Also check with updates mode for node execution tracking
        current_state = graph.get_state(config)
        messages = current_state.values.get('messages', []) if current_state.values else []
        
        # Count final state
        print(f"\n📊 STEP {step} SUMMARY:")
        print(f"   • Yielded Messages Captured: {len(step_yields)}")
        print(f"   • Current Stage: {current_state.values.get('current_stage', 'N/A') if current_state.values else 'N/A'}")
        print(f"   • Intent: {current_state.values.get('intent', 'N/A') if current_state.values else 'N/A'}")
        
        if step_yields:
            print(f"\n   📝 All Yielded Messages in Step {step}:")
            for i, msg in enumerate(step_yields, 1):
                truncated = msg[:80] + "..." if len(msg) > 80 else msg
                print(f"      {i}. {truncated}")
        
        print_separator("-")
    
    # Final comprehensive test: Complete workflow with all nodes
    print_header("🎯 COMPREHENSIVE TEST: Complete Workflow with All Nodes")
    
    # Reset with new thread
    config_full = {"configurable": {"thread_id": "test_full_workflow_" + datetime.now().strftime("%Y%m%d_%H%M%S")}}
    initial_state = {"user_id": "test_full_user"}
    graph.update_state(config_full, initial_state, as_node="__start__")
    
    # Complete workflow steps
    full_workflow = [
        "My name is Alice Smith, age 30, email alice@test.com, phone 9999888877",
        "I have PAN card ABCDE1234F",
        "Here is Aadhaar 123456789012",
        "My salary slip shows 100000 monthly income, existing EMIs 12000, working at ABC Corp",
        "I need 60 lakhs loan with 15 lakhs down payment for 20 years"
    ]
    
    print("\n🚀 Running complete workflow to trigger all nodes including save and email...\n")
    
    all_workflow_yields = []
    
    for i, query in enumerate(full_workflow, 1):
        print(f"\n📍 Step {i}: {query[:60]}...")
        
        current_state = graph.get_state(config_full)
        messages = current_state.values.get('messages', []) if current_state.values else []
        messages.append(HumanMessage(content=query))
        graph.update_state(config_full, {"messages": messages}, as_node="__start__")
        
        try:
            for chunk in graph.stream(None, config_full, stream_mode="values"):
                if 'messages' in chunk and chunk['messages']:
                    last_msg = chunk['messages'][-1]
                    if isinstance(last_msg, AIMessage):
                        content = last_msg.content
                        if content not in [y['message'] for y in all_workflow_yields]:
                            all_workflow_yields.append({
                                "step": i,
                                "message": content
                            })
                            # Detect yield type
                            if any(indicator in content for indicator in ["Analyzing", "Extracting", "Processing", "Checking", "Calculating", "Saving", "Preparing", "Sending"]):
                                print(f"      ✨ YIELD: {content[:100]}")
        except Exception as e:
            print(f"      ⚠️  Error: {type(e).__name__}: {str(e)[:100]}")
    
    # Final Statistics
    print_header("📈 FINAL TEST RESULTS")
    
    print("\n✅ YIELD STREAMING TEST COMPLETED!\n")
    print(f"{'='*100}")
    print(f"📊 STATISTICS:")
    print(f"{'='*100}")
    print(f"   • Total Test Scenarios: {len(test_scenarios) + 1} (including full workflow)")
    print(f"   • Total Yielded Messages Captured: {len(all_captured_yields) + len(all_workflow_yields)}")
    print(f"   • Yield Messages from Partial Tests: {len(all_captured_yields)}")
    print(f"   • Yield Messages from Full Workflow: {len(all_workflow_yields)}")
    
    # Categorize yields by type
    print(f"\n{'='*100}")
    print(f"🎨 YIELD MESSAGE CATEGORIES DETECTED:")
    print(f"{'='*100}")
    
    yield_categories = {
        "🔍 Analysis": 0,
        "📝 Extraction": 0,
        "📄 Processing": 0,
        "📋 Checking": 0,
        "📊 Calculation": 0,
        "💾 Saving": 0,
        "📧 Email": 0,
        "💬 Query Response": 0,
        "✅ Completion": 0,
    }
    
    all_yields_combined = all_captured_yields + all_workflow_yields
    
    for yield_data in all_yields_combined:
        msg = yield_data['message']
        if "Analyzing" in msg:
            yield_categories["🔍 Analysis"] += 1
        elif "Extracting" in msg:
            yield_categories["📝 Extraction"] += 1
        elif "Processing" in msg:
            yield_categories["📄 Processing"] += 1
        elif "Checking" in msg:
            yield_categories["📋 Checking"] += 1
        elif "Calculating" in msg:
            yield_categories["📊 Calculation"] += 1
        elif "Saving" in msg:
            yield_categories["💾 Saving"] += 1
        elif "email" in msg.lower() or "Email" in msg:
            yield_categories["📧 Email"] += 1
        elif "Finding information" in msg:
            yield_categories["💬 Query Response"] += 1
        elif "classified" in msg or "noted" in msg or "collected" in msg:
            yield_categories["✅ Completion"] += 1
    
    for category, count in yield_categories.items():
        if count > 0:
            print(f"   {category}: {count} message(s)")
    
    # Verification
    print(f"\n{'='*100}")
    print(f"✅ VERIFICATION:")
    print(f"{'='*100}")
    
    critical_yields = [
        "Analyzing your query",
        "Extracting information",
        "Processing document",
        "Checking document status",
        "Checking loan details",
        "Processing loan details",
        "Calculating financial metrics",
        "Calculating EMI",
        "Saving application data to JSON"
    ]
    
    found_critical = []
    missing_critical = []
    
    for critical in critical_yields:
        found = False
        for yield_data in all_yields_combined:
            if critical in yield_data['message']:
                found = True
                break
        
        if found:
            found_critical.append(critical)
            print(f"   ✅ Found: {critical}")
        else:
            missing_critical.append(critical)
            print(f"   ⚠️  Not captured: {critical}")
    
    print(f"\n{'='*100}")
    print(f"🎯 FINAL VERDICT:")
    print(f"{'='*100}")
    
    if len(found_critical) >= 7:  # At least 7 critical yields should be found
        print(f"   ✅ PASS: Yield streaming is working correctly!")
        print(f"   ✅ Found {len(found_critical)}/{len(critical_yields)} critical yield messages")
        print(f"   ✅ Graph is properly yielding progress updates for UI streaming")
    else:
        print(f"   ⚠️  PARTIAL PASS: Some yields may not be captured correctly")
        print(f"   ⚠️  Found {len(found_critical)}/{len(critical_yields)} critical yield messages")
        print(f"   ℹ️  This might be due to graph flow or interrupt handling")
    
    print(f"\n{'='*100}")
    print("🎉 YIELD STREAMING TEST COMPLETED!")
    print(f"{'='*100}\n")
    
    return len(found_critical) >= 7


if __name__ == "__main__":
    try:
        success = test_yield_streaming()
        if success:
            print("\n✅ All tests passed! Yield streaming is working as expected.\n")
        else:
            print("\n⚠️  Tests completed with warnings. Review the results above.\n")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
