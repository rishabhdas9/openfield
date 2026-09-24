from pathlib import Path

from openfield.eval import aggregate, write_results
from openfield.models import EvaluationCase, EvaluationResult


def test_aggregate_reports_raw_counts_by_hop_and_abstention() -> None:
    cases = {
        "q1": EvaluationCase(
            id="q1",
            question="x",
            hop_count=2,
            packages=("httpx",),
            versions=("0.28.0",),
            required_evidence_ids=("a", "b"),
            answerable=True,
        ),
        "q2": EvaluationCase(
            id="q2",
            question="y",
            hop_count=0,
            packages=("httpx",),
            versions=("0.28.0",),
            required_evidence_ids=(),
            answerable=False,
        ),
    }
    results = [
        EvaluationResult(
            case_id="q1",
            mode="vector",
            retrieved_ids=("a",),
            citation_ids=("a",),
            abstained=False,
            latency_ms=10,
        ),
        EvaluationResult(
            case_id="q2",
            mode="vector",
            retrieved_ids=(),
            citation_ids=(),
            abstained=True,
            latency_ms=20,
        ),
    ]
    summary = aggregate(cases, results)
    assert summary["evidence_recall_by_hop"]["2"] == {
        "found": 1,
        "required": 2,
        "rate": 0.5,
    }
    assert summary["abstention"] == {"correct": 1, "total": 1, "rate": 1.0}
    assert summary["latency_ms"]["median"] == 15.0


def test_citation_validity_counts_only_selected_evidence() -> None:
    cases = {
        "q": EvaluationCase(
            id="q",
            question="x",
            hop_count=1,
            packages=("httpx",),
            versions=("0.28.0",),
            required_evidence_ids=("a",),
            answerable=True,
        )
    }
    results = [
        EvaluationResult(
            case_id="q",
            mode="hybrid-graph",
            retrieved_ids=("a",),
            citation_ids=("invented",),
            abstained=False,
            latency_ms=1,
        )
    ]
    assert aggregate(cases, results)["citation_validity"] == {
        "valid": 0,
        "total": 1,
        "rate": 0.0,
    }


def test_report_uses_the_recorded_question_count(tmp_path: Path) -> None:
    summary = {
        "evidence_recall_by_hop": {},
        "abstention": {"correct": 0, "total": 0, "rate": 0.0},
        "unnecessary_abstention": {"count": 0, "total": 2, "rate": 0.0},
        "citation_validity": {"valid": 2, "total": 2, "rate": 1.0},
        "latency_ms": {"median": 1.0, "p95": 2.0},
    }
    result = {
        "raw_results": [],
        "summaries_by_mode": {"vector": summary},
        "metadata": {
            "question_count": 2,
            "top_k": 6,
            "model_api_cost_usd": 0,
            "model_preparation_ms": 3.0,
            "corpus": {"chunk_count": 1, "digest": "digest"},
            "git_commit": "commit",
            "python": "3.13",
            "openfield": "0.1.0",
        },
    }
    report = tmp_path / "report.md"

    write_results(result, tmp_path / "results.json", report)

    assert "2-question set" in report.read_text()
