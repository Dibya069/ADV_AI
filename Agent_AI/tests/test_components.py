"""
Component Tests — v2 Architecture
Tests structured ExecutionResult, ToolRegistry, error classification,
observability metrics, and core utilities.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tempfile
import os

from core.config import config
from core.schemas import (
    AgentState, ExecutionResult, Observation, Plan, TokenMetrics,
    ToolRegistry, StepTelemetry, StepStatus, ErrorCategory,
)
from core.executor import CodeExecutor


def test_config_loads():
    assert config.groq_api_key, "GROQ_API_KEY must be set"
    assert config.groq_model, "groq_model must be set"
    print(f"  ✓ Config loaded — model: {config.groq_model}")


def test_structured_execution_result():
    # Test auto-classification of SyntaxError
    r = ExecutionResult.from_process(
        stdout="",
        stderr='  File "tmp.py", line 100\nSyntaxError: unterminated triple-quoted string literal',
        exit_code=1,
        duration=0.1,
        code='x = """broken',
        file="tmp.py",
        attempt=1,
    )
    assert r.success is False
    assert r.error_type == ErrorCategory.SYNTAX
    assert r.error_line == 100
    assert "tmp.py" in r.file

    ctx = r.to_repair_context()
    assert ctx["error_type"] == "SyntaxError"
    assert ctx["line"] == 100
    assert ctx["success"] is False
    print(f"  ✓ ExecutionResult — SyntaxError classified, line={r.error_line}")

    # Test ImportError
    r2 = ExecutionResult.from_process(
        stdout="", stderr="ModuleNotFoundError: No module named 'bogus'",
        exit_code=1, duration=0.05, code="import bogus", file="t.py", attempt=1,
    )
    assert r2.error_type == ErrorCategory.IMPORT
    print(f"  ✓ ExecutionResult — ImportError classified")

    # Test timeout
    r3 = ExecutionResult.from_process(
        stdout="", stderr="Execution timed out after 45 seconds.",
        exit_code=-1, duration=45.0, code="while True: pass", file="t.py", attempt=1,
    )
    assert r3.error_type == ErrorCategory.TIMEOUT
    print(f"  ✓ ExecutionResult — TimeoutError classified")


def test_tool_registry():
    reg = ToolRegistry.default("/my/workspace")
    assert reg.can("execute_python") is True
    assert reg.can("read_file") is True
    assert reg.can("network_request") is False
    assert reg.can("shell_command") is False
    assert reg.needs_approval("delete_file") is True
    assert reg.needs_approval("execute_python") is False

    summary = reg.summary()
    assert "execute_python" in summary
    assert "✓ available" in summary
    assert "✗ unavailable" in summary
    print(f"  ✓ ToolRegistry — 7 capabilities, approval gates correct")


def test_token_metrics_per_node():
    metrics = TokenMetrics()
    metrics.add_usage({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}, latency=1.0, node="planner")
    metrics.add_usage({"prompt_tokens": 200, "completion_tokens": 100, "total_tokens": 300}, latency=2.0, node="coder")
    metrics.add_usage({"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}, latency=0.5, node="verifier")

    assert metrics.total_tokens == 530
    assert metrics.llm_calls == 3
    assert metrics.calls_by_node["planner"] == 1
    assert metrics.tokens_by_node["coder"] == 300
    d = metrics.to_dict()
    assert "calls_by_node" in d
    assert "tokens_by_node" in d
    print(f"  ✓ TokenMetrics — per-node tracking: {d['tokens_by_node']}")


def test_executor_success():
    executor = CodeExecutor(working_dir=tempfile.gettempdir())
    result = executor.execute_python('print("hello agent")\nprint("count: 42")', attempt=1)
    assert result.success is True
    assert result.exit_code == 0
    assert "hello agent" in result.stdout
    assert result.duration > 0
    assert result.error_type == ErrorCategory.UNKNOWN  # No error
    print(f"  ✓ Executor success in {result.duration}s")


def test_executor_failure_structured():
    executor = CodeExecutor(working_dir=tempfile.gettempdir())
    result = executor.execute_python('x = 1/0', attempt=1)
    assert result.success is False
    assert result.exit_code != 0
    assert result.error_type == ErrorCategory.RUNTIME
    assert result.error_message  # Should contain "ZeroDivisionError" or similar
    ctx = result.to_repair_context()
    assert "exit_code" in ctx
    assert "error_type" in ctx
    print(f"  ✓ Executor failure structured — type={result.error_type}, msg={result.error_message[:60]}")


def test_agent_state_complete():
    reg = ToolRegistry.default("/ws")
    state = AgentState(
        task="test task",
        workspace_dir="/ws",
        tool_registry=reg,
        plan=["step 1", "step 2"],
    )
    assert state.task == "test task"
    assert state.tool_registry.can("execute_python") is True
    assert len(state.plan) == 2
    assert state.total_execution_attempts == 0
    assert state.pending_approval is False
    print(f"  ✓ AgentState — all fields initialised correctly")


if __name__ == "__main__":
    tests = [
        test_config_loads,
        test_structured_execution_result,
        test_tool_registry,
        test_token_metrics_per_node,
        test_executor_success,
        test_executor_failure_structured,
        test_agent_state_complete,
    ]
    print(f"\n{'='*60}")
    print(f"  Running {len(tests)} Component Tests — v2 Architecture")
    print(f"{'='*60}\n")
    passed = 0
    for t in tests:
        try:
            print(f"[TEST] {t.__name__}")
            t()
            passed += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{len(tests)} passed")
    print(f"{'='*60}\n")
    sys.exit(0 if passed == len(tests) else 1)
