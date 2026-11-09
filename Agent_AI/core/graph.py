"""
LangGraph Workflow Architecture — v2
New architecture:

  User Request
      ↓
    Guard
      ↓
   Planner  (also sets ToolRegistry)
      ↓
   Coder
      ↓
  Executor
      ↓
  Execution Result
      ↙           ↘
  Error?           No Error
    ↓                 ↓
ErrorAnalyzer      Verifier
    ↓                 ↓
 RepairLLM        Success?
    ↓               ↙   ↘
 Executor        Yes      No (re-analyze)
  (retry)         ↓
             Synthesizer
                  ↓
               END

Safeguards:
- Retry limit: max_repair_attempts per step
- Timeout: execution_timeout in config
- Idempotency: total_execution_attempts tracked
- Human approval gate: destructive ops blocked in executor_node
- Verification: semantic output check, not just exit code 0
- Observability: per-node token tracking + step telemetry
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from core.config import config
from core.schemas import AgentState
from core.nodes import (
    guard_node,
    planner_node,
    coder_node,
    executor_node,
    error_analyzer_node,
    repair_node,
    verifier_node,
    synthesizer_node,
)
from core.ui import print_agent_action


# ---------------------------------------------------------------------------
# Routing functions — NEVER mutate state here, only read it
# ---------------------------------------------------------------------------

def route_guard(state: AgentState) -> Literal["planner", "__end__"]:
    """After guard: proceed to planner if safe, otherwise end."""
    if not state.is_safe:
        return END
    return "planner"


def route_after_executor(
    state: AgentState,
) -> Literal["error_analyzer", "verifier"]:
    """
    After execution: route to ErrorAnalyzer if the run failed,
    otherwise to Verifier for semantic output checking.
    """
    exec_res = state.last_execution
    # Approval-blocked runs also route to error_analyzer (which will surface it)
    if not exec_res or not exec_res.success:
        return "error_analyzer"
    return "verifier"


def route_after_verifier(
    state: AgentState,
) -> Literal["error_analyzer", "coder", "synthesizer"]:
    """
    After verification:
    - If verification failed and repairs remain → error_analyzer → repair loop
    - If all plan steps done → synthesizer
    - If more steps remain → coder (next step)
    """
    obs = state.last_observation
    has_issue = not obs or not obs.is_success

    if has_issue:
        if state.repair_attempts < state.max_repair_attempts:
            # Route through error_analyzer for structured diagnosis
            return "error_analyzer"
        # Repair limit reached — synthesise whatever we have
        print_agent_action(
            "Verifier",
            "⚠ Repair limit reached — proceeding to synthesis",
            f"({state.repair_attempts}/{state.max_repair_attempts} attempts used)",
        )
        return "synthesizer"

    # Verifier advanced current_step_index — check if more steps remain
    if state.current_step_index < len(state.plan):
        return "coder"

    return "synthesizer"


def route_after_error_analyzer(
    state: AgentState,
) -> Literal["repair", "synthesizer"]:
    """
    After error analysis: if repairs remain → repair node.
    Otherwise give up and synthesize.
    """
    if state.repair_attempts < state.max_repair_attempts:
        return "repair"
    return "synthesizer"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_agent_graph() -> StateGraph:
    """Builds the complete LangGraph StateGraph workflow."""
    workflow = StateGraph(AgentState)

    # Nodes
    workflow.add_node("guard",          guard_node)
    workflow.add_node("planner",        planner_node)
    workflow.add_node("coder",          coder_node)
    workflow.add_node("executor",       executor_node)
    workflow.add_node("error_analyzer", error_analyzer_node)
    workflow.add_node("repair",         repair_node)
    workflow.add_node("verifier",       verifier_node)
    workflow.add_node("synthesizer",    synthesizer_node)

    # Edges
    workflow.add_edge(START, "guard")

    workflow.add_conditional_edges(
        "guard",
        route_guard,
        {"planner": "planner", END: END},
    )

    workflow.add_edge("planner", "coder")
    workflow.add_edge("coder",   "executor")

    # After executor: success → verifier, failure → error_analyzer
    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "error_analyzer": "error_analyzer",
            "verifier":       "verifier",
        },
    )

    # After verifier: failed → error_analyzer, next step → coder, done → synthesizer
    workflow.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "error_analyzer": "error_analyzer",
            "coder":          "coder",
            "synthesizer":    "synthesizer",
        },
    )

    # After error_analyzer: repair → repair node, give up → synthesizer
    workflow.add_conditional_edges(
        "error_analyzer",
        route_after_error_analyzer,
        {
            "repair":      "repair",
            "synthesizer": "synthesizer",
        },
    )

    # Repair loops back to executor for retry
    workflow.add_edge("repair",      "executor")

    # Synthesizer ends the graph
    workflow.add_edge("synthesizer", END)

    return workflow


# ---------------------------------------------------------------------------
# High-level runner
# ---------------------------------------------------------------------------

class AgentGraph:
    """High-level runner wrapping the compiled LangGraph workflow."""

    def __init__(
        self,
        workspace_dir: str = None,
        max_repair_attempts: int = None,
    ):
        self.workspace_dir = workspace_dir or config.workspace_root
        self.max_repair_attempts = max_repair_attempts or config.max_repair_attempts
        self.graph = build_agent_graph().compile()

    def run(self, task: str) -> AgentState:
        """Runs the LangGraph agent on the given task."""
        initial_state = AgentState(
            task=task,
            workspace_dir=self.workspace_dir,
            max_repair_attempts=self.max_repair_attempts,
        )
        print_agent_action("Orchestrator", "Task Received", task)

        final_state_dict = self.graph.invoke(
            initial_state,
            config={"recursion_limit": 30},
        )

        if isinstance(final_state_dict, AgentState):
            return final_state_dict
        return AgentState(**final_state_dict)
