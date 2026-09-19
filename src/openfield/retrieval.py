import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from openfield.models import RetrievedEvidence

MODEL_ID = "BAAI/bge-small-en-v1.5"


class MissingModelError(RuntimeError):
    pass


def require_numpy() -> Any:
    try:
        import numpy
    except ImportError as exc:
        raise MissingModelError("install with: uv sync --extra semantic") from exc
    return numpy


def normalize(vector: Sequence[float]):
    np = require_numpy()
    vector = np.asarray(vector, dtype="<f4")
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        raise ValueError("embedding vector must be non-zero")
    return np.asarray(vector / norm, dtype="<f4")


def encode_vector(vector: Sequence[float]) -> tuple[int, bytes]:
    normalized = normalize(vector)
    return normalized.size, normalized.tobytes()


def decode_vector(blob: bytes, dimensions: int):
    np = require_numpy()
    vector = np.frombuffer(blob, dtype="<f4")
    if vector.size != dimensions:
        raise ValueError("stored embedding dimensions do not match metadata")
    return vector


def store_vectors(
    connection: sqlite3.Connection,
    model_id: str,
    vectors: Mapping[str, Sequence[float]],
) -> None:
    with connection:
        for chunk_id, vector in vectors.items():
            dimensions, blob = encode_vector(vector)
            connection.execute(
                """
                INSERT INTO vectors (chunk_id, model_id, dimensions, values_blob)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chunk_id) DO UPDATE SET
                    model_id = excluded.model_id,
                    dimensions = excluded.dimensions,
                    values_blob = excluded.values_blob
                """,
                (chunk_id, model_id, dimensions, blob),
            )


def vector_search(
    connection: sqlite3.Connection,
    query_vector: Sequence[float],
    model_id: str,
    package: str,
    versions: set[str],
    limit: int,
) -> list[RetrievedEvidence]:
    if not versions:
        return []
    model = connection.execute(
        "SELECT dimensions FROM vectors WHERE model_id = ? LIMIT 1",
        (model_id,),
    ).fetchone()
    if model is None:
        raise MissingModelError("vector model is not prepared; run evidence embed after model prepare")

    query = normalize(query_vector)
    if query.size != model["dimensions"]:
        raise ValueError("query dimension does not match stored embedding dimension")
    placeholders = ", ".join("?" for _ in versions)
    rows = connection.execute(
        f"""
        SELECT c.*, v.dimensions, v.values_blob
        FROM vectors AS v JOIN chunks AS c ON c.id = v.chunk_id
        WHERE v.model_id = ? AND c.package = ? AND c.version IN ({placeholders})
        """,
        (model_id, package, *sorted(versions)),
    ).fetchall()
    if any(row["dimensions"] != query.size for row in rows):
        raise ValueError("stored embedding dimension does not match query dimension")
    scored = [
        (float(decode_vector(row["values_blob"], row["dimensions"]) @ query), row)
        for row in rows
    ]
    scored.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [
        RetrievedEvidence(
            id=row["id"],
            text=row["text"],
            source_url=row["source_url"],
            heading=row["heading"],
            package=row["package"],
            version=row["version"],
            score=score,
            origins=("vector",),
        )
        for score, row in scored[:limit]
    ]


def fastembed_vectors(
    texts: list[str], cache_dir: Path, local_only: bool
) -> list[Sequence[float]]:
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise MissingModelError("install with: uv sync --extra semantic") from exc
    np = require_numpy()
    try:
        model = TextEmbedding(
            model_name=MODEL_ID,
            cache_dir=str(cache_dir),
            local_files_only=local_only,
        )
        return [np.asarray(vector, dtype=np.float32) for vector in model.embed(texts)]
    except Exception as exc:
        if local_only:
            raise MissingModelError(
                f"model artifacts are absent; run: openfield model prepare --cache-dir {cache_dir}"
            ) from exc
        raise


def prepare_model(cache_dir: Path) -> None:
    fastembed_vectors(["Openfield model preparation"], cache_dir, local_only=False)


def embed_database(connection: sqlite3.Connection, cache_dir: Path) -> None:
    rows = connection.execute("SELECT id, text FROM chunks ORDER BY id").fetchall()
    if not rows:
        raise ValueError("evidence database contains no chunks")
    vectors = fastembed_vectors(
        [row["text"] for row in rows],
        cache_dir,
        local_only=True,
    )
    store_vectors(
        connection,
        MODEL_ID,
        {row["id"]: vector for row, vector in zip(rows, vectors, strict=True)},
    )
