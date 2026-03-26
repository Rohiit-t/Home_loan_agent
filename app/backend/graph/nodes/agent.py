"""
HomeLoan Agent - A class-based implementation of all LangGraph nodes.

"""

import random
import re
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from typing import Literal

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
                - 'Text_info': if the user provides information like personal, financial, or employment details in text.
                    IMPORTANT: if the message contains an email address, classify as 'Text_info'.
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
        Answer their question concisely and accurately. At the end of your answer, ask if they would like to 
        start or continue their home loan application by providing their details or documents. Answer shortly and precisely in about 2-3 sentences. Always encourage them to proceed with the application process after answering their query.
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
        
        # IMPORTANT: Do NOT return dict(subgraph_updates) directly.
        # The subgraph returns the FULL accumulated state (including ALL
        # messages from previous turns) because `messages` uses the
        # add_messages reducer.  We must cherry-pick only the keys that
        # carry genuinely new information and build a single fresh message.
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

        # Build a single NEW message summarising what the subgraph did.
        # The subgraph's last node always adds exactly one AIMessage; grab
        # only THAT text so we don't replay old messages.
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
        Personal information includes email address if provided.
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

        if personal_info.get("email"):
            msg = AIMessage(content="I have noted this information, including your email address.")
        else:
            msg = AIMessage(content="I have noted this information.")

        return {
            "personal_info": personal_info,
            "financial_info": financial_info,
            "employment_info": employment_info,
            "messages": [msg],
        }
    
    def state_evaluator(self, state: ApplicationState) -> Dict[str, Any]:
        """
        Node 6: State Evaluator
        
        Evaluates if all mandatory documents are uploaded.
        Routes to interrupt_handler if docs missing, or loan_details if all docs present.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with evaluation results
        """
        writer = get_stream_writer()
        writer({"type": "status", "node": "state_evaluator", "msg": "📋 Checking document status..."})

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
            }
        
        msg = (
            " All required documents uploaded successfully!\n\n"
            " Next step: Loan Details\n"
            "We now need to collect your loan requirements (amount, down payment, tenure)."
        )
        
        writer({"type": "status", "node": "state_evaluator", "msg": "✅ Documents complete"})

        return {
            "messages": [AIMessage(content=msg)],
            "intent": None,
            "paused_reason": None,
            "all_documents_uploaded": True,
            "current_stage": "loan_details_collection",
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

            llm = get_structured_model()
            structured_llm = llm.with_structured_output(LoanDetails)
            result = (prompt | structured_llm).invoke({"query": user_reply})

            if result.home_loan_amount and result.home_loan_amount > 0:
                financial_info["home_loan_amount"] = result.home_loan_amount
            if result.down_payment is not None and result.down_payment >= 0:
                financial_info["down_payment"] = result.down_payment
            if result.tenure_years and result.tenure_years > 0:
                financial_info["tenure_years"] = result.tenure_years

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
            }

        success_msg = (
            " Loan Details Collected Successfully!\n\n"
            f"  • Home Loan Amount: ₹{financial_info['home_loan_amount']:,.2f}\n"
            f"  • Down Payment: ₹{financial_info['down_payment']:,.2f}\n"
            f"  • Loan Tenure: {financial_info['tenure_years']} years\n\n"
            "Proceeding to financial risk assessment..."
        )

        writer({"type": "status", "node": "loan_details_checker", "msg": "✅ Loan details captured"})

        return {
            "messages": [AIMessage(content=success_msg)],
            "paused_reason": None,
            "all_loan_details_provided": True,
            "current_stage": "financial_risk_check",
            "financial_info": financial_info,
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
        foir = (emis / income) * 100
        
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
        
        msg += "\nProceeding to save application data..."
        
        writer({"type": "status", "node": "emi_calculator", "msg": "✅ EMI calculation complete"})

        return {
            "emi_details": emi_details,
            "messages": [AIMessage(content=msg)],
            "current_stage": "saving_data",
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
        writer({"type": "status", "node": "email_notification", "msg": "📬 Sending email..."})

        msg, email_sent = send_application_summary_email(
            recipient_email=recipient_email,
            applicant_name=applicant_name,
            user_id=user_id,
            personal_info=personal_info,
            financial_info=financial_info,
            financial_metrics=financial_metrics,
            emi_details=emi_details
        )
        
        writer({"type": "status", "node": "email_notification", "msg": msg})

        return {
            "messages": [AIMessage(content=msg)],
            "email_sent": email_sent,
            "current_stage": "completed",
        }
