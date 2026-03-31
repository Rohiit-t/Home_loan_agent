"""
HomeLoan Agent - A class-based implementation of all LangGraph nodes.

"""

import random
import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from typing import Literal
import threading
import logging

logger = logging.getLogger("home-loan-email")

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt
try:
    from langgraph.config import get_stream_writer
except ImportError:
    from langgraph.types import get_stream_writer

from app.backend.graph.state import ApplicationState
from app.backend.util.model import get_structured_model, get_model
from app.static.config import MANDATORY_DOCS, LTV_THRESHOLD, FOIR_THRESHOLD, MIN_CIBIL, DEFAULT_INTEREST_RATE

class IntentClassification(BaseModel):
    """Schema for intent classification output."""
    intent: Literal["Document_upload", "Text_info", "Irrelevant", "Homeloan_query"] = Field(
        description="The assigned intent of the user's message."
    )


class PersonalInfo(BaseModel):
    """Schema for personal information."""
    name: Optional[str] = Field(None, description="Full name of the person")
    age: Optional[int] = Field(None, description="Age of the person")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    
    class Config:
        extra = "forbid" 


class FinancialInfo(BaseModel):
    """Schema for financial information."""
    net_monthly_income: Optional[float] = Field(None, description="Net monthly income")
    total_existing_emis: Optional[float] = Field(None, description="Total existing EMIs")
    
    class Config:
        extra = "forbid"


class EmploymentInfo(BaseModel):
    """Schema for employment information."""
    employer_name: Optional[str] = Field(None, description="Name of the employer")
    employment_type: Optional[str] = Field(None, description="Type of employment (Salaried/Self-employed)")
    
    class Config:
        extra = "forbid"


class ExtractedInfo(BaseModel):
    """Schema for extracting user information from text."""
    personal_info: Optional[PersonalInfo] = Field(
        None,
        description="Personal information like name, age, phone, email if found."
    )
    financial_info: Optional[FinancialInfo] = Field(
        None,
        description="Financial information like net_monthly_income, total_existing_emis if found."
    )
    employment_info: Optional[EmploymentInfo] = Field(
        None,
        description="Employment information like employer_name, employment_type if found."
    )
    
    class Config:
        extra = "forbid"


class LoanDetails(BaseModel):
    """Schema for loan details extraction."""
    home_loan_amount: Optional[float] = Field(
        None,
        description="The desired home loan amount."
    )
    down_payment: Optional[float] = Field(
        None,
        description="The planned down payment amount."
    )
    tenure_years: Optional[int] = Field(
        None,
        description="The loan tenure in years."
    )
    
    class Config:
        extra = "forbid"


class EmploymentStatusChoice(BaseModel):
    """Schema for employment status classification."""
    employment_status: Literal["employed", "self_employed", "unemployed", "unknown"] = Field(
        description=(
            "Canonical employment status. Use 'employed', 'self_employed', "
            "'unemployed', or 'unknown'."
        )
    )
    
    class Config:
        extra = "forbid"


class ExistingEmiChoice(BaseModel):
    """Schema for existing EMI availability classification."""
    has_existing_emi: Literal["yes", "no", "unknown"] = Field(
        description="Whether user has existing EMI obligations."
    )

    class Config:
        extra = "forbid"


class ExistingEmiDetails(BaseModel):
    """Schema for existing EMI details extraction."""
    monthly_emi: Optional[float] = Field(
        None,
        description="Monthly EMI amount in rupees for existing loan obligation."
    )
    loan_amount: Optional[float] = Field(
        None,
        description="Original existing loan amount in rupees."
    )
    tenure_months: Optional[int] = Field(
        None,
        description="Remaining tenure for existing loan in months."
    )

    class Config:
        extra = "forbid"


