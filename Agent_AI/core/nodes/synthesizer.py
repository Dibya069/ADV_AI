"""
Synthesizer Node (LangGraph)
Synthesises verified step outcomes into a direct final answer.
Includes observability summary (retries, errors, token usage per node).
"""

from langchain_core.messages import SystemMessage, HumanMessage

from core.schemas import AgentState
from core.llm import get_groq_llm, invoke_groq
from core.ui import print_agent_action, print_token_summary, print_observability_summary


def synthesizer_node(state: AgentState) -> AgentState:
    """Synthesises verified execution data into final response with observability report."""
    print_agent_action("Synthesizer", "Synthesising final verified response...")

    # Fallback: if no step_history but we have output, build one
    if not state.step_history and state.last_execution and state.last_execution.stdout:
        step_idx = min(state.current_step_index, len(state.plan) - 1) if state.plan else 0
        state.step_history.append({
            "step": state.plan[step_idx] if state.plan else state.task,
            "stdout": state.last_execution.stdout,
            "summary": (
                state.last_observation.summary
                if state.last_observation
                else state.last_execution.stdout[:200]
            ),
        })

    llm = get_groq_llm(temperature=0.2, max_tokens=500)
    system_prompt = (
        "You are the final response synthesiser. "
        "Provide a direct, clear, well-formatted answer to the user's task "
        "based strictly on verified execution results. "
        "Use Markdown tables or bullet points where appropriate. "
        "Do not repeat internal debugging thoughts or code unless asked. "
        "If some steps failed and were not repaired, state what succeeded and what did not."
    )

    evidence = "\n\n".join(
        f"[Step: {h['step']}]\nOutput: {h['stdout']}\nSummary: {h['summary']}"
        for h in state.step_history
    )

    # Include repair stats if repairs occurred
    repair_note = ""
    if state.repair_attempts > 0:
        repair_note = (
            f"\n\nNote: This task required {state.repair_attempts} repair cycle(s) "
            f"over {state.total_execution_attempts} total execution attempt(s)."
        )

    user_content = (
        f"User Task: {state.task}\n\n"
        f"Verified Execution Evidence:\n{evidence}"
        f"{repair_note}\n\n"
        "Synthesise the final answer for the user."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    final_text = invoke_groq(llm, messages, state, node="synthesizer")
    state.final_answer = final_text
    state.is_completed = True

    # Print observability summary then token metrics
    print_observability_summary(state)
    print_token_summary(state.token_metrics.to_dict())

    return state
