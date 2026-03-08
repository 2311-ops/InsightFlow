"""
InsightFlow AI Engine
FastAPI service exposing /ai/insights and /ai/ask endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm_integration.ai_insights import generate_insight, answer_question

app = FastAPI(title="InsightFlow AI Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MetricsPayload(BaseModel):
    metrics: dict


class QuestionPayload(BaseModel):
    question: str
    metrics: dict


@app.get("/health")
def health():
    return {"status": "ok", "service": "insightflow-ai"}


@app.post("/ai/insights")
async def get_insights(payload: MetricsPayload):
    """Generate AI insights from computed metrics."""
    try:
        insight = generate_insight(payload.metrics)
        return {"insight": insight}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/ask")
async def ask_question(payload: QuestionPayload):
    """Answer a natural language question about the data."""
    try:
        answer = answer_question(payload.question, payload.metrics)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
