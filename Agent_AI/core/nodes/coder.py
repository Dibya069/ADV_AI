"""
Coder Node (LangGraph)
Synthesises clean, executable Python code for the current plan step.
Knows the ToolRegistry and only uses available capabilities.
"""

import re
from langchain_core.messages import SystemMessage, HumanMessage

from core.schemas import AgentState
from core.llm import get_groq_llm, invoke_groq
from core.ui import print_agent_action, print_code_box


def coder_node(state: AgentState) -> AgentState:
    """Synthesises executable Python code for the active step."""
    step_idx = min(state.current_step_index, len(state.plan) - 1) if state.plan else 0
    step_desc = state.plan[step_idx] if state.plan else state.task
    step_num = step_idx + 1
    total = len(state.plan) if state.plan else 1

    print_agent_action("CodeBuilder", f"Synthesising code for Step {step_num}/{total}", step_desc)

    # Build capability context — agent must not invent unavailable tools
    registry_summary = state.tool_registry.summary() if state.tool_registry else ""

    llm = get_groq_llm(temperature=0.1, max_tokens=800)
    system_prompt = (
        "You are an expert Python code generator. "
        "Write concise, clean, self-contained, executable Python code for the given step.\n\n"
        "AVAILABLE TOOLS (use ONLY these):\n"
        f"{registry_summary}\n\n"
        "CRITICAL RULES:\n"
        "1. DO NOT print thousands of raw lines or paths. Print aggregated statistics and top-10 samples.\n"
        "2. Exclude '.venv', 'venv', '.git', '__pycache__', 'node_modules' when scanning directories.\n"
        "3. Print results clearly to stdout so the verifier can confirm the task is done.\n"
        "4. Use only standard libraries or pre-installed packages (os, sys, pathlib, json, math, etc.).\n"
        "5. If a capability is marked 'unavailable', do NOT use it — say so in a print() statement instead.\n"
        "6. Output ONLY the python code wrapped in ```python ... ``` block. No conversational text."
    )

    user_content = (
        f"Overall Task: {state.task}\n"
        f"Current Step: {step_desc}\n"
        f"Workspace directory: {state.workspace_dir}\n"
    )
    if state.step_history:
        # Only pass summaries, not raw stdout, to save tokens
        prior = [{"step": h["step"], "summary": h["summary"]} for h in state.step_history]
        user_content += f"Prior step summaries: {prior}\n"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response_text = invoke_groq(llm, messages, state, node="coder")
    code = extract_code(response_text)
    state.current_code = code

    print_code_box(code, f"CodeBuilder: Step {step_num}")
    return state


def extract_code(text: str) -> str:
    """Extracts code block from markdown ```python ... ``` or returns raw text."""
    match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()
