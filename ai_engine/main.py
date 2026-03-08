# Phase 3
"""InsightFlow AI Engine FastAPI application."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import ollama

from data_processing.clean_data import load_and_clean
from data_processing.feature_engineering import engineer_features
from data_processing.metrics import MetricsReport, compute_metrics
from llm_integration.ai_insights import (
    answer_question,
    explain_anomaly,
    generate_insight,
    stream_insight,
)

app = FastAPI(title="InsightFlow AI Engine", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MetricsPayload(BaseModel):
    """Payload containing flat metrics for AI insight generation."""

    metrics: dict[str, Any]


class QuestionPayload(BaseModel):
    """Payload for question answering over metrics."""

    question: str
    metrics: dict[str, Any]


class ProcessPayload(BaseModel):
    """Payload for dataset processing pipeline."""

    file_path: str
    dataset_id: int


class AnomalyPayload(BaseModel):
    """Payload for anomaly explanation requests."""

    column: str
    anomaly_values: list[float]
    context_metrics: dict[str, Any]


class StreamPayload(BaseModel):
    """Payload for insight streaming endpoint."""

    metrics: dict[str, Any]


def _dict_to_report(metrics: dict[str, Any]) -> MetricsReport:
    """Create a minimal MetricsReport from a flat metrics dictionary."""
    return MetricsReport(
        summary=metrics,
        trends=[],
        anomalies=[],
        segments=[],
        correlations={},
        raw_metrics=metrics,
    )


def _to_serializable_flat(metrics: dict[str, Any]) -> dict[str, int | float | str | bool]:
    """Filter metrics to scalar JSON-serializable primitives only."""
    serializable: dict[str, int | float | str | bool] = {}
    for key, value in metrics.items():
        if isinstance(value, (list, dict, tuple, set)):
            continue
        if hasattr(value, "item"):
            try:
                value = value.item()
            except Exception:
                continue
        if isinstance(value, (int, float, str, bool)):
            serializable[key] = value
    return serializable


@app.get("/health")
def health() -> dict[str, Any]:
    """Return service and Ollama availability status."""
    try:
        listing = ollama.list()
        models = listing.get("models", []) if isinstance(listing, dict) else []
        available_models = [
            m.get("name", "") for m in models if isinstance(m, dict) and m.get("name")
        ]
        return {
            "status": "ok",
            "version": "0.3.0",
            "llama3_ready": any("llama3" in name for name in available_models),
            "available_models": available_models,
        }
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


@app.post("/ai/process")
async def process_dataset(payload: ProcessPayload) -> dict[str, Any]:
    """Run clean, feature engineering, metrics, and insight pipeline."""
    try:
        clean_result = load_and_clean(payload.file_path)
        enriched_result = engineer_features(clean_result)
        report = compute_metrics(enriched_result)
        insight = generate_insight(report)

        anomalies = [
            {
                "column": a.column,
                "method": a.method,
                "count": a.count,
                "pct": a.pct,
            }
            for a in report.anomalies
        ]

        trends = [
            {
                "column": t.column,
                "growth_pct": t.growth_pct,
                "direction": t.direction,
                "data_points": t.data_points,
            }
            for t in report.trends
        ]

        segments = [
            {
                "group_column": s.group_column,
                "metric_column": s.metric_column,
                "top_segment": s.top_segment,
                "segments": s.segments[:10],
            }
            for s in report.segments
        ]

        return {
            "metrics": _to_serializable_flat(report.raw_metrics),
            "insight": insight,
            "anomalies": anomalies,
            "trends": trends,
            "segments": segments,
            "data_quality": {
                "original_rows": enriched_result.original_rows,
                "cleaned_rows": enriched_result.cleaned_rows,
                "duplicates_removed": enriched_result.duplicates_removed,
                "warnings": enriched_result.warnings,
            },
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ai/insights")
async def get_insights(payload: MetricsPayload) -> dict[str, str]:
    """Generate AI insights from flat metrics input."""
    try:
        report = _dict_to_report(payload.metrics)
        insight = generate_insight(report)
        return {"insight": insight}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ai/ask")
async def ask_question(payload: QuestionPayload) -> dict[str, str]:
    """Answer natural-language questions based on provided metrics."""
    try:
        report = _dict_to_report(payload.metrics)
        answer = answer_question(payload.question, report)
        return answer
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ai/anomaly")
async def anomaly_explanation(payload: AnomalyPayload) -> dict[str, str]:
    """Generate a concise explanation for anomaly values."""
    try:
        explanation = explain_anomaly(
            payload.column,
            payload.anomaly_values,
            payload.context_metrics,
        )
        return {"explanation": explanation, "column": payload.column}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ai/stream")
async def stream_ai_insight(payload: StreamPayload) -> StreamingResponse:
    """Stream AI insight tokens as server-sent events."""

    def event_stream():
        try:
            report = _dict_to_report(payload.metrics)
            for token in stream_insight(report):
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5001, reload=True)

