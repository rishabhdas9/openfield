import json
from pathlib import Path

from openfield.answering import answer_from_evidence
from openfield.cli import main
from openfield.evidence import ingest_demo, open_database
from openfield.models import Generation, Report, RetrievedEvidence

EVIDENCE = [
    RetrievedEvidence(
        id="httpx-0.28.0-client-arguments-removed",
        text="HTTPX 0.28.0 removed the previously deprecated proxies and app client arguments.",
        source_url="https://github.com/encode/httpx/releases/tag/0.28.0",
        heading="deprecated client arguments removed",
        package="httpx",
        version="0.28.0",
        score=1.0,
        origins=("lexical",),
    )
]


def test_deterministic_answer_uses_selected_evidence() -> None:
    answer = answer_from_evidence(
        "What was removed in HTTPX 0.28.0?",
        EVIDENCE,
        retrieval_mode="lexical",
        generate=None,
    )
    assert answer.abstained is False
    assert answer.claims[0].citation_ids == ("httpx-0.28.0-client-arguments-removed",)


def test_unanswerable_safety_question_abstains() -> None:
    answer = answer_from_evidence(
        "Is the whole upgrade safe?",
        EVIDENCE,
        retrieval_mode="lexical",
        generate=None,
    )
    assert answer.abstained is True
    assert answer.claims == ()


def test_question_with_no_content_support_abstains() -> None:
    answer = answer_from_evidence(
        "Did HTTPX 0.28.0 remove the timeout argument?",
        EVIDENCE,
        retrieval_mode="lexical",
        generate=None,
    )
    assert answer.abstained is True
    assert answer.claims == ()


def test_invented_citation_falls_back_to_deterministic_answer() -> None:
    def fake_generate(_payload: str) -> Generation:
        return Generation(
            text=json.dumps(
                {
                    "question": "What changed?",
                    "claims": [{"text": "Everything changed.", "citation_ids": ["invented"]}],
                    "abstained": False,
                    "limitations": [],
                    "retrieval_mode": "hybrid-graph",
                }
            ),
            model="fake",
            input_tokens=20,
            output_tokens=10,
        )

    answer = answer_from_evidence(
        "What changed?",
        EVIDENCE,
        retrieval_mode="hybrid-graph",
        generate=fake_generate,
    )
    assert answer.model is None
    assert answer.claims[0].citation_ids == ("httpx-0.28.0-client-arguments-removed",)
    assert "model response rejected" in answer.limitations


def test_provider_exception_keeps_deterministic_answer() -> None:
    def fail(_payload: str) -> Generation:
        raise TimeoutError("provider timed out")

    answer = answer_from_evidence("What changed?", EVIDENCE, "hybrid", generate=fail)
    assert answer.model is None
    assert "provider unavailable" in answer.limitations


def test_ask_cli_defaults_to_deterministic_output(tmp_path: Path, capsys) -> None:
    database = tmp_path / "evidence.db"
    connection = open_database(database)
    ingest_demo(
        connection,
        Path("src/openfield/corpus/demo.jsonl"),
        Path("examples/httpx_028/environment.json"),
        Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text()),
    )
    connection.close()

    assert main(["ask", "--database", str(database), "What was removed in HTTPX 0.28.0?"]) == 0
    answer = json.loads(capsys.readouterr().out)
    assert answer["model"] is None
    assert answer["claims"][0]["citation_ids"] == ["httpx-0.28.0-client-arguments-removed"]
