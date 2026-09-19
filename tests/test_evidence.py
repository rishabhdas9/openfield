from pathlib import Path

from openfield.evidence import ingest_demo, lexical_search, open_database, provenance_path
from openfield.models import Report


def load_expected_report() -> Report:
    return Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text())


def test_ingestion_is_idempotent_and_every_edge_has_provenance(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    for _ in range(2):
        ingest_demo(
            connection,
            Path("src/openfield/corpus/demo.jsonl"),
            Path("examples/httpx_028/environment.json"),
            load_expected_report(),
        )
    assert connection.execute("SELECT count(*) FROM chunks").fetchone()[0] == 14
    assert connection.execute("SELECT count(*) FROM edges WHERE chunk_id IS NULL").fetchone()[0] == 0


def test_lexical_search_filters_package_and_version(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    ingest_demo(
        connection,
        Path("src/openfield/corpus/demo.jsonl"),
        Path("examples/httpx_028/environment.json"),
        load_expected_report(),
    )

    results = lexical_search(connection, "removed proxies", "httpx", {"0.28.0"}, limit=6)
    assert results[0].id == "httpx-0.28.0-client-arguments-removed"
    assert all(result.package == "httpx" and result.version == "0.28.0" for result in results)


def test_fts_query_text_cannot_change_sql(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    ingest_demo(
        connection,
        Path("src/openfield/corpus/demo.jsonl"),
        Path("examples/httpx_028/environment.json"),
        load_expected_report(),
    )
    assert lexical_search(connection, '\" OR 1=1 --', "httpx", {"0.28.0"}, limit=6) == []
    assert connection.execute("SELECT count(*) FROM chunks").fetchone()[0] == 14


def test_provenance_path_connects_starlette_to_httpx_removal(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    ingest_demo(
        connection,
        Path("src/openfield/corpus/demo.jsonl"),
        Path("examples/httpx_028/environment.json"),
        load_expected_report(),
    )
    path = provenance_path(
        connection,
        "release:starlette:0.36.3",
        "parameter:httpx.Client:app",
        max_depth=3,
        allowed_relations={"contains", "passes"},
    )
    assert path == [
        "release:starlette:0.36.3",
        "symbol:starlette.TestClient",
        "parameter:httpx.Client:app",
    ]
