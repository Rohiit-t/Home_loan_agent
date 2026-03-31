import json
import os
import re
from typing import Any, Dict
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END

from app.backend.graph.state import ApplicationState

def _norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _flatten_keys(value: Any, output: set[str]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            output.add(str(key).strip().lower())
            _flatten_keys(nested, output)
    elif isinstance(value, list):
        for item in value:
            _flatten_keys(item, output)


def detect_document_type(doc: Dict[str, Any]) -> str:
    keys: set[str] = set()
    _flatten_keys(doc, keys)

    normalized_text = " ".join(sorted(keys)).lower()
    serialized_doc = json.dumps(doc, ensure_ascii=False).lower()
    doc_type_value = str(doc.get("document_type") or "").strip().lower()

    aadhaar_markers = {"aadhaar", "aadhaar_number", "uidai", "uid", "aadhar", "id_number"}
    pan_markers = {"pan", "pan_number", "permanent_account_number", "father_name"}
    itr_markers = {
        "itr",
        "assessment_year",
        "gross_total_income",
        "total_income",
        "taxable_income",
        "annual_income",
        "income_tax",
        "tax_paid",
        "ack_number",
        "form16",
    }

    if doc_type_value in {"aadhaar", "aadhar", "aadhaar_card", "aadhar_card"}:
        return "aadhaar"
    if doc_type_value in {"pan", "pan_card"}:
        return "pan"
    if doc_type_value in {"itr", "income_tax_return"}:
        return "itr"

    search_space = f"{normalized_text} {serialized_doc}"

    has_aadhaar_signal = (
        bool(keys.intersection(aadhaar_markers))
        or bool(re.search(r"\b(aadhaar|aadhar|uidai|uid)\b", search_space))
        or bool(re.search(r"\b\d{4}[ -]\d{4}[ -]\d{4}\b", serialized_doc))
    )

    has_itr_signal = (
        bool(keys.intersection(itr_markers))
        or bool(re.search(r"\bitr\b|assessment[_ ]?year|taxable[_ ]?income|gross[_ ]?total[_ ]?income|total[_ ]?income|tax[_ ]?paid|ack[_ ]?number", search_space))
    )

    has_pan_signal = (
        bool(keys.intersection(pan_markers))
        or bool(re.search(r"\bpan\b|\b[a-z]{5}[0-9]{4}[a-z]\b", search_space))
    )

    if has_aadhaar_signal:
        return "aadhaar"
    if has_itr_signal:
        return "itr"
    if has_pan_signal:
        return "pan"

    return "unknown"


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
        Second node: Classify uploaded document type using rule-based regex.
        """
        input_doc = state.get("uploaded_docs")

        if not isinstance(input_doc, dict):
            return {
                "current_processing_doc": None,
                "uploaded_docs": None,
            }

        doc_type = detect_document_type(input_doc)
        if doc_type == "unknown":
            doc_type = None

        return {"current_processing_doc": doc_type}

    def data_extraction_node(self, state: ApplicationState) -> ApplicationState:
        """
        Third node: Extract data from corresponding mock JSON and store to state.
        Safely accumulates data across multiple invocations.
        """
        doc_type = state.get("current_processing_doc")
        input_doc = state.get("uploaded_docs")
        
        if not doc_type:
            return {
                "current_processing_doc": None,
                "uploaded_docs": None,
                "document_processing_status": "unsupported",
                "messages": [AIMessage(content="Unsupported document type. This file is skipped. Please upload Aadhaar, PAN, or ITR JSON.")],
            }

        if not isinstance(input_doc, dict):
            return {
                "current_processing_doc": None,
                "uploaded_docs": None,
                "document_processing_status": "invalid_payload",
                "messages": [AIMessage(content="No document payload received. Please upload a valid JSON document.")],
            }

        uploaded_docs = state.get("uploaded_documents", {}) or {}

        existing_doc = uploaded_docs.get(doc_type) if isinstance(uploaded_docs, dict) else None
        if isinstance(existing_doc, dict) and existing_doc.get("uploaded"):
            doc_label = str(doc_type).upper()
            return {
                "current_processing_doc": None,
                "uploaded_docs": None,
                "extracted_doc_payload": None,
                "document_processing_status": "duplicate",
                "messages": [
                    AIMessage(
                        content=f"{doc_label} is already uploaded. Re-upload of {doc_label} is not allowed. Please continue with other required documents."
                    )
                ],
            }

        updates: Dict[str, Any] = {
            "uploaded_docs": None,
            "document_processing_status": "extracted",
        }

        # Extract specific details to the main state
        personal_info_updates: Dict[str, Any] = {}
        financial_info_updates: Dict[str, Any] = {}

        if doc_type == "aadhaar":
            personal_info_updates["name"] = input_doc.get("name")
            personal_info_updates["age"] = input_doc.get("age")
            personal_info_updates["dob"] = input_doc.get("dob")
        elif doc_type == "pan":
            personal_info_updates["name"] = input_doc.get("name")
            personal_info_updates["pan_number"] = input_doc.get("pan_number") or input_doc.get("pan")
            personal_info_updates["dob"] = input_doc.get("dob")
        elif doc_type == "itr":
            annual_income = (
                input_doc.get("annual_income")
                or input_doc.get("gross_total_income")
                or input_doc.get("total_income")
            )
            if isinstance(annual_income, (int, float)) and annual_income > 0:
                financial_info_updates["net_monthly_income"] = float(annual_income) / 12
            else:
                net_monthly_income = input_doc.get("net_monthly_income")
                if isinstance(net_monthly_income, (int, float)):
                    financial_info_updates["net_monthly_income"] = float(net_monthly_income)

            personal_info_updates["name"] = input_doc.get("name")
            personal_info_updates["pan_number"] = input_doc.get("pan") or input_doc.get("pan_number")

        updates["extracted_doc_payload"] = {
            "doc_type": doc_type,
            "doc_data": input_doc,
            "personal_info_updates": {k: v for k, v in personal_info_updates.items() if v is not None},
            "financial_info_updates": {k: v for k, v in financial_info_updates.items() if v is not None},
        }

        return updates

    def mismatch_check_node(self, state: ApplicationState) -> ApplicationState:
        # If extraction already failed (e.g. duplicate or unsupported), do nothing
        # and preserve the error status.
        status = state.get("document_processing_status")
        if status in ["duplicate", "unsupported"]:
            return {}

        payload = state.get("extracted_doc_payload")
        if not isinstance(payload, dict):
            return {
                "current_processing_doc": None,
                "uploaded_docs": None,
                "extracted_doc_payload": None,
                "document_processing_status": "invalid_payload",
                "messages": [AIMessage(content="Unable to process document. Invalid payload.")],
            }

        doc_type = payload.get("doc_type")
        doc_data = payload.get("doc_data") if isinstance(payload.get("doc_data"), dict) else {}
        personal_info_updates = payload.get("personal_info_updates") if isinstance(payload.get("personal_info_updates"), dict) else {}
        financial_info_updates = payload.get("financial_info_updates") if isinstance(payload.get("financial_info_updates"), dict) else {}

        existing_personal_info = dict(state.get("personal_info", {}) or {})

        existing_name = _norm_text(existing_personal_info.get("name"))
        new_name = _norm_text(personal_info_updates.get("name"))

        existing_pan = _norm_text(existing_personal_info.get("pan_number"))
        new_pan = _norm_text(personal_info_updates.get("pan_number"))

        existing_dob = _norm_text(existing_personal_info.get("dob"))
        new_dob = _norm_text(personal_info_updates.get("dob"))

        mismatch_reasons = []
        if existing_name and new_name and existing_name != new_name:
            mismatch_reasons.append("name mismatch")
        if existing_pan and new_pan and existing_pan != new_pan:
            mismatch_reasons.append("PAN mismatch")
        if existing_dob and new_dob and existing_dob != new_dob:
            mismatch_reasons.append("DOB mismatch")

        if mismatch_reasons:
            doc_label = str(doc_type).upper() if doc_type else "DOCUMENT"
            reason_text = ", ".join(mismatch_reasons)
            return {
                "current_processing_doc": None,
                "uploaded_docs": None,
                "extracted_doc_payload": None,
                "document_processing_status": "mismatch",
                "messages": [
                    AIMessage(
                        content=(
                            f"{doc_label} data mismatch detected ({reason_text}). "
                            "Wrong document may be uploaded. Please re-upload the correct document or start a new chat."
                        )
                    )
                ],
            }

        uploaded_docs = dict(state.get("uploaded_documents", {}) or {})
        uploaded_docs[doc_type] = {
            "uploaded": True,
            "verified": True,
            "data": doc_data,
        }

        updated_personal_info = dict(existing_personal_info)
        updated_personal_info.update(personal_info_updates)

        updated_financial_info = dict(state.get("financial_info", {}) or {})
        updated_financial_info.update(financial_info_updates)

        extracted_details = []
        for key, value in personal_info_updates.items():
            if key == 'pan_number':
                label = 'PAN Number'
            elif key == 'dob':
                label = 'DOB'
            else:
                label = key.replace('_', ' ').title()
            extracted_details.append(f"• {label}: {value}")

        for key, value in financial_info_updates.items():
            if key == 'net_monthly_income':
                label = 'Net Monthly Income'
                if isinstance(value, (int, float)):
                    extracted_details.append(f"• {label}: ₹{value:,.2f}")
                    continue
            else:
                label = key.replace('_', ' ').title()
            extracted_details.append(f"• {label}: {value}")

        msg_content = f"Successfully processed {doc_type} document."
        if extracted_details:
            msg_content += "\n\nExtracted Info:\n" + "\n".join(extracted_details)

        return {
            "uploaded_documents": uploaded_docs,
            "personal_info": updated_personal_info,
            "financial_info": updated_financial_info,
            "current_processing_doc": None,
            "uploaded_docs": None,
            "extracted_doc_payload": None,
            "document_processing_status": "processed",
            "messages": [AIMessage(content=msg_content)],
        }


def build_document_processing_subgraph():
    """Builds and returns the document processing subgraph."""
    builder = StateGraph(ApplicationState)
    nodes = DocumentProcessingNodes()

    builder.add_node("document_tampering", nodes.document_tampering_node)
    builder.add_node("document_classification", nodes.document_classification_node)
    builder.add_node("data_extraction", nodes.data_extraction_node)
    builder.add_node("mismatch_check", nodes.mismatch_check_node)

    builder.add_edge(START, "document_tampering")
    builder.add_edge("document_tampering", "document_classification")
    builder.add_edge("document_classification", "data_extraction")
    builder.add_edge("data_extraction", "mismatch_check")
    builder.add_edge("mismatch_check", END)

    return builder.compile()

