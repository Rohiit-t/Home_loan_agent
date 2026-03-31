"""
Direct test of document processing subgraph integration.
Tests the document_processing node directly without needing LLM API keys.
"""
import json
from pprint import pprint
from langchain_core.messages import HumanMessage
from app.backend.nodes.agent import HomeLoanAgent


def print_state_summary(state, title):
    """Print a formatted summary of the application state."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)
    
    print("\n🔄 CURRENT STAGE:", state.get("current_stage", "None"))
    
    print("\n📄 UPLOADED DOCUMENTS:")
    uploaded_docs = state.get("uploaded_documents", {})
    if uploaded_docs:
        for doc_type, doc_info in uploaded_docs.items():
            print(f"  ✅ {doc_type.upper()}: verified={doc_info.get('verified')}")
            print(f"     Data: {json.dumps(doc_info.get('data', {}), indent=10)[:100]}...")
    else:
        print("  (none)")
    
    print("\n👤 PERSONAL INFO:")
    personal_info = state.get("personal_info", {})
    if personal_info:
        for key, value in personal_info.items():
            print(f"  {key}: {value}")
    else:
        print("  (none)")
    
    print("\n💰 FINANCIAL INFO:")
    financial_info = state.get("financial_info", {})
    if financial_info:
        for key, value in financial_info.items():
            print(f"  {key}: {value}")
    else:
        print("  (none)")
    
    print("\n💬 MESSAGES:")
    messages = state.get("messages", [])
    if messages:
        for i, msg in enumerate(messages[-3:], 1):  # Show last 3 messages
            print(f"  {i}. {msg.content}")
    else:
        print("  (none)")
    
    print("\n" + "="*80 + "\n")


def test_document_processing_node():
    """Test the document_processing node directly."""
    
    print("\n🚀 TESTING DOCUMENT PROCESSING NODE INTEGRATION\n")
    
    # Initialize the agent
    agent = HomeLoanAgent()
    print("✅ HomeLoanAgent initialized\n")
    
    # Test 1: Process Aadhaar
    print("📤 TEST 1: Processing Aadhaar document")
    state_1 = {
        "user_id": "test_user_789",
        "messages": [HumanMessage(content="Uploading Aadhaar")],
        "intent": "Document_upload",
        "current_stage": "document_processing",
        "last_valid_stage": "intent_detection",
        "uploaded_documents": {},
        "all_documents_uploaded": False,
        "current_processing_doc": None,
        "personal_info": {},
        "financial_info": {},
        "employment_info": {},
        "financial_metrics": {},
        "paused_reason": None,
        "retry_count": 0
    }
    
    result_1 = agent.document_processing(state_1)
    print_state_summary(result_1, "RESULT AFTER AADHAAR PROCESSING")
    
    # Test 2: Process PAN
    print("📤 TEST 2: Processing PAN document")
    state_2 = result_1.copy()
    state_2["messages"] = [HumanMessage(content="Uploading PAN")]
    
    result_2 = agent.document_processing(state_2)
    print_state_summary(result_2, "RESULT AFTER PAN PROCESSING")
    
    # Test 3: Process ITR
    print("📤 TEST 3: Processing ITR document")
    state_3 = result_2.copy()
    state_3["messages"] = [HumanMessage(content="Uploading ITR")]
    
    result_3 = agent.document_processing(state_3)
    print_state_summary(result_3, "RESULT AFTER ITR PROCESSING")
    
    # Test 4: All documents already processed
    print("📤 TEST 4: All documents already processed")
    state_4 = result_3.copy()
    state_4["messages"] = [HumanMessage(content="Uploading another document")]
    
    result_4 = agent.document_processing(state_4)
    print_state_summary(result_4, "RESULT AFTER ALL DOCS PROCESSED")
    
    # Now test state evaluator integration
    print("🔍 TEST 5: Testing State Evaluator after document processing")
    result_5 = agent.state_evaluator(result_4)
    print_state_summary(result_5, "RESULT AFTER STATE EVALUATION")
    
    # Verification
    print("\n✅ INTEGRATION VERIFICATION:")
    print(f"  • Aadhaar Processed: {'aadhaar' in result_1.get('uploaded_documents', {})}")
    print(f"  • PAN Processed: {'pan' in result_2.get('uploaded_documents', {})}")
    print(f"  • ITR Processed: {'itr' in result_3.get('uploaded_documents', {})}")
    print(f"  • Name Extracted: {result_1.get('personal_info', {}).get('name') == 'Jane Doe'}")
    print(f"  • Income Extracted: {result_3.get('financial_info', {}).get('net_monthly_income') == 85000.0}")
    print(f"  • Stage Set to Evaluation: {result_1.get('current_stage') == 'state_evaluation'}")
    print(f"  • All Documents Flag: {result_5.get('all_documents_uploaded', False)}")
    
    all_docs_processed = len(result_3.get('uploaded_documents', {})) == 3
    name_extracted = result_1.get('personal_info', {}).get('name') == 'Jane Doe'
    income_extracted = result_3.get('financial_info', {}).get('net_monthly_income') == 85000.0
    stage_correct = result_1.get('current_stage') == 'state_evaluation'
    
    if all_docs_processed and name_extracted and income_extracted and stage_correct:
        print("\n🎉 SUCCESS! Document processing subgraph is fully integrated!")
        print("   ✅ Subgraph processes documents correctly")
        print("   ✅ Data extracted to personal_info and financial_info")
        print("   ✅ Returns to state_evaluation stage")
        print("   ✅ State evaluator can check completion status")
    else:
        print("\n⚠️ Integration has some issues:")
        if not all_docs_processed:
            print("   ❌ Not all documents were processed")
        if not name_extracted:
            print("   ❌ Name was not extracted from Aadhaar")
        if not income_extracted:
            print("   ❌ Income was not extracted from ITR")
        if not stage_correct:
            print("   ❌ Stage was not set to state_evaluation")
    
    return result_5


if __name__ == "__main__":
    final_state = test_document_processing_node()
