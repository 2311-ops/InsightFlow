"""
ai_insights.py
Sends metrics to Llama 3 (via Ollama) and returns AI-generated insights.
"""

import ollama
from typing import Any
from data_processing.metrics import metrics_to_summary


MODEL = "llama3"


def generate_insight(metrics: dict[str, Any]) -> str:
    """
    Given a metrics dict, build a prompt and ask Llama 3
    for business insights and recommendations.
    """
    summary = metrics_to_summary(metrics)

    prompt = f"""You are an expert business analyst AI assistant.

A business has uploaded a dataset. Below are the computed metrics:

{summary}

Please provide:
1. A brief overview of what this data represents
2. Key trends or patterns you can identify
3. Any anomalies or areas of concern
4. Actionable recommendations for the business

Be concise, professional, and data-driven. Use plain English."""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"]


def answer_question(question: str, metrics: dict[str, Any]) -> str:
    """
    Answer a natural language question about the dataset metrics.
    """
    summary = metrics_to_summary(metrics)

    prompt = f"""You are an expert business analyst AI assistant.

Here are the dataset metrics:

{summary}

A user is asking: "{question}"

Answer clearly and concisely based only on the data provided."""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    return response["message"]["content"]
