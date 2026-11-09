# Autonomous Agentic AI System (LangGraph + LangChain + Pydantic + Groq)

A production-grade, collaborative multi-agent execution system built with **LangGraph**, **LangChain**, and **Pydantic v2**, powered strictly by **Groq** for high-speed, lowest-token inference.

---

## 🌟 Architecture (LangGraph StateGraph)

```
                    ┌────────────────────────┐
                    │  User Task / Prompt    │
                    └───────────┬────────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │      guard_node      │
                     │  (Prompt Screening)  │
                     └──────────┬───────────┘
                                │ Safe
                                ▼
                     ┌──────────────────────┐
                     │     planner_node     │
                     │ (Minimal Plan Steps) │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │      coder_node      │
                     │  (Python Synthesis)  │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │    executor_node     │
                     │ (Subprocess Sandbox) │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │    observer_node     │
                     │  (Verification & QA) │
                     └──────────┬───────────┘
                                │
                 ┌──────────────┴──────────────┐
                 │ Failure / Error             │ Success
                 ▼                             ▼
        ┌──────────────────┐         ┌────────────────────┐
        │   repair_node    │         │  synthesizer_node  │
        │  (Self-Healing)  │         │   (Final Answer)   │
        └────────┬─────────┘         └─────────┬──────────┘
                 │                             │
                 └────────► executor_node      ▼
                                              END
```

---

## 🛠️ Stack & Technologies

- **LangGraph**: Orchestrates state transitions, nodes, conditional routing, and the self-healing error recovery loop.
- **LangChain (`langchain-groq`)**: Provides `ChatGroq`, structured messages (`SystemMessage`, `HumanMessage`), and token accounting metadata.
- **Pydantic v2**: Type-safe schemas for `AgentState`, `Plan`, `Observation`, `ExecutionResult`, and `TokenMetrics`.
- **Groq LPU**: Uses official Groq models (default: `qwen/qwen3.8-27b`) requiring only a single `GROQ_API_KEY`.

---

## 📁 Clean Directory Structure

```
/Users/dibyajyotimohanty/My project/ADV_AI/Agent_AI/
├── .env.example              # Example environment configuration (Groq-only)
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── main.py                   # Main launcher
├── cli.py                    # Interactive console & CLI task runner
├── core/
│   ├── __init__.py           # Package exports (AgentGraph, AgentState, schemas)
│   ├── config.py             # Pydantic SystemConfig loading from AI_gateway/.env
│   ├── schemas.py            # Pydantic v2 data models & LangGraph AgentState
│   ├── llm.py                # LangChain ChatGroq initialization & token tracking
│   ├── executor.py           # Subprocess execution sandbox with timeout & error capture
│   ├── ui.py                 # Terminal styling, action badges, code boxes, token tables
│   ├── graph.py              # LangGraph StateGraph workflow definition & conditional routing
│   └── nodes/                # LangGraph node implementations
│       ├── __init__.py
│       ├── guard.py          # Safety verification node
│       ├── planner.py        # Planning node
│       ├── coder.py          # Code synthesis node
│       ├── executor.py       # Code execution node
│       ├── observer.py       # Verification node
│       ├── repair.py         # Self-healing repair node
│       └── synthesizer.py    # Final response synthesis node
└── tests/
    ├── test_components.py    # Unit tests for Pydantic schemas, config & executor
    ├── test_healing.py       # Verified test of the auto-repair loop
    └── test_tasks.py         # End-to-end task tests with LangGraph & ChatGroq
```

---

## ⚡ Environment & Setup

1. **Environment Configuration**:
   The agent automatically reads your key from `../AI_gateway/.env` or a local `.env`:
   ```bash
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=qwen/qwen3.8-27b
   ```

2. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Usage

### 1. Command-Line Task Execution

```bash
# Example 1: Inspect files and folders
python3 cli.py "Check my folders and files in current project and count how many python files exist."

# Example 2: Find the largest file
python3 cli.py "Inspect the AI_gateway folder, find all python files with their line counts, and identify which file has the most lines of code."

# Example 3: Perform calculations or data operations
python3 cli.py "Calculate the first 25 prime numbers and find their sum and average."
```

### 2. Interactive Console Mode

Start an interactive multi-agent chat session:

```bash
python3 main.py
```
Or:
```bash
python3 cli.py
```

### 3. Programmatic Python API

```python
from core import AgentGraph

agent = AgentGraph(
    workspace_dir="/Users/dibyajyotimohanty/My project/ADV_AI"
)

state = agent.run("List all git branches and find uncommitted changes.")

print("Final Answer:\n", state.final_answer)
print("Token Metrics:\n", state.token_metrics.to_dict())
```

---

## 🧪 Testing

Run unit tests:
```bash
python3 tests/test_components.py
```

Run self-healing verification tests:
```bash
python3 tests/test_healing.py
```

Run end-to-end task tests:
```bash
python3 tests/test_tasks.py
```
