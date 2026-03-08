# Phase 2
"""
InsightFlow AI Engine
FastAPI service exposing /ai/insights and /ai/ask endpoints.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from data_processing.clean_data import load_and_clean
from data_processing.metrics import compute_metrics
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


class ProcessPayload(BaseModel):
    file_path: str
    dataset_id: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "insightflow-ai"}


@app.post("/ai/process")
async def process_dataset(payload: ProcessPayload):
    try:
        df = load_and_clean(payload.file_path)
        computed = compute_metrics(df)

        serializable_metrics: dict[str, float] = {}
        for key, value in computed.items():
            if isinstance(value, (dict, list, tuple, set)):
                continue
            if isinstance(value, bool):
                continue
            if hasattr(value, "item"):
                try:
                    value = value.item()
                except Exception:
                    continue
            try:
                serializable_metrics[key] = float(value)
            except (TypeError, ValueError):
                continue

        insight = generate_insight(serializable_metrics)
        return {"metrics": serializable_metrics, "insight": insight}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
