# Phase 3
"""LLM integration for business insights and Q&A."""

from __future__ import annotations

from collections.abc import Generator

import ollama

from data_processing.metrics import MetricsReport, metrics_to_summary


SYSTEM_PROMPT = (
    "You are InsightFlow's AI analyst - an expert business intelligence assistant.\n"
    "Your role is to analyze business metrics and provide clear, actionable insights.\n"
    "Guidelines:\n"
    "- Be specific and data-driven, always reference actual numbers\n"
    "- Use plain business language, avoid jargon\n"
    "- Structure your responses with clear sections\n"
    "- Flag risks and anomalies prominently\n"
    "- Always end with 2-3 concrete, prioritized action items\n"
    "- Keep responses concise but complete (aim for 200-400 words)"
)


def _build_insight_prompt(report: MetricsReport) -> str:
    """Build a structured prompt for insight generation."""
    summary = metrics_to_summary(report)

    instructions = [
        "Use markdown and respond with exactly these sections:",
        "**📊 Overview**",
        "**📈 Trends**",
        "**⚠️ Anomalies & Risks**",
        "**✅ Recommendations**",
    ]

    if report.trends:
        instructions.append("Analyze the growth trends shown above.")
    if report.anomalies:
        instructions.append("Address the anomalies detected.")
    if report.segments:
        instructions.append("Also include a **🏆 Top Performers** section.")

    return f"Dataset summary:\n\n{summary}\n\n" + "\n".join(instructions)


def generate_insight(report: MetricsReport) -> str:
    """Generate a full AI insight response from a metrics report."""
    prompt = _build_insight_prompt(report)
    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]


def stream_insight(report: MetricsReport) -> Generator[str, None, None]:
    """Stream AI insight tokens from Ollama."""
    prompt = _build_insight_prompt(report)
    stream = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    for chunk in stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield content


def _classify_question(question: str) -> str:
    """Classify a natural-language question into an insight type."""
    q = question.lower()

    if any(k in q for k in ["compare", "vs", "versus", "difference", "better", "worse", "top", "best", "worst"]):
        return "comparison"
    if any(k in q for k in ["trend", "growth", "decline", "increase", "decrease", "over time", "month", "quarter"]):
        return "trend"
    if any(k in q for k in ["anomaly", "unusual", "outlier", "spike", "drop", "sudden", "weird"]):
        return "anomaly"
    if any(k in q for k in ["recommend", "suggest", "should", "improve", "action", "what to do"]):
        return "recommendation"
    return "general"


def answer_question(question: str, report: MetricsReport) -> dict[str, str]:
    """Answer a user question using metrics context and a focused hint."""
    q_type = _classify_question(question)
    context_hints = {
        "comparison": "Focus on ranking and side-by-side differences using exact values.",
        "trend": "Focus on direction over time and quantify changes clearly.",
        "anomaly": "Focus on unusual values, risk implications, and probable causes.",
        "recommendation": "Focus on practical next steps prioritized by impact.",
        "general": "Provide a concise data-backed explanation in plain business language.",
    }

    summary = metrics_to_summary(report)
    hint = context_hints[q_type]
    prompt = (
        f"Dataset summary:\n\n{summary}\n\n"
        f"Question: {question}\n"
        f"Focus hint: {hint}\n"
        "Keep the answer under 200 words."
    )

    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    response_text = response["message"]["content"]
    return {"answer": response_text, "insight_type": q_type}


def explain_anomaly(column: str, anomaly_values: list[float], context_metrics: dict) -> str:
    """Explain why anomaly values are unusual and what they might mean."""
    mean_key = f"{column}_mean"
    median_key = f"{column}_median"
    std_key = f"{column}_std"

    prompt = (
        f"Column: {column}\n"
        f"Anomaly values: {anomaly_values}\n"
        f"Context stats: mean={context_metrics.get(mean_key)}, "
        f"median={context_metrics.get(median_key)}, std={context_metrics.get(std_key)}\n\n"
        "Explain in 3-4 sentences: why these values are anomalous, "
        "possible business causes, and whether this is likely a data error or real event."
    )

    response = ollama.chat(
        model="llama3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]

