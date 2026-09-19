import json
from pathlib import Path


def test_expected_report_is_specific_and_bounded() -> None:
    report = json.loads(Path("examples/httpx_028/expected-report.json").read_text())

    assert report["upgrade"] == {
        "package": "httpx",
        "from_version": "0.27.2",
        "to_version": "0.28.0",
        "provenance": "user_supplied",
    }
    assert report["findings"][0]["span"] == {
        "path": "examples/httpx_028/direct_client.py",
        "line": 3,
        "end_line": 5,
    }
    assert report["findings"][0]["source_url"].endswith("/0.28.0")
    assert report["coverage"]["complete"] is False
    assert report["network_used"] is False
    assert report["model_used"] is False
