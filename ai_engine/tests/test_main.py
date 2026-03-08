from fastapi.testclient import TestClient

from ai_engine import main  # the module you showed me

client = TestClient(main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "insightflow-ai"}


def test_insights(monkeypatch):
    monkeypatch.setattr(main, "generate_insight", lambda metrics: "dummy")
    r = client.post("/ai/insights", json={"metrics": {"a": 1}})
    assert r.status_code == 200
    assert r.json() == {"insight": "dummy"}


def test_ask(monkeypatch):
    monkeypatch.setattr(main, "answer_question", lambda q, m: "answer")
    r = client.post(
        "/ai/ask", json={"question": "What?", "metrics": {"x": 2}}
    )
    assert r.status_code == 200
    assert r.json() == {"answer": "answer"}


def test_process(monkeypatch):
    # stub out the helpers so we don't need a real file or dataframe
    monkeypatch.setattr(main, "load_and_clean", lambda path: {})
    monkeypatch.setattr(main, "compute_metrics", lambda df: {"v": 3, "ok": True})
    monkeypatch.setattr(main, "generate_insight", lambda m: "insight")
    r = client.post(
        "/ai/process",
        json={"file_path": "foo.csv", "dataset_id": 123},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["insight"] == "insight"
    # bools are dropped, numbers turned into floats
    assert body["metrics"] == {"v": 3.0}