import hashlib
import json
import re
import sqlite3
from collections import deque
from collections.abc import Iterable
from pathlib import Path

from openfield.models import EvidenceChunk, Relation, Report, RetrievedEvidence

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    package TEXT NOT NULL,
    version TEXT NOT NULL,
    heading TEXT NOT NULL,
    text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_digest TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    id UNINDEXED,
    heading,
    text
);

CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    label TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL REFERENCES entities(id),
    relation TEXT NOT NULL,
    target_id TEXT NOT NULL REFERENCES entities(id),
    chunk_id TEXT NOT NULL REFERENCES chunks(id),
    PRIMARY KEY (source_id, relation, target_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS vectors (
    chunk_id TEXT PRIMARY KEY REFERENCES chunks(id),
    model_id TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    values_blob BLOB NOT NULL
);
"""

ALIASES = {
    "package:httpx": ["httpx"],
    "parameter:httpx.Client:proxies": ["proxies", "httpx.Client", "httpx.Client proxies"],
    "parameter:httpx.Client:app": ["app", "httpx.Client", "httpx.Client app"],
    "package:starlette": ["starlette"],
    "symbol:starlette.TestClient": ["TestClient", "starlette TestClient"],
}


def open_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def _insert_entity(connection: sqlite3.Connection, entity_id: str) -> None:
    connection.execute(
        """
        INSERT INTO entities (id, kind, label, aliases_json) VALUES (?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            kind = excluded.kind,
            label = excluded.label,
            aliases_json = excluded.aliases_json
        """,
        (
            entity_id,
            entity_id.split(":", 1)[0],
            entity_id.rsplit(":", 1)[-1],
            json.dumps(ALIASES.get(entity_id, [])),
        ),
    )


def _upsert_chunk(connection: sqlite3.Connection, chunk: EvidenceChunk) -> None:
    connection.execute(
        """
        INSERT INTO chunks (id, package, version, heading, text, source_url, source_digest)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            package = excluded.package,
            version = excluded.version,
            heading = excluded.heading,
            text = excluded.text,
            source_url = excluded.source_url,
            source_digest = excluded.source_digest
        """,
        (
            chunk.id,
            chunk.package,
            chunk.version,
            chunk.heading,
            chunk.text,
            chunk.source_url,
            chunk.source_digest,
        ),
    )
    connection.execute("DELETE FROM chunks_fts WHERE id = ?", (chunk.id,))
    connection.execute(
        "INSERT INTO chunks_fts (id, heading, text) VALUES (?, ?, ?)",
        (chunk.id, chunk.heading, chunk.text),
    )
    connection.execute("DELETE FROM edges WHERE chunk_id = ?", (chunk.id,))
    for entity_id in chunk.entity_ids:
        _insert_entity(connection, entity_id)
    _insert_edges(connection, chunk.id, chunk.relations)


def _insert_edges(
    connection: sqlite3.Connection,
    chunk_id: str,
    relations: Iterable[Relation],
) -> None:
    for relation in relations:
        for endpoint in (relation.source, relation.target):
            if connection.execute("SELECT 1 FROM entities WHERE id = ?", (endpoint,)).fetchone() is None:
                raise ValueError(f"missing edge endpoint: {endpoint}")
        connection.execute(
            "INSERT OR IGNORE INTO edges (source_id, relation, target_id, chunk_id) VALUES (?, ?, ?, ?)",
            (relation.source, relation.relation, relation.target, chunk_id),
        )


def _load_corpus(path: Path) -> list[EvidenceChunk]:
    chunks = [
        EvidenceChunk.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for chunk in chunks:
        digest = hashlib.sha256(chunk.text.encode()).hexdigest()
        if digest != chunk.source_digest:
            raise ValueError(f"source digest mismatch: {chunk.id}")
    return chunks


def ingest_demo(
    connection: sqlite3.Connection,
    corpus: Path,
    environment_path: Path,
    report: Report,
) -> None:
    chunks = _load_corpus(corpus)
    environment_bytes = environment_path.read_bytes()
    environment = json.loads(environment_bytes)
    provenance = environment["provenance"]
    environment_chunk = EvidenceChunk(
        id=f"environment:{provenance}",
        package="environment",
        version=provenance,
        heading="Owned dependency environment",
        text="demo-project uses Starlette 0.36.3 with HTTPX 0.28.0.",
        source_url="owned:examples/httpx_028/environment.json",
        source_digest=hashlib.sha256(environment_bytes).hexdigest(),
        entity_ids=(
            "project:demo-project",
            "release:starlette:0.36.3",
            "release:httpx:0.28.0",
        ),
        relations=(
            Relation(
                source="project:demo-project",
                relation="depends_on",
                target="release:starlette:0.36.3",
            ),
            Relation(
                source="release:starlette:0.36.3",
                relation="depends_on",
                target="release:httpx:0.28.0",
            ),
        ),
    )
    finding = report.findings[0]
    finding_text = (
        f"Reviewed direct call match: {finding.symbol} uses keyword {finding.keyword} at "
        f"{finding.span.path}:{finding.span.line}. {finding.suggestion}"
    )
    usage_id = f"usage:{finding.span.path}:{finding.span.line}"
    rule_id = f"rule:{finding.rule_id}"
    parameter_id = f"parameter:{finding.symbol}:{finding.keyword}"
    finding_chunk = EvidenceChunk(
        id=f"finding:{finding.id}",
        package=report.upgrade.package,
        version=report.upgrade.to_version,
        heading="Reviewed deterministic finding",
        text=finding_text,
        source_url=finding.source_url,
        source_digest=hashlib.sha256(finding_text.encode()).hexdigest(),
        entity_ids=("project:demo-project", usage_id, rule_id, parameter_id),
        relations=(
            Relation(
                source="project:demo-project",
                relation="contains_usage",
                target=usage_id,
            ),
            Relation(source=usage_id, relation="matches", target=rule_id),
            Relation(source=rule_id, relation="targets", target=parameter_id),
        ),
    )

    with connection:
        for chunk in (*chunks, environment_chunk, finding_chunk):
            _upsert_chunk(connection, chunk)


def fts_expression(question: str) -> str | None:
    raw_terms = re.findall(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", question)
    terms = [
        term
        for term in raw_terms
        if not term.isdigit() and term.casefold() not in {"and", "not", "or"}
    ]
    return " OR ".join(f'"{term}"' for term in terms[:12]) or None


def lexical_search(
    connection: sqlite3.Connection,
    question: str,
    package: str,
    versions: set[str],
    limit: int,
) -> list[RetrievedEvidence]:
    expression = fts_expression(question)
    if expression is None or not versions:
        return []
    placeholders = ", ".join("?" for _ in versions)
    rows = connection.execute(
        f"""
        SELECT c.*, bm25(chunks_fts) AS rank
        FROM chunks_fts JOIN chunks AS c ON c.id = chunks_fts.id
        WHERE chunks_fts MATCH ? AND c.package = ? AND c.version IN ({placeholders})
        ORDER BY rank, c.id
        LIMIT ?
        """,
        (expression, package, *sorted(versions), limit),
    ).fetchall()
    return [
        RetrievedEvidence(
            id=row["id"],
            text=row["text"],
            source_url=row["source_url"],
            heading=row["heading"],
            package=row["package"],
            version=row["version"],
            score=-float(row["rank"]),
            origins=("lexical",),
        )
        for row in rows
    ]


def provenance_path(
    connection: sqlite3.Connection,
    source: str,
    target: str,
    max_depth: int,
    allowed_relations: set[str] | None = None,
) -> list[str]:
    if not 0 <= max_depth <= 6:
        raise ValueError("max_depth must be between 0 and 6")
    queue = deque([(source, [source], 0)])
    visited = {source}
    while queue:
        current, path, depth = queue.popleft()
        if current == target:
            return path
        if depth == max_depth:
            continue
        parameters: list[object] = [current]
        relation_filter = ""
        if allowed_relations:
            placeholders = ", ".join("?" for _ in allowed_relations)
            relation_filter = f" AND relation IN ({placeholders})"
            parameters.extend(sorted(allowed_relations))
        rows = connection.execute(
            f"SELECT target_id FROM edges WHERE source_id = ?{relation_filter} ORDER BY target_id",
            parameters,
        )
        for row in rows:
            next_id = row["target_id"]
            if next_id in visited:
                continue
            visited.add(next_id)
            queue.append((next_id, [*path, next_id], depth + 1))
    return []
