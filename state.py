from typing import TypedDict, List, Dict, Optional , Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages 


class DocumentMeta(TypedDict):
    uploaded: bool
    verified: bool
    data: dict


class ApplicationState(TypedDict):

    user_id: Optional[str]
    messages: Annotated[List[BaseMessage] , add_messages]
    intent: str
    current_stage: str
    last_valid_stage: str

    uploaded_documents: Dict[str, DocumentMeta]
    all_documents_uploaded: bool

    personal_info: dict
    financial_info: dict
    employment_info: dict

    financial_metrics: Dict

    paused_reason: Optional[str]
    retry_count: int
