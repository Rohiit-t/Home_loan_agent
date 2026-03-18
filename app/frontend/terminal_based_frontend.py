"""
Complete Graph End-to-End Test with Terminal Interaction.

This test executes the entire Home Loan Application graph and
interacts with the user through terminal input, demonstrating
the full workflow including interrupts and real-time yield messages.
"""

import os
import sys

# Fix Unicode encoding for Windows terminal
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv

load_dotenv("app/static/.env")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.backend.util.graph import build_graph


def print_header(title):
    """Print a formatted header."""
    print(f"  {title}")


def print_section(title):
    """Print a formatted section."""
    print(f"  {title}")


def display_state_summary(state):
    """Display current state summary."""
    print("\n📊 CURRENT STATE SUMMARY:")
    print(f"   User ID: {state.get('user_id', 'N/A')}")
    print(f"   Current Stage: {state.get('current_stage', 'initial')}")
    print(f"   Intent: {state.get('intent', 'Not classified yet')}")
    
    uploaded_docs = state.get('uploaded_documents', {})
    print(f"   Documents Uploaded: {len(uploaded_docs)}/3")
    if uploaded_docs:
        print(f"      ↳ {', '.join(uploaded_docs.keys())}")
    print(f"   All Docs Complete: {'✅' if state.get('all_documents_uploaded', False) else '⏳'}")
    
    personal = state.get('personal_info', {})
    if personal:
        print(f"   Personal Info: {len(personal)} fields collected")
        if 'name' in personal:
            print(f"      ↳ Name: {personal['name']}")
    
    financial = state.get('financial_info', {})
    if financial:
        print(f"   Financial Info: {len(financial)} fields collected")
        if 'home_loan_amount' in financial:
            print(f"      ↳ Loan Amount: ₹{financial['home_loan_amount']:,.0f}")
    
    employment = state.get('employment_info', {})
    if employment:
        print(f"   Employment Info: {len(employment)} fields collected")
    
    if state.get('all_loan_details_provided'):
        print(f"   Loan Details: ✅ Complete")
    
    financial_metrics = state.get('financial_metrics', {})
    if financial_metrics:
        print(f"   Risk Assessment: ✅ Completed")
        if 'ltv_ratio' in financial_metrics:
            print(f"      ↳ LTV: {financial_metrics['ltv_ratio']:.2f}%")
    
    emi_details = state.get('emi_details', {})
    if emi_details and 'monthly_emi' in emi_details:
        print(f"   EMI Calculated: ₹{emi_details['monthly_emi']:,.2f}/month")
    
    print(f"   Application Saved: {'✅' if state.get('application_saved', False) else '⏳'}")


def display_messages(messages):
    """Display recent messages, filtering out progress/yield messages."""
    if not messages:
        return
    
    print("\n💬 CONVERSATION:")
    
    # Filter to show only substantive messages (not progress indicators)
    substantive_messages = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            # Skip pure progress messages
            is_progress = any(indicator in msg.content for indicator in [
                "Analyzing", "Extracting", "Processing", "Checking",
                "Calculating", "Saving", "Preparing", "Sending",
                "Query classified"
            ])
            if not is_progress or len(msg.content) > 100:
                substantive_messages.append(msg)
        else:
            substantive_messages.append(msg)
    
    # Show last 3 substantive messages
    for msg in substantive_messages[-3:]:
        if isinstance(msg, HumanMessage):
            print(f"   👤 User: {msg.content}")
        elif isinstance(msg, AIMessage):
            content_preview = msg.content[:150] + '...' if len(msg.content) > 150 else msg.content
            print(f"   🤖 Assistant: {content_preview}")


