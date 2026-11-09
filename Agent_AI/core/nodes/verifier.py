"""
Verifier Node (LangGraph)
Replaces the old Observer.
Goes beyond checking exit code 0 — semantically verifies that the actual
output satisfies the step objective and that expected artifacts exist.
"""

import json
import re
from langchain_core.messages import SystemMessage, HumanMessage

from core.schemas import AgentState, Observation
from core.llm import get_groq_llm, invoke_groq
from core.ui import print_agent_action, Colors


def verifier_node(state: AgentState) -> AgentState:
    """
    Semantically verifies execution output against the step objective.
    Does NOT simply trust exit code 0 — checks actual output content.
    Advances current_step_index on success.
    """
    exec_res = state.last_execution
    step_idx = min(state.current_step_index, len(state.plan) - 1) if state.plan else 0
    step_desc = state.plan[step_idx] if state.plan else state.task

    print_agent_action("Verifier", "Verifying execution output against step objective...")

    # ── 1. Deterministic fail: non-zero exit ─────────────────────────────
    if not exec_res or not exec_res.success:
        err = exec_res.stderr if exec_res else "No execution result"
        critique = (
            f"Code exited with code {exec_res.exit_code if exec_res else -1}: "
            f"{exec_res.error_message if exec_res else err}"
        )
        state.last_observation = Observation(is_success=False, critique=critique, summary="")
        print_agent_action("Verifier", f"{Colors.RED}✗ Execution Failed{Colors.RESET}", critique[:300])
        return state

    # ── 2. Deterministic fail: empty stdout ──────────────────────────────
    if not exec_res.stdout.strip():
        critique = (
            "Exit code 0 but stdout is completely empty. "
            "Ensure the script prints its results or counts."
        )
        state.last_observation = Observation(is_success=False, critique=critique, summary="")
        print_agent_action("Verifier", f"{Colors.RED}✗ No Output{Colors.RESET}", critique)
        return state

    # ── 3. Semantic verification via LLM ─────────────────────────────────
    stdout = exec_res.stdout.strip()
    # Show head + tail so summary counts at the bottom are always visible
    if len(stdout) > 1500:
        formatted = stdout[:500] + "\n... [intermediate output omitted] ...\n" + stdout[-1000:]
    else:
        formatted = stdout

    llm = get_groq_llm(temperature=0.0, max_tokens=180)
    system_prompt = (
        "You are a strict, pragmatic output verifier. "
        "Check if the execution stdout actually satisfies the step objective. "
        "PASS if: output contains the requested answers, counts, files, or calculations. "
        "FAIL if: output is a placeholder, claims capability is unavailable when a tool exists, "
        "references a file that wasn't actually created, or the requested artifact is missing.\n"
        "Return ONLY valid JSON:\n"
        '{"is_success": true|false, "critique": "reason if failed", "summary": "brief verified summary"}'
    )

    user_content = (
        f"Step Objective: {step_desc}\n"
        f"User Task: {state.task}\n"
        f"Execution Stdout:\n{formatted}\n"
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]

    response_text = invoke_groq(llm, messages, state, node="verifier")
    obs = _parse_observation(response_text, stdout)
    state.last_observation = obs

    if obs.is_success:
        print_agent_action("Verifier", f"{Colors.GREEN}✓ Step Verified{Colors.RESET}", obs.summary)
        state.step_history.append({
            "step": step_desc,
            "stdout": stdout[-800:],
            "summary": obs.summary,
        })
        # Advance step counter — MUST be done here in the node, not in routing functions
        state.current_step_index += 1
        state.repair_attempts = 0  # Reset repair counter for next step
    else:
        print_agent_action("Verifier", f"{Colors.RED}✗ Verification Failed{Colors.RESET}", obs.critique[:300])

    return state


def _parse_observation(text: str, fallback_stdout: str) -> Observation:
    """Parses LLM output into Pydantic Observation model."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return Observation(
                is_success=bool(data.get("is_success", False)),
                critique=str(data.get("critique", "")).strip(),
                summary=str(data.get("summary", "")).strip() or fallback_stdout[-250:],
            )
        except Exception:
            pass

    # Heuristic fallback
    low = text.lower()
    is_success = "true" in low and "false" not in low and "fail" not in low and "error" not in low
    return Observation(
        is_success=is_success,
        critique="" if is_success else text.strip(),
        summary=text.strip() if is_success else fallback_stdout[-250:],
    )

