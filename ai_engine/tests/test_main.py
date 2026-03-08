from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main
from data_processing.clean_data import CleanResult
from data_processing.metrics import MetricsReport

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in {"ok", "degraded"}
    if data["status"] == "ok":
        assert "version" in data
        assert "llama3_ready" in data
        assert "available_models" in data
    else:
        assert "error" in data



def test_insights(monkeypatch):
    monkeypatch.setattr(main, "generate_insight", lambda metrics: "dummy")
    r = client.post("/ai/insights", json={"metrics": {"a": 1}})
    assert r.status_code == 200
    assert r.json() == {"insight": "dummy"}


def test_ask(monkeypatch):
    monkeypatch.setattr(
        main,
        "answer_question",
        lambda q, m: {"answer": "answer", "insight_type": "general"},
    )
    r = client.post(
        "/ai/ask", json={"question": "What?", "metrics": {"x": 2}}
    )
    assert r.status_code == 200
    assert r.json()["answer"] == "answer"


def test_process(monkeypatch):
    clean_result = CleanResult(
        df=pd.DataFrame({"sales": [1, 2, 3]}),
        original_rows=3,
        cleaned_rows=3,
        dropped_rows=0,
        duplicates_removed=0,
        columns_parsed=["sales"],
        date_columns=[],
        numeric_columns=["sales"],
        categorical_columns=[],
        warnings=[],
    )

    monkeypatch.setattr(main, "load_and_clean", lambda path: clean_result)
    monkeypatch.setattr(main, "engineer_features", lambda result: result)

    monkeypatch.setattr(
        main,
        "compute_metrics",
        lambda df: MetricsReport(
            summary={"row_count": 3, "column_count": 1},
            trends=[],
            anomalies=[],
            segments=[],
            correlations={},
            raw_metrics={"v": 3, "label": "ok"},
        ),
    )

    monkeypatch.setattr(
        main,
        "generate_insight",
        lambda report: "test insight",
    )

    r = client.post(
        "/ai/process",
        json={"file_path": "foo.csv", "dataset_id": 123},
    )

    assert r.status_code == 200
    payload = r.json()
    assert payload["insight"] == "test insight"
    assert payload["metrics"]["v"] == 3
    assert payload["data_quality"]["original_rows"] == 3
