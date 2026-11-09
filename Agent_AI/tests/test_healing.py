"""
Self-Healing and Repair Verification Test
Tests that when flawed code is generated, the observer detects it,
the repair node fixes it, and re-execution succeeds.
"""

import sys
import unittest
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

from core.schemas import AgentState, ExecutionResult, Observation
from core.executor import CodeExecutor
from core.nodes.observer import observer_node
from core.nodes.repair import repair_node


class TestSelfHealingLoop(unittest.TestCase):
    def test_repair_flawed_code(self):
        task = "Read a non-existent file 'config_missing.json', but if it does not exist, return a dict {'mode': 'default', 'version': 1} and save it, then print it."
        step = "Attempt to read 'config_missing.json' or create default fallback and output JSON"

        flawed_code = (
            "import json\n"
            "# Flawed code that forgets error handling\n"
            "with open('config_missing_test_nonexistent.json', 'r') as f:\n"
            "    data = json.load(f)\n"
            "print(json.dumps(data))\n"
        )

        state = AgentState(
            task=task,
            plan=[step],
            current_code=flawed_code,
            workspace_dir=str(AGENT_DIR),
        )

        # 1. Execute flawed code
        executor = CodeExecutor(working_dir=state.workspace_dir)
        state.last_execution = executor.execute_python(flawed_code)
        self.assertFalse(state.last_execution.success)

        # 2. Observe failure
        state = observer_node(state)
        self.assertFalse(state.last_observation.is_success)

        # 3. Repair node fixes code
        state = repair_node(state)
        self.assertNotEqual(state.current_code, flawed_code)
        self.assertEqual(state.repair_attempts, 1)

        # 4. Re-execute repaired code
        state.last_execution = executor.execute_python(state.current_code)
        self.assertTrue(state.last_execution.success, f"Repaired code should succeed! Stderr: {state.last_execution.stderr}")

        # 5. Re-observe
        state = observer_node(state)
        self.assertTrue(state.last_observation.is_success)
        self.assertIn("default", state.last_execution.stdout.lower() + state.last_observation.summary.lower())


if __name__ == "__main__":
    unittest.main()
