import os
from .chat_completions_client import ChatCompletionsClient

LLM_MODEL = os.getenv("LLM_MODEL", "mistral-7b-instruct")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://llama:8001")

def get_llm_client():
    return ChatCompletionsClient(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL
    )