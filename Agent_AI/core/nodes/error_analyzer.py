"""
Error Analyzer Node (LangGraph)
NEW NODE — sits between Executor and Repair.
Receives a structured ExecutionResult, performs root-cause analysis,
and produces a concise diagnostic for the Repair LLM.
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage

from core.schemas import AgentState
from core.llm import get_groq_llm, invoke_groq
from core.ui import print_agent_action, Colors


def error_analyzer_node(state: AgentState) -> AgentState:
    """
    Analyses the structured ExecutionResult and produces a targeted root-cause
    diagnosis used by the Repair LLM to fix the code.
    """
    exec_res = state.last_execution
    if not exec_res:
        state.last_error_analysis = "No execution result available to analyse."
        return state

    structured_ctx = exec_res.to_repair_context()

    print_agent_action(
        "ErrorAnalyzer",
        f"Analysing {structured_ctx['error_type']} (exit code {structured_ctx['exit_code']})",
        f"Line {structured_ctx['line']} — {structured_ctx['error_message'][:200]}",
    )

    # Build a compact, token-efficient prompt
    llm = get_groq_llm(temperature=0.0, max_tokens=200)

    system_prompt = (
        "You are a Python error analyst. "
        "Given a structured execution failure, identify:\n"
        "1. The root cause (one sentence).\n"
        "2. The exact fix needed (one sentence).\n"
        "3. Whether the agent needs a capability that is unavailable (yes/no).\n"
        "Be concise — maximum 3 bullet points."
    )

    user_content = (
        f"Execution failure context:\n{json.dumps(structured_ctx, indent=2)}\n\n"
        f"Code that failed:\n```python\n{state.current_code[:1500]}\n```"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    analysis = invoke_groq(llm, messages, state, node="error_analyzer")
    state.last_error_analysis = analysis

    print_agent_action("ErrorAnalyzer", f"{Colors.YELLOW}Root-Cause Analysis{Colors.RESET}", analysis)
    return state

