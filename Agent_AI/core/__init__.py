"""
Core Package for Agent_AI — v2
Powered by LangGraph, LangChain, and Pydantic with Groq.
"""

from core.config import config, SystemConfig
from core.schemas import (
    AgentState,
    ExecutionResult,
    Observation,
    Plan,
    TokenMetrics,
    ToolRegistry,
    StepTelemetry,
    ErrorCategory,
)
from core.executor import CodeExecutor
from core.graph import AgentGraph, build_agent_graph

# Alias for backwards compatibility
MultiAgentOrchestrator = AgentGraph

__version__ = "3.0.0"
__all__ = [
    "config",
    "SystemConfig",
    "AgentState",
    "ExecutionResult",
    "Observation",
    "Plan",
    "TokenMetrics",
    "ToolRegistry",
    "StepTelemetry",
    "ErrorCategory",
    "CodeExecutor",
    "AgentGraph",
    "MultiAgentOrchestrator",
    "build_agent_graph",
]
