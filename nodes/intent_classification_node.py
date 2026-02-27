from pydantic import BaseModel , Field
from typing import Literal
from state import ApplicationState
from langchain_core.prompts import ChatPromptTemplate
from util.model import get_structured_model

class IntentClassification(BaseModel):
    intent: Literal["Document_upload", "Text_info", "Irrelevant", "Homeloan_query"] = Field(
        description="The assigned intent of the user's message."
    )

def intent_classifier_node(state: ApplicationState) -> ApplicationState:
    """Intent Classifier Node (Structured Output)."""
    messages = state.get("messages", [])
    if not messages:
        return state
    
    user_query = messages[-1].content
    if(state["intent"]):
        return state
    
    system_prompt = """
    You are a strict intent classifier for a Home Loan Application.

    Your task:
    Given the user's message, classify it into exactly one of the following categories:
    - 'Document_upload': if the user mentions uploading a document like PAN, Aadhaar, Salary slip, etc.
    - 'Text_info': if the user provides information like personal, financial, or employment details in text.
    - 'Homeloan_query': if the user asks questions about home loans, interest rates, eligibility,etc.
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

