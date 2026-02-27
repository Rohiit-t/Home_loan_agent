from langchain_openai import ChatOpenAI
import os
from typing import TypedDict, Annotated, Literal, Optional


def get_api_key()->str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")
    return api_key

def get_model(temperature: float = 0.5) -> ChatOpenAI:
    api_key = get_api_key()
    model = ChatOpenAI(
        model = "meta-llama/llama-3.3-70b-instruct",
        temperature = temperature,
        api_key = api_key,
        max_tokens = 100,
        base_url = "https://openrouter.ai/api/v1"
    )
    return model

def get_structured_model() -> ChatOpenAI:
    api_key = get_api_key()
    model = ChatOpenAI(
        model = "openai/gpt-4o-mini",
        temperature = 0,
        max_tokens = 50,
        api_key = api_key,
        base_url = "https://openrouter.ai/api/v1"
    )
    return model
