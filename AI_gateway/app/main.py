"""
AI Gateway — Production‑grade FastAPI application
==================================================
Stack:
  - FastAPI (REST API)
  - Groq (LLM — open‑source models like LLaMA 3)
  - Prometheus (metrics scraping via /metrics)
  - Guardrails (input/output safety middleware)
"""

from email.policy import default
import os
import time
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from dotenv import load_dotenv

from litellm import acompletion, completion_cost
from litellm.caching import Cache
import litellm
litellm.suppress_debug_info = True

import warnings
warnings.filterwarnings("ignore")
logging.getLogger("LiteLLM").setLevel(logging.ERROR)
litellm.cache = Cache(type="local")

# ---------------------------------------------------------------------------
# Optional Groq import (fails gracefully if not installed)
# ---------------------------------------------------------------------------
try:
    from groq import Groq as GroqClient
except ImportError:
    GroqClient = None

# ---------------------------------------------------------------------------
# Optional Guardrails import (fails gracefully if not installed)
# ---------------------------------------------------------------------------
try:
    import guardrails as grd
    _GUARDRAILS_AVAILABLE = True
except ImportError:
    _GUARDRAILS_AVAILABLE = False

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("ai_gateway")

# ---------------------------------------------------------------------------
# Settings (read from .env)
# ---------------------------------------------------------------------------
class Settings(BaseSettings):
    groq_api_key: str = ""
    groq_llama_model: str = "llama3-8b-8192"
    groq_gpt_model: str = ""
    groq_qwen_model: str = ""
    guardrails_enabled: bool = True
    app_env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
REQUEST_COUNT = Counter(
    "ai_gateway_request_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "ai_gateway_request_latency_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
)

LLM_TOKEN_COUNT = Counter(
    "ai_gateway_llm_tokens_total",
    "Total tokens consumed by LLM calls",
    ["model"],
)

GUARDRAIL_VIOLATIONS = Counter(
    "ai_gateway_guardrail_violations_total",
    "Total number of guardrail violations detected",
)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Gateway",
    description="Production‑grade AI gateway with Groq LLM, Guardrails, and Prometheus monitoring.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Prometheus middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
    ).inc()

    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)
    return response

# ---------------------------------------------------------------------------
# Guardrails helper
# ---------------------------------------------------------------------------
BLOCKED_PHRASES = [
    "ignore previous instructions",
    "jailbreak",
    "override system prompt",
    "act as dan",
]

def run_guardrails(text: str, direction: str = "input") -> str:
    """
    Simple built-in guardrail check.
    Replace / extend with the full guardrails-ai library when needed.
    """
    lower = text.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase in lower:
            GUARDRAIL_VIOLATIONS.inc()
            logger.warning("Guardrail violation detected in %s: '%s'", direction, phrase)
            raise HTTPException(
                status_code=400,
                detail=f"Request blocked by guardrails ({direction}): policy violation detected.",
            )
    return text

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    system_prompt: str = "You are a helpful AI assistant."
    temperature: float = 0.7
    max_tokens: int = 512

class ChatResponse(BaseModel):
    response: str
    model: str
    tokens_used: int | None = None

# ---------------------------------------------------------------------------
# Models + Unified APIs + Fallback + Caching (as it call acompletion func instead of completion, we can't cache here, that why I have cached in globally[at line 36])
# ---------------------------------------------------------------------------
class Models:
    def __init__(self):
        self.model_qwen = settings.groq_qwen_model
        self.model_llama = settings.groq_llama_model
        self.model_gpt = settings.groq_gpt_model

    async def model_call(self, payload, model):
        model_response = await acompletion(
            model=f"groq/{model}",
            api_key=settings.groq_api_key,
            messages=[
                {"role": "system", "content": payload.system_prompt},
                {"role": "user", "content": payload.message},
            ],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            fallbacks = [
                f"groq/{self.model_gpt}",
                f"groq/{self.model_llama}"
            ]
        )

        return model_response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Observability"])
async def health_check():
    """Liveness probe — returns 200 when the service is up."""
    return {
        "status": "ok",
        "env": settings.app_env,
        "groq_configured": bool(settings.groq_api_key),
        "guardrails_enabled": settings.guardrails_enabled
    }

@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/chat", response_model=ChatResponse, tags=["AI Gateway"])
async def chat_endpoint(payload: ChatRequest):
    """
    Chat endpoint — forwards the user message to Groq (LLaMA 3 by default),
    applies input/output guardrails, and returns the generated response.
    """
    logger.info("Incoming /chat request | message_len=%d", len(payload.message))

    # ── Input guardrails ──────────────────────────────────────────────────
    if settings.guardrails_enabled:
        run_guardrails(payload.message, direction="input")

    # ── LLM call ─────────────────────────────────────────────────────────
    if not GroqClient:
        raise HTTPException(status_code=503, detail="Groq client is not installed.")
    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured.")
    model_call = Models()
    t1 = time.time()
    try:
        default_model = model_call.model_qwen
        res_completion = await model_call.model_call(payload, default_model)
    except Exception as exc:
        logger.error("Groq API error: %s", exc)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}")

    response_text = res_completion.choices[0].message.content
    tokens_used = getattr(res_completion.usage, "total_tokens", None)
    cost = completion_cost(model = f"groq/{res_completion.model}" , completion_response=res_completion)
    logger.info(f"Cost: ${cost}, Time: {time.time() - t1}")

    # Track token usage
    if tokens_used:
        LLM_TOKEN_COUNT.labels(model=res_completion.model).inc(tokens_used)

    # ── Output guardrails ─────────────────────────────────────────────────
    if settings.guardrails_enabled:
        run_guardrails(response_text, direction="output")

    logger.info("Response generated | tokens=%s", tokens_used)

    return ChatResponse(
        response=response_text,
        model= res_completion.model,
        tokens_used=tokens_used
    )
