from langchain_core.messages import AIMessage
from state import ApplicationState

def irrelevant_node(state: ApplicationState) -> ApplicationState:
    """Irrelevant Query Handler.
    Handles completely irrelevant queries by asking the user to stay on topic.
    Updates paused_reason or simply appends a message.
    """
    response_msg = AIMessage(
        content="I am a Home Loan Application assistant. I can only help you with home loan queries, "
                "document uploads, and processing your loan application. Please ask something related to home loans."
    )
    
    return {
        "messages": [response_msg],
        "paused_reason": "Irrelevant query. Waiting for valid input."
    }
