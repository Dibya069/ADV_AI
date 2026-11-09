"""
UI & Terminal Presentation
Provides clean, colored terminal indicators, agent message badges,
code rendering, structured execution result display,
observability summary, and token consumption tables.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from core.schemas import AgentState, ExecutionResult


class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    RED     = "\033[31m"
    WHITE   = "\033[37m"


# Agent → color mapping (includes new nodes)
_AGENT_COLORS = {
    "Guard":         Colors.MAGENTA,
    "Planner":       Colors.BLUE,
    "CodeBuilder":   Colors.CYAN,
    "Executor":      Colors.YELLOW,
    "ErrorAnalyzer": Colors.RED,
    "RepairLLM":     Colors.RED,
    "Verifier":      Colors.GREEN,
    "Synthesizer":   Colors.BOLD + Colors.WHITE,
    "Orchestrator":  Colors.BOLD + Colors.WHITE,
}


def print_header(title: str):
    width = 72
    print(f"\n{Colors.CYAN}{'═' * width}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title.center(width - 4)}{Colors.RESET}")
    print(f"{Colors.CYAN}{'═' * width}{Colors.RESET}\n")


def print_agent_action(agent_name: str, action: str, details: str = ""):
    color = _AGENT_COLORS.get(agent_name, Colors.WHITE)
    badge = f"{color}[{agent_name}]{Colors.RESET}"
    print(f"{badge} {Colors.BOLD}{action}{Colors.RESET}")
    if details:
        indent = "    "
        formatted = "\n".join(f"{indent}{line}" for line in details.strip().splitlines())
        print(f"{Colors.DIM}{formatted}{Colors.RESET}")


def print_code_box(code: str, title: str = "Generated Code"):
    print(f"\n  {Colors.BOLD}{Colors.CYAN}╭── {title} {'─' * max(0, 55 - len(title))}╮{Colors.RESET}")
    for line in code.splitlines():
        print(f"  {Colors.CYAN}│{Colors.RESET} {line}")
    print(f"  {Colors.CYAN}╰{'─' * 60}╯{Colors.RESET}\n")


def print_tool_registry(registry_summary: str):
    """Displays the ToolRegistry so the user can see what the agent can do."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}┌─ Tool Capability Registry ───────────────────────────────────────┐{Colors.RESET}")
    for line in registry_summary.splitlines():
        print(f"  {Colors.DIM}{line}{Colors.RESET}")
    print(f"{Colors.BLUE}└──────────────────────────────────────────────────────────────────┘{Colors.RESET}\n")


def print_execution_result(result: "ExecutionResult"):
    """Displays structured execution feedback."""
    if result.success:
        print(
            f"{_AGENT_COLORS['Executor']}[Executor]{Colors.RESET} "
            f"{Colors.GREEN}✓ Success{Colors.RESET} in {result.duration}s"
        )
        if result.stdout:
            preview = result.stdout[:300].rstrip()
            print(f"{Colors.DIM}    stdout preview: {preview}...{Colors.RESET}" if len(result.stdout) > 300 else f"{Colors.DIM}    {result.stdout.strip()}{Colors.RESET}")
    else:
        print(
            f"{_AGENT_COLORS['Executor']}[Executor]{Colors.RESET} "
            f"{Colors.RED}✗ Failed{Colors.RESET} (exit {result.exit_code}) in {result.duration}s"
        )
        print(f"{Colors.DIM}    error_type:    {result.error_type.value}{Colors.RESET}")
        print(f"{Colors.DIM}    error_message: {result.error_message[:200]}{Colors.RESET}")
        if result.error_line:
            print(f"{Colors.DIM}    line:          {result.error_line}{Colors.RESET}")
        if result.file:
            print(f"{Colors.DIM}    file:          {result.file}{Colors.RESET}")


def print_observability_summary(state: "AgentState"):
    """Prints a full observability report: retries, errors, step outcomes."""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}┌─ Observability Report ───────────────────────────────────────────┐{Colors.RESET}")
    print(f"  {Colors.DIM}Total Execution Attempts:{Colors.RESET} {state.total_execution_attempts}")
    print(f"  {Colors.DIM}Total Repair Cycles:     {Colors.RESET} {state.repair_attempts}")
    print(f"  {Colors.DIM}Steps Completed:         {Colors.RESET} {len(state.step_history)}/{len(state.plan)}")

    if state.step_telemetry:
        print(f"\n  {Colors.BOLD}Step Telemetry:{Colors.RESET}")
        for tel in state.step_telemetry:
            status_color = Colors.GREEN if tel.status.value == "success" else Colors.RED
            errs = ", ".join(tel.error_categories) or "none"
            print(
                f"    Step {tel.step_index + 1}: "
                f"{status_color}{tel.status.value}{Colors.RESET} | "
                f"attempts={tel.attempts} | errors=[{errs}] | {tel.duration_seconds:.2f}s"
            )

    if state.token_metrics.tokens_by_node:
        print(f"\n  {Colors.BOLD}Tokens by Node:{Colors.RESET}")
        for node, tokens in state.token_metrics.tokens_by_node.items():
            calls = state.token_metrics.calls_by_node.get(node, 0)
            print(f"    {node:<18}: {tokens:>5} tokens ({calls} calls)")

    print(f"{Colors.YELLOW}└──────────────────────────────────────────────────────────────────┘{Colors.RESET}")


def print_token_summary(summary: Dict[str, Any]):
    llm_calls         = summary.get("llm_calls", 0)
    prompt_tokens     = summary.get("prompt_tokens", 0)
    completion_tokens = summary.get("completion_tokens", 0)
    total_tokens      = summary.get("total_tokens", prompt_tokens + completion_tokens)
    latency           = summary.get("total_latency_seconds", 0.0)

    print(f"\n{Colors.BOLD}{Colors.CYAN}┌─ Token Usage & Performance ──────────────────────────────────────┐{Colors.RESET}")
    print(f"  {Colors.DIM}Total LLM Calls:    {Colors.RESET} {llm_calls}")
    print(f"  {Colors.DIM}Prompt Tokens:      {Colors.RESET} {prompt_tokens:,}")
    print(f"  {Colors.DIM}Completion Tokens:  {Colors.RESET} {completion_tokens:,}")
    print(f"  {Colors.BOLD}Total Tokens:       {Colors.RESET} {Colors.GREEN}{total_tokens:,}{Colors.RESET}")
    print(f"  {Colors.DIM}Total Latency:      {Colors.RESET} {latency}s")
    print(f"{Colors.CYAN}└──────────────────────────────────────────────────────────────────┘{Colors.RESET}\n")
