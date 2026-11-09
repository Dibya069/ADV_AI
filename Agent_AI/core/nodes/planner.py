"""
Planner Node (LangGraph)
Decomposes user tasks into minimal executable steps.
Also initialises the ToolRegistry so all downstream agents know what is available.
"""

import json
import re
from langchain_core.messages import SystemMessage, HumanMessage

from core.schemas import AgentState, Plan, ToolRegistry
from core.llm import get_groq_llm, invoke_groq
from core.ui import print_agent_action, print_tool_registry


def planner_node(state: AgentState) -> AgentState:
    """Decomposes the task into 1-2 minimal execution steps and sets up the ToolRegistry."""

    # Initialise ToolRegistry so agents know what is available
    state.tool_registry = ToolRegistry.default(workspace_dir=state.workspace_dir)
    registry_summary = state.tool_registry.summary()

    print_agent_action("Planner", "Analysing task and generating execution plan...")
    print_tool_registry(registry_summary)

    llm = get_groq_llm(temperature=0.1, max_tokens=300)
    system_prompt = (
        "You are an ultra-concise, high-accuracy task planner. "
        "Decompose the user's task into the MINIMUM necessary executable steps for a Python code generator.\n"
        "IMPORTANT: Prefer 1 unified execution step if the entire task can be done in one Python script.\n"
        "The agent can: execute Python scripts, read/write files, list directories inside the workspace.\n"
        "The agent CANNOT: make network requests, run shell commands, or access files outside the workspace without approval.\n"
        "Return ONLY a valid JSON object:\n"
        '{"objective": "concise goal summary", "steps": ["Step 1 description"]}'
    )

    user_content = f"Task: {state.task}"
    if state.workspace_dir:
        user_content += f"\nWorkspace directory: {state.workspace_dir}"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response_text = invoke_groq(llm, messages, state, node="planner")
    plan = _parse_plan(response_text, state.task)

    state.plan = plan.steps
    state.current_step_index = 0

    steps_preview = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(plan.steps))
    print_agent_action("Planner", f"Formulated {len(plan.steps)}-step plan:", steps_preview)

    return state


def _parse_plan(text: str, fallback_task: str) -> Plan:
    """Parses and validates LLM response into Pydantic Plan model."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            steps = data.get("steps", [])
            objective = data.get("objective", fallback_task)
            if isinstance(steps, list) and steps:
                cleaned = [str(s).strip() for s in steps if str(s).strip()][:2]
                return Plan(objective=objective, steps=cleaned)
        except Exception:
            pass
    return Plan(objective=fallback_task, steps=[f"Execute task: {fallback_task}"])
