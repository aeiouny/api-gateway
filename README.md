# Cloud-Native API Gateway & Service Mesh

## Project Goal
Build a lightweight API gateway with request routing, authentication, rate limiting, and metrics collection.

# Tech Stack
- **Backend:** Python (FastAPI)
- **Containerization:** Docker
- **Orchestration:** Kubernetes (local via Minikube or Kind)
- **Observability:** OpenTelemetry for tracing


# Commands
Creating python virtual environment: python -m venv <name>

Install FastAPI: pip install fastapi "uvicorn[standard]"

Run locally: uvicorn main:app --reload