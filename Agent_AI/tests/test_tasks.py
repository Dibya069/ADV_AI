"""
End-to-End Task Tests for LangGraph Agent
Tests autonomous execution, folder inspection, and self-healing.
"""

import sys
import unittest
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from core import AgentGraph


class TestEndToEndLangGraph(unittest.TestCase):
    def setUp(self):
        self.orchestrator = AgentGraph()

    def test_file_folder_inspection_task(self):
        """Tests user's exact example: inspect files and folders in project."""
        task = "Check my folders and files in current project and count how many python (.py) files exist."
        state = self.orchestrator.run(task)
        
        self.assertTrue(state.is_completed, "Task should complete successfully")
        self.assertGreater(len(state.plan), 0, "Plan should be generated")
        self.assertTrue(bool(state.final_answer), "Final answer should be synthesized")
        self.assertIn(".py", state.final_answer.lower() + " ".join(str(s) for s in state.step_history).lower())
        
        print("\n=== Token Summary for LangGraph File Inspection Task ===")
        metrics = state.token_metrics
        print(f"Total Tokens: {metrics.total_tokens}")
        print(f"Prompt Tokens: {metrics.prompt_tokens}")
        print(f"Completion Tokens: {metrics.completion_tokens}")
        print(f"LLM Calls: {metrics.llm_calls}")
        self.assertGreater(metrics.total_tokens, 0)


if __name__ == "__main__":
    unittest.main()
