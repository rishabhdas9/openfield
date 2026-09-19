import json
import re
import sqlite3
from collections import deque
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

from openfield.evidence import lexical_search
from openfield.models import RetrievedEvidence

MODEL_ID = "BAAI/bge-small-en-v1.5"


class MissingModelError(RuntimeError):
    pass


class RetrievalMode(StrEnum):
    LEXICAL = "lexical"
    VECTOR = "vector"
    HYBRID = "hybrid"
    HYBRID_GRAPH = "hybrid-graph"


def route_question(question: str) -> RetrievalMode:
    words = set(question.casefold().replace("?", "").split())
    if words & {"why", "relationship", "depends", "dependency", "through", "affected"}:
        return RetrievalMode.HYBRID_GRAPH
    return RetrievalMode.HYBRID


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    rank_constant: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rank_constant + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


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


def resolve_entities(connection: sqlite3.Connection, question: str) -> set[str]:
    resolved: set[str] = set()
    for row in connection.execute("SELECT id, label, aliases_json FROM entities ORDER BY id"):
        names = [row["label"], *json.loads(row["aliases_json"])]
        if any(
            re.search(rf"(?<![\w.]){re.escape(name)}(?![\w.])", question, re.IGNORECASE)
            for name in names
        ):
            resolved.add(row["id"])
    return resolved


def graph_expand(
    connection: sqlite3.Connection,
    seed_entities: set[str],
    allowed_packages: set[str],
    allowed_versions: set[str],
    max_depth: int = 3,
    limit: int = 6,
) -> list[RetrievedEvidence]:
    if not 0 <= max_depth <= 6:
        raise ValueError("max_depth must be between 0 and 6")
    if not seed_entities or not allowed_packages or not allowed_versions:
        return []
    queue = deque((entity, entity, 0) for entity in sorted(seed_entities))
    visited = set(seed_entities)
    found: dict[str, RetrievedEvidence] = {}
    while queue:
        current, seed, depth = queue.popleft()
        if depth == max_depth:
            continue
        rows = connection.execute(
            """
            SELECT e.target_id, c.*
            FROM edges AS e JOIN chunks AS c ON c.id = e.chunk_id
            WHERE e.source_id = ?
            ORDER BY e.target_id, c.id
            """,
            (current,),
        )
        for row in rows:
            target = row["target_id"]
            if target not in visited:
                visited.add(target)
                queue.append((target, seed, depth + 1))
            if row["package"] not in allowed_packages or row["version"] not in allowed_versions:
                continue
            score = 1.0 / (depth + 1)
            candidate = RetrievedEvidence(
                id=row["id"],
                text=row["text"],
                source_url=row["source_url"],
                heading=row["heading"],
                package=row["package"],
                version=row["version"],
                score=score,
                origins=(f"graph:{seed}",),
            )
            existing = found.get(candidate.id)
            if existing is None or candidate.score > existing.score:
                found[candidate.id] = candidate
            elif candidate.origins[0] not in existing.origins:
                found[candidate.id] = existing.model_copy(
                    update={"origins": (*existing.origins, *candidate.origins)}
                )
    return sorted(found.values(), key=lambda item: (-item.score, item.id))[:limit]


def _with_origin(item: RetrievedEvidence, origin: str) -> RetrievedEvidence:
    if origin in item.origins:
        return item
    return item.model_copy(update={"origins": (*item.origins, origin)})


def _fuse(
    rankings: list[list[RetrievedEvidence]],
    limit: int,
) -> list[RetrievedEvidence]:
    by_id: dict[str, RetrievedEvidence] = {}
    for ranking in rankings:
        for item in ranking:
            existing = by_id.get(item.id)
            if existing is None:
                by_id[item.id] = item
            else:
                origins = tuple(dict.fromkeys((*existing.origins, *item.origins)))
                by_id[item.id] = existing.model_copy(update={"origins": origins})
    fused = reciprocal_rank_fusion([[item.id for item in ranking] for ranking in rankings])
    return [by_id[chunk_id].model_copy(update={"score": score}) for chunk_id, score in fused[:limit]]


def retrieve(
    connection: sqlite3.Connection,
    question: str,
    mode: RetrievalMode,
    packages: set[str],
    versions: set[str],
    top_k: int = 6,
    query_vector: Sequence[float] | None = None,
    model_id: str | None = None,
) -> list[RetrievedEvidence]:
    lexical = sorted(
        (
            item
            for package in sorted(packages)
            for item in lexical_search(connection, question, package, versions, limit=20)
        ),
        key=lambda item: (-item.score, item.id),
    )[:20]
    if mode is RetrievalMode.LEXICAL:
        return lexical[:top_k]
    if mode is RetrievalMode.VECTOR and (query_vector is None or model_id is None):
        raise ValueError("vector retrieval requires query_vector and model_id")

    vectors: list[RetrievedEvidence] = []
    vector_unavailable = query_vector is None or model_id is None
    if not vector_unavailable:
        try:
            vectors = sorted(
                (
                    item
                    for package in sorted(packages)
                    for item in vector_search(
                        connection,
                        query_vector,
                        model_id=model_id,
                        package=package,
                        versions=versions,
                        limit=20,
                    )
                ),
                key=lambda item: (-item.score, item.id),
            )[:20]
        except MissingModelError:
            if mode is RetrievalMode.VECTOR:
                raise
            vector_unavailable = True
    if mode is RetrievalMode.VECTOR:
        return vectors[:top_k]
    if vector_unavailable:
        lexical = [_with_origin(item, "vector-unavailable") for item in lexical]
    hybrid = _fuse([lexical, vectors], limit=20) if vectors else lexical
    if mode is RetrievalMode.HYBRID:
        return hybrid[:top_k]

    graph = graph_expand(
        connection,
        seed_entities=resolve_entities(connection, question),
        allowed_packages=packages,
        allowed_versions=versions,
        max_depth=3,
        limit=20,
    )
    return _fuse([hybrid, graph], limit=top_k) if graph else hybrid[:top_k]
