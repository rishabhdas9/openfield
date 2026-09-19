from pathlib import Path

import numpy as np
import pytest

from openfield.evidence import ingest_demo, open_database
from openfield.models import Report
from openfield.retrieval import MissingModelError, store_vectors, vector_search


def seeded_database(tmp_path: Path):
    connection = open_database(tmp_path / "evidence.db")
    report = Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text())
    ingest_demo(
        connection,
        Path("src/openfield/corpus/demo.jsonl"),
        Path("examples/httpx_028/environment.json"),
        report,
    )
    return connection


def test_exact_vector_search_is_ranked_and_version_filtered(tmp_path: Path) -> None:
    connection = seeded_database(tmp_path)
    store_vectors(
        connection,
        model_id="test-2d",
        vectors={
            "httpx-0.28.0-client-arguments-removed": np.array([1.0, 0.0], dtype=np.float32),
            "httpx-0.26.0-proxies-deprecated": np.array([0.8, 0.2], dtype=np.float32),
            "starlette-0.37.2-testclient-transport": np.array([0.0, 1.0], dtype=np.float32),
        },
    )
    results = vector_search(
        connection,
        np.array([1.0, 0.0], dtype=np.float32),
        model_id="test-2d",
        package="httpx",
        versions={"0.28.0"},
        limit=6,
    )
    assert [result.id for result in results] == ["httpx-0.28.0-client-arguments-removed"]


def test_vector_search_rejects_model_identity_or_dimension_mismatch(tmp_path: Path) -> None:
    connection = seeded_database(tmp_path)
    with pytest.raises(MissingModelError, match="prepare"):
        vector_search(
            connection,
            np.array([1.0, 0.0], dtype=np.float32),
            model_id="missing",
            package="httpx",
            versions={"0.28.0"},
            limit=6,
        )
    store_vectors(
        connection,
        model_id="test-2d",
        vectors={"httpx-0.28.0-client-arguments-removed": np.array([1.0, 0.0])},
    )
    with pytest.raises(ValueError, match="dimension"):
        vector_search(
            connection,
            np.array([1.0, 0.0, 0.0], dtype=np.float32),
            model_id="test-2d",
            package="httpx",
            versions={"0.28.0"},
            limit=6,
        )
