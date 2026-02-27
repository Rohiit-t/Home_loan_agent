from typing import TypedDict, Optional, Dict, Any
from langgraph.graph import StateGraph, END
from state import ApplicationState



class DocumentState(TypedDict):
    file_type: str
    file_name: str
    document_class: Optional[str]
    extracted_data: Optional[Dict[str, Any]]


def document_intake_node(state: DocumentState) -> DocumentState:
    print("Received file:", state["file_name"])
    return state


def classification_node(state: DocumentState) -> DocumentState:
    name = state["file_name"].lower()

    if "aadhar" in name or "aadhaar" in name:
        state["document_class"] = "identity_proof_aadhar"

    elif "pan" in name:
        state["document_class"] = "identity_proof_pan"

    elif "salary" in name or "payslip" in name:
        state["document_class"] = "income_proof"

    elif "bank" in name or "statement" in name:
        state["document_class"] = "bank_statement"

    else:
        state["document_class"] = "unknown_document"

    print("Classified as:", state["document_class"])
    return state


def extraction_node(state: DocumentState) -> DocumentState:
    doc_type = state["document_class"]

    if doc_type == "identity_proof_aadhar":
        state["extracted_data"] = {
            "name": "Palak Verma",
            "dob": "1999-05-12",
            "aadhaar_number": "XXXX-XXXX-1234",
            "address": "Delhi"
        }

    elif doc_type == "identity_proof_pan":
        state["extracted_data"] = {
            "name": "Palak Verma",
            "pan_number": "ABCDE1234F"
        }

    elif doc_type == "income_proof":
        state["extracted_data"] = {
            "name": "Palak Verma",
            "monthly_income": 85000,
            "employment_type": "salaried"
        }

    elif doc_type == "bank_statement":
        state["extracted_data"] = {
            "account_holder": "Palak Verma",
            "avg_balance": 120000
        }

    else:
        state["extracted_data"] = {}

    print("Dummy extraction done")
    return state


def document_processing_node(state: ApplicationState) -> ApplicationState:
    """Wrapper node for document processing in the main graph."""
    print("Document processing initiated...")
    # This is a placeholder - actual document processing would happen here
    return state
