from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from state import ApplicationState
from util.model import get_structured_model

class ExtractedInfo(BaseModel):
    personal_info: Optional[dict] = Field(description="Dictionary containing keys like 'name', 'age', 'phone', 'email' if found.")
    financial_info: Optional[dict] = Field(description="Dictionary containing 'net_monthly_income', 'total_existing_emis' if found.")
    employment_info: Optional[dict] = Field(description="Dictionary containing 'employer_name', 'employment_type' if found.")

def text_info_node(state: ApplicationState) -> ApplicationState:
    """Text_info_Node
    Extracts personal, financial, and employment info from user text queries.
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
