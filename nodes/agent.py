"""
HomeLoan Agent - A class-based implementation of all LangGraph nodes.
This follows LangGraph industry standards by encapsulating all node logic
within a single agent class for better organization and maintainability.
"""

import random
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from typing import Literal

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from state import ApplicationState
from util.model import get_structured_model, get_model
from config import MANDATORY_DOCS, LTV_THRESHOLD, FOIR_THRESHOLD, MIN_CIBIL

class IntentClassification(BaseModel):
    """Schema for intent classification output."""
    intent: Literal["Document_upload", "Text_info", "Irrelevant", "Homeloan_query"] = Field(
        description="The assigned intent of the user's message."
    )


class ExtractedInfo(BaseModel):
    """Schema for extracting user information from text."""
    personal_info: Optional[dict] = Field(
        description="Dictionary containing keys like 'name', 'age', 'phone', 'email' if found."
    )
    financial_info: Optional[dict] = Field(
        description="Dictionary containing 'net_monthly_income', 'total_existing_emis' if found."
    )
    employment_info: Optional[dict] = Field(
        description="Dictionary containing 'employer_name', 'employment_type' if found."
    )


class LoanDetails(BaseModel):
    """Schema for loan details extraction."""
    home_loan_amount: Optional[float] = Field(
        description="The desired home loan amount."
    )
    down_payment: Optional[float] = Field(
        description="The planned down payment amount."
    )
    tenure_years: Optional[int] = Field(
        description="The loan tenure in years."
    )


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
    
    
    def intent_classifier(self, state: ApplicationState) -> ApplicationState:
        """
        Node 1: Intent Classifier
        
        Classifies user intent into one of four categories:
        - Document_upload: User mentions document upload
        - Text_info: User provides textual information
        - Homeloan_query: User asks questions about home loans
        - Irrelevant: User query is off-topic
        
    
        """
        messages = state.get("messages", [])
        if not messages:
            return state
        
        user_query = messages[-1].content
        
        if state.get("intent"):
            return state
        
        system_prompt = """
        You are a strict intent classifier for a Home Loan Application.

        Your task:
        Given the user's message, classify it into exactly one of the following categories:
        - 'Document_upload': if the user mentions uploading a document like PAN, Aadhaar, Salary slip, etc.
        - 'Text_info': if the user provides information like personal, financial, or employment details in text.
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
        
        return {"intent": result.intent}
    
    def irrelevant_handler(self, state: ApplicationState) -> ApplicationState:
        """
        Node 2: Irrelevant Query Handler
        
        Handles queries that are not related to home loan application.
        Provides a polite response to guide user back on topic.

        """
        response_msg = AIMessage(
            content="I am a Home Loan Application assistant. I can only help you with home loan queries, "
                    "document uploads, and processing your loan application. Please ask something related to home loans."
        )
        
        return {
            "messages": [response_msg],
            "paused_reason": "Irrelevant query. Waiting for valid input."
        }
    
    def homeloan_query(self, state: ApplicationState) -> ApplicationState:
        """
        Node 3: Home Loan Query Handler
        
        Answers general questions about home loans (rates, eligibility, process, etc.)
        using the LLM. Encourages user to start/continue their application afterward.
        
        """
        messages = state.get("messages", [])
        if not messages:
            return state
            
        user_query = messages[-1].content
        
        system_prompt = """
        You are a helpful Home Loan Application assistant.
        The user is asking a general question about home loans (interest rates, eligibility, process, etc.).
        Answer their question concisely and accurately. At the end of your answer, ask if they would like to 
        start or continue their home loan application by providing their details or documents.
        """
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{query}")
        ])
        
        llm = get_model(temperature=0.4)
        chain = prompt | llm
        
        response = chain.invoke({"query": user_query})
        
        return {
            "messages": [AIMessage(content=response.content)],
            "paused_reason": "Answered home loan query. Waiting for user to proceed with application."
        }
    
    def document_processing(self, state: ApplicationState) -> ApplicationState:
        """
        Node 4: Document Processing
        
        Args:
            state: Current application state
            
        Returns:
            Updated state after document processing
        """
        from nodes.document_processing import build_document_processing_subgraph
    
        doc_subgraph = build_document_processing_subgraph()
    
        subgraph_updates = doc_subgraph.invoke(state)
        
        result = dict(subgraph_updates)
        result["current_stage"] = "state_evaluation"
   
        return result
    
    def text_info_extractor(self, state: ApplicationState) -> ApplicationState:
        """
        Node 5: Text Information Extractor
        
        Extracts personal, financial, and employment information from user's
        text messages using structured LLM output.
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with extracted information
        """
        messages = state.get("messages", [])
        if not messages:
            return state
            
        user_query = messages[-1].content
        
        system_prompt = """
        You are an information extraction assistant for a Home Loan Application.
        Extract relevant personal, financial, and employment information from the user's message.
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
        
        if result.personal_info:
            personal_info.update(result.personal_info)
        if result.financial_info:
            financial_info.update(result.financial_info)
        if result.employment_info:
            employment_info.update(result.employment_info)
            
        msg = AIMessage(content="I have noted this information.")
            
        return {
            "personal_info": personal_info,
            "financial_info": financial_info,
            "employment_info": employment_info,
            "messages": [msg]
        }
    
    def state_evaluator(self, state: ApplicationState) -> ApplicationState:
        """
        Node 6: State Evaluator
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with evaluation results
        """
        uploaded_docs = state.get("uploaded_documents", {})
        missing_docs = [
            doc for doc in self.mandatory_docs 
            if doc not in uploaded_docs or not uploaded_docs[doc].get("verified")
        ]
        
        # Check for missing documents
        if missing_docs:
            msg = (
                f"📄 Document Status: {len(uploaded_docs)}/{len(self.mandatory_docs)} uploaded\n\n"
                f"⚠️ We need the following documents to proceed:\n"
            )
            for doc in missing_docs:
                msg += f"  • {doc.upper()}\n"
            msg += f"\nPlease upload the required document(s) to continue your application."
            
            return {
                "messages": [AIMessage(content=msg)],
                "paused_reason": f"Waiting for documents: {', '.join(missing_docs)}",
                "all_documents_uploaded": False,
                "current_stage": "awaiting_documents",
                "intent": None  # Reset intent so user can provide documents or info
            }
            
        # All documents uploaded successfully
        state["all_documents_uploaded"] = True
        
        # Check for missing information
        personal = state.get("personal_info", {})
        financial = state.get("financial_info", {})
        employment = state.get("employment_info", {})
        
        missing_info = []
        missing_fields = []
        
        if not personal.get("name") or not personal.get("phone"):
            missing_info.append("personal details (name, phone)")
            missing_fields.append("personal_info")
        if not financial.get("net_monthly_income") or not financial.get("total_existing_emis"):
            missing_info.append("financial details (monthly income, existing EMIs)")
            missing_fields.append("financial_info")
        if not employment.get("employer_name"):
            missing_info.append("employment details (employer name)")
            missing_fields.append("employment_info")
            
        if missing_info:
            msg = (
                f"✅ All documents uploaded successfully!\n\n"
                f"📋 Now we need some additional information:\n"
            )
            for info in missing_info:
                msg += f"  • {info}\n"
            msg += f"\nPlease provide the required information to continue."
            
            return {
                "messages": [AIMessage(content=msg)],
                "paused_reason": f"Waiting for info: {', '.join(missing_fields)}",
                "current_stage": "awaiting_information",
                "intent": None  # Reset intent so user can provide new info
            }

        # All documents and information collected - proceed to loan details
        msg = (
            "✅ All required documents and information collected!\n\n"
            "📊 Next step: Loan Details\n"
            "We now need to collect your loan requirements (amount, down payment, tenure)."
        )
        
        return {
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "current_stage": "loan_details_collection"
        }
    
    def loan_details_collector(self, state: ApplicationState) -> ApplicationState:
        """
        Node 7: Loan Details Collector
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with loan details or request for missing information
        """
        financial_info = state.get("financial_info", {}) or {}
        messages = state.get("messages", [])
        
        # If user just provided a response, extract loan details using structured model
        if messages and len(messages) > 0:
            user_query = messages[-1].content
            
            # Only attempt extraction if it's a HumanMessage (user input)
            
            if isinstance(messages[-1], HumanMessage):
                system_prompt = """
                You are a loan details extraction assistant.
                Extract the following loan parameters from the user's message:
                - Home Loan Amount (in rupees/currency)
                - Down Payment (in rupees/currency)
                - Tenure (loan duration in years)
                
                Be flexible with formats:
                - "50 lakhs" = 5000000
                - "5 crores" = 50000000
                - "20 years" or "20" = 20
                
                If a value is not mentioned, return None for that field.
                """
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("user", "{query}")
                ])
                
                llm = get_structured_model()
                structured_llm = llm.with_structured_output(LoanDetails)
                
                chain = prompt | structured_llm
                result = chain.invoke({"query": user_query})
                
                # Update financial_info with extracted values
                if result.home_loan_amount and result.home_loan_amount > 0:
                    financial_info["home_loan_amount"] = result.home_loan_amount
                if result.down_payment is not None and result.down_payment >= 0:
                    financial_info["down_payment"] = result.down_payment
                if result.tenure_years and result.tenure_years > 0:
                    financial_info["tenure_years"] = result.tenure_years
        
        # Check what's still missing
        missing = []
        missing_details = []
        
        if "home_loan_amount" not in financial_info or financial_info.get("home_loan_amount", 0) <= 0:
            missing.append("Home Loan Amount (e.g., ₹50,00,000 or 50 lakhs)")
            missing_details.append("home_loan_amount")
        if "down_payment" not in financial_info or financial_info.get("down_payment") is None:
            missing.append("Down Payment amount (e.g., ₹10,00,000 or 10 lakhs)")
            missing_details.append("down_payment")
        if "tenure_years" not in financial_info or financial_info.get("tenure_years", 0) <= 0:
            missing.append("Loan Tenure in years (e.g., 20 years)")
            missing_details.append("tenure_years")
        
        # If we're missing any details, ask the user
        if missing:
            if len(missing) == 3:
                # First time asking - friendly introduction
                msg = (
                    "📋 To proceed with your loan application, I need a few details:\n\n"
                    f"Please provide:\n• {missing[0]}\n• {missing[1]}\n• {missing[2]}\n\n"
                    "You can provide all at once or one at a time."
                )
            else:
                # Follow-up request for remaining details
                msg = f"✅ Got it! Now please provide: {', '.join(missing)}"
            
            paused_reason = f"Waiting for loan details: {', '.join(missing_details)}"
            
            return {
                "financial_info": financial_info,
                "messages": [AIMessage(content=msg)],
                "paused_reason": paused_reason,
                "current_stage": "loan_details_collection"
            }
        
        # All loan details collected successfully!
        msg = (
            "✅ Loan Details Collected Successfully!\n\n"
            f"• Home Loan Amount: ₹{financial_info['home_loan_amount']:,.2f}\n"
            f"• Down Payment: ₹{financial_info['down_payment']:,.2f}\n"
            f"• Loan Tenure: {financial_info['tenure_years']} years\n\n"
            "Proceeding to financial risk assessment..."
        )
        
        return {
            "financial_info": financial_info,
            "paused_reason": None,
            "current_stage": "financial_risk_check",
            "messages": [AIMessage(content=msg)]
        }
    
    def financial_risk_checker(self, state: ApplicationState) -> ApplicationState:
        """
        Node 8: Financial Risk Checker
        
        Performs financial risk assessment by calculating:
        - LTV (Loan to Value ratio)
        - FOIR (Fixed Obligation to Income Ratio)
        - CIBIL score check
    
        """
        financial_info = state.get("financial_info", {})
        
        amount = financial_info.get("home_loan_amount", 0.0)
        down_payment = financial_info.get("down_payment", 0.0)
        income = financial_info.get("net_monthly_income", 1.0)  # Avoid division by zero
        emis = financial_info.get("total_existing_emis", 0.0)
        
        # Mock CIBIL score if not present
        personal_info = state.get("personal_info", {})
        cibil = personal_info.get("credit_score")
        if not cibil:
            cibil = random.randint(650, 850)
            personal_info["credit_score"] = cibil
            
        # Calculate property value and ratios
        property_value = amount + down_payment
        if property_value <= 0:
            property_value = 1.0  # Fallback to avoid division by zero
            
        ltv = (amount / property_value) * 100
        foir = (emis / income) * 100
        
        # Build assessment message
        msg = f"--- Financial Risk Assessment ---\n"
        msg += f"LTV: {ltv:.2f}% (Threshold: {self.ltv_threshold}%)\n"
        msg += f"FOIR: {foir:.2f}% (Threshold: {self.foir_threshold}%)\n"
        msg += f"CIBIL Score: {cibil} (Minimum: {self.min_cibil})\n\n"
        
        # Determine approval status
        approval_status = "approved"
        if ltv > self.ltv_threshold:
            approval_status = "rejected_ltv"
            msg += f"❌ Application does not meet LTV requirements.\n"
        if foir > self.foir_threshold:
            approval_status = "rejected_foir"
            msg += f"❌ Application does not meet FOIR requirements.\n"
        if cibil < self.min_cibil:
            approval_status = "rejected_cibil"
            msg += f"❌ CIBIL score is below minimum threshold.\n"
        
        if approval_status == "approved":
            msg += "✅ Congratulations! Your loan application meets all risk criteria."
        
        return {
            "personal_info": personal_info,
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "current_stage": "save_confirmation"
        }
    
    def save_confirmation_request(self, state: ApplicationState) -> ApplicationState:
        """
        Node 9: Save Confirmation Request
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with save confirmation request
        """
        msg = (
            "\n--- Application Processing Complete ---\n\n"
            "Would you like to save your application data for future reference?\n"
            "Reply with 'yes' to save or 'no' to skip saving."
        )
        
        return {
            "messages": [AIMessage(content=msg)],
            "paused_reason": "Waiting for user confirmation to save data.",
            "current_stage": "awaiting_save_confirmation"
        }
    
    def save_application_data(self, state: ApplicationState) -> ApplicationState:
        """
        Node 10: Save Application Data
        
        Args:
            state: Current application state
            
        Returns:
            Updated state with save completion status
        """
        import json
        import os
        from datetime import datetime
        
        # Check user's last message for confirmation
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1].content.lower().strip()
            
            # If user said no, skip saving
            if "no" in last_msg or "skip" in last_msg or "don't" in last_msg:
                return {
                    "messages": [AIMessage(content="Application data not saved. Thank you for using our service!")],
                    "paused_reason": None,
                    "current_stage": "completed"
                }
        
        # Prepare data to save
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
            "all_documents_uploaded": state.get("all_documents_uploaded", False)
        }
        
        # Create saved_docs directory if it doesn't exist
        saved_docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_docs")
        os.makedirs(saved_docs_dir, exist_ok=True)
        
        # Save to JSON file
        filename = f"application_{user_id}_{timestamp}.json"
        filepath = os.path.join(saved_docs_dir, filename)
        
        try:
            with open(filepath, "w") as f:
                json.dump(application_data, f, indent=2)
            
            msg = f" Application data saved successfully!\nFile: {filename}"
        except Exception as e:
            msg = f" Error saving application data: {str(e)}"
        
        return {
            "messages": [AIMessage(content=msg)],
            "paused_reason": None,
            "current_stage": "completed"
        }
