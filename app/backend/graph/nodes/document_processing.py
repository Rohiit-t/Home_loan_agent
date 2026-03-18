import json
import os
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from app.backend.graph.state import ApplicationState

# Mock data lives at repo-root mock_data/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MOCK_DATA_DIR = os.path.join(PROJECT_ROOT, "mock_data")


class DocumentProcessingNodes:
    """Class to encapsulate document processing nodes for the subgraph."""

    def document_tampering_node(self, state: ApplicationState) -> ApplicationState:
        """
        First node: Document tampering check.
        We just pass it as requested.
        """
        return state

    def document_classification_node(self, state: ApplicationState) -> ApplicationState:
        """
        Second node: Classify the document based on missing docs.
        Sequence: Aadhaar -> PAN -> ITR.
        """
        uploaded_docs = state.get("uploaded_documents", {})
        if not uploaded_docs:
            uploaded_docs = {}
        
        if "aadhaar" not in uploaded_docs:
            doc_type = "aadhaar"
        elif "pan" not in uploaded_docs:
            doc_type = "pan"
        elif "itr" not in uploaded_docs:
            doc_type = "itr"
        else:
            doc_type = None

        return {"current_processing_doc": doc_type}

    def data_extraction_node(self, state: ApplicationState) -> ApplicationState:
        """
        Third node: Extract data from corresponding mock JSON and store to state.
        Safely accumulates data across multiple invocations.
        """
        doc_type = state.get("current_processing_doc")
        
        if not doc_type:
            return {"current_processing_doc": None}

        mock_file_path = os.path.join(MOCK_DATA_DIR, f"{doc_type}.json")
        
        try:
            with open(mock_file_path, "r") as f:
                mock_data = json.load(f)
        except FileNotFoundError:
            mock_data = {}

        uploaded_docs = state.get("uploaded_documents", {})
        if not uploaded_docs:
            uploaded_docs = {}
        
        uploaded_docs = dict(uploaded_docs)
            
        uploaded_docs[doc_type] = {
            "uploaded": True,
            "verified": True,
            "data": mock_data
        }

        updates = {
            "uploaded_documents": uploaded_docs,
            "current_processing_doc": None,
            "messages": [AIMessage(content=f"Successfully processed {doc_type} document.")]
        }

        # Extract specific details to the main state
        if doc_type == "aadhaar":
            personal_info = dict(state.get("personal_info", {}) or {})
            personal_info["name"] = mock_data.get("name")
            updates["personal_info"] = personal_info
        elif doc_type == "pan":
            personal_info = dict(state.get("personal_info", {}) or {})
            updates["personal_info"] = personal_info
        elif doc_type == "itr":
            financial_info = dict(state.get("financial_info", {}) or {})
            financial_info["net_monthly_income"] = mock_data.get("net_monthly_income")
            updates["financial_info"] = financial_info

        return updates


def build_document_processing_subgraph():
    """Builds and returns the document processing subgraph."""
    builder = StateGraph(ApplicationState)
    nodes = DocumentProcessingNodes()

    builder.add_node("document_tampering", nodes.document_tampering_node)
    builder.add_node("document_classification", nodes.document_classification_node)
    builder.add_node("data_extraction", nodes.data_extraction_node)

    builder.add_edge(START, "document_tampering")
    builder.add_edge("document_tampering", "document_classification")
    builder.add_edge("document_classification", "data_extraction")
    builder.add_edge("data_extraction", END)

    return builder.compile()

