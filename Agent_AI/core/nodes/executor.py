"""
Executor Node (LangGraph)
Runs the generated Python code via subprocess, produces a structured ExecutionResult,
and handles human-approval gate for destructive operations.
"""

import re
from core.schemas import AgentState, StepTelemetry, StepStatus
from core.executor import CodeExecutor
from core.ui import print_agent_action, print_execution_result, Colors


# Operations that require human approval before execution
_DESTRUCTIVE_PATTERNS = [
    r"\bos\.remove\b",
    r"\bshutil\.rmtree\b",
    r"\bos\.unlink\b",
    r"\bsmtplib\b",
    r"\brequests\.post\b",
    r"\bhttpx\.post\b",
    r"\bsubprocess\.Popen\b",
]


def _requires_human_approval(code: str) -> str:
    """Returns the matched pattern name if code requires approval, else empty string."""
    for pattern in _DESTRUCTIVE_PATTERNS:
        if re.search(pattern, code):
            return pattern
    return ""


def executor_node(state: AgentState) -> AgentState:
    """Executes the current code, populating a structured ExecutionResult."""

    # ── Human Approval Gate ───────────────────────────────────────────────
    dangerous_op = _requires_human_approval(state.current_code)
    if dangerous_op:
        state.pending_approval = True
        state.approval_action = f"Code uses potentially destructive operation: `{dangerous_op}`"
        if not state.approval_granted:
            print_agent_action(
                "Executor",
                f"{Colors.YELLOW}⚠ Approval Required{Colors.RESET}",
                f"{state.approval_action}\nSet approval_granted=True to proceed.",
            )
            # Mark as failed so the graph can route to synthesizer with a message
            from core.schemas import ExecutionResult
            state.last_execution = ExecutionResult.from_process(
                stdout="",
                stderr=f"Execution blocked: human approval required for '{dangerous_op}'",
                exit_code=-2,
                duration=0.0,
                code=state.current_code,
                attempt=state.total_execution_attempts + 1,
            )
            return state
        # Approval granted — reset flags and proceed
        state.pending_approval = False

    # ── Idempotency guard ─────────────────────────────────────────────────
    state.total_execution_attempts += 1

    executor = CodeExecutor(
        working_dir=state.workspace_dir,
        timeout=None,  # Uses config.execution_timeout
    )

    print_agent_action(
        "Executor",
        f"Executing code (attempt {state.total_execution_attempts})",
        f"Workspace: {state.workspace_dir}",
    )

    result = executor.execute_python(
        state.current_code,
        attempt=state.total_execution_attempts,
    )
    state.last_execution = result

    print_execution_result(result)

    # ── Step Telemetry ────────────────────────────────────────────────────
    step_idx = min(state.current_step_index, len(state.plan) - 1) if state.plan else 0
    step_desc = state.plan[step_idx] if state.plan else state.task

    tel = StepTelemetry(
        step_index=step_idx,
        description=step_desc,
        status=StepStatus.SUCCESS if result.success else StepStatus.FAILED,
        attempts=state.repair_attempts + 1,
        error_categories=[result.error_type.value] if not result.success else [],
        duration_seconds=result.duration,
        stdout_summary=result.stdout[:300],
    )
    # Update or append telemetry for this step
    existing = [t for t in state.step_telemetry if t.step_index == step_idx]
    if existing:
        state.step_telemetry[-1] = tel
    else:
        state.step_telemetry.append(tel)

    return state
