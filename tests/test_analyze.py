import json
from pathlib import Path

from openfield.cli import main


def test_analyze_reports_the_owned_httpx_usage(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    exit_code = main(
        [
            "analyze",
            "examples/httpx_028/direct_client.py",
            "--package",
            "httpx",
            "--from",
            "0.27.2",
            "--to",
            "0.28.0",
            "--root",
            ".",
            "--output",
            str(output),
        ]
    )
    report = json.loads(output.read_text())

    assert exit_code == 1
    assert report["findings"][0]["id"] == (
        "httpx.client.proxies.removed:examples/httpx_028/direct_client.py:3"
    )
    assert report["findings"][0]["keyword"] == "proxies"
    assert report["network_used"] is False
    assert report["model_used"] is False


def test_analyze_never_executes_the_target() -> None:
    source = 'import httpx\nhttpx.Client(proxies={})\nraise RuntimeError("must not run")\n'
    from openfield.analyze import analyze_source
    from openfield.models import Upgrade
    from openfield.rules import applicable_rules, load_pack

    rules = applicable_rules(
        load_pack("httpx"),
        Upgrade(package="httpx", from_version="0.27.2", to_version="0.28.0"),
    )
    findings, limitations = analyze_source(source, "owned.py", rules)
    assert len(findings) == 1
    assert limitations == []


def test_comments_strings_and_shadowed_imports_do_not_match() -> None:
    source = '''
import httpx
text = "httpx.Client(proxies={})"

def build(httpx):
    return httpx.Client(proxies={})
'''
    from openfield.analyze import analyze_source
    from openfield.models import Upgrade
    from openfield.rules import applicable_rules, load_pack

    rules = applicable_rules(
        load_pack("httpx"),
        Upgrade(package="httpx", from_version="0.27.2", to_version="0.28.0"),
    )
    findings, _ = analyze_source(source, "shadowed.py", rules)
    assert findings == []


def test_syntax_error_is_incomplete_coverage(tmp_path: Path) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("def broken(:\n")
    output = tmp_path / "report.json"

    exit_code = main(
        [
            "analyze", str(broken), "--package", "httpx", "--from", "0.27.2",
            "--to", "0.28.0", "--root", str(tmp_path), "--output", str(output),
        ]
    )
    report = json.loads(output.read_text())
    assert exit_code == 0
    assert report["coverage"]["complete"] is False
    assert report["coverage"]["skipped_files"] == 1
