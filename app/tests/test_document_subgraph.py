"""
Test script to verify document processing subgraph independently.
This will process all three documents (aadhaar, pan, itr) sequentially.
"""
import json
from pprint import pprint
from app.backend.nodes.document_processing import build_document_processing_subgraph


def print_state_summary(state, title):
    """Print a formatted summary of the application state."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)
    
    print("\n📄 UPLOADED DOCUMENTS:")
    uploaded_docs = state.get("uploaded_documents", {})
    if uploaded_docs:
        for doc_type, doc_info in uploaded_docs.items():
            print(f"  • {doc_type.upper()}: uploaded={doc_info.get('uploaded')}, verified={doc_info.get('verified')}")
            if doc_info.get('data'):
                print(f"    Data: {json.dumps(doc_info['data'], indent=6)}")
    else:
        print("  (none)")
    
    print("\n👤 PERSONAL INFO:")
    personal_info = state.get("personal_info", {})
    if personal_info:
        pprint(personal_info, indent=4)
    else:
        print("  (none)")
    
    print("\n💰 FINANCIAL INFO:")
    financial_info = state.get("financial_info", {})
    if financial_info:
        pprint(financial_info, indent=4)
    else:
        print("  (none)")
    
    print("\n📋 CURRENT PROCESSING DOC:")
    current_doc = state.get("current_processing_doc")
    print(f"  {current_doc if current_doc else '(none)'}")
    
    print("\n💬 MESSAGES:")
    messages = state.get("messages", [])
    if messages:
        for msg in messages:
            print(f"  • {msg.content}")
    else:
        print("  (none)")
    
    print("\n" + "="*80 + "\n")


def test_document_processing_subgraph():
    """Test the document processing subgraph with mock data."""
    
    print("\n" + "🚀 STARTING DOCUMENT PROCESSING SUBGRAPH TEST" + "\n")
    
    # Build the subgraph
    subgraph = build_document_processing_subgraph()
    
    # Initial state (no documents uploaded)
    initial_state = {
        "user_id": "test_user_123",
        "messages": [],
        "intent": "apply_loan",
        "current_stage": "document_processing",
        "last_valid_stage": "intent_detection",
        "uploaded_documents": {},
        "all_documents_uploaded": False,
        "personal_info": {},
        "financial_info": {},
        "employment_info": {},
        "financial_metrics": {},
        "paused_reason": None,
        "retry_count": 0,
        "current_processing_doc": None
    }
    
    print_state_summary(initial_state, "INITIAL STATE (No documents)")
    
    # Run 1: Process Aadhaar
    print("🔄 Running subgraph - Round 1 (should process Aadhaar)...")
    result_1 = subgraph.invoke(initial_state)
    print_state_summary(result_1, "STATE AFTER ROUND 1 (Aadhaar processed)")
    
    # Run 2: Process PAN
    print("🔄 Running subgraph - Round 2 (should process PAN)...")
    result_2 = subgraph.invoke(result_1)
    print_state_summary(result_2, "STATE AFTER ROUND 2 (PAN processed)")
    
    # Run 3: Process ITR
    print("🔄 Running subgraph - Round 3 (should process ITR)...")
    result_3 = subgraph.invoke(result_2)
    print_state_summary(result_3, "STATE AFTER ROUND 3 (ITR processed)")
    
    # Run 4: All documents processed
    print("🔄 Running subgraph - Round 4 (all documents already processed)...")
    result_4 = subgraph.invoke(result_3)
    print_state_summary(result_4, "STATE AFTER ROUND 4 (All documents done)")
    
    # Verification
    print("\n✅ VERIFICATION:")
    print(f"  • Aadhaar uploaded: {result_4.get('uploaded_documents', {}).get('aadhaar', {}).get('uploaded', False)}")
    print(f"  • PAN uploaded: {result_4.get('uploaded_documents', {}).get('pan', {}).get('uploaded', False)}")
    print(f"  • ITR uploaded: {result_4.get('uploaded_documents', {}).get('itr', {}).get('uploaded', False)}")
    print(f"  • Personal info extracted: {'name' in result_4.get('personal_info', {})}")
    print(f"  • Financial info extracted: {'net_monthly_income' in result_4.get('financial_info', {})}")
    print(f"  • Name from Aadhaar: {result_4.get('personal_info', {}).get('name', 'N/A')}")
    print(f"  • Net monthly income from ITR: {result_4.get('financial_info', {}).get('net_monthly_income', 'N/A')}")
    
    print("\n✨ TEST COMPLETED!\n")
    
    return result_4


if __name__ == "__main__":
    final_state = test_document_processing_subgraph()
