#!/usr/bin/env python3
"""
Agent CLI
Interactive terminal and command-line execution for the LangGraph agent system.
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core import AgentGraph, config
from core.ui import print_header, Colors


def run_single_task(task_str: str, workspace: str, max_retries: int):
    orchestrator = AgentGraph(
        workspace_dir=workspace,
        max_repair_attempts=max_retries,
    )
    state = orchestrator.run(task_str)

    print(f"\n{Colors.BOLD}{Colors.GREEN}══════════════════════════════════════════════════════════════════════{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}  FINAL ANSWER / OUTCOME                                              {Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}══════════════════════════════════════════════════════════════════════{Colors.RESET}\n")
    print(state.final_answer or "No answer synthesized.")
    print(f"\n{Colors.DIM}Status: {'Completed' if state.is_completed else 'Incomplete'}{Colors.RESET}\n")


def interactive_mode(workspace: str, max_retries: int):
    print_header("Agent_AI — LangGraph & Groq Console")
    print(f"{Colors.CYAN}Workspace:{Colors.RESET} {workspace}")
    print(f"{Colors.CYAN}Groq Model:{Colors.RESET} {config.groq_model}")
    print(f"{Colors.DIM}Type your task below. Type 'exit', 'quit', or 'q' to stop.\n{Colors.RESET}")

    orchestrator = AgentGraph(
        workspace_dir=workspace,
        max_repair_attempts=max_retries,
    )

    while True:
        try:
            prompt = input(f"\n{Colors.BOLD}{Colors.CYAN}Task > {Colors.RESET}").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit", "q"):
                print(f"{Colors.GREEN}Goodbye!{Colors.RESET}")
                break

            state = orchestrator.run(prompt)
            print(f"\n{Colors.BOLD}{Colors.GREEN}── Final Result ───────────────────────────────────────────────────────{Colors.RESET}\n")
            print(state.final_answer or "No answer synthesized.")

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Operation cancelled by user.{Colors.RESET}")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {e}{Colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Multi-Agent AI System powered by LangGraph, LangChain, and Groq",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "task",
        nargs="*",
        help="The task instruction for the agentic system. If omitted, starts interactive console.",
    )
    parser.add_argument(
        "-w", "--workspace",
        default=config.workspace_root,
        help="Working directory path for code execution (default: workspace root).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=config.max_repair_attempts,
        help=f"Maximum auto-repair attempts on error (default: {config.max_repair_attempts}).",
    )

    args = parser.parse_args()

    if args.task:
        task_str = " ".join(args.task)
        print_header("Agent_AI — Autonomous Task Execution (LangGraph)")
        run_single_task(task_str, workspace=args.workspace, max_retries=args.retries)
    else:
        interactive_mode(workspace=args.workspace, max_retries=args.retries)


if __name__ == "__main__":
    main()
