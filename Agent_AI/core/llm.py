"""
LangChain Groq LLM Wrapper
Initialises ChatGroq instances and handles token metrics tracking with per-node attribution.
"""

import time
from typing import List
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage

from core.config import config
from core.schemas import AgentState


def get_groq_llm(temperature: float = 0.1, max_tokens: int = 700) -> ChatGroq:
    """Instantiates ChatGroq using the configured Groq model and API key."""
    config.validate_api_key()
    return ChatGroq(
        model=config.groq_model,
        api_key=config.groq_api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def invoke_groq(
    llm: ChatGroq,
    messages: List[BaseMessage],
    state: AgentState,
    node: str = "",
) -> str:
    """
    Invokes the Groq LLM, tracks token usage + latency into AgentState.token_metrics
    with per-node attribution for observability.
    Returns the string response.
    """
    start_time = time.time()
    response = llm.invoke(messages)
    latency = time.time() - start_time

    metadata = getattr(response, "response_metadata", {})
    usage = metadata.get("token_usage", {})
    if usage:
        state.token_metrics.add_usage(usage, latency, node=node)

    return response.content.strip()
