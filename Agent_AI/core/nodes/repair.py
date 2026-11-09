"""
Repair Node (LangGraph)
Receives structured error analysis + ExecutionResult and returns corrected code.
Operates on the structured repair context, not plain error strings.
"""

import json
from langchain_core.messages import SystemMessage, HumanMessage

from core.config import config
from core.schemas import AgentState
from core.llm import get_groq_llm, invoke_groq
from core.ui import print_agent_action, print_code_box
from core.nodes.coder import extract_code


def _compress_stderr(stderr: str, max_lines: int = 15) -> str:
    """Keep only the head + tail of a long traceback to save tokens."""
    if not stderr:
        return ""
    lines = stderr.strip().splitlines()
    if len(lines) <= max_lines:
        return stderr.strip()
    head = lines[:3]
    tail = lines[-(max_lines - 3):]
    return "\n".join(head + ["... [intermediate frames omitted] ..."] + tail)


def repair_node(state: AgentState) -> AgentState:
    """Repairs flawed code using structured error context and root-cause analysis."""
    state.repair_attempts += 1

    step_idx = min(state.current_step_index, len(state.plan) - 1) if state.plan else 0
    step_desc = state.plan[step_idx] if state.plan else state.task

    # Build the structured repair context
    exec_res = state.last_execution
    structured_ctx = exec_res.to_repair_context() if exec_res else {}

    print_agent_action(
        "RepairLLM",
        f"Auto-Repair — Attempt {state.repair_attempts}/{state.max_repair_attempts}",
        f"Error type: {structured_ctx.get('error_type', 'Unknown')} | "
        f"Line: {structured_ctx.get('line', '?')} | "
        f"{structured_ctx.get('error_message', '')[:150]}",
    )

    llm = get_groq_llm(temperature=0.1, max_tokens=900)

    # Give the repair LLM the full structured instruction
    system_prompt = (
        "You are a code debugging and repair specialist.\n\n"
        "The generated code failed during execution. Your task:\n"
        "1. Analyse the error using the structured failure context.\n"
        "2. Identify the root cause (use the analyst's diagnosis if provided).\n"
        "3. Inspect the failing line and surrounding code carefully.\n"
        "4. Fix the issue completely — including unterminated strings, bad indentation, "
        "missing imports, or wrong file paths.\n"
        "5. Return the COMPLETE corrected Python code.\n"
        "6. Do NOT claim success until all identified issues are fixed.\n\n"
        "RULES:\n"
        "- Output ONLY ```python ... ``` block. No explanations outside the block.\n"
        "- Do NOT print thousands of raw paths — use aggregated summaries.\n"
        "- Exclude '.venv', 'venv', '.git', '__pycache__' when scanning directories.\n"
        "- Only use capabilities marked 'available' in the tool registry."
    )

    compact_stderr = _compress_stderr(
        structured_ctx.get("stderr", ""), max_lines=config.max_traceback_lines
    )

    user_content = (
        f"Task: {state.task}\n"
        f"Step: {step_desc}\n"
        f"Workspace: {state.workspace_dir}\n\n"
        f"Previous execution error (structured):\n"
        f"{json.dumps(structured_ctx, indent=2)}\n\n"
        f"Root-cause analysis:\n{state.last_error_analysis or '(none provided)'}\n\n"
        f"Failed code:\n```python\n{state.current_code}\n```\n\n"
        f"Compressed stderr:\n{compact_stderr}\n\n"
        "Return the complete corrected Python script."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response_text = invoke_groq(llm, messages, state, node="repair")
    repaired_code = extract_code(response_text)

    state.current_code = repaired_code
    print_code_box(repaired_code, f"Repaired Code (Attempt {state.repair_attempts})")

    return state
