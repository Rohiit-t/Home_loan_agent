"""
Test case for Intent Classification Node.

This test builds a minimal graph with only the intent_classifier node
and tests it interactively with terminal input.
"""

import os
import sys
from typing import TypedDict, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

# Load environment variables
load_dotenv("app/static/.env")

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.backend.nodes.agent import HomeLoanAgent
from app.backend.schema.state import ApplicationState


def build_intent_test_graph():
    """
    Build a minimal graph with only the intent_classifier node for testing.
    """
    # Initialize agent
    agent = HomeLoanAgent()
    
    # Create StateGraph
    workflow = StateGraph(ApplicationState)
    
    # Add only the intent_classifier node
    workflow.add_node("intent_classifier", agent.intent_classifier)
    
    # Add edges
    workflow.add_edge(START, "intent_classifier")
    workflow.add_edge("intent_classifier", END)
    
    # Compile graph
    graph = workflow.compile()
    
    return graph


def test_intent_classification_interactive():
    """
    Interactive test for intent classification.
    Takes user input from terminal and classifies intent.
    """
    print("="*80)
    print("  INTENT CLASSIFICATION TEST")
    print("="*80)
    print("\nThis test will classify your queries into one of these intents:")
    print("  1. Document_upload - User wants to upload documents")
    print("  2. Text_info - User provides personal/financial/employment info")
    print("  3. Homeloan_query - User asks questions about home loans")
    print("  4. Irrelevant - Query not related to home loans")
    print("\nType 'exit' to quit the test.\n")
    print("="*80)
    
    # Build the test graph
    graph = build_intent_test_graph()
    
    test_count = 0
    
    while True:
        # Get user input from terminal
        print("\n" + "-"*80)
        user_input = input("\n💬 Enter your query: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("\n👋 Exiting test. Thank you!")
            break
        
        if not user_input:
            print("⚠️  Please enter a valid query.")
            continue
        
        test_count += 1
        
        # Create initial state with user message
        initial_state = {
            "messages": [HumanMessage(content=user_input)],
            "intent": None,
            "user_id": "test_user",
            "uploaded_documents": {},
            "missing_documents": [],
            "all_documents_uploaded": False,
            "personal_info": {},
            "financial_info": {},
            "employment_info": {},
            "loan_details": {},
            "risk_assessment": {},
            "paused_reason": None,
            "application_saved": False
        }
        
        try:
            # Run the graph
            print("\n🔄 Processing...")
            result = graph.invoke(initial_state)
            
            # Extract and display results
            classified_intent = result.get("intent", "Unknown")
            
            print("\n" + "="*80)
            print(f"  TEST #{test_count} - RESULT")
            print("="*80)
            print(f"\n📝 Your Query: {user_input}")
            print(f"\n🎯 Classified Intent: {classified_intent}")
            
            # Provide interpretation
            intent_descriptions = {
                "Document_upload": "✅ System detected you want to upload documents (PAN, Aadhaar, etc.)",
                "Text_info": "✅ System detected you're providing personal/financial/employment information",
                "Homeloan_query": "✅ System detected you're asking questions about home loans",
                "Irrelevant": "❌ System detected this query is not related to home loan application"
            }
            
            description = intent_descriptions.get(classified_intent, "Unknown intent type")
            print(f"\n💡 Interpretation: {description}")
            print("\n" + "="*80)
            
        except Exception as e:
            print(f"\n❌ Error during classification: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "="*80)
    print(f"  TEST SUMMARY")
    print("="*80)
    print(f"\nTotal queries tested: {test_count}")
    print("\n✅ Intent classification test completed!")
    print("="*80)


def test_intent_classification_batch():
    """
    Batch test with predefined queries to test all intent types.
    """
    print("\n" + "="*80)
    print("  BATCH INTENT CLASSIFICATION TEST")
    print("="*80)
    
    # Build the test graph
    graph = build_intent_test_graph()
    
    # Test cases covering all intents
    test_cases = [
        ("I want to upload my PAN card", "Document_upload"),
        ("I have my Aadhaar and ITR documents ready", "Document_upload"),
        ("My name is John Doe and I earn 50000 per month", "Text_info"),
        ("I work at TCS and my annual income is 600000", "Text_info"),
        ("What is the current home loan interest rate?", "Homeloan_query"),
        ("What documents do I need for home loan?", "Homeloan_query"),
        ("What is the weather today?", "Irrelevant"),
        ("Tell me a joke", "Irrelevant"),
    ]
    
    results = []
    
    for idx, (query, expected_intent) in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case #{idx}")
        print(f"{'='*80}")
        print(f"Query: {query}")
        print(f"Expected Intent: {expected_intent}")
        
        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "intent": None,
            "user_id": "test_user",
            "uploaded_documents": {},
            "missing_documents": [],
            "all_documents_uploaded": False,
            "personal_info": {},
            "financial_info": {},
            "employment_info": {},
            "loan_details": {},
            "risk_assessment": {},
            "paused_reason": None,
            "application_saved": False
        }
        
        try:
            # Run the graph
            result = graph.invoke(initial_state)
            classified_intent = result.get("intent", "Unknown")
            
            # Check if classification matches expected
            match = "✅ PASS" if classified_intent == expected_intent else "❌ FAIL"
            
            print(f"Classified Intent: {classified_intent}")
            print(f"Result: {match}")
            
            results.append({
                "query": query,
                "expected": expected_intent,
                "actual": classified_intent,
                "passed": classified_intent == expected_intent
            })
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append({
                "query": query,
                "expected": expected_intent,
                "actual": "ERROR",
                "passed": False
            })
    
    # Print summary
    print("\n" + "="*80)
    print("  BATCH TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Show failed tests
    failed_tests = [r for r in results if not r["passed"]]
    if failed_tests:
        print("\n❌ Failed Tests:")
        for test in failed_tests:
            print(f"\n  Query: {test['query']}")
            print(f"  Expected: {test['expected']}")
            print(f"  Actual: {test['actual']}")
    else:
        print("\n✅ All tests passed!")
    
    print("\n" + "="*80)


def main():
    """
    Main function to run intent classification tests.
    """
    print("\n" + "="*80)
    print("  INTENT CLASSIFIER NODE TEST SUITE")
    print("="*80)
    print("\nChoose test mode:")
    print("  1. Interactive Mode - Enter queries manually")
    print("  2. Batch Mode - Test with predefined queries")
    print("  3. Both modes")
    print("="*80)
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if choice == "1":
        test_intent_classification_interactive()
    elif choice == "2":
        test_intent_classification_batch()
    elif choice == "3":
        test_intent_classification_batch()
        print("\n\nNow starting interactive mode...\n")
        test_intent_classification_interactive()
    else:
        print("\n❌ Invalid choice. Please run again and select 1, 2, or 3.")


if __name__ == "__main__":
    main()
