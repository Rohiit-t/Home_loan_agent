"""
Graph builder for Home Loan Application System.
This module builds the LangGraph workflow using a class-based agent structure
following industry standards for better organization and maintainability.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.backend.graph.state import ApplicationState
from app.backend.graph.nodes.agent import HomeLoanAgent
from dotenv import load_dotenv

load_dotenv()


def route_intent(state: ApplicationState) -> str:
    """
    Routes based on intent classification.
    """
    intent = state.get("intent")
    if intent == "Irrelevant":
        return "irrelevant"
    elif intent == "Homeloan_query":
        return "homeloan_query"
    elif intent == "Document_upload":
        return "document_processing"
    elif intent == "Text_info":
        return "text_info"
    else:
        return "state_evaluator"


def route_evaluation(state: ApplicationState) -> str:
    """
    Routes after state evaluation.
    Routes to interrupt_handler if docs missing,
    employment_status if docs are complete.
    """
    if str(state.get("current_stage") or "").startswith("failed"):
        return "failed"

    all_docs_uploaded = state.get("all_documents_uploaded", False)
    
    if all_docs_uploaded:
        return "employment_status"
    else:
        return "interrupt_handler"


def route_employment_status(state: ApplicationState) -> str:
    """
    Routes after employment status collection.
    Loops until valid status is captured, fails for terminal failure,
    proceeds to loan_details for eligible statuses.
    """
    if str(state.get("current_stage") or "").startswith("failed"):
        return "failed"

    if state.get("employment_status_collected", False):
        return "loan_details"

    return "employment_status"


def route_loan_details(state: ApplicationState) -> str:
    """
    Routes after loan details check.
    Routes back to loan_details if details missing, existing_emi if all present.
    """
    if str(state.get("current_stage") or "").startswith("failed"):
        return "failed"

    all_loan_details_provided = state.get("all_loan_details_provided", False)

    if all_loan_details_provided:
        return "existing_emi"
    else:
        return "loan_details"


def route_existing_emi(state: ApplicationState) -> str:
    """
    Routes after existing EMI choice collection.
    - If not yet collected -> loop existing_emi
    - If user has no existing EMI -> financial_risk
    - If user has existing EMI -> existing_loan_details
    """
    if str(state.get("current_stage") or "").startswith("failed"):
        return "failed"

    if not state.get("existing_emi_collected", False):
        return "existing_emi"

    financial_info = state.get("financial_info", {}) or {}
    has_existing_emi = financial_info.get("has_existing_emi")

    if has_existing_emi is False:
        return "emi_calculator"

    if has_existing_emi is True:
        return "existing_loan_details"

    return "existing_emi"


def route_existing_loan_details(state: ApplicationState) -> str:
    """
    Routes after existing loan details collection.
    - If not yet complete -> loop existing_loan_details
    - If complete -> financial_risk
    """
    if str(state.get("current_stage") or "").startswith("failed"):
        return "failed"

    if state.get("existing_loan_details_collected", False):
        return "emi_calculator"

    return "existing_loan_details"


def build_graph():
    """
    Builds and compiles the LangGraph workflow.
    """
    agent = HomeLoanAgent()
    
    graph = StateGraph(ApplicationState)

    graph.add_node("intent_classifier", agent.intent_classifier)
    graph.add_node("irrelevant_handler", agent.irrelevant_handler)
    graph.add_node("homeloan_query", agent.homeloan_query)
    graph.add_node("document_processing", agent.document_processing)
    graph.add_node("text_info", agent.text_info_extractor)
    graph.add_node("state_evaluator", agent.state_evaluator)
    graph.add_node("employment_status", agent.employment_status_collector)
    graph.add_node("interrupt_handler", agent.interrupt_handler)
    graph.add_node("loan_details", agent.loan_details_checker)
    graph.add_node("existing_emi", agent.existing_emi_collector)
    graph.add_node("existing_loan_details", agent.existing_loan_details_collector)
    graph.add_node("financial_risk", agent.financial_risk_checker)
    graph.add_node("emi_calculator", agent.emi_calculator)
    graph.add_node("save_json", agent.save_application_json)
    graph.add_node("save_db", agent.save_application_db)
    graph.add_node("email_notification", agent.email_notification)

    graph.add_edge(START, "intent_classifier")
    
    graph.add_conditional_edges(
        "intent_classifier",
        route_intent,
        {
            "irrelevant": "irrelevant_handler",
            "homeloan_query": "homeloan_query",
            "document_processing": "document_processing",
            "text_info": "text_info",
            "state_evaluator": "state_evaluator"
        }
    )
    
    graph.add_edge("irrelevant_handler", "state_evaluator")
    graph.add_edge("homeloan_query", "state_evaluator")
    graph.add_edge("document_processing", "state_evaluator")
    graph.add_edge("text_info", "state_evaluator")
    
    graph.add_conditional_edges(
        "state_evaluator",
        route_evaluation,
        {
            "interrupt_handler": "interrupt_handler",
            "employment_status": "employment_status",
            "failed": END,
        }
    )

    graph.add_conditional_edges(
        "employment_status",
        route_employment_status,
        {
            "employment_status": "employment_status",
            "loan_details": "loan_details",
            "failed": END,
        }
    )

    graph.add_edge("interrupt_handler", "intent_classifier")
    
    graph.add_conditional_edges(
        "loan_details",
        route_loan_details,
        {
            "loan_details": "loan_details",
            "existing_emi": "existing_emi",
            "failed": END,
        }
    )

    graph.add_conditional_edges(
        "existing_emi",
        route_existing_emi,
        {
            "existing_emi": "existing_emi",
            "existing_loan_details": "existing_loan_details",
            "emi_calculator": "emi_calculator",
            "failed": END,
        }
    )

    graph.add_conditional_edges(
        "existing_loan_details",
        route_existing_loan_details,
        {
            "existing_loan_details": "existing_loan_details",
            "emi_calculator": "emi_calculator",
            "failed": END,
        }
    )
    
    graph.add_edge("emi_calculator", "financial_risk")
    graph.add_edge("financial_risk", "save_json")
    graph.add_edge("save_json", "save_db")
    graph.add_edge("save_db", "email_notification")
    graph.add_edge("email_notification", END)
    
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)