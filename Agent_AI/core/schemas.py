"""
Pydantic Schemas for Agent_AI
Defines state schemas, structured execution feedback, tool capability registry,
observability metrics, and production-grade workflow state.
"""

from __future__ import annotations

import re
import traceback as tb
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ErrorCategory(str, Enum):
    SYNTAX      = "SyntaxError"
    RUNTIME     = "RuntimeError"
    IMPORT      = "ImportError"
    TIMEOUT     = "TimeoutError"
    PERMISSION  = "PermissionError"
    ASSERTION   = "AssertionError"
    OUTPUT      = "OutputVerificationError"
    UNKNOWN     = "UnknownError"


class StepStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    SUCCESS  = "success"
    FAILED   = "failed"
    SKIPPED  = "skipped"


# ---------------------------------------------------------------------------
# Tool Capability Registry
# ---------------------------------------------------------------------------

class ToolCapability(BaseModel):
    """Describes a single tool/capability available to agents."""
    name: str
    description: str
    available: bool = True
    requires_approval: bool = False   # True for destructive / external ops


class ToolRegistry(BaseModel):
    """
    Registry of tools the agent system is authorised to use.
    Agents MUST check this before claiming a capability is unavailable.
    """
    capabilities: List[ToolCapability] = Field(default_factory=list)

    @classmethod
    def default(cls, workspace_dir: str = "") -> "ToolRegistry":
        return cls(capabilities=[
            ToolCapability(
                name="execute_python",
                description="Run a Python script in a subprocess inside the workspace directory.",
                available=True,
                requires_approval=False,
            ),
            ToolCapability(
                name="read_file",
                description=f"Read any file inside the workspace: {workspace_dir or 'configured workspace'}.",
                available=True,
                requires_approval=False,
            ),
            ToolCapability(
                name="write_file",
                description="Write or create a file inside the workspace (non-destructive path only).",
                available=True,
                requires_approval=False,
            ),
            ToolCapability(
                name="list_directory",
                description="List files and folders inside the workspace (recursive or shallow).",
                available=True,
                requires_approval=False,
            ),
            ToolCapability(
                name="delete_file",
                description="Delete a file from the workspace.",
                available=True,
                requires_approval=True,   # Destructive — needs human approval
            ),
            ToolCapability(
                name="network_request",
                description="Make HTTP requests to external URLs (requires sandbox bypass).",
                available=False,          # Disabled in sandbox mode
                requires_approval=True,
            ),
            ToolCapability(
                name="shell_command",
                description="Execute arbitrary shell commands (non-Python).",
                available=False,
                requires_approval=True,
            ),
        ])

    def can(self, name: str) -> bool:
        for cap in self.capabilities:
            if cap.name == name:
                return cap.available
        return False

    def needs_approval(self, name: str) -> bool:
        for cap in self.capabilities:
            if cap.name == name:
                return cap.requires_approval
        return True  # Fail-safe: unknown → needs approval

    def summary(self) -> str:
        lines = []
        for cap in self.capabilities:
            status = "✓ available" if cap.available else "✗ unavailable"
            approval = " [requires approval]" if cap.requires_approval else ""
            lines.append(f"  - {cap.name}: {status}{approval} — {cap.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Structured Execution Result
# ---------------------------------------------------------------------------

def _classify_error(stderr: str, exit_code: int) -> ErrorCategory:
    """Classify error type from stderr text."""
    if not stderr:
        return ErrorCategory.UNKNOWN
    low = stderr.lower()
    if "syntaxerror" in low or "unexpected eof" in low or "unterminated" in low:
        return ErrorCategory.SYNTAX
    if "importerror" in low or "modulenotfounderror" in low:
        return ErrorCategory.IMPORT
    if "permissionerror" in low or "access denied" in low:
        return ErrorCategory.PERMISSION
    if "assertionerror" in low:
        return ErrorCategory.ASSERTION
    if "timeout" in low or exit_code == -1:
        return ErrorCategory.TIMEOUT
    if "runtimeerror" in low or "traceback" in low:
        return ErrorCategory.RUNTIME
    return ErrorCategory.UNKNOWN


def _extract_error_line(stderr: str) -> Optional[int]:
    """Try to extract line number from Python traceback."""
    match = re.search(r"line (\d+)", stderr)
    return int(match.group(1)) if match else None


def _extract_error_message(stderr: str) -> str:
    """Extract the final exception line from a traceback."""
    lines = stderr.strip().splitlines()
    for line in reversed(lines):
        line = line.strip()
        if line and not line.startswith("File") and not line.startswith("Traceback"):
            return line
    return stderr.strip()[:200] if stderr else ""


class ExecutionResult(BaseModel):
    """
    Structured execution feedback passed to Error Analyzer and Repair LLM.
    Contains full context needed to understand and fix failures.
    """
    # Core outcome
    success: bool = True
    exit_code: int = 0

    # Structured error analysis
    error_type: ErrorCategory = ErrorCategory.UNKNOWN
    error_message: str = ""
    error_line: Optional[int] = None
    file: str = ""          # temp filename of executed script

    # Raw streams
    stdout: str = ""
    stderr: str = ""

    # Metadata
    duration: float = 0.0
    code: str = ""
    attempt: int = 1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_process(
        cls,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration: float,
        code: str,
        file: str = "",
        attempt: int = 1,
    ) -> "ExecutionResult":
        """Smart constructor — auto-classifies error from process output."""
        success = exit_code == 0
        error_type = ErrorCategory.UNKNOWN
        error_message = ""
        error_line = None

        if not success:
            error_type = _classify_error(stderr, exit_code)
            error_message = _extract_error_message(stderr)
            error_line = _extract_error_line(stderr)

        return cls(
            success=success,
            exit_code=exit_code,
            error_type=error_type,
            error_message=error_message,
            error_line=error_line,
            file=file,
            stdout=stdout,
            stderr=stderr,
            duration=round(duration, 3),
            code=code,
            attempt=attempt,
        )

    def to_repair_context(self) -> Dict[str, Any]:
        """Serialises to the structured dict passed to the Repair LLM."""
        return {
            "success": self.success,
            "exit_code": self.exit_code,
            "error_type": self.error_type.value,
            "error_message": self.error_message,
            "file": self.file,
            "line": self.error_line,
            "stderr": self.stderr[:1500],
            "stdout": self.stdout[:500],
        }


# ---------------------------------------------------------------------------
# Verification / Observation
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """Semantic verification of execution output — goes beyond exit code 0."""
    is_success: bool = True
    critique: str = ""
    summary: str = ""
    # Detailed check: did the output actually contain the requested artifact?
    expected_artifacts: List[str] = Field(default_factory=list)
    found_artifacts: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------

class Plan(BaseModel):
    """Execution plan generated by the Planner node."""
    objective: str
    steps: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Observability — per-step telemetry
# ---------------------------------------------------------------------------

class StepTelemetry(BaseModel):
    """Telemetry record for one completed or failed execution step."""
    step_index: int
    description: str
    status: StepStatus = StepStatus.PENDING
    attempts: int = 0
    error_categories: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    stdout_summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TokenMetrics(BaseModel):
    """Tracks token consumption across all LangChain / Groq calls."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    llm_calls: int = 0
    total_latency_seconds: float = 0.0

    # Per-node breakdown for observability
    calls_by_node: Dict[str, int] = Field(default_factory=dict)
    tokens_by_node: Dict[str, int] = Field(default_factory=dict)

    def add_usage(self, usage: Dict[str, Any], latency: float = 0.0, node: str = ""):
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        t = usage.get("total_tokens", p + c)
        self.prompt_tokens += p
        self.completion_tokens += c
        self.total_tokens += t
        self.llm_calls += 1
        self.total_latency_seconds += latency
        if node:
            self.calls_by_node[node] = self.calls_by_node.get(node, 0) + 1
            self.tokens_by_node[node] = self.tokens_by_node.get(node, 0) + t

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "llm_calls": self.llm_calls,
            "total_latency_seconds": round(self.total_latency_seconds, 2),
            "calls_by_node": self.calls_by_node,
            "tokens_by_node": self.tokens_by_node,
        }


# ---------------------------------------------------------------------------
# Main Workflow State
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    """
    LangGraph Workflow State.
    Passed between Planner, Coder, Executor, ErrorAnalyzer, Repair, Verifier, Synthesizer.
    Includes full observability, structured error feedback, and human-approval gate.
    """
    # ── Task ────────────────────────────────────────────────────────────────
    task: str
    workspace_dir: str = ""

    # ── Safety ──────────────────────────────────────────────────────────────
    is_safe: bool = True
    safety_reason: str = ""

    # ── Tool Registry ───────────────────────────────────────────────────────
    tool_registry: ToolRegistry = Field(default_factory=ToolRegistry)

    # ── Planning ────────────────────────────────────────────────────────────
    plan: List[str] = Field(default_factory=list)
    current_step_index: int = 0

    # ── Code & Execution ────────────────────────────────────────────────────
    current_code: str = ""
    last_execution: Optional[ExecutionResult] = None
    last_observation: Optional[Observation] = None

    # ── Error Analysis (structured — fed to Repair LLM) ─────────────────────
    last_error_analysis: str = ""   # Natural-language root-cause from ErrorAnalyzer

    # ── Self-Healing loop ───────────────────────────────────────────────────
    repair_attempts: int = 0
    max_repair_attempts: int = 3
    total_execution_attempts: int = 0   # Idempotency: across all repair cycles

    # ── Human Approval Gate ─────────────────────────────────────────────────
    pending_approval: bool = False
    approval_action: str = ""       # What needs approval (e.g., "delete file X")
    approval_granted: bool = False

    # ── History & Telemetry ─────────────────────────────────────────────────
    step_history: List[Dict[str, Any]] = Field(default_factory=list)
    step_telemetry: List[StepTelemetry] = Field(default_factory=list)

    # ── Synthesis ───────────────────────────────────────────────────────────
    final_answer: str = ""
    is_completed: bool = False

    # ── Token Metrics ───────────────────────────────────────────────────────
    token_metrics: TokenMetrics = Field(default_factory=TokenMetrics)
