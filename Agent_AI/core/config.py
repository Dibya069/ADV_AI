"""
Configuration for Agent_AI
Loads environment variables from AI_gateway/.env or local .env
Configured strictly for Groq LLMs.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Search locations for .env
CURRENT_DIR = Path(__file__).resolve().parent
AGENT_DIR = CURRENT_DIR.parent
PROJECT_DIR = AGENT_DIR.parent
AI_GATEWAY_ENV = PROJECT_DIR / "AI_gateway" / ".env"
LOCAL_ENV = AGENT_DIR / ".env"

if LOCAL_ENV.exists():
    load_dotenv(dotenv_path=LOCAL_ENV)
elif AI_GATEWAY_ENV.exists():
    load_dotenv(dotenv_path=AI_GATEWAY_ENV)
else:
    load_dotenv()


class SystemConfig(BaseModel):
    """Pydantic model for system configuration."""
    groq_api_key: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    # Official, fast Groq model
    groq_model: str = Field(default_factory=lambda: os.getenv("GROQ_MODEL", os.getenv("GROQ_QWEN_MODEL", "qwen/qwen3.8-27b")))
    
    # Execution & Safety Settings
    workspace_root: str = Field(default_factory=lambda: os.getenv("WORKSPACE_ROOT", str(PROJECT_DIR)))
    max_repair_attempts: int = Field(default_factory=lambda: int(os.getenv("MAX_REPAIR_ATTEMPTS", "3")))
    execution_timeout: float = Field(default_factory=lambda: float(os.getenv("EXECUTION_TIMEOUT", "45.0")))
    guardrails_enabled: bool = Field(default_factory=lambda: os.getenv("GUARDRAILS_ENABLED", "true").lower() in ("true", "1", "yes"))
    
    # Token optimization settings
    max_traceback_lines: int = 15
    max_output_chars: int = 2500

    def validate_api_key(self) -> bool:
        if not self.groq_api_key:
            raise ValueError(
                f"GROQ_API_KEY is not set. Please add it to {AI_GATEWAY_ENV} or {LOCAL_ENV}"
            )
        return True


config = SystemConfig()
