import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from state import ApplicationState
from util.model import get_model

def homeloan_query_node(state: ApplicationState) -> ApplicationState:
    """Home Loan Query Handler.
    Answers general queries about home loans using the LLM.
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