def test_complete_graph_interactive():
    """
    Test the complete graph with interactive terminal input.
    """
    print_header("HOME LOAN APPLICATION ")
    print("Let's start Home Loan Application.\n" \
    "Start Sharing Your Information")
    print("\nType 'exit' at any prompt to quit the test.")
    
    print_section("Initial Setup")
    user_id = input("Enter User ID (or press Enter for 'test_user'): ").strip()
    if not user_id:
        user_id = "test_user"
    
    print(f"\n User ID: {user_id}")

    email = input("Enter your email (for notifications, optional): ").strip()
    
    print("\n Building the complete graph...")
    graph = build_graph()
    print(" Graph built successfully!")
    
    config = {
        "configurable": {
            "thread_id": f"test_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    }
    
    initial_state = {
        "messages": [],
        "intent": None,
        "user_id": user_id,
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
    initial_state["personal_info"] = {"email": email} if email else {}
    
    print("\n Starting the Home Loan Application workflow...")
    
    step_count = 0
    interaction_count = 0
    is_first_run = True
    
    try:
        while True:
            step_count += 1
            
            if is_first_run or step_count > 1:
                snapshot = graph.get_state(config)
                current_state = snapshot.values if snapshot.values else initial_state
                next_nodes = snapshot.next
                
                # Display current messages
                messages = current_state.get("messages", [])
                if messages:
                    print("\n💬 Recent Conversation:")
                    for msg in messages[-2:]:  # Show last 2 messages
                        if isinstance(msg, HumanMessage):
                            print(f"    User: {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}")
                        elif isinstance(msg, AIMessage):
                            print(f"    Assistant: {msg.content[:200]}{'...' if len(msg.content) > 200 else ''}")
                
                print("\n Your turn to interact with the system:")
                user_input = input(" You: ").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    print("\n Exiting test. Thank you!")
                    break
                
                if not user_input:
                    print("  Please enter a valid input.")
                    continue
                
                interaction_count += 1
                
                # Prepare input for graph: only pass the new message, not entire state
                if is_first_run:
                    input_state = initial_state.copy()
                    input_state["messages"] = [HumanMessage(content=user_input)]
                    is_first_run = False
                else:
                    input_state = {
                        "messages": [HumanMessage(content=user_input)]
                    }
            else:
                input_state = None
            
            # Stream through the graph with dual mode for yield messages and node updates
            print("\n🔄 Processing through the graph...\n")
            
            events_collected = []
            seen_messages = set()
            yield_progress_msgs = []
            
            # Track previous message count to detect new messages
            snapshot_before = graph.get_state(config)
            prev_msg_count = len(snapshot_before.values.get("messages", [])) if snapshot_before.values else 0
            
            # Use values mode to capture yielded messages in real-time
            for chunk in graph.stream(input_state, config, stream_mode="values"):
                events_collected.append(chunk)
                
                # Check for new messages (including yielded progress messages)
                if "messages" in chunk:
                    messages = chunk["messages"]
                    if len(messages) > prev_msg_count:
                        # New messages were added
                        for msg in messages[prev_msg_count:]:
                            if isinstance(msg, AIMessage):
                                content = msg.content
                                msg_hash = hash(content)
                                
                                # Check if this is a progress/yield message
                                is_progress_msg = any(indicator in content for indicator in [
                                    "Analyzing", "Extracting", "Processing", "Checking",
                                    "Calculating", "Saving", "Preparing", "Sending",
                                    "Finding information"
                                ])
                                
                                if msg_hash not in seen_messages:
                                    seen_messages.add(msg_hash)
                                    
                                    if is_progress_msg:
                                        # Show progress message immediately
                                        print(f"   ⚡ {content}")
                                        yield_progress_msgs.append(content)
                                    elif len(content) < 150 and any(x in content for x in ["Query classified", "noted"]):
                                        # Short status messages
                                        print(f"   ℹ️  {content}")
                    
                    prev_msg_count = len(messages)
                
                # Show key state changes
                if "intent" in chunk and chunk["intent"]:
                    print(f"   📌 Intent: {chunk['intent']}")
                
                if "uploaded_documents" in chunk:
                    docs = chunk["uploaded_documents"]
                    if docs and len(docs) > len(snapshot_before.values.get("uploaded_documents", {})) if snapshot_before.values else True:
                        print(f"   📄 Documents: {list(docs.keys())}")
                
                if "all_documents_uploaded" in chunk:
                    if chunk["all_documents_uploaded"]:
                        print(f"   ✅ All documents uploaded!")
                
                if "all_loan_details_provided" in chunk:
                    if chunk.get("all_loan_details_provided"):
                        print(f"   ✅ All loan details collected!")
                
                if "application_saved" in chunk:
                    if chunk["application_saved"]:
                        print(f"   💾 Application saved successfully!")
            
            print(f"\n✓ Processing complete (captured {len(yield_progress_msgs)} progress updates)")
            
            # Get updated state from checkpoint
            snapshot = graph.get_state(config)
            current_state = snapshot.values
            next_nodes = snapshot.next
            
            print(f"Current position: {next_nodes if next_nodes else 'END'}")
            
            # Display state summary
            display_state_summary(current_state)
            
            # Display recent messages
            display_messages(current_state.get("messages", []))
            
            # Check if execution is complete
            if not next_nodes:
                # Check if workflow is truly complete or just paused
                is_truly_complete = (
                    current_state.get("application_saved", False) or
                    current_state.get("current_stage") == "completed"
                )
                
                if is_truly_complete:
                    print_section("Workflow Complete")
                    print("\n The graph execution has reached END!")
                    print(f"\nTotal Steps: {step_count}")
                    print(f"\n Total Interactions: {interaction_count}")
                    
                    # Show final state
                    print_header("FINAL APPLICATION STATE")
                    display_state_summary(current_state)
                    
                    # Check if application was saved
                    if current_state.get("application_saved"):
                        print("\n Application was successfully saved!")
                    else:
                        print("\n  Application was not saved (may have ended early)")
                    
                    break
                else:
                    print(f"\n⏸  Graph paused. Workflow is incomplete - continuing...")
            
            if next_nodes:
                print(f"\n  Graph paused. Waiting for user input...")
                # Loop will continue and prompt for next user input
    
    except KeyboardInterrupt:
        print("\n\n  Test interrupted by user (Ctrl+C)")
    
    except Exception as e:
        print(f"\n\n Error during graph execution: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print_header("TEST COMPLETE")


def main():
    """
    Main function to run complete graph tests.
    """
    test_complete_graph_interactive()
    


if __name__ == "__main__":
    main()
