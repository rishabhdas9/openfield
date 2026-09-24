import hashlib
import json
import math
import platform
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import median
from typing import Any

from openfield import __version__
from openfield.answering import answer_from_evidence
from openfield.evidence import open_database
from openfield.models import EvaluationCase, EvaluationResult
from openfield.retrieval import MODEL_ID, RetrievalMode, fastembed_vectors, retrieve


def load_cases(path: Path) -> list[EvaluationCase]:
    return [
        EvaluationCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def aggregate(
    cases: dict[str, EvaluationCase],
    results: list[EvaluationResult],
) -> dict[str, Any]:
    recall: dict[str, dict[str, int | float]] = {}
    for result in results:
        case = cases[result.case_id]
        if not case.required_evidence_ids:
            continue
        hop = str(case.hop_count)
        counts = recall.setdefault(hop, {"found": 0, "required": 0, "rate": 0.0})
        counts["found"] += len(set(case.required_evidence_ids) & set(result.retrieved_ids))
        counts["required"] += len(case.required_evidence_ids)
    for counts in recall.values():
        counts["rate"] = _rate(int(counts["found"]), int(counts["required"]))

    unanswerable = [result for result in results if not cases[result.case_id].answerable]
    answerable = [result for result in results if cases[result.case_id].answerable]
    correct_abstentions = sum(result.abstained for result in unanswerable)
    unnecessary_abstentions = sum(result.abstained for result in answerable)
    valid_citations = sum(
        set(result.citation_ids) <= set(result.retrieved_ids) for result in results
    )
    latencies = sorted(result.latency_ms for result in results)
    p95_index = math.ceil(0.95 * len(latencies)) - 1
    return {
        "evidence_recall_by_hop": recall,
        "abstention": {
            "correct": correct_abstentions,
            "total": len(unanswerable),
            "rate": _rate(correct_abstentions, len(unanswerable)),
        },
        "unnecessary_abstention": {
            "count": unnecessary_abstentions,
            "total": len(answerable),
            "rate": _rate(unnecessary_abstentions, len(answerable)),
        },
        "citation_validity": {
            "valid": valid_citations,
            "total": len(results),
            "rate": _rate(valid_citations, len(results)),
        },
        "latency_ms": {
            "median": median(latencies),
            "p95": latencies[p95_index],
        },
    }


def _package_versions(names: tuple[str, ...]) -> dict[str, str]:
    found = {}
    for name in names:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            found[name] = "not-installed"
    return found


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_benchmark(
    database: Path,
    cases: list[EvaluationCase],
    modes: list[RetrievalMode],
    top_k: int,
    cache_dir: Path,
) -> dict[str, Any]:
    if not database.is_file():
        raise ValueError(f"database is not a file: {database}")
    if not cases:
        raise ValueError("evaluation set is empty")
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("evaluation case IDs must be unique")

    preparation_started = time.perf_counter_ns()
    vectors = fastembed_vectors([case.question for case in cases], cache_dir, local_only=True)
    preparation_ms = (time.perf_counter_ns() - preparation_started) / 1_000_000
    vectors_by_case = dict(zip((case.id for case in cases), vectors, strict=True))
    case_map = {case.id: case for case in cases}
    results: list[EvaluationResult] = []
    connection = open_database(database)
    try:
        corpus_rows = connection.execute(
            "SELECT id, source_digest FROM chunks ORDER BY id"
        ).fetchall()
        corpus_digest = hashlib.sha256(
            "\n".join(f"{row['id']}:{row['source_digest']}" for row in corpus_rows).encode()
        ).hexdigest()
        for mode in modes:
            for case in cases:
                started = time.perf_counter_ns()
                evidence = retrieve(
                    connection,
                    case.question,
                    mode,
                    set(case.packages),
                    set(case.versions),
                    top_k=top_k,
                    query_vector=vectors_by_case[case.id],
                    model_id=MODEL_ID,
                )
                latency_ms = (time.perf_counter_ns() - started) / 1_000_000
                answer = answer_from_evidence(case.question, evidence, mode.value, generate=None)
                results.append(
                    EvaluationResult(
                        case_id=case.id,
                        mode=mode.value,
                        retrieved_ids=tuple(item.id for item in evidence),
                        citation_ids=tuple(
                            citation for claim in answer.claims for citation in claim.citation_ids
                        ),
                        abstained=answer.abstained,
                        latency_ms=latency_ms,
                    )
                )
    finally:
        connection.close()

    summaries = {
        mode.value: aggregate(
            case_map,
            [result for result in results if result.mode == mode.value],
        )
        for mode in modes
    }
    hop_denominators = {str(hop): sum(case.hop_count == hop for case in cases) for hop in range(4)}
    return {
        "raw_results": [result.model_dump(mode="json") for result in results],
        "summaries_by_mode": summaries,
        "metadata": {
            "git_commit": _git_commit(),
            "python": sys.version.split()[0],
            "openfield": __version__,
            "dependencies": _package_versions(("fastembed", "numpy", "packaging", "pydantic")),
            "model": MODEL_ID,
            "corpus": {"chunk_count": len(corpus_rows), "digest": corpus_digest},
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
            "top_k": top_k,
            "retrieval_modes": [mode.value for mode in modes],
            "question_count": len(cases),
            "hop_count_denominators": hop_denominators,
            "model_preparation_ms": preparation_ms,
            "model_api_cost_usd": 0,
        },
    }


def write_results(result: dict[str, Any], output: Path, report: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    summaries = result["summaries_by_mode"]
    rows = []
    for mode, summary in summaries.items():
        recalls = summary["evidence_recall_by_hop"]
        rows.append(
            "| {mode} | {hop1:.3f} | {hop2:.3f} | {hop3:.3f} | {abstain:.3f} | "
            "{citations:.3f} | {median:.3f} | {p95:.3f} |".format(
                mode=mode,
                hop1=recalls.get("1", {}).get("rate", 0.0),
                hop2=recalls.get("2", {}).get("rate", 0.0),
                hop3=recalls.get("3", {}).get("rate", 0.0),
                abstain=summary["abstention"]["rate"],
                citations=summary["citation_validity"]["rate"],
                median=summary["latency_ms"]["median"],
                p95=summary["latency_ms"]["p95"],
            )
        )
    recommended = next(iter(summaries))
    if "vector" in summaries and "hybrid-graph" in summaries:
        vector = summaries["vector"]["evidence_recall_by_hop"]
        hybrid = summaries["hybrid-graph"]["evidence_recall_by_hop"]
        vector_multi = sum(vector.get(str(hop), {}).get("found", 0) for hop in (2, 3))
        hybrid_multi = sum(hybrid.get(str(hop), {}).get("found", 0) for hop in (2, 3))
        recommended = "hybrid-graph" if hybrid_multi > vector_multi else "vector"
    metadata = result["metadata"]
    report.write_text(
        "\n".join(
            [
                "# Openfield retrieval benchmark",
                "",
                (
                    "> Development benchmark on a frozen "
                    f"{metadata['question_count']}-question set; not a held-out public claim."
                ),
                "",
                "| Mode | Recall hop 1 | Recall hop 2 | Recall hop 3 | Abstention | Citations | Median ms | P95 ms |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
                *rows,
                "",
                f"Recommended default: **{recommended}**.",
                "",
                (
                    f"Questions: {metadata['question_count']}; top-k: {metadata['top_k']}; "
                    f"model/API cost: ${metadata['model_api_cost_usd']}."
                ),
                f"Local model preparation and query embedding: {metadata['model_preparation_ms']:.3f} ms.",
                f"Corpus: {metadata['corpus']['chunk_count']} chunks, digest `{metadata['corpus']['digest']}`.",
                (
                    f"Git commit: `{metadata['git_commit']}`; Python: {metadata['python']}; "
                    f"Openfield: {metadata['openfield']}."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
