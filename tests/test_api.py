from pathlib import Path

from fastapi.testclient import TestClient

from openfield.api import create_app
from openfield.evidence import ingest_demo, open_database
from openfield.models import Report


def seeded_database(tmp_path: Path) -> Path:
    database = tmp_path / "evidence.db"
    connection = open_database(database)
    report = Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text())
    ingest_demo(
        connection,
        Path("src/openfield/corpus/demo.jsonl"),
        Path("examples/httpx_028/environment.json"),
        report,
    )
    connection.close()
    return database


def test_health_and_deterministic_ask(tmp_path: Path) -> None:
    client = TestClient(create_app(seeded_database(tmp_path)))
    assert client.get("/healthz").json() == {"status": "ok"}

    response = client.post(
        "/ask",
        json={
            "question": "What was removed in HTTPX 0.28.0?",
            "retrieval": "lexical",
            "packages": ["httpx"],
            "versions": ["0.28.0"],
            "generate": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert body["claims"][0]["citation_ids"] == ["httpx-0.28.0-client-arguments-removed"]


def test_api_refuses_cloud_generation_without_explicit_server_enablement(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(seeded_database(tmp_path), allow_cloud=False))
    response = client.post(
        "/ask",
        json={
            "question": "What changed?",
            "retrieval": "lexical",
            "packages": ["httpx"],
            "versions": ["0.28.0"],
            "generate": True,
        },
    )
    assert response.status_code == 403