class HomeLoanAgent:
    """
    Unified Agent class for Home Loan Application processing.
    
    This class encapsulates all node logic for the LangGraph workflow,
    following industry standards for better organization, maintainability,
    and testability.
    
    Each method represents a node in the LangGraph workflow.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the HomeLoanAgent.
        """
        self.config = config or {}
        self.mandatory_docs = MANDATORY_DOCS
        self.ltv_threshold = LTV_THRESHOLD
        self.foir_threshold = FOIR_THRESHOLD
        self.min_cibil = MIN_CIBIL
        self.interest_rate = DEFAULT_INTEREST_RATE

    def _latest_user_query(self, messages: list) -> str:
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                content = getattr(message, "content", "")
                if isinstance(content, str) and content.strip():
                    return content

            message_type = str(getattr(message, "type", "")).lower()
            if message_type == "human":
                content = getattr(message, "content", "")
                if isinstance(content, str) and content.strip():
                    return content

        last_content = getattr(messages[-1], "content", "") if messages else ""
        return str(last_content) if last_content else ""

    def _resolve_user_query(self, state: ApplicationState) -> str:
        direct_query = state.get("user_query")
        if isinstance(direct_query, str) and direct_query.strip():
            return direct_query.strip()

        messages = state.get("messages", [])
        return self._latest_user_query(messages)

    def _normalize_employment_status(self, value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None

        normalized = value.strip().lower()
        if not normalized:
            return None

        if "unemploy" in normalized:
            return "unemployed"

        if (
            "self" in normalized
            or "business" in normalized
            or "entrepreneur" in normalized
            or "freelanc" in normalized
        ):
            return "self_employed"

        if "employ" in normalized or "salaried" in normalized or "salary" in normalized or "job" in normalized:
            return "employed"

        return None
    
    
    def intent_classifier(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 1: Intent Classifier
        
        Classifies user intent into one of four categories:
        - Document_upload: User mentions document upload
        - Text_info: User provides textual information
        - Homeloan_query: User asks questions about home loans
        - Irrelevant: User query is off-topic
    
        """
        writer = get_stream_writer()
        uploaded_docs = state.get("uploaded_docs")

        if isinstance(uploaded_docs, dict):
            writer({"type": "status", "node": "intent_classifier", "msg": "✅ Query classified: Document_upload"})
            return {"intent": "Document_upload"}

        messages = state.get("messages", [])
        user_query = self._resolve_user_query(state)
        if not user_query:
            if not messages:
                return state
            return {"intent": "Irrelevant"}

        writer({"type": "status", "node": "intent_classifier", "msg": "🔍 Analyzing your query..."})

        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", user_query):
            writer({"type": "status", "node": "intent_classifier", "msg": "✅ Query classified: Text_info"})
            return {"intent": "Text_info"}

        system_prompt = """
        You are a strict intent classifier for a Home Loan Application.

        Your task:
        Given the user's message, classify it into exactly one of the following categories:
        - 'Document_upload': if the user mentions uploading a document like PAN, Aadhaar, Salary slip, etc.
        - 'Text_info': if the user provides information like personal details (e.g. name), financial, or employment details in text.
            IMPORTANT: if the message contains an email address, a person's name (such as "User One", "John", etc.), or other personal details, classify as 'Text_info'.
        - 'Homeloan_query': if the user asks questions about home loans, interest rates, eligibility, etc.
        - 'Irrelevant': if the user asks something completely unrelated to home loans or the application process.

        Be strict. If unsure, return "irrelevant".
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        llm = get_structured_model()
        structured_llm = llm.with_structured_output(IntentClassification)
        
        chain = prompt | structured_llm
        result = chain.invoke({"query": user_query})

        writer({"type": "status", "node": "intent_classifier", "msg": f"✅ Query classified: {result.intent}"})

        return {"intent": result.intent}
    
    def irrelevant_handler(self, state: ApplicationState) -> ApplicationState:
        """
        Node 2: Irrelevant Query Handler
        
        Handles queries that are not related to home loan application.
        Provides a polite response to guide user back on topic.

        """
        all_docs_uploaded = state.get("all_documents_uploaded", False)
        doc_retry_count = int(state.get("doc_retry_count", 0) or 0)
        max_retry_count = 3

        if not all_docs_uploaded:
            doc_retry_count += 1
            attempts_left = max_retry_count - doc_retry_count

            if doc_retry_count >= max_retry_count:
                fail_msg = AIMessage(
                    content=(
                        "❌ Unsuccessful process: maximum retry attempts reached.\n\n"
                        "You provided irrelevant/invalid responses multiple times while uploading required documents. "
                        "Please start a new application."
                    )
                )
                return {
                    "messages": [fail_msg],
                    "paused_reason": "Maximum retries reached in document collection loop.",
                    "current_stage": "failed_max_retries",
                    "all_documents_uploaded": False,
                    "doc_retry_count": doc_retry_count,
                }

            response_msg = AIMessage(
                content=(
                    "I am a Home Loan Application assistant. I can only help you with home loan queries, "
                    "document uploads, and processing your loan application. Please continue home loan process.\n"
                    f"Retry {doc_retry_count}/{max_retry_count}. Attempts left: {attempts_left}."
                )
            )
            return {
                "messages": [response_msg],
                "paused_reason": "Waiting for relevant input during document collection.",
                "current_stage": "awaiting_documents",
                "all_documents_uploaded": False,
                "doc_retry_count": doc_retry_count,
            }

        response_msg = AIMessage(
            content="I am a Home Loan Application assistant. I can only help you with home loan queries, "
                    "document uploads, and processing your loan application. Please continue home loan process."
        )
        return {
            "messages": [response_msg],
            "paused_reason": None,
        }
    
    def homeloan_query(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 3: Home Loan Query Handler
        
        Answers general questions about home loans (rates, eligibility, process, etc.)
        using the LLM. Encourages user to start/continue their application afterward.
        
        """
        writer = get_stream_writer()
        user_query = self._resolve_user_query(state)
        if not user_query:
            return state

        writer({"type": "status", "node": "homeloan_query", "msg": "💬 Finding information about your query..."})
        
        system_prompt = """
        You are a helpful Home Loan Application assistant.
        The user is asking a general question about home loans (interest rates, eligibility, process, etc.).
        the interest rate we are considering for our process is 8.5% .
        Important information about our specific home loan process to use in your answers:
        - Required Documents: Aadhaar Card, PAN Card, and ITR (Income Tax Return).
        - Eligible Employment Status: Employed or Self-employed/Business (Unemployed applicants are currently not processed).
        - Next steps: After documents, we collect employment status, loan details (amount, down payment, tenure), and existing EMI information to calculate financial eligibility.
        
        Answer their question concisely and accurately based on our process if applicable. At the end of your answer, ask if they would like to 
        start or continue their home loan application by providing their details or documents. Answer shortly and precisely in about 3-4 sentences. Always encourage them to proceed with the application process after answering their query.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        llm = get_model(temperature=0.4)
        chain = prompt | llm
        
        response = chain.invoke({"query": user_query})
        
        writer({"type": "status", "node": "homeloan_query", "msg": "✅ Answer ready"})

        return {
            "messages": [AIMessage(content=response.content)],
            "paused_reason": "Answered home loan query. Waiting for user to proceed with application.",
        }
    
    def document_processing(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 4: Document Processing
        
        Args:
            state: Current application state
            
        Returns:
            Updated state after document processing
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "document_processing", "msg": "📄 Processing document..."})

        from app.backend.graph.nodes.document_processing import build_document_processing_subgraph
    
        doc_subgraph = build_document_processing_subgraph()
    
        subgraph_updates = doc_subgraph.invoke(state)

        processing_status = None
        if isinstance(subgraph_updates, dict):
            processing_status = subgraph_updates.get("document_processing_status")

        if processing_status == "unsupported":
            writer({
                "type": "warning",
                "node": "document_processing",
                "msg": "⚠️ Wrong document uploaded. We didn't process it. Please upload Aadhaar, PAN, or ITR JSON.",
            })

        if processing_status == "duplicate":
            writer({
                "type": "warning",
                "node": "document_processing",
                "msg": "⚠️ This document is already uploaded. Please upload the other document.",
            })

        if processing_status == "mismatch":
            writer({
                "type": "warning",
                "node": "document_processing",
                "msg": "⚠️ Document data mismatch detected. Wrong document may be uploaded. Re-upload correct file or start a new chat.",
            })

        bad_statuses = {"unsupported", "duplicate", "mismatch"}
        max_retry_count = 3
        doc_retry_count = int(state.get("doc_retry_count", 0) or 0)

        if processing_status in bad_statuses:
            doc_retry_count += 1
            if doc_retry_count >= max_retry_count:
                fail_msg = (
                    "❌ Unsuccessful process: maximum retry attempts reached.\n\n"
                    "Multiple invalid document attempts detected (wrong/re-uploaded/mismatch). "
                    "Please start a new application."
                )
                return {
                    "messages": [AIMessage(content=fail_msg)],
                    "paused_reason": "Maximum retries reached in document collection loop.",
                    "current_stage": "failed_max_retries",
                    "all_documents_uploaded": False,
                    "doc_retry_count": doc_retry_count,
                }
        else:
            doc_retry_count = 0
        
        _SUBGRAPH_KEYS = {
            "uploaded_documents", "personal_info", "financial_info",
            "employment_info", "current_processing_doc", "uploaded_docs",
            "extracted_doc_payload", "document_processing_status",
        }
        result = {
            k: subgraph_updates[k]
            for k in _SUBGRAPH_KEYS
            if k in subgraph_updates
        }
        result["current_stage"] = "state_evaluation"

        subgraph_msgs = subgraph_updates.get("messages", [])
        last_ai_text = None
        for m in reversed(subgraph_msgs):
            if not isinstance(m, HumanMessage):
                content = getattr(m, "content", None)
                if isinstance(content, str) and content.strip():
                    last_ai_text = content.strip()
                    break
        if last_ai_text:
            result["messages"] = [AIMessage(content=last_ai_text)]

        result["doc_retry_count"] = doc_retry_count

        writer({"type": "status", "node": "document_processing", "msg": "✅ Document processing complete"})

        return result
    
    def text_info_extractor(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 5: Text Information Extractor
        
        Extracts personal, financial, and employment information from user's
        text messages using structured LLM output.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with extracted information
        """
        writer = get_stream_writer()
        user_query = self._resolve_user_query(state)
        if not user_query:
            return state

        writer({"type": "status", "node": "text_info_extractor", "msg": "📝 Extracting information from your message..."})
        
        system_prompt = """
        You are an information extraction assistant for a Home Loan Application.
        Extract relevant personal, financial, and employment information from the user's message.
        Personal information includes the person's name (like "User One", "John", etc.), age, and email address if provided.
        Map them strictly to the given structured output format.
        If a piece of information is not present, omit it or leave it null.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        llm = get_structured_model()
        structured_llm = llm.with_structured_output(ExtractedInfo)
        
        chain = prompt | structured_llm
        result = chain.invoke({"query": user_query})
        
        personal_info = state.get("personal_info", {}) or {}
        financial_info = state.get("financial_info", {}) or {}
        employment_info = state.get("employment_info", {}) or {}

        def normalize_email(value: Any) -> Optional[str]:
            if not isinstance(value, str):
                return None
            email = value.strip().lower().rstrip(".,;:")
            if "@" not in email:
                return None
            return email
        
        if result.personal_info:
            extracted_personal = {k: v for k, v in result.personal_info.model_dump().items() if v is not None}

            normalized_email = normalize_email(extracted_personal.get("email"))
            if normalized_email:
                extracted_personal["email"] = normalized_email

            personal_info.update(extracted_personal)

        regex_email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", user_query)
        if regex_email_match:
            fallback_email = normalize_email(regex_email_match.group(0))
            if fallback_email:
                personal_info["email"] = fallback_email

        if result.financial_info:
            extracted_financial = {k: v for k, v in result.financial_info.model_dump().items() if v is not None}
            financial_info.update(extracted_financial)
        if result.employment_info:
            extracted_employment = {k: v for k, v in result.employment_info.model_dump().items() if v is not None}
            employment_info.update(extracted_employment)

        writer({"type": "status", "node": "text_info_extractor", "msg": "✅ Info captured"})

        extracted_items = []
        if result.personal_info and result.personal_info.name:
            extracted_items.append("name")
        if (result.personal_info and result.personal_info.email) or regex_email_match:
            extracted_items.append("email address")

        if extracted_items:
            msg = AIMessage(content=f"I have noted this information, including your {' and '.join(extracted_items)}.")
        else:
            msg = AIMessage(content="I have noted this information.")

        return {
            "personal_info": personal_info,
            "financial_info": financial_info,
            "employment_info": employment_info,
            "messages": [msg],
            "doc_retry_count": 0,
        }
    
    def state_evaluator(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 6: State Evaluator
        
        Evaluates if all mandatory documents are uploaded.
        Routes to interrupt_handler if docs missing, or employment status
        collection if all docs are present.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with evaluation results
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "state_evaluator", "msg": "📋 Checking document status..."})

        if str(state.get("current_stage") or "").startswith("failed"):
            return {
                "all_documents_uploaded": False,
                "current_stage": state.get("current_stage") or "failed_max_retries",
            }

        uploaded_docs = state.get("uploaded_documents", {})
        missing_docs = [
            doc for doc in self.mandatory_docs 
            if doc not in uploaded_docs
        ]
        
        if missing_docs:
            msg = (
                f" Document Status: {len(uploaded_docs)}/{len(self.mandatory_docs)} uploaded\n\n"
                f" We need the following documents to proceed:\n"
            )
            for doc in missing_docs:
                msg += f"  • {doc.upper()}\n"
            msg += f"\nPlease upload the required document(s) or provide any information to continue your application."
            
            writer({"type": "status", "node": "state_evaluator", "msg": "⏸ Waiting for documents"})

            return {
                "messages": [AIMessage(content=msg)],
                "paused_reason": f"Waiting for documents: {', '.join(missing_docs)}",
                "all_documents_uploaded": False,
                "current_stage": "awaiting_documents",
                "doc_retry_count": int(state.get("doc_retry_count", 0) or 0),
            }
        
        msg = (
            " All required documents uploaded successfully!\n\n"
            " Next step: Employment Status\n"
            "Please tell your employment status to continue:\n"
                "1) Employed\n"
                "2) Self-employed / Business\n"
                "3) Unemployed"
        )
        
        writer({"type": "status", "node": "state_evaluator", "msg": "✅ Documents complete"})

        return {
            "messages": [AIMessage(content=msg)],
            "intent": None,
            "paused_reason": None,
            "all_documents_uploaded": True,
            "employment_status_collected": False,
            "current_stage": "employment_status_collection",
            "doc_retry_count": 0,
        }

    def employment_status_collector(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 6.7: Employment Status Collector (interrupt + structured LLM)

        Collects employment status via interrupt, extracts canonical value with LLM,
        and gates the workflow:
        - unemployed -> fail and end workflow
        - employed/self-employed -> proceed to loan details
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "employment_status_collector", "msg": "🧾 Collecting employment status..."})

        if str(state.get("current_stage") or "").startswith("failed"):
            return {
                "employment_status_collected": False,
                "current_stage": state.get("current_stage") or "failed_max_retries",
            }

        employment_info = dict(state.get("employment_info", {}) or {})
        retry_count = int(state.get("employment_retry_count", 0) or 0)
        max_retry_count = 3

        status = self._normalize_employment_status(
            employment_info.get("employment_status") or employment_info.get("employment_type")
        )

        if not status:
            prompt_payload = {
                "type": "employment_status",
                "stage": "awaiting_employment_status",
                "message": (
                    "Please tell your employment status to continue:\n"
                    "1) Employed\n"
                    "2) Self-employed / Business\n"
                    "3) Unemployed"
                ),
                "options": [
                    "Employed",
                    "Self-employed/Business",
                    "Unemployed",
                ],
            }

            writer({"type": "status", "node": "employment_status_collector", "msg": "⏸ Waiting for employment status"})
            user_reply = interrupt(prompt_payload)

            query_text = ""
            if isinstance(user_reply, dict):
                query_text = str(user_reply.get("user_query") or user_reply.get("message") or "").strip()
            else:
                query_text = str(user_reply or "").strip()

            extracted_status = "unknown"
            if query_text:
                system_prompt = """
                You are an employment status extraction assistant for home loan processing.

                Classify the user's response into exactly one canonical value:
                - employed
                - self_employed
                - unemployed
                - unknown

                Notes:
                - 'self_employed' includes business owner, entrepreneur, freelancer, consultant, professional practice.
                - If unclear, return 'unknown'.
                """

                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("user", "{query}"),
                ])

                llm = get_structured_model()
                structured_llm = llm.with_structured_output(EmploymentStatusChoice)
                result = (prompt | structured_llm).invoke({"query": query_text})
                extracted_status = result.employment_status

            status = self._normalize_employment_status(extracted_status)

            if not status:
                retry_count += 1
                attempts_left = max_retry_count - retry_count

                if retry_count >= max_retry_count:
                    fail_msg = (
                        "❌ Unsuccessful process: maximum retry attempts reached.\n\n"
                        "We could not capture a valid employment status after multiple attempts. "
                        "Please start a new application."
                    )
                    writer({"type": "warning", "node": "employment_status_collector", "msg": "❌ Maximum retries reached"})
                    return {
                        "messages": [AIMessage(content=fail_msg)],
                        "paused_reason": "Maximum retries reached in employment status collection.",
                        "employment_info": employment_info,
                        "employment_status_collected": False,
                        "current_stage": "failed_max_retries",
                        "employment_retry_count": retry_count,
                    }

                retry_msg = (
                    "I couldn't identify your employment status from your last response.\n"
                    "Please reply with one of these options: Employed, Self-employed/Business, or Unemployed.\n"
                    f"Retry {retry_count}/{max_retry_count}. Attempts left: {attempts_left}."
                )
                return {
                    "messages": [AIMessage(content=retry_msg)],
                    "paused_reason": "Waiting for valid employment status input.",
                    "employment_info": employment_info,
                    "employment_status_collected": False,
                    "current_stage": "awaiting_employment_status",
                    "employment_retry_count": retry_count,
                }

        employment_info["employment_status"] = status

        if status == "self_employed":
            employment_info["employment_type"] = "Self-employed"
        elif status == "employed":
            employment_info["employment_type"] = "Salaried"

        if status == "unemployed":
            writer({"type": "warning", "node": "employment_status_collector", "msg": "❌ Unemployed applicants are not processed"})
            fail_msg = (
                "❌ We currently do not process home loan applications for unemployed applicants "
                "as per current bank rules.\n\n"
                "Please apply again once your employment status changes."
            )
            return {
                "messages": [AIMessage(content=fail_msg)],
                "paused_reason": "Application closed due to unemployed status.",
                "employment_info": employment_info,
                "employment_status_collected": False,
                "current_stage": "failed_unemployed",
                "employment_retry_count": 0,
            }

        status_label = "Self-employed/Business" if status == "self_employed" else "Employed"
        success_msg = (
            f"✅ Employment status recorded: {status_label}.\n\n"
            "📋 Loan details needed to proceed.\n"
            "Please share Home Loan Amount (e.g., 50 lakhs), Down Payment, and Tenure (years)."
        )

        writer({"type": "status", "node": "employment_status_collector", "msg": "✅ Employment status captured"})

        return {
            "messages": [AIMessage(content=success_msg)],
            "paused_reason": None,
            "employment_info": employment_info,
            "employment_status_collected": True,
            "current_stage": "loan_details_collection",
            "employment_retry_count": 0,
        }
    
    def interrupt_handler(self, state: ApplicationState) -> ApplicationState:
        """
        Node 6.5: Interrupt Handler
        
        Handles missing documents by using interrupt() to get user query.
        Saves the query to state and routes to intent_classifier.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with user query
        """
        uploaded_docs = state.get("uploaded_documents", {})
        missing_docs = [
            doc for doc in self.mandatory_docs 
            if doc not in uploaded_docs
        ]
        
        if missing_docs:
            prompt_msg = (
                f"⚠️ Missing documents: {', '.join(missing_docs)}\n\n"
                "Please provide the documents or any information to proceed:"
            )
        else:
            prompt_msg = "Please provide your query or information:"
        
        resumed_input = interrupt(prompt_msg)

        if isinstance(resumed_input, dict):
            if "uploaded_docs" in resumed_input or "user_query" in resumed_input:
                normalized_query = resumed_input.get("user_query")
                normalized_docs = resumed_input.get("uploaded_docs")
                query_text = str(normalized_query or "").strip()
                return {
                    "messages": [HumanMessage(content=query_text)] if query_text else [],
                    "user_query": query_text or None,
                    "uploaded_docs": normalized_docs if isinstance(normalized_docs, dict) else None,
                    "paused_reason": None,
                    "intent": None,
                }

            payload_type = str(resumed_input.get("type") or "").strip().lower()
            if payload_type == "file_upload" and isinstance(resumed_input.get("data"), dict):
                return {
                    "uploaded_docs": resumed_input.get("data"),
                    "user_query": None,
                    "paused_reason": None,
                    "intent": None,
                }

            if payload_type == "text":
                text = str(resumed_input.get("message") or "").strip()
                return {
                    "messages": [HumanMessage(content=text)] if text else [],
                    "user_query": text,
                    "uploaded_docs": None,
                    "paused_reason": None,
                    "intent": None,
                }

        user_query = str(resumed_input or "").strip()
        return {
            "messages": [HumanMessage(content=user_query)] if user_query else [],
            "user_query": user_query,
            "uploaded_docs": None,
            "paused_reason": None,
            "intent": None,
        }
    
    def loan_details_checker(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 7: Loan Details Checker (self-loop with interrupt)

        Collects/validates loan amount, down payment, and tenure.
        If details are missing, interrupts the graph to ask the user,
        parses the reply with a structured LLM, updates state, and
        marks completeness via all_loan_details_provided.
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "loan_details_checker", "msg": "💰 Checking loan details..."})

        financial_info = dict(state.get("financial_info", {}) or {})
        retry_count = int(state.get("retry_count", 0) or 0)
        max_retry_count = 3

        def missing_fields(info: Dict[str, Any]) -> list:
            missing = []
            if info.get("home_loan_amount", 0) <= 0:
                missing.append("Home Loan Amount")
            if info.get("down_payment") is None:
                missing.append("Down Payment")
            if info.get("tenure_years", 0) <= 0:
                missing.append("Loan Tenure")
            return missing

        missing = missing_fields(financial_info)

        if missing:
            prompt_msg = (
                "📋 Loan details needed to proceed. "
                "Please share Home Loan Amount (e.g., 50 lakhs), Down Payment, and Tenure (years)."
            )
            writer({"type": "status", "node": "loan_details_checker", "msg": "⏸ Waiting for loan details"})

            user_reply = interrupt(prompt_msg)

            query_text = ""
            if isinstance(user_reply, dict):
                query_text = str(
                    user_reply.get("user_query")
                    or user_reply.get("message")
                    or ""
                ).strip()
            else:
                query_text = str(user_reply or "").strip()

            extracted_any = False

            # Parse reply with structured LLM
            system_prompt = """
            You are a loan details extraction assistant.
            Extract the following loan parameters from the user's message:
            - home_loan_amount (numeric, in rupees)
            - down_payment (numeric, in rupees)
            - tenure_years (integer, in years)
            If a value is not mentioned, leave it null.
            """

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", "{query}"),
            ])

            if query_text:
                llm = get_structured_model()
                structured_llm = llm.with_structured_output(LoanDetails)
                result = (prompt | structured_llm).invoke({"query": query_text})

                if result.home_loan_amount and result.home_loan_amount > 0:
                    financial_info["home_loan_amount"] = result.home_loan_amount
                    extracted_any = True
                if result.down_payment is not None and result.down_payment >= 0:
                    financial_info["down_payment"] = result.down_payment
                    extracted_any = True
                if result.tenure_years and result.tenure_years > 0:
                    financial_info["tenure_years"] = result.tenure_years
                    extracted_any = True

            if not extracted_any:
                retry_count += 1
                attempts_left = max_retry_count - retry_count

                if retry_count >= max_retry_count:
                    fail_msg = (
                        "❌ Unsuccessful process: maximum retry attempts reached.\n\n"
                        "You provided irrelevant/invalid responses 3 times while collecting loan details. "
                        "Please start a new application."
                    )
                    writer({"type": "warning", "node": "loan_details_checker", "msg": "❌ Maximum retries reached"})
                    return {
                        "messages": [AIMessage(content=fail_msg)],
                        "paused_reason": "Maximum retries reached in loan details collection.",
                        "all_loan_details_provided": False,
                        "current_stage": "failed_max_retries",
                        "financial_info": financial_info,
                        "retry_count": retry_count,
                    }

                retry_msg = (
                    "I couldn't extract valid loan details from your last response.\n"
                    "Please provide at least one of these clearly: Home Loan Amount, Down Payment, Tenure (years).\n"
                    f"Retry {retry_count}/{max_retry_count}. Attempts left: {attempts_left}."
                )
                return {
                    "messages": [AIMessage(content=retry_msg)],
                    "paused_reason": "Waiting for valid loan details input.",
                    "all_loan_details_provided": False,
                    "current_stage": "awaiting_loan_details",
                    "financial_info": financial_info,
                    "retry_count": retry_count,
                }

        # Re-evaluate completeness
        missing = missing_fields(financial_info)
        complete = len(missing) == 0

        if not complete:
            writer({"type": "status", "node": "loan_details_checker", "msg": "⏳ Still missing loan details"})
            msg = (
                "I still need the following details:\n" + "\n".join(f"  • {m}" for m in missing)
            )
            return {
                "messages": [AIMessage(content=msg)],
                "paused_reason": f"Waiting for loan details: {', '.join(missing)}",
                "all_loan_details_provided": False,
                "current_stage": "awaiting_loan_details",
                "financial_info": financial_info,
                "retry_count": retry_count,
            }

        success_msg = (
            " Loan Details Collected Successfully!\n\n"
            f"  • Home Loan Amount: ₹{financial_info['home_loan_amount']:,.2f}\n"
            f"  • Down Payment: ₹{financial_info['down_payment']:,.2f}\n"
            f"  • Loan Tenure: {financial_info['tenure_years']} years\n\n"
            "Proceeding to existing EMI check...\n" 
            "Do you have any existing EMIs? Please select Yes or No."
        )

        writer({"type": "status", "node": "loan_details_checker", "msg": "✅ Loan details captured"})

        return {
            "messages": [AIMessage(content=success_msg)],
            "paused_reason": None,
            "all_loan_details_provided": True,
            "current_stage": "existing_emi_collection",
            "financial_info": financial_info,
            "retry_count": 0,
        }

    def existing_emi_collector(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 7.5: Existing EMI Choice Collector (interrupt-driven)

        Flow:
        1. Ask whether user has any existing EMIs (Yes/No).
        2. If No -> store 0 existing EMI and move to financial risk.
        3. If Yes -> route to existing loan details collector node.
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "existing_emi_collector", "msg": "🏦 Checking if you have existing EMIs..."})

        if str(state.get("current_stage") or "").startswith("failed"):
            return {
                "existing_emi_collected": False,
                "current_stage": state.get("current_stage") or "failed_max_retries",
            }

        financial_info = dict(state.get("financial_info", {}) or {})
        retry_count = int(state.get("existing_emi_retry_count", 0) or 0)
        max_retry_count = 3

        def _extract_text(payload: Any) -> str:
            if isinstance(payload, dict):
                return str(payload.get("user_query") or payload.get("message") or "").strip()
            return str(payload or "").strip()

        def _as_positive_float(value: Any) -> Optional[float]:
            try:
                number = float(value)
                return number if number > 0 else None
            except (TypeError, ValueError):
                return None

        def _as_positive_int(value: Any) -> Optional[int]:
            try:
                number = int(value)
                return number if number > 0 else None
            except (TypeError, ValueError):
                return None

        has_existing_emi = financial_info.get("has_existing_emi")
        if not isinstance(has_existing_emi, bool):
            prompt_payload = {
                "type": "existing_emi_choice",
                "stage": "awaiting_existing_emi_choice",
                "message": "Do you have any existing EMIs? Please select Yes or No.",
                "options": ["Yes", "No"],
            }

            writer({"type": "status", "node": "existing_emi_collector", "msg": "⏸ Waiting for existing EMI choice"})
            user_reply = interrupt(prompt_payload)
            query_text = _extract_text(user_reply)

            choice = "unknown"
            if query_text:
                system_prompt = """
                You are an intent extractor for loan applications.
                Classify user response into exactly one value:
                - yes
                - no
                - unknown

                Rules:
                - Positive confirmation (yes, haan, sure, I have EMI) => yes
                - Negative confirmation (no, none, don't have) => no
                - Anything ambiguous => unknown
                """

                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("user", "{query}"),
                ])

                llm = get_structured_model()
                structured_llm = llm.with_structured_output(ExistingEmiChoice)
                result = (prompt | structured_llm).invoke({"query": query_text})
                choice = result.has_existing_emi

            if choice == "unknown":
                retry_count += 1
                attempts_left = max_retry_count - retry_count

                if retry_count >= max_retry_count:
                    fail_msg = (
                        "❌ Unsuccessful process: maximum retry attempts reached.\n\n"
                        "We could not capture whether you have existing EMIs. "
                        "Please start a new application."
                    )
                    writer({"type": "warning", "node": "existing_emi_collector", "msg": "❌ Maximum retries reached"})
                    return {
                        "messages": [AIMessage(content=fail_msg)],
                        "paused_reason": "Maximum retries reached while asking existing EMI choice.",
                        "financial_info": financial_info,
                        "existing_emi_collected": False,
                        "current_stage": "failed_max_retries",
                        "existing_emi_retry_count": retry_count,
                    }

                retry_msg = (
                    "I couldn't identify your response.\n"
                    "Please reply only with Yes or No for existing EMIs.\n"
                    f"Retry {retry_count}/{max_retry_count}. Attempts left: {attempts_left}."
                )
                return {
                    "messages": [AIMessage(content=retry_msg)],
                    "paused_reason": "Waiting for valid existing EMI Yes/No response.",
                    "financial_info": financial_info,
                    "existing_emi_collected": False,
                    "current_stage": "awaiting_existing_emi_choice",
                    "existing_emi_retry_count": retry_count,
                }

            has_existing_emi = choice == "yes"
            financial_info["has_existing_emi"] = has_existing_emi

        if not has_existing_emi:
            financial_info["total_existing_emis"] = 0.0
            financial_info.pop("existing_emi_loan_amount", None)
            financial_info.pop("existing_emi_tenure_months", None)
            financial_info.pop("existing_emi_time_period_months", None)

            msg = (
                "✅ Noted. You do not have any existing EMIs.\n\n"
                "Proceeding to EMI calculations..."
            )
            writer({"type": "status", "node": "existing_emi_collector", "msg": "✅ No existing EMI declared"})
            return {
                "messages": [AIMessage(content=msg)],
                "paused_reason": None,
                "financial_info": financial_info,
                "existing_emi_collected": True,
                "existing_loan_details_collected": False,
                "existing_loan_details_retry_count": 0,
                "current_stage": "emi_calculation",
                "existing_emi_retry_count": 0,
            }

        msg = (
            "✅ Noted. You have existing EMI obligations.\n\n"
            "Please share your existing EMI loan details:\n"
            "1) Monthly EMI amount\n"
            "2) Existing loan amount\n"
            "3) Remaining tenure (months or years)"
        )

        writer({"type": "status", "node": "existing_emi_collector", "msg": "✅ Existing EMI declared"})

        return {
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "financial_info": financial_info,
            "existing_emi_collected": True,
            "existing_loan_details_collected": False,
            "existing_loan_details_retry_count": 0,
            "current_stage": "existing_emi_collection",
            "existing_emi_retry_count": 0,
        }

    def existing_loan_details_collector(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 7.6: Existing Loan Details Collector (interrupt-driven)

        Collects details for existing EMI obligations:
        - Monthly EMI
        - Existing loan amount
        - Remaining tenure
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "existing_loan_details_collector", "msg": "📋 Collecting existing loan details..."})

        if str(state.get("current_stage") or "").startswith("failed"):
            return {
                "existing_loan_details_collected": False,
                "current_stage": state.get("current_stage") or "failed_max_retries",
            }

        financial_info = dict(state.get("financial_info", {}) or {})
        retry_count = int(state.get("existing_loan_details_retry_count", 0) or 0)
        max_retry_count = 3

        def _extract_text(payload: Any) -> str:
            if isinstance(payload, dict):
                return str(payload.get("user_query") or payload.get("message") or "").strip()
            return str(payload or "").strip()

        def _as_positive_float(value: Any) -> Optional[float]:
            try:
                number = float(value)
                return number if number > 0 else None
            except (TypeError, ValueError):
                return None

        def _as_positive_int(value: Any) -> Optional[int]:
            try:
                number = int(value)
                return number if number > 0 else None
            except (TypeError, ValueError):
                return None

        def _resolve_tenure_months(info: Dict[str, Any]) -> Optional[int]:
            tenure = _as_positive_int(info.get("existing_emi_tenure_months"))
            if tenure is None:
                tenure = _as_positive_int(info.get("existing_emi_time_period_months"))
            return tenure

        def _missing_fields(info: Dict[str, Any]) -> list:
            missing = []
            if _as_positive_float(info.get("total_existing_emis")) is None:
                missing.append("Monthly EMI amount")
            if _as_positive_float(info.get("existing_emi_loan_amount")) is None:
                missing.append("Existing loan amount")
            if _resolve_tenure_months(info) is None:
                missing.append("Remaining tenure (months or years)")
            return missing

        missing = _missing_fields(financial_info)

        if missing:
            prompt_payload = {
                "type": "existing_emi_details",
                "stage": "awaiting_existing_emi_details",
                "message": (
                    "Please share your existing EMI loan details:\n"
                    "1) Monthly EMI amount\n"
                    "2) Existing loan amount\n"
                    "3) Remaining tenure (months or years)"
                ),
            }

            writer({"type": "status", "node": "existing_loan_details_collector", "msg": "⏸ Waiting for existing loan details"})
            user_reply = interrupt(prompt_payload)
            query_text = _extract_text(user_reply)

            extracted_any = False

            if query_text:
                system_prompt = """
                You are an information extraction assistant for home loan processing.
                Extract from user response:
                - monthly_emi (monthly existing EMI in rupees)
                - loan_amount (existing loan amount in rupees)
                - tenure_months (remaining tenure in months)

                Rules:
                - If user provides tenure in years, convert it to months.
                - Return null for missing values.
                """

                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("user", "{query}"),
                ])

                llm = get_structured_model()
                structured_llm = llm.with_structured_output(ExistingEmiDetails)
                result = (prompt | structured_llm).invoke({"query": query_text})

                extracted_monthly_emi = _as_positive_float(result.monthly_emi)
                extracted_loan_amount = _as_positive_float(result.loan_amount)
                extracted_tenure_months = _as_positive_int(result.tenure_months)

                if extracted_monthly_emi is not None:
                    financial_info["total_existing_emis"] = extracted_monthly_emi
                    extracted_any = True
                if extracted_loan_amount is not None:
                    financial_info["existing_emi_loan_amount"] = extracted_loan_amount
                    extracted_any = True
                if extracted_tenure_months is not None:
                    financial_info["existing_emi_tenure_months"] = extracted_tenure_months
                    financial_info["existing_emi_time_period_months"] = extracted_tenure_months
                    extracted_any = True

            if not extracted_any:
                retry_count += 1
                attempts_left = max_retry_count - retry_count

                if retry_count >= max_retry_count:
                    fail_msg = (
                        "❌ Unsuccessful process: maximum retry attempts reached.\n\n"
                        "We could not capture complete existing loan details. "
                        "Please start a new application."
                    )
                    writer({"type": "warning", "node": "existing_loan_details_collector", "msg": "❌ Maximum retries reached"})
                    return {
                        "messages": [AIMessage(content=fail_msg)],
                        "paused_reason": "Maximum retries reached while collecting existing loan details.",
                        "financial_info": financial_info,
                        "existing_loan_details_collected": False,
                        "current_stage": "failed_max_retries",
                        "existing_loan_details_retry_count": retry_count,
                    }

                retry_msg = (
                    "I couldn't extract valid existing loan details from your last response.\n"
                    "Please provide at least one of these clearly: monthly EMI amount, existing loan amount, or remaining tenure.\n"
                    f"Retry {retry_count}/{max_retry_count}. Attempts left: {attempts_left}."
                )
                return {
                    "messages": [AIMessage(content=retry_msg)],
                    "paused_reason": "Waiting for valid existing loan details input.",
                    "financial_info": financial_info,
                    "existing_loan_details_collected": False,
                    "current_stage": "awaiting_existing_emi_details",
                    "existing_loan_details_retry_count": retry_count,
                }

            missing = _missing_fields(financial_info)
            if missing:
                writer({"type": "status", "node": "existing_loan_details_collector", "msg": "⏳ Existing loan details incomplete"})
                missing_msg = (
                    "I still need the following existing loan details:\n"
                    + "\n".join(f"  • {field}" for field in missing)
                )
                return {
                    "messages": [AIMessage(content=missing_msg)],
                    "paused_reason": f"Waiting for existing loan details: {', '.join(missing)}",
                    "financial_info": financial_info,
                    "existing_loan_details_collected": False,
                    "current_stage": "awaiting_existing_emi_details",
                    "existing_loan_details_retry_count": retry_count,
                }

        monthly_emi = _as_positive_float(financial_info.get("total_existing_emis")) or 0.0
        existing_loan_amount = _as_positive_float(financial_info.get("existing_emi_loan_amount")) or 0.0
        tenure_months = _resolve_tenure_months(financial_info) or 0

        msg = (
            "✅ Existing loan details captured successfully!\n\n"
            f"  • Monthly Existing EMI: ₹{monthly_emi:,.2f}\n"
            f"  • Existing Loan Amount: ₹{existing_loan_amount:,.2f}\n"
            f"  • Remaining Tenure: {tenure_months} months\n\n"
            "Proceeding to EMI calculation..."
        )

        writer({"type": "status", "node": "existing_loan_details_collector", "msg": "✅ Existing loan details captured"})

        return {
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "financial_info": financial_info,
            "existing_emi_collected": True,
            "existing_loan_details_collected": True,
            "current_stage": "emi_calculation",
            "existing_loan_details_retry_count": 0,
        }
    
    def financial_risk_checker(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 8: Financial Risk Checker
        
        Performs financial risk assessment by calculating:
        - LTV (Loan to Value ratio)
        - FOIR (Fixed Obligation to Income Ratio)
        - CIBIL score check
    
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "financial_risk_checker", "msg": "📊 Calculating financial metrics..."})

        financial_info = state.get("financial_info", {})

        def as_float(value: Any, default: float) -> float:
            if value is None:
                return default
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        
        amount = as_float(financial_info.get("home_loan_amount"), 0.0)
        down_payment = as_float(financial_info.get("down_payment"), 0.0)
        income = as_float(financial_info.get("net_monthly_income"), 1.0)
        emis = as_float(financial_info.get("total_existing_emis"), 0.0)
        
        # Include the new EMI calculated in the previous step
        emi_details = state.get("emi_details", {})
        new_loan_emi = as_float(emi_details.get("monthly_emi"), 0.0)
        total_monthly_obligations = emis + new_loan_emi

        if income <= 0:
            income = 1.0
       
        personal_info = state.get("personal_info", {})
        cibil = personal_info.get("credit_score")
        if not cibil:
            cibil = random.randint(650, 850)
            personal_info["credit_score"] = cibil
            
        # Calculate property value and ratios
        property_value = amount + down_payment
        if property_value <= 0:
            property_value = 1.0
            
        ltv = (amount / property_value) * 100
        foir = (total_monthly_obligations / income) * 100
        
        # Build assessment message
        msg = f"--- Financial Risk Assessment ---\n"
        msg += f"LTV: {ltv:.2f}% (Threshold: {self.ltv_threshold}%)\n"
        msg += f"FOIR: {foir:.2f}% (Threshold: {self.foir_threshold}%)\n"
        msg += f"CIBIL Score: {cibil} (Minimum: {self.min_cibil})\n\n"
        
        
        # Store financial metrics for saving and future reference
        financial_metrics = {
            "ltv_ratio": round(ltv, 2),
            "foir_ratio": round(foir, 2),
            "cibil_score": cibil,
            "property_value": property_value,
            "ltv_threshold": self.ltv_threshold,
            "foir_threshold": self.foir_threshold,
            "cibil_threshold": self.min_cibil
        }
        
        writer({"type": "status", "node": "financial_risk_checker", "msg": "✅ Financial assessment complete"})

        return {
            "personal_info": personal_info,
            "financial_metrics": financial_metrics,
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "current_stage": "saving_data",
        }
    

    
    def emi_calculator(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 8.5: EMI Calculator
        
        Calculates EMI and detailed loan repayment breakdown:
        - Monthly EMI
        - Total interest payable
        - Total amount payable
        - Monthly principal & interest split (first month)
        - Year-wise amortization summary
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "emi_calculator", "msg": "🧮 Calculating EMI and amortization schedule..."})

        financial_info = state.get("financial_info", {})
        
        principal = financial_info.get("home_loan_amount", 0)
        tenure_years = financial_info.get("tenure_years", 1)
        annual_rate = self.interest_rate
        
        monthly_rate = annual_rate / (12 * 100)
        n_months = tenure_years * 12
        
        # EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        if monthly_rate > 0 and n_months > 0:
            emi = principal * monthly_rate * ((1 + monthly_rate) ** n_months) / (((1 + monthly_rate) ** n_months) - 1)
        else:
            emi = principal / max(n_months, 1)
        
        total_payable = emi * n_months
        total_interest = total_payable - principal
        
        # First month breakdown
        first_month_interest = principal * monthly_rate
        first_month_principal = emi - first_month_interest
        
        # Year-wise amortization summary
        yearly_summary = []
        balance = principal
        for year in range(1, tenure_years + 1):
            year_interest = 0
            year_principal = 0
            for _ in range(12):
                if balance <= 0:
                    break
                month_interest = balance * monthly_rate
                month_principal = min(emi - month_interest, balance)
                year_interest += month_interest
                year_principal += month_principal
                balance -= month_principal
            yearly_summary.append({
                "year": year,
                "principal_paid": round(year_principal, 2),
                "interest_paid": round(year_interest, 2),
                "closing_balance": round(max(balance, 0), 2)
            })
        
        emi_details = {
            "loan_amount": principal,
            "annual_interest_rate": annual_rate,
            "tenure_years": tenure_years,
            "tenure_months": n_months,
            "monthly_emi": round(emi, 2),
            "total_interest_payable": round(total_interest, 2),
            "total_amount_payable": round(total_payable, 2),
            "first_month_interest": round(first_month_interest, 2),
            "first_month_principal": round(first_month_principal, 2),
            "yearly_amortization": yearly_summary
        }
        
        # Build display message
        msg = "\n📊 --- EMI & Loan Repayment Summary ---\n\n"
        msg += f"  Loan Amount        : ₹{principal:,.2f}\n"
        msg += f"  Interest Rate      : {annual_rate}% per annum\n"
        msg += f"  Tenure             : {tenure_years} years ({n_months} months)\n\n"
        msg += f"  💰 Monthly EMI      : ₹{emi:,.2f}\n"
        msg += f"  📈 Total Interest   : ₹{total_interest:,.2f}\n"
        msg += f"  📦 Total Payable    : ₹{total_payable:,.2f}\n\n"
        msg += f"  --- First Month Breakdown ---\n"
        msg += f"  Principal Component : ₹{first_month_principal:,.2f}\n"
        msg += f"  Interest Component  : ₹{first_month_interest:,.2f}\n\n"
        
        # Show first 3 and last year of amortization
        msg += "  --- Year-wise Amortization ---\n"
        show_years = yearly_summary[:3]
        if tenure_years > 4:
            show_years.append(None)  # placeholder for "..."
            show_years.append(yearly_summary[-1])
        elif tenure_years == 4:
            show_years.append(yearly_summary[-1])
        
        for entry in show_years:
            if entry is None:
                msg += "  ...\n"
            else:
                msg += (f"  Year {entry['year']:>2}: "
                        f"Principal ₹{entry['principal_paid']:>12,.2f} | "
                        f"Interest ₹{entry['interest_paid']:>12,.2f} | "
                        f"Balance ₹{entry['closing_balance']:>14,.2f}\n")
        
        msg += "\nProceeding to financial risk check..."
        
        writer({"type": "status", "node": "emi_calculator", "msg": "✅ EMI calculation complete"})

        return {
            "emi_details": emi_details,
            "messages": [AIMessage(content=msg)],
            "current_stage": "financial_risk_check",
        }

    def save_application_json(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 9A: Save Application Data as JSON
        
        Saves application data to JSON file in saved_docs directory.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with JSON save status
        """

        writer = get_stream_writer()
        writer({"type": "status", "node": "save_application_json", "msg": "💾 Saving application data to JSON..."})
        
        import json
        import os
        from datetime import datetime
        
        user_id = state.get("user_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        application_data = {
            "user_id": user_id,
            "timestamp": timestamp,
            "personal_info": state.get("personal_info", {}),
            "financial_info": state.get("financial_info", {}),
            "employment_info": state.get("employment_info", {}),
            "uploaded_documents": {
                doc_type: {
                    "uploaded": doc_info.get("uploaded"),
                    "verified": doc_info.get("verified"),
                    "data": doc_info.get("data")
                }
                for doc_type, doc_info in state.get("uploaded_documents", {}).items()
            },
            "financial_metrics": state.get("financial_metrics", {}),
            "emi_details": state.get("emi_details", {}),
            "all_documents_uploaded": state.get("all_documents_uploaded", False)
        }
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        saved_docs_dir = os.path.join(project_root, "saved_docs")
        os.makedirs(saved_docs_dir, exist_ok=True)
        
        filename = f"application_{user_id}_{timestamp}.json"
        filepath = os.path.join(saved_docs_dir, filename)
        
        try:
            with open(filepath, "w") as f:
                json.dump(application_data, f, indent=2)
            
            msg = f"✅ JSON: Saved to {filename}"
            json_saved = True
        except Exception as e:
            msg = f"❌ JSON: Error - {str(e)}"
            json_saved = False
        
        writer({"type": "status", "node": "save_application_json", "msg": msg})

        return {
            "messages": [AIMessage(content=msg)],
            "application_saved": json_saved,
        }
    
    def save_application_db(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 9B: Save Application Data to PostgreSQL
        
        Saves application data to PostgreSQL database.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with database save status
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "save_application_db", "msg": "🗄️ Saving application data to database..."})

        from datetime import datetime
        import psycopg2
        import json
        from psycopg2.extras import Json
        from app.static.config import DATABASE_URL
        
        user_id = state.get("user_id", "unknown")
        
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode="require")
            cursor = conn.cursor()
            
            create_table_query = """
            CREATE TABLE IF NOT EXISTS loan_applications (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                personal_info JSONB,
                financial_info JSONB,
                employment_info JSONB,
                uploaded_documents JSONB,
                financial_metrics JSONB,
                emi_details JSONB,
                all_documents_uploaded BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_query)
            
            uploaded_documents = {
                doc_type: {
                    "uploaded": doc_info.get("uploaded"),
                    "verified": doc_info.get("verified"),
                    "data": doc_info.get("data")
                }
                for doc_type, doc_info in state.get("uploaded_documents", {}).items()
            }
            
            insert_query = """
            INSERT INTO loan_applications (
                user_id, personal_info, financial_info, 
                employment_info, uploaded_documents, financial_metrics,
                emi_details, all_documents_uploaded
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            
            cursor.execute(insert_query, (
                user_id,
                Json(state.get("personal_info", {})),
                Json(state.get("financial_info", {})),
                Json(state.get("employment_info", {})),
                Json(uploaded_documents),
                Json(state.get("financial_metrics", {})),
                Json(state.get("emi_details", {})),
                state.get("all_documents_uploaded", False)
            ))
            
            app_id = cursor.fetchone()[0]
            conn.commit()
            
            msg = f"✅ Database: Saved with ID {app_id}"
            db_saved = True
            
        except psycopg2.OperationalError as e:
            msg = f"⚠️ Database: Connection failed - {str(e)}"
            db_saved = False
        except Exception as e:
            msg = f"❌ Database: Error - {str(e)}"
            db_saved = False
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
        
        saved = state.get("application_saved", False) or db_saved

        writer({"type": "status", "node": "save_application_db", "msg": msg})

        return {
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "current_stage": "email_notification",
            "application_saved": saved,
        }

    def email_notification(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 10: Email Notification
        
        Sends a professional application summary email to the applicant.
        Uses the email service layer for sending emails.
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "email_notification", "msg": "📧 Preparing email notification..."})

        from app.backend.services.email_services import send_application_summary_email
        
        # Extract state data
        personal_info = state.get("personal_info", {})
        financial_info = state.get("financial_info", {})
        employment_info = state.get("employment_info", {})
        financial_metrics = state.get("financial_metrics", {})
        emi_details = state.get("emi_details", {})
        user_id = state.get("user_id", "unknown")
        
        recipient_email = personal_info.get("email")
        applicant_name = personal_info.get("name", "Applicant")
        
        # Validate recipient email
        if not recipient_email:
            return {
                "messages": [AIMessage(content="⚠️ Email: No email address found in application. Notification skipped.")],
                "email_sent": False,
                "current_stage": "completed"
            }
        
        # Call email service
        writer({"type": "status", "node": "email_notification", "msg": "📬 Queueing email in background..."})

        def send_async_email() -> None:
            try:
                msg, email_sent = send_application_summary_email(
                    recipient_email=recipient_email,
                    applicant_name=applicant_name,
                    user_id=user_id,
                    personal_info=personal_info,
                    financial_info=financial_info,
                    financial_metrics=financial_metrics,
                    emi_details=emi_details
                )
                logger.info("[user_id=%s] async email result: %s | sent=%s", user_id, msg, email_sent)
            except Exception as exc:
                logger.exception("[user_id=%s] async email failed: %s", user_id, exc)

        threading.Thread(target=send_async_email, daemon=True).start()

        msg = f"📨 Email: Summary queued for {recipient_email}. You will receive it shortly."
        writer({"type": "status", "node": "email_notification", "msg": msg})

        return {
            "messages": [AIMessage(content=msg)],
            "email_sent": True,
            "current_stage": "completed",
        }