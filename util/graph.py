"""
Graph builder for Home Loan Application System.
This module builds the LangGraph workflow using a class-based agent structure
following industry standards for better organization and maintainability.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from state import ApplicationState
from nodes.agent import HomeLoanAgent
from dotenv import load_dotenv

load_dotenv()


def route_intent(state: ApplicationState) -> str:
    if state.get("current_stage") == "loan_details_collection":
        return "loan_details"
    
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
    
    """
    current_stage = state.get("current_stage")
    
    if current_stage == "loan_details_collection":
        # All documents and info collected, proceed to loan details
        return "loan_details"
    elif current_stage in ["awaiting_documents", "awaiting_information"]:
        # Missing documents or info - loop back to intent_classifier
        return "intent_classifier"
    else:
        # Fallback: end the workflow
        return END


def route_loan_details(state: ApplicationState) -> str:
    """
    Routes after loan details collection.
    
    """
    if state.get("paused_reason"):
        # Still waiting for user to provide loan details
        return "loan_details"
    elif state.get("current_stage") == "financial_risk_check":
        # All details collected, proceed to risk check
        return "financial_risk"
    return END


def route_financial_risk(state: ApplicationState) -> str:
    """
    Routes after financial risk check.
    Proceeds to save confirmation if risk check is complete.
    """
    if state.get("current_stage") == "save_confirmation":
        return "save_confirmation"
    return END


def route_save_confirmation(state: ApplicationState) -> str:
    """
    Routes after user responds to save confirmation.
    Checks the user's response to decide whether to save or end.
    """
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1].content.lower().strip()
        
        # Check if user wants to save
        if "yes" in last_msg or "save" in last_msg or "ok" in last_msg or "sure" in last_msg:
            return "save_data"
        elif "no" in last_msg or "skip" in last_msg or "don't" in last_msg:
            return "skip_save"
    
    return "save_data"


def build_graph():
    """
    Builds and compiles the LangGraph workflow.
    
    """
    # Initialize the agent
    agent = HomeLoanAgent()
    
    # Create the state graph
    graph = StateGraph(ApplicationState)

    # Add nodes using agent methods
    graph.add_node("intent_classifier", agent.intent_classifier)
    graph.add_node("irrelevant_handler", agent.irrelevant_handler)
    graph.add_node("homeloan_query", agent.homeloan_query)
    graph.add_node("document_processing", agent.document_processing)
    graph.add_node("text_info", agent.text_info_extractor)
    graph.add_node("state_evaluator", agent.state_evaluator)
    graph.add_node("loan_details", agent.loan_details_collector)
    graph.add_node("financial_risk", agent.financial_risk_checker)
    graph.add_node("save_confirmation", agent.save_confirmation_request)
    graph.add_node("save_data", agent.save_application_data)
    graph.add_node("skip_save", agent.save_application_data)

    # Define edges
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
    
    graph.add_edge("irrelevant_handler", END)
    graph.add_edge("homeloan_query", END)
    graph.add_edge("document_processing", "state_evaluator")
    graph.add_edge("text_info", "state_evaluator")
    
    graph.add_conditional_edges(
        "state_evaluator",
        route_evaluation,
        {
            "intent_classifier": "intent_classifier",
            "loan_details": "loan_details",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "loan_details",
        route_loan_details,
        {
            "loan_details": "loan_details",
            "financial_risk": "financial_risk",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "financial_risk",
        route_financial_risk,
        {
            "save_confirmation": "save_confirmation",
            END: END
        }
    )
    
    graph.add_conditional_edges(
        "save_confirmation",
        route_save_confirmation,
        {
            "save_data": "save_data",
            "skip_save": "skip_save"
        }
    )
    
    graph.add_edge("save_data", END)
    graph.add_edge("skip_save", END)
    
    memory = MemorySaver()
    
    # Compile with checkpointer and interrupt points
    return graph.compile(
        checkpointer=memory,
        interrupt_after=["state_evaluator", "loan_details", "save_confirmation"]
    )