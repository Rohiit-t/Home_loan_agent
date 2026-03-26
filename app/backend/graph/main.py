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
    Routes to interrupt_handler if docs missing, loan_details if all docs present.
    """
    all_docs_uploaded = state.get("all_documents_uploaded", False)
    
    if all_docs_uploaded:
        return "loan_details"
    else:
        return "interrupt_handler"


def route_loan_details(state: ApplicationState) -> str:
    """
    Routes after loan details check.
    Routes back to loan_details if details missing, financial_risk if all present.
    """
    all_loan_details_provided = state.get("all_loan_details_provided", False)

    if all_loan_details_provided:
        return "financial_risk"
    else:
        return "loan_details"


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
    graph.add_node("interrupt_handler", agent.interrupt_handler)
    graph.add_node("loan_details", agent.loan_details_checker)
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
            "loan_details": "loan_details"
        }
    )

    graph.add_edge("interrupt_handler", "intent_classifier")
    
    graph.add_conditional_edges(
        "loan_details",
        route_loan_details,
        {
            "loan_details": "loan_details",
            "financial_risk": "financial_risk",
        }
    )
    
    graph.add_edge("financial_risk", "emi_calculator")
    graph.add_edge("emi_calculator", "save_json")
    graph.add_edge("save_json", "save_db")
    graph.add_edge("save_db", "email_notification")
    graph.add_edge("email_notification", END)
    
    memory = MemorySaver()
    
    return graph.compile(checkpointer=memory)