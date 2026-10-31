# AI Gateway Microservice

> FastAPI-powered AI Gateway with Groq LPU inference, bidirectional guardrails, and Prometheus/Grafana metrics.

Please refer to the comprehensive guide in the root directory:
👉 **[AI_ENGINEER_GUIDE.md](../AI_ENGINEER_GUIDE.md)**

### Quick Run
```bash
docker-compose up -d
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

