from langgraph.graph import StateGraph, END
from app.backend.schema.state import ApplicationState
from app.backend.nodes.agent import HomeLoanAgent
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def build_test_graph():
    """Build a simple test graph with just the intent classification node."""
    agent = HomeLoanAgent()
    graph = StateGraph(ApplicationState)
    
    # Add the intent classification node
    graph.add_node("intent_classifier", agent.intent_classifier)
    
    # Set entry point
    graph.set_entry_point("intent_classifier")
    
    # After intent classification, end the graph
    graph.add_edge("intent_classifier", END)
    
    return graph.compile()


def test_intent_classifier():
    """Test the intent classifier with user input from terminal."""
    print("=" * 60)
    print("Intent Classification Node Tester")
    print("=" * 60)
    print("\nThis will classify your query into one of these intents:")
    print("  - Document_upload")
    print("  - Text_info")
    print("  - Homeloan_query")
    print("  - Yes")
    print("\nType 'quit' or 'exit' to stop testing.\n")
    
    # Build the graph
    graph = build_test_graph()
    
    while True:
        # Get user input
        user_query = input("Enter your query: ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            print("\nExiting tester. Goodbye!")
            break
        
        if not user_query:
            print("Please enter a valid query.\n")
            continue
        
        # Create initial state with user message
        initial_state = {
            "messages": [HumanMessage(content=user_query)],
            "intent": "",
            "current_stage": "intent_classification",
            "last_valid_stage": "",
            "user_id": None,
            "uploaded_documents": {},
            "all_documents_uploaded": False,
            "personal_info": {},
            "financial_info": {},
            "employment_info": {},
            "financial_metrics": {},
            "paused_reason": None,
            "retry_count": 0
        }
        
        try:
            # Run the graph
            print("\nProcessing...")
            result = graph.invoke(initial_state)
            
            # Display the result
            print(f"\n{'─' * 60}")
            print(f"Query: {user_query}")
            print(f"Classified Intent: {result.get('intent', 'Unknown')}")
            print(f"{'─' * 60}\n")
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")


if __name__ == "__main__":
    test_intent_classifier()
