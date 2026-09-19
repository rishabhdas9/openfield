import os
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from openfield.answering import answer_from_evidence, anthropic_generate
from openfield.evidence import open_database
from openfield.models import Answer
from openfield.retrieval import (
    MODEL_ID,
    MissingModelError,
    RetrievalMode,
    fastembed_vectors,
    retrieve,
)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500)
    retrieval: RetrievalMode = RetrievalMode.HYBRID_GRAPH
    packages: list[str] = Field(min_length=1, max_length=4)
    versions: list[str] = Field(min_length=1, max_length=8)
    generate: bool = False
    model: str | None = None


def run_question(database: Path, request: AskRequest) -> Answer:
    connection = open_database(database)
    try:
        query_vector = None
        if request.retrieval is not RetrievalMode.LEXICAL:
            try:
                query_vector = fastembed_vectors(
                    [request.question], Path(".cache/openfield"), local_only=True
                )[0]
            except MissingModelError:
                if request.retrieval is RetrievalMode.VECTOR:
                    raise
        evidence = retrieve(
            connection,
            request.question,
            request.retrieval,
            set(request.packages),
            set(request.versions),
            top_k=6,
            query_vector=query_vector,
            model_id=MODEL_ID if query_vector is not None else None,
        )
    finally:
        connection.close()

    generate = None
    if request.generate:
        if not request.model:
            raise ValueError("cloud generation requires a model")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY is not set")
        generate = partial(anthropic_generate, model=request.model)
    return answer_from_evidence(
        request.question,
        evidence,
        request.retrieval.value,
        generate,
    )


def create_app(database: Path, allow_cloud: bool = False) -> FastAPI:
    app = FastAPI(title="Openfield", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask")
    def ask(request: AskRequest):
        if request.generate and not allow_cloud:
            raise HTTPException(status_code=403, detail="cloud generation is disabled")
        try:
            return run_question(database, request).model_dump(mode="json")
        except (MissingModelError, OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


def app_from_environment() -> FastAPI:
    database = os.environ.get("OPENFIELD_DATABASE")
    if not database:
        raise RuntimeError("OPENFIELD_DATABASE is required")
    return create_app(
        Path(database),
        allow_cloud=os.environ.get("OPENFIELD_ALLOW_CLOUD") == "true",
    )
