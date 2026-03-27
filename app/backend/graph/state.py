from typing import TypedDict, List, Dict, Optional , Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages 


class DocumentMeta(TypedDict):
    uploaded: bool
    verified: bool
    data: dict


class ApplicationState(TypedDict):

    user_id: Optional[str]
    user_query: Optional[str]
    uploaded_docs: Optional[dict]
    messages: Annotated[List[BaseMessage] , add_messages]
    intent: Optional[str]
    current_stage: str
    last_valid_stage: str

    uploaded_documents: Dict[str, DocumentMeta]
    all_documents_uploaded: bool
    missing_documents: List[str]
    current_processing_doc: Optional[str]
    extracted_doc_payload: Optional[dict]
    document_processing_status: Optional[str]

    personal_info: dict
    financial_info: dict
    employment_info: dict
    
    all_loan_details_provided: bool
    missing_loan_details: List[str]

    financial_metrics: Dict
    emi_details: Dict

    paused_reason: Optional[str]
    application_saved: bool
    email_sent: bool
    retry_count: int
    doc_retry_count: int