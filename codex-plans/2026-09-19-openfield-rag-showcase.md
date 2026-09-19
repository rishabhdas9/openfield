# Openfield Interview-Worthy RAG Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interview-ready Openfield vertical slice that detects one real Python dependency-upgrade impact, connects it to a versioned evidence graph, answers graph/vector questions with validated citations, and publishes a controlled vector-only versus hybrid-graph benchmark.

**Architecture:** A deterministic Python analyzer owns code and version facts. SQLite stores authored evidence chunks and typed provenance edges, FTS5 supplies the lexical baseline, FastEmbed plus NumPy supplies optional exact vector search, and bounded graph expansion augments retrieval. A direct Anthropic SDK call may explain already-selected evidence, while the offline CLI, deterministic answer, and benchmark continue to work without a key.

**Tech Stack:** Python 3.13 development with a 3.12 floor, `uv`/`uv_build`, `argparse`, `ast`, `pathlib`, `sqlite3`, SQLite FTS5, `packaging`, Pydantic 2, optional FastEmbed + NumPy, optional Anthropic SDK, optional FastAPI + Uvicorn, pytest, Ruff.

**Spec:** `plan.md` - especially sections 1, 4-8, 11, and slices C0.01 through C6.02. This implementation plan intentionally brings the smallest C4-C6 retrieval path immediately after C1 instead of waiting for general C2/C3 hardening.

## Global Constraints

- Develop on Python 3.13; publish the core package with `requires-python = ">=3.12"`.
- Normal analysis is offline, read-only, and never imports, installs, builds, or executes the repository under analysis.
- Deterministic rules and parsed source facts own findings. Retrieval and model output cannot create blocking findings.
- Use SQLite tables as the evidence graph, FTS5 for lexical retrieval, and exact NumPy cosine search for the first vector implementation.
- Keep FastEmbed, Anthropic, FastAPI, and Uvicorn in implemented optional dependency groups; importing the core package must not import them.
- A scan must not download a model or make a network request. Model preparation and cloud generation are separate explicit commands.
- Use direct functions and SQL. Do not add LangChain, LlamaIndex, Neo4j, PostgreSQL, a vector database, an ORM, a provider factory, or a generic plugin system.
- Scope the first fixture to HTTPX `0.27.2 -> 0.28.0`, the removed `proxies`/`app` arguments, and the documented Starlette `0.36.3 -> 0.37.2` `TestClient` compatibility path.
- Every asserted relationship records its originating chunk or parsed input. Graph expansion may return only evidence reachable through recorded edges.
- Every non-abstaining generated claim has at least one citation ID, and every citation ID must belong to the evidence supplied for that answer.
- Compare vector-only and hybrid-graph retrieval on the same corpus, questions, `top_k=6`, model identity, and hardware.
- Publish measured counts and timings only after the benchmark runs; never substitute proposed targets for results.
- Commit only authored summaries, short necessary excerpts, URLs, headings, and digests. Do not copy entire upstream release-note pages.
- The first showcase ends with one CLI, one `/ask` endpoint, one 16-question evaluation set, one benchmark report, and a README demonstration. Broader package support, hosting, and arbitrary-repository ingestion are excluded.

## Why This Project Is Worth Building

Proceed with Openfield. It is stronger than a generic document chatbot because it forces the candidate to explain retrieval boundaries, entity identity, version filters, graph provenance, citation validation, abstention, evaluation design, latency, and cost.

Current role signals support this scope:

- OpenAI's Applied AI Engineer role emphasizes prototypes, evaluation systems, reliability, latency, cost, safety, and technical judgment: <https://openai.com/careers/applied-ai-engineer-digital-natives-new-york-city/>.
- Titan's retrieval role explicitly names chunking, metadata, dense/sparse/hybrid retrieval, recall/MRR/nDCG, and graph databases: <https://jobs.ashbyhq.com/titan-ai/2bd78c4f-6cea-44a2-977b-32b4147a2e8d>.
- Level's applied-AI role explicitly calls out GraphRAG, hybrid retrieval, grounding, versioned gold sets, evaluation-driven tuning, and public technical work: <https://jobs.ashbyhq.com/level/16021400-6ce7-47c8-87ef-58baf6652b75/>.
- Redpine's retrieval-quality role emphasizes hybrid search, fusion, knowledge graphs, evaluation gates, provenance, and proving one retrieval method better than another: <https://jobs.ashbyhq.com/redpine/be3acdef-df36-441b-bb79-09d06a79c951>.

A stronger alternative would be an agent reliability/evaluation platform, but that would dilute the specific goal of proving RAG depth. Openfield already combines an unusual developer-tool domain with exactly the retrieval and evaluation work these roles describe.

## Review Focus

1. **Target code contains imports with side effects or an explicit `raise`:** parsing still succeeds because Openfield never imports or executes the target file; Task 3 pins this behavior.
2. **The query mentions a different package or version:** retrieval excludes wrong-package and wrong-version chunks rather than presenting plausible but inapplicable evidence; Tasks 4-6 pin this behavior.
3. **A model returns an invented or unselected citation:** the response is rejected and the deterministic evidence answer is returned; Task 7 pins this behavior.
4. **FastEmbed artifacts or an Anthropic key are absent:** core analysis and deterministic answers still work, while the requested optional operation returns an actionable error; Tasks 5 and 7 pin this behavior.
5. **The question asks whether the entire upgrade is safe or requires unavailable runtime facts:** the system abstains and states the missing evidence instead of widening the search or inventing certainty; Tasks 6-9 pin this behavior.

---

## File Structure

Create only files used by this showcase:

```text
pyproject.toml                         package metadata, extras, CLI entry point, pytest/Ruff config
uv.lock                                exact development environment
README.md                              product contract, quickstart, measured result, architecture
src/openfield/__init__.py              package version only
src/openfield/cli.py                   argparse entry point and command wiring
src/openfield/models.py                validated rule/report/evidence/answer schemas
src/openfield/rules.py                 pack loading and version applicability
src/openfield/analyze.py               bounded AST matching; never imports target code
src/openfield/report.py                stable IDs and deterministic report construction
src/openfield/evidence.py              SQLite schema, ingestion, provenance graph, FTS5
src/openfield/retrieval.py             lexical, vector, fusion, routing, graph expansion
src/openfield/answering.py              deterministic and optional Anthropic cited answers
src/openfield/api.py                   minimal FastAPI `/healthz` and `/ask` adapter
src/openfield/eval.py                  benchmark runner and metrics
src/openfield/packs/httpx.json          one reviewed HTTPX rule pack
src/openfield/corpus/demo.jsonl         authored evidence records with source metadata
examples/httpx_028/direct_client.py     owned direct removed-keyword fixture
examples/httpx_028/environment.json     owned dependency/version snapshot
examples/httpx_028/expected-report.json manually checked first output contract
evals/questions.jsonl                  16 labeled single/multi-hop/abstention questions
tests/test_contract.py                 C0.01 contract check
tests/test_rules.py                    version boundary and pack validation
tests/test_analyze.py                  source matching and no-execution checks
tests/test_evidence.py                 graph/FTS ingestion and provenance checks
tests/test_retrieval.py                lexical/vector/hybrid/graph behavior
tests/test_answering.py                citations, abstention, optional-provider failures
tests/test_api.py                      HTTP contract with no external socket/model call
tests/test_eval.py                     metric definitions and controlled comparison
benchmarks/results.json                generated raw benchmark output
benchmarks/report.md                   generated human-readable comparison
```

Keep implementation files focused. Do not split providers, repositories, routers, or storage into additional packages until a second real implementation creates duplication.

## Dependency and Delivery Order

```text
Task 1 contract/scaffold
  -> Task 2 rule/version boundary
  -> Task 3 deterministic finding
  -> Task 4 evidence graph and lexical corpus
  -> Task 5 vector retrieval
  -> Task 6 routing, fusion, graph expansion
  -> Task 7 cited answers
  -> Task 8 API
  -> Task 9 benchmark
  -> Task 10 portfolio packaging
```

Tasks 1-3 produce the offline M0 result. Tasks 4-9 produce the first interview-worthy RAG result. Task 10 packages evidence already produced; it does not invent new metrics.

### Task 1: Freeze the C0.01 Contract and Initialize the Package

**Files:**
- Create: `.gitignore`
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `README.md`
- Create: `src/openfield/__init__.py`
- Create: `src/openfield/cli.py`
- Create: `examples/httpx_028/direct_client.py`
- Create: `examples/httpx_028/environment.json`
- Create: `examples/httpx_028/expected-report.json`
- Create: `tests/test_contract.py`

**Interfaces:**
- Consumes: the C0.01 product contract in `plan.md`.
- Produces: `openfield.cli:main() -> int`, the owned fixture, and the manually verified expected report used by Tasks 2-3.

- [ ] **Step 1: Initialize Git and the smallest package**

Run from the repository root:

```bash
uv init --name openfield --package --build-backend uv --vcs git --python 3.13
uv add packaging pydantic
uv add --dev pytest ruff
```

Then set this console script and tool configuration in `pyproject.toml`:

```toml
[project]
name = "openfield"
version = "0.1.0"
description = "Version-aware evidence retrieval for Python dependency upgrades"
requires-python = ">=3.12"

[project.scripts]
openfield = "openfield.cli:main"

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

Remove any generated hello-world function or `main.py`; the console script is the only entry point.

Set `.gitignore` to:

```gitignore
# Local analysis artifacts are regenerable and are not product source.
/graft/
/graphify-out/
/.remember/
.cache/
.venv/
dist/
*.db
__pycache__/
.pytest_cache/
.ruff_cache/
```

Set the initial `README.md` to:

```markdown
# Openfield

Openfield connects a Python dependency upgrade to the source usages and reviewed evidence that make the upgrade relevant.

The first slice covers HTTPX 0.27.2 to 0.28.0. It is intentionally narrow until its deterministic finding and evidence contract pass.
```

- [ ] **Step 2: Create the owned source and environment fixtures**

Create `examples/httpx_028/direct_client.py` exactly as an intentionally unsafe-to-execute fixture:

```python
import httpx

client = httpx.Client(
    proxies={"https://": "http://localhost:8080"},
)

raise RuntimeError("Openfield must parse this fixture without executing it")
```

Create `examples/httpx_028/environment.json`:

```json
{
  "python": "3.13",
  "packages": [
    {"name": "httpx", "version": "0.28.0"},
    {"name": "starlette", "version": "0.36.3"}
  ],
  "dependencies": [
    {"from": "demo-project", "to": "starlette", "requirement": "==0.36.3"},
    {"from": "starlette", "to": "httpx", "requirement": "==0.28.0"}
  ],
  "provenance": "owned-demo-fixture"
}
```

- [ ] **Step 3: Write the manually checked report contract**

Create `examples/httpx_028/expected-report.json`:

```json
{
  "schema_version": "1",
  "upgrade": {
    "package": "httpx",
    "from_version": "0.27.2",
    "to_version": "0.28.0",
    "provenance": "user_supplied"
  },
  "findings": [
    {
      "id": "httpx.client.proxies.removed:examples/httpx_028/direct_client.py:3",
      "rule_id": "httpx.client.proxies.removed",
      "span": {
        "path": "examples/httpx_028/direct_client.py",
        "line": 3,
        "end_line": 5
      },
      "symbol": "httpx.Client",
      "keyword": "proxies",
      "impact": "breaking",
      "evidence": "reviewed-rule/direct-call-match",
      "source_url": "https://github.com/encode/httpx/releases/tag/0.28.0",
      "suggestion": "Use proxy= for one proxy or mounts= for per-scheme transports."
    }
  ],
  "coverage": {
    "complete": false,
    "parsed_files": 1,
    "skipped_files": 0,
    "limitations": [
      "This slice recognizes direct qualified calls only.",
      "Dynamic imports, star imports, getattr, **kwargs, wrappers, and inferred instances are unresolved.",
      "A clean report is not proof that the upgrade is safe."
    ]
  },
  "network_used": false,
  "model_used": false
}
```

- [ ] **Step 4: Write the contract test**

Create `tests/test_contract.py`:

```python
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
```

- [ ] **Step 5: Implement a real help command, not an empty architecture**

Create `src/openfield/cli.py`:

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openfield",
        description="Connect Python dependency changes to source usages and evidence.",
    )
    parser.add_argument("--version", action="version", version="openfield 0.1.0")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0
```

Create `src/openfield/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 6: Run the first checks**

Run:

```bash
uv run openfield --help
uv run pytest tests/test_contract.py -v
uv run ruff check .
```

Expected: help exits `0`; the contract test passes; Ruff reports no errors; importing `direct_client.py` is never attempted.

- [ ] **Step 7: Commit the contract**

```bash
git add .gitignore .python-version pyproject.toml uv.lock README.md src examples tests/test_contract.py plan.md codex-plans/2026-09-19-openfield-rag-showcase.md
git commit -m "chore: define openfield demo contract"
```

### Task 2: Implement the Reviewed HTTPX Rule and Version Boundary

**Files:**
- Create: `src/openfield/models.py`
- Create: `src/openfield/rules.py`
- Create: `src/openfield/packs/httpx.json`
- Create: `tests/test_rules.py`

**Interfaces:**
- Consumes: `Upgrade`, `RulePack`, and the HTTPX source/target versions.
- Produces: `load_pack(package: str) -> RulePack` and `applicable_rules(pack: RulePack, upgrade: Upgrade) -> list[Rule]` for Task 3.

- [ ] **Step 1: Write failing pack and boundary tests**

Create `tests/test_rules.py`:

```python
import pytest
from pydantic import ValidationError

from openfield.models import Rule, RulePack, Upgrade
from openfield.rules import applicable_rules, load_pack


def test_removed_keyword_applies_only_when_upgrade_crosses_removal() -> None:
    pack = load_pack("httpx")
    rule_ids = {
        rule.id
        for rule in applicable_rules(
            pack,
            Upgrade(package="httpx", from_version="0.27.2", to_version="0.28.0"),
        )
    }
    assert "httpx.client.proxies.removed" in rule_ids

    for source, target in [("0.27.0", "0.27.2"), ("0.28.0", "0.28.0"), ("0.28.0", "0.27.2")]:
        assert applicable_rules(
            pack,
            Upgrade(package="httpx", from_version=source, to_version=target),
        ) == []


def test_pack_rejects_missing_citation_and_review_state() -> None:
    rule = {
        "id": "broken",
        "qualified_names": ["httpx.Client"],
        "keyword": "proxies",
        "removed_in": "0.28.0",
        "impact": "breaking",
        "summary": "Removed.",
        "suggestion": "Use proxy=.",
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(rule)


def test_pack_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        RulePack.model_validate({"schema_version": "1", "package": "httpx", "rules": [], "typo": 1})
```

- [ ] **Step 2: Run the tests and verify the missing modules fail**

Run:

```bash
uv run pytest tests/test_rules.py -v
```

Expected: collection fails because `openfield.models` or `openfield.rules` does not exist.

- [ ] **Step 3: Define strict schemas**

Create the following core of `src/openfield/models.py`:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Upgrade(StrictModel):
    package: str
    from_version: str
    to_version: str
    provenance: Literal["user_supplied", "environment_snapshot"] = "user_supplied"


class Rule(StrictModel):
    id: str
    qualified_names: tuple[str, ...]
    keyword: str
    removed_in: str
    impact: Literal["breaking"]
    summary: str
    suggestion: str
    source_url: str
    source_heading: str
    reviewed: Literal[True]


class RulePack(StrictModel):
    schema_version: Literal["1"]
    package: str
    rules: tuple[Rule, ...]


class SourceSpan(StrictModel):
    path: str
    line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class Finding(StrictModel):
    id: str
    rule_id: str
    span: SourceSpan
    symbol: str
    keyword: str
    impact: Literal["breaking"]
    evidence: Literal["reviewed-rule/direct-call-match"]
    source_url: str
    suggestion: str


class Coverage(StrictModel):
    complete: bool
    parsed_files: int = Field(ge=0)
    skipped_files: int = Field(ge=0)
    limitations: tuple[str, ...]


class Report(StrictModel):
    schema_version: Literal["1"] = "1"
    upgrade: Upgrade
    findings: tuple[Finding, ...]
    coverage: Coverage
    network_used: bool = False
    model_used: bool = False
```

- [ ] **Step 4: Add the reviewed pack**

Create `src/openfield/packs/httpx.json`:

```json
{
  "schema_version": "1",
  "package": "httpx",
  "rules": [
    {
      "id": "httpx.client.proxies.removed",
      "qualified_names": ["httpx.Client", "httpx.AsyncClient"],
      "keyword": "proxies",
      "removed_in": "0.28.0",
      "impact": "breaking",
      "summary": "HTTPX 0.28.0 removed the previously deprecated proxies argument.",
      "suggestion": "Use proxy= for one proxy or mounts= for per-scheme transports.",
      "source_url": "https://github.com/encode/httpx/releases/tag/0.28.0",
      "source_heading": "0.28.0 (28th November, 2024)",
      "reviewed": true
    },
    {
      "id": "httpx.client.app.removed",
      "qualified_names": ["httpx.Client", "httpx.AsyncClient"],
      "keyword": "app",
      "removed_in": "0.28.0",
      "impact": "breaking",
      "summary": "HTTPX 0.28.0 removed the previously deprecated app argument.",
      "suggestion": "Use an explicit WSGITransport or ASGITransport.",
      "source_url": "https://github.com/encode/httpx/releases/tag/0.28.0",
      "source_heading": "0.28.0 (28th November, 2024)",
      "reviewed": true
    }
  ]
}
```

- [ ] **Step 5: Implement pack loading and PEP 440 applicability**

Create `src/openfield/rules.py`:

```python
from importlib.resources import files

from packaging.utils import canonicalize_name
from packaging.version import Version

from openfield.models import Rule, RulePack, Upgrade


def load_pack(package: str) -> RulePack:
    name = canonicalize_name(package)
    path = files("openfield").joinpath("packs", f"{name}.json")
    return RulePack.model_validate_json(path.read_text(encoding="utf-8"))


def applicable_rules(pack: RulePack, upgrade: Upgrade) -> list[Rule]:
    if canonicalize_name(pack.package) != canonicalize_name(upgrade.package):
        return []
    source = Version(upgrade.from_version)
    target = Version(upgrade.to_version)
    if target <= source:
        return []
    return [rule for rule in pack.rules if source < Version(rule.removed_in) <= target]
```

No additional package-data setting is needed: `uv_build` includes files under the module root. Task 10's clean-wheel smoke test must still prove that `packs/httpx.json` and `corpus/demo.jsonl` are present after installation.

- [ ] **Step 6: Run rule checks**

Run:

```bash
uv run pytest tests/test_rules.py -v
uv run ruff check src/openfield/models.py src/openfield/rules.py tests/test_rules.py
```

Expected: all rule tests pass; invalid versions raise `packaging.version.InvalidVersion` for the CLI to convert into an input error in Task 3.

- [ ] **Step 7: Commit the rule contract**

```bash
git add pyproject.toml uv.lock src/openfield/models.py src/openfield/rules.py src/openfield/packs/httpx.json tests/test_rules.py
git commit -m "feat: add reviewed HTTPX rule pack"
```

### Task 3: Produce the First Deterministic Finding Without Executing Target Code

**Files:**
- Create: `src/openfield/analyze.py`
- Create: `src/openfield/report.py`
- Modify: `src/openfield/cli.py`
- Modify: `src/openfield/models.py`
- Create: `tests/test_analyze.py`

**Interfaces:**
- Consumes: `Rule`, `Upgrade`, source text, and a repository-relative path.
- Produces: `analyze_source(source: str, relative_path: str, rules: list[Rule]) -> tuple[list[Finding], list[str]]`, `build_report(...) -> Report`, and `openfield analyze PATH --package httpx --from 0.27.2 --to 0.28.0`.

- [ ] **Step 1: Write the end-to-end and no-execution tests**

Create `tests/test_analyze.py`:

```python
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
```

- [ ] **Step 2: Run tests and confirm the analyzer is absent**

Run:

```bash
uv run pytest tests/test_analyze.py -v
```

Expected: collection fails because `openfield.analyze` or the `analyze` command is missing.

- [ ] **Step 3: Implement conservative AST symbol resolution**

Create `src/openfield/analyze.py` around these exact rules:

```python
import ast
from collections.abc import Iterable

from openfield.models import Finding, Rule, SourceSpan


def finding_id(rule: Rule, relative_path: str, line: int) -> str:
    return f"{rule.id}:{relative_path}:{line}"


def analyze_source(
    source: str,
    relative_path: str,
    rules: Iterable[Rule],
) -> tuple[list[Finding], list[str]]:
    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as exc:
        return [], [f"{relative_path}: syntax error at line {exc.lineno}"]

    module_aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "httpx":
                    module_aliases[alias.asname or alias.name] = "httpx"

    findings: list[Finding] = []
    rule_by_key = {
        (qualified_name, rule.keyword): rule
        for rule in rules
        for qualified_name in rule.qualified_names
    }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        module = node.func.value.id
        if module not in module_aliases or _shadowed_in_enclosing_function(tree, node, module):
            continue
        symbol = f"{module_aliases[module]}.{node.func.attr}"
        keywords = {keyword.arg for keyword in node.keywords if keyword.arg is not None}
        for keyword in keywords:
            rule = rule_by_key.get((symbol, keyword))
            if rule is None:
                continue
            findings.append(
                Finding(
                    id=finding_id(rule, relative_path, node.lineno),
                    rule_id=rule.id,
                    span=SourceSpan(
                        path=relative_path,
                        line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                    ),
                    symbol=symbol,
                    keyword=keyword,
                    impact=rule.impact,
                    evidence="reviewed-rule/direct-call-match",
                    source_url=rule.source_url,
                    suggestion=rule.suggestion,
                )
            )
    return sorted(findings, key=lambda item: (item.span.path, item.span.line, item.rule_id)), []
```

Implement `_shadowed_in_enclosing_function(tree, call, name) -> bool` conservatively:

1. Find the narrowest `FunctionDef`, `AsyncFunctionDef`, or `Lambda` whose line range contains the call.
2. Treat parameters and every `ast.Name(id=name, ctx=ast.Store())` in that function as local for the entire function.
3. Return `True` when the import name is local.
4. Do not implement control-flow dataflow, star imports, `getattr`, `**kwargs`, factories, re-exports, or instance type inference in this slice; include those in coverage limitations.

This deliberately supports only qualified `import httpx` and `import httpx as alias` calls. Direct `from httpx import Client` support remains outside the showcase unless a benchmark case proves it is required.

- [ ] **Step 4: Build deterministic reports and atomic output**

Create `src/openfield/report.py` with:

```python
import json
import os
from pathlib import Path

from openfield.models import Coverage, Finding, Report, Upgrade


LIMITATIONS = (
    "This slice recognizes direct qualified calls only.",
    "Dynamic imports, star imports, getattr, **kwargs, wrappers, and inferred instances are unresolved.",
    "A clean report is not proof that the upgrade is safe.",
)


def build_report(
    upgrade: Upgrade,
    findings: list[Finding],
    parsed_files: int,
    skipped_files: int,
    extra_limitations: list[str],
) -> Report:
    return Report(
        upgrade=upgrade,
        findings=tuple(findings),
        coverage=Coverage(
            complete=False,
            parsed_files=parsed_files,
            skipped_files=skipped_files,
            limitations=LIMITATIONS + tuple(extra_limitations),
        ),
    )


def write_report(report: Report, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, output)
```

- [ ] **Step 5: Wire the `analyze` command and exit policy**

Extend `src/openfield/cli.py` with an `analyze` subparser requiring `PATH`, `--package`, `--from`, `--to`, `--root`, and `--output`.

Command behavior:

- Resolve both root and target with `Path.resolve()` and reject a target outside root.
- Read source with `tokenize.open()`; do not import it.
- Convert invalid versions, missing packs, missing paths, and outside-root paths to a concise stderr message and exit `2`.
- Return `1` when a reviewed finding exists, `0` when no finding exists, and preserve incomplete coverage in JSON.
- Refuse to overwrite an existing output unless `--overwrite` is present.

- [ ] **Step 6: Run the deterministic vertical slice**

Run:

```bash
uv run pytest tests/test_contract.py tests/test_rules.py tests/test_analyze.py -v
uv run openfield analyze examples/httpx_028/direct_client.py \
  --package httpx --from 0.27.2 --to 0.28.0 --root . \
  --output /tmp/openfield-report.json
uv run python -c 'import json; from pathlib import Path; expected=json.loads(Path("examples/httpx_028/expected-report.json").read_text()); actual=json.loads(Path("/tmp/openfield-report.json").read_text()); assert actual == expected'
```

Expected: pytest passes; the command exits `1`; the parsed generated report equals the manual contract. If fields differ, revise the implementation or explicitly revise the manual contract before proceeding.

- [ ] **Step 7: Commit the first working product**

```bash
git add src/openfield/analyze.py src/openfield/report.py src/openfield/cli.py src/openfield/models.py tests/test_analyze.py
git commit -m "feat: report reviewed HTTPX upgrade impacts"
```

### Task 4: Build the Versioned Evidence Corpus, Graph, and Lexical Baseline

**Files:**
- Create: `src/openfield/corpus/demo.jsonl`
- Create: `src/openfield/evidence.py`
- Modify: `src/openfield/models.py`
- Modify: `src/openfield/cli.py`
- Create: `tests/test_evidence.py`

**Interfaces:**
- Consumes: `examples/httpx_028/environment.json`, the deterministic `Report`, and JSONL `EvidenceChunk` records.
- Produces: `open_database(path: Path) -> sqlite3.Connection`, `ingest_demo(connection, corpus, environment, report) -> None`, `lexical_search(...) -> list[RetrievedEvidence]`, and typed graph edges for Tasks 5-7.

- [ ] **Step 1: Add concrete evidence and retrieval schemas**

Append these models to `src/openfield/models.py`:

```python
class Relation(StrictModel):
    source: str
    relation: str
    target: str


class EvidenceChunk(StrictModel):
    id: str
    package: str
    version: str
    heading: str
    text: str
    source_url: str
    source_digest: str
    entity_ids: tuple[str, ...]
    relations: tuple[Relation, ...]


class RetrievedEvidence(StrictModel):
    id: str
    text: str
    source_url: str
    heading: str
    package: str
    version: str
    score: float
    origins: tuple[str, ...]
```

Use SHA-256 digests calculated from the exact authored `text` field when creating the JSONL records. The checked-in digest is therefore independently verifiable without downloading upstream pages.

- [ ] **Step 2: Create the authored twelve-record corpus**

Create `src/openfield/corpus/demo.jsonl` with five answer-bearing records and seven same-release distractors, one valid JSON object per line. The distractors keep `top_k=6` below corpus size and test whether retrieval separates the removed arguments from other HTTPX 0.28.0 changes:

```json
{"id":"httpx-0.26.0-proxies-deprecated","package":"httpx","version":"0.26.0","heading":"proxy argument and proxies deprecation","text":"HTTPX 0.26.0 added proxy for a single proxy, recommended mounts for more complex routing, and deprecated proxies.","source_url":"https://github.com/encode/httpx/releases/tag/0.26.0","source_digest":"df40abbd66917192c00883ebdf9ef76ba0667ca95424cffd59e831e288b8b706","entity_ids":["package:httpx","release:httpx:0.26.0","parameter:httpx.Client:proxies","parameter:httpx.Client:proxy","parameter:httpx.Client:mounts"],"relations":[{"source":"release:httpx:0.26.0","relation":"deprecates","target":"parameter:httpx.Client:proxies"},{"source":"parameter:httpx.Client:proxy","relation":"replaces_simple_case","target":"parameter:httpx.Client:proxies"},{"source":"parameter:httpx.Client:mounts","relation":"replaces_complex_case","target":"parameter:httpx.Client:proxies"}]}
{"id":"httpx-0.27.0-app-deprecated","package":"httpx","version":"0.27.0","heading":"app shortcut deprecated","text":"HTTPX 0.27.0 deprecated the app shortcut and recommended explicit WSGITransport or ASGITransport configuration.","source_url":"https://github.com/encode/httpx/releases/tag/0.27.0","source_digest":"b03736c5c49699cb8a048cc4ff7a4e5ca8d3b54eb4eaed7d2135526fd1e07b37","entity_ids":["package:httpx","release:httpx:0.27.0","parameter:httpx.Client:app","symbol:httpx.WSGITransport","symbol:httpx.ASGITransport"],"relations":[{"source":"release:httpx:0.27.0","relation":"deprecates","target":"parameter:httpx.Client:app"},{"source":"symbol:httpx.ASGITransport","relation":"replaces","target":"parameter:httpx.Client:app"},{"source":"symbol:httpx.WSGITransport","relation":"replaces","target":"parameter:httpx.Client:app"}]}
{"id":"httpx-0.28.0-client-arguments-removed","package":"httpx","version":"0.28.0","heading":"deprecated client arguments removed","text":"HTTPX 0.28.0 removed the previously deprecated proxies and app client arguments.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"44562942fc39cf9a5c9144d85d22d13dcd9dea36e7c627417a58e3cc9cb28803","entity_ids":["package:httpx","release:httpx:0.28.0","parameter:httpx.Client:proxies","parameter:httpx.Client:app"],"relations":[{"source":"release:httpx:0.28.0","relation":"removes","target":"parameter:httpx.Client:proxies"},{"source":"release:httpx:0.28.0","relation":"removes","target":"parameter:httpx.Client:app"}]}
{"id":"starlette-0.36.3-testclient-httpx-app","package":"starlette","version":"0.36.3","heading":"TestClient incompatibility with HTTPX 0.28","text":"Starlette 0.36.3 TestClient passed app to httpx.Client, which fails when paired with HTTPX 0.28.0 after that argument was removed.","source_url":"https://github.com/Kludex/starlette/discussions/2770","source_digest":"03f4c0266a2ad1c8a2c3b87caee7748de3dd6872f3aa6d65429c1ffe8a9ecddb","entity_ids":["package:starlette","release:starlette:0.36.3","symbol:starlette.TestClient","package:httpx","parameter:httpx.Client:app"],"relations":[{"source":"release:starlette:0.36.3","relation":"contains","target":"symbol:starlette.TestClient"},{"source":"symbol:starlette.TestClient","relation":"passes","target":"parameter:httpx.Client:app"}]}
{"id":"starlette-0.37.2-testclient-transport","package":"starlette","version":"0.37.2","heading":"TestClient stops passing app to HTTPX","text":"Starlette 0.37.2 removed the deprecated app argument passed by TestClient to httpx.Client.","source_url":"https://www.starlette.io/release-notes/#0372-march-5-2024","source_digest":"8caa97115a180f25d37747eccff445e4a066a84e16cdb2273b5cc9d183568109","entity_ids":["package:starlette","release:starlette:0.37.2","symbol:starlette.TestClient","parameter:httpx.Client:app"],"relations":[{"source":"release:starlette:0.37.2","relation":"changes","target":"symbol:starlette.TestClient"},{"source":"release:starlette:0.37.2","relation":"stops_passing","target":"parameter:httpx.Client:app"}]}
{"id":"httpx-0.28.0-verify-string-deprecated","package":"httpx","version":"0.28.0","heading":"string verify values deprecated","text":"HTTPX 0.28.0 deprecated string values for verify while retaining boolean and SSLContext usage.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"7d99b54041fb19af0914e71ec58d8db3feb43826a955d88f90cdfb37ebff82fa","entity_ids":["release:httpx:0.28.0","parameter:httpx.Client:verify"],"relations":[{"source":"release:httpx:0.28.0","relation":"deprecates_string_form","target":"parameter:httpx.Client:verify"}]}
{"id":"httpx-0.28.0-cert-deprecated","package":"httpx","version":"0.28.0","heading":"cert argument deprecated","text":"HTTPX 0.28.0 deprecated the cert argument as part of simplifying SSL configuration.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"6f6a13918e1dcd89f1c096a7a02d9cfe966257f88b85a5b555cdc1389db435b8","entity_ids":["release:httpx:0.28.0","parameter:httpx.Client:cert"],"relations":[{"source":"release:httpx:0.28.0","relation":"deprecates","target":"parameter:httpx.Client:cert"}]}
{"id":"httpx-0.28.0-compact-json","package":"httpx","version":"0.28.0","heading":"compact JSON request bodies","text":"HTTPX 0.28.0 changed JSON request bodies to use a compact representation.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"74e6a70ee5b515c60160ee1c8b8f5c14da437e09693beb3e7221b376e0a3df5e","entity_ids":["release:httpx:0.28.0","feature:httpx:json-request-body"],"relations":[{"source":"release:httpx:0.28.0","relation":"changes","target":"feature:httpx:json-request-body"}]}
{"id":"httpx-0.28.0-url-escape-review","package":"httpx","version":"0.28.0","heading":"URL percent escape review","text":"HTTPX 0.28.0 reviewed URL percent escape sets against the WHATWG specification.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"1426abc28612d1797d36601a5b86ab7164e169068e1f96019d0f8127b9b59d1b","entity_ids":["release:httpx:0.28.0","feature:httpx:url-percent-escape"],"relations":[{"source":"release:httpx:0.28.0","relation":"reviews","target":"feature:httpx:url-percent-escape"}]}
{"id":"httpx-0.28.0-lazy-imports","package":"httpx","version":"0.28.0","heading":"conditional certifi and httpcore imports","text":"HTTPX 0.28.0 imports certifi and httpcore only when they are required.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"cf3f014d5a4f2c1ed73f41d5cefc056977e12b9191d1d7358ee8c41db1d02d10","entity_ids":["release:httpx:0.28.0","feature:httpx:conditional-imports"],"relations":[{"source":"release:httpx:0.28.0","relation":"changes","target":"feature:httpx:conditional-imports"}]}
{"id":"httpx-0.28.0-socks5h","package":"httpx","version":"0.28.0","heading":"socks5h proxy scheme","text":"HTTPX 0.28.0 recognizes socks5h as a valid proxy scheme.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"727331d98e523ede541b637a94a946b06de7d34592ab97d9eb63f28747bba216","entity_ids":["release:httpx:0.28.0","feature:httpx:socks5h"],"relations":[{"source":"release:httpx:0.28.0","relation":"recognizes","target":"feature:httpx:socks5h"}]}
{"id":"httpx-0.28.0-empty-params","package":"httpx","version":"0.28.0","heading":"empty params replace query string","text":"HTTPX 0.28.0 makes params={} replace an existing query string instead of merging with it.","source_url":"https://github.com/encode/httpx/releases/tag/0.28.0","source_digest":"d928d958d0f3f84c6496cc8099d904da08e0841fb4d7d66f110d17fc9686d971","entity_ids":["release:httpx:0.28.0","parameter:httpx.Request:params"],"relations":[{"source":"release:httpx:0.28.0","relation":"changes","target":"parameter:httpx.Request:params"}]}
```

- [ ] **Step 3: Write failing graph, provenance, FTS, and wrong-version tests**

Create `tests/test_evidence.py`:

```python
import json
from pathlib import Path

from openfield.evidence import ingest_demo, lexical_search, open_database, provenance_path
from openfield.models import Report


def load_expected_report() -> Report:
    return Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text())


def test_ingestion_is_idempotent_and_every_edge_has_provenance(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    for _ in range(2):
        ingest_demo(
            connection,
            Path("src/openfield/corpus/demo.jsonl"),
            Path("examples/httpx_028/environment.json"),
            load_expected_report(),
        )
    assert connection.execute("SELECT count(*) FROM chunks").fetchone()[0] == 14
    assert connection.execute("SELECT count(*) FROM edges WHERE chunk_id IS NULL").fetchone()[0] == 0


def test_lexical_search_filters_package_and_version(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    ingest_demo(connection, Path("src/openfield/corpus/demo.jsonl"), Path("examples/httpx_028/environment.json"), load_expected_report())

    results = lexical_search(connection, "removed proxies", "httpx", {"0.28.0"}, limit=6)
    assert results[0].id == "httpx-0.28.0-client-arguments-removed"
    assert all(result.package == "httpx" and result.version == "0.28.0" for result in results)


def test_fts_query_text_cannot_change_sql(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    ingest_demo(connection, Path("src/openfield/corpus/demo.jsonl"), Path("examples/httpx_028/environment.json"), load_expected_report())
    assert lexical_search(connection, '\" OR 1=1 --', "httpx", {"0.28.0"}, limit=6) == []
    assert connection.execute("SELECT count(*) FROM chunks").fetchone()[0] == 14


def test_provenance_path_connects_starlette_to_httpx_removal(tmp_path: Path) -> None:
    connection = open_database(tmp_path / "evidence.db")
    ingest_demo(connection, Path("src/openfield/corpus/demo.jsonl"), Path("examples/httpx_028/environment.json"), load_expected_report())
    path = provenance_path(
        connection,
        "release:starlette:0.36.3",
        "parameter:httpx.Client:app",
        max_depth=3,
        allowed_relations={"contains", "passes"},
    )
    assert path == [
        "release:starlette:0.36.3",
        "symbol:starlette.TestClient",
        "parameter:httpx.Client:app",
    ]
```

The expected fourteen chunks are the twelve corpus records, one generated environment-provenance chunk, and one deterministic finding chunk derived from the report. This is still a development-sized corpus, but `top_k=6` can no longer retrieve nearly everything.

- [ ] **Step 4: Run tests and verify the storage module is absent**

Run:

```bash
uv run pytest tests/test_evidence.py -v
```

Expected: collection fails because `openfield.evidence` does not exist.

- [ ] **Step 5: Implement the minimal SQLite schema**

Create `src/openfield/evidence.py` with `sqlite3.connect`, `PRAGMA foreign_keys = ON`, and this schema:

```sql
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
```

Use `INSERT ... ON CONFLICT DO UPDATE` for authored chunks and `INSERT OR IGNORE` for entity/edge identities. On chunk update, delete and reinsert the matching `chunks_fts` row inside the same transaction.

`ingest_demo()` must also:

- Insert `project:demo-project -> release:starlette:0.36.3` and `release:starlette:0.36.3 -> release:httpx:0.28.0` edges from `environment.json` with a generated chunk ID `environment:owned-demo-fixture`.
- Insert one chunk with ID `finding:httpx.client.proxies.removed:examples/httpx_028/direct_client.py:3`. Add `project:demo-project -[contains_usage]-> usage:examples/httpx_028/direct_client.py:3`, `usage:examples/httpx_028/direct_client.py:3 -[matches]-> rule:httpx.client.proxies.removed`, and `rule:httpx.client.proxies.removed -[targets]-> parameter:httpx.Client:proxies`, all with the finding chunk as provenance. The authored HTTPX release chunk separately owns the `release:httpx:0.28.0 -[removes]-> parameter:httpx.Client:proxies` edge.
- Verify every corpus `source_digest` before inserting it.
- Roll back the whole transaction on malformed JSON, digest mismatch, or a missing edge endpoint.

Store the generated environment chunk with `package="environment"`, `version="owned-demo-fixture"`, `source_url="owned:examples/httpx_028/environment.json"`, and the SHA-256 of the raw fixture bytes. Store the generated finding chunk with `package="httpx"`, `version="0.28.0"`, the finding's source URL, text assembled only from the finding fields, and the SHA-256 of that exact text.

Derive each entity's `kind` from the prefix before the first colon and its label from the final colon-separated segment. Store these explicit aliases: `package:httpx -> ["httpx"]`, `parameter:httpx.Client:proxies -> ["proxies", "httpx.Client proxies"]`, `parameter:httpx.Client:app -> ["app", "httpx.Client app"]`, `package:starlette -> ["starlette"]`, and `symbol:starlette.TestClient -> ["TestClient", "starlette TestClient"]`. All other entities use an empty alias list.

- [ ] **Step 6: Implement safe lexical search and bounded graph traversal**

Build the FTS expression only from alphanumeric/dotted identifier tokens:

```python
import re


def fts_expression(question: str) -> str | None:
    raw_terms = re.findall(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", question)
    terms = [
        term
        for term in raw_terms
        if not term.isdigit() and term.casefold() not in {"and", "not", "or"}
    ]
    return " OR ".join(f'"{term}"' for term in terms[:12]) or None
```

Pass the expression, package, versions, and limit as SQL parameters. Construct only the count of `?` placeholders for the version set. Return `[]` when the expression or version set is empty.

Implement `provenance_path()` as breadth-first search over rows loaded with parameterized SQL, a visited set, an optional `allowed_relations: set[str] | None`, and an enforced `max_depth <= 6`. Preserve edge direction for reported paths.

- [ ] **Step 7: Add an explicit evidence-build command**

Extend `src/openfield/cli.py` with:

```text
openfield evidence build --database PATH --corpus src/openfield/corpus/demo.jsonl \
  --environment examples/httpx_028/environment.json \
  --report examples/httpx_028/expected-report.json
```

It may write only the named database. It makes no network request.

- [ ] **Step 8: Run storage and lexical checks**

Run:

```bash
uv run pytest tests/test_evidence.py -v
uv run openfield evidence build --database /tmp/openfield-evidence.db \
  --corpus src/openfield/corpus/demo.jsonl \
  --environment examples/httpx_028/environment.json \
  --report examples/httpx_028/expected-report.json
sqlite3 /tmp/openfield-evidence.db "PRAGMA foreign_key_check; SELECT count(*) FROM chunks;"
```

Expected: pytest passes; `foreign_key_check` prints no rows; the chunk count is `14`.

- [ ] **Step 9: Commit the evidence graph**

```bash
git add src/openfield/models.py src/openfield/evidence.py src/openfield/cli.py src/openfield/corpus/demo.jsonl tests/test_evidence.py
git commit -m "feat: add versioned evidence graph and lexical search"
```

### Task 5: Add Optional Exact Vector Retrieval Without Weakening Offline Behavior

**Files:**
- Create: `src/openfield/retrieval.py`
- Modify: `src/openfield/evidence.py`
- Modify: `src/openfield/cli.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: stored chunks and caller-supplied NumPy vectors.
- Produces: `store_vectors(...)`, `vector_search(...)`, `prepare_model(...)`, and the optional `FastEmbed` adapter used by Tasks 6 and 9.

- [ ] **Step 1: Add only the implemented semantic dependencies**

Run:

```bash
uv add --optional semantic fastembed numpy
```

Do not import either package from `openfield.__init__`, `cli`, `analyze`, `rules`, or `report` at module import time.

- [ ] **Step 2: Write deterministic vector and missing-artifact tests**

Add these tests to `tests/test_retrieval.py`:

```python
from pathlib import Path

import numpy as np
import pytest

from openfield.evidence import ingest_demo, open_database
from openfield.models import Report
from openfield.retrieval import MissingModelError, store_vectors, vector_search


def seeded_database(tmp_path: Path):
    connection = open_database(tmp_path / "evidence.db")
    report = Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text())
    ingest_demo(connection, Path("src/openfield/corpus/demo.jsonl"), Path("examples/httpx_028/environment.json"), report)
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
```

- [ ] **Step 3: Run the tests and verify vector functions are absent**

Run:

```bash
uv run --extra semantic pytest tests/test_retrieval.py -v
```

Expected: collection fails because `openfield.retrieval` does not exist.

- [ ] **Step 4: Implement float32 storage and exact cosine search**

In `src/openfield/retrieval.py`, keep NumPy behind the semantic boundary, normalize at write and query time, and store little-endian float32 bytes:

```python
from collections.abc import Sequence
from typing import Any


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
    return vector / norm


def encode_vector(vector: Sequence[float]) -> tuple[int, bytes]:
    normalized = normalize(vector)
    return normalized.size, normalized.tobytes()


def decode_vector(blob: bytes, dimensions: int):
    np = require_numpy()
    vector = np.frombuffer(blob, dtype="<f4")
    if vector.size != dimensions:
        raise ValueError("stored embedding dimensions do not match metadata")
    return vector
```

`vector_search()` must load only rows joined to chunks matching the requested package/version set, reject a model/dimension mismatch, compute `matrix @ normalized_query`, and sort by descending score then chunk ID for deterministic ties. Exact search is the intended implementation under 10,000 chunks.

- [ ] **Step 5: Add a thin FastEmbed adapter and explicit preparation command**

Keep the optional import inside the called function:

```python
MODEL_ID = "BAAI/bge-small-en-v1.5"


def fastembed_vectors(
    texts: list[str], cache_dir: Path, local_only: bool
) -> list[Sequence[float]]:
    try:
        from fastembed import TextEmbedding
    except ImportError as exc:
        raise MissingModelError("install with: uv sync --extra semantic") from exc
    np = require_numpy()
    model = TextEmbedding(
        model_name=MODEL_ID,
        cache_dir=str(cache_dir),
        local_files_only=local_only,
    )
    return [np.asarray(vector, dtype=np.float32) for vector in model.embed(texts)]
```

Add:

```text
openfield model prepare --cache-dir PATH
openfield evidence embed --database PATH --cache-dir PATH
```

`model prepare` may download the named model. `evidence embed`, `analyze`, `ask`, and API startup must pass `local_files_only=True` and fail with an actionable preparation message when artifacts are absent.

- [ ] **Step 6: Verify core and semantic installations separately**

Run:

```bash
uv run pytest tests/test_contract.py tests/test_rules.py tests/test_analyze.py tests/test_evidence.py -q
uv run --extra semantic pytest tests/test_retrieval.py -v
uv run python -c "import openfield, openfield.retrieval, sys; assert 'fastembed' not in sys.modules and 'numpy' not in sys.modules"
```

Expected: all tests pass; importing core and importing `openfield.retrieval` without invoking vector functions do not import FastEmbed or NumPy.

- [ ] **Step 7: Commit vector retrieval**

```bash
git add pyproject.toml uv.lock src/openfield/retrieval.py src/openfield/evidence.py src/openfield/cli.py tests/test_retrieval.py
git commit -m "feat: add optional exact vector retrieval"
```

### Task 6: Add Deterministic Routing, Rank Fusion, and Graph Expansion

**Files:**
- Modify: `src/openfield/models.py`
- Modify: `src/openfield/retrieval.py`
- Modify: `tests/test_retrieval.py`

**Interfaces:**
- Consumes: lexical results, vector results, known entity labels/aliases, and stored edges.
- Produces: `route_question(question: str) -> RetrievalMode`, `reciprocal_rank_fusion(...)`, `graph_expand(...)`, and `retrieve(...) -> list[RetrievedEvidence]`.

- [ ] **Step 1: Write routing, fusion, cycle, and wrong-version tests**

Append to `tests/test_retrieval.py`:

```python
from openfield.retrieval import RetrievalMode, reciprocal_rank_fusion, route_question


def test_router_uses_graph_for_relationship_questions() -> None:
    assert route_question("Why does Starlette 0.36.3 break with HTTPX 0.28.0?") is RetrievalMode.HYBRID_GRAPH
    assert route_question("What was removed in HTTPX 0.28.0?") is RetrievalMode.HYBRID


def test_rrf_is_deterministic_and_deduplicates() -> None:
    fused = reciprocal_rank_fusion(
        [["a", "b"], ["b", "c"]],
        rank_constant=60,
    )
    assert [chunk_id for chunk_id, _ in fused] == ["b", "a", "c"]


def test_hybrid_graph_does_not_cross_package_version_filters(tmp_path: Path) -> None:
    connection = seeded_database(tmp_path)
    from openfield.retrieval import graph_expand

    results = graph_expand(
        connection,
        seed_entities={"release:httpx:0.28.0"},
        allowed_packages={"httpx"},
        allowed_versions={"0.28.0"},
        max_depth=3,
        limit=6,
    )
    assert {result.package for result in results} <= {"httpx"}
    assert {result.version for result in results} <= {"0.28.0"}


def test_graph_expansion_terminates_on_cycles(tmp_path: Path) -> None:
    connection = seeded_database(tmp_path)
    connection.execute(
        "INSERT OR IGNORE INTO edges VALUES (?, ?, ?, ?)",
        ("parameter:httpx.Client:app", "related", "release:starlette:0.36.3", "starlette-0.36.3-testclient-httpx-app"),
    )
    from openfield.retrieval import graph_expand

    results = graph_expand(
        connection,
        seed_entities={"release:starlette:0.36.3"},
        allowed_packages={"httpx", "starlette"},
        allowed_versions={"0.28.0", "0.36.3"},
        max_depth=3,
        limit=6,
    )
    assert len(results) <= 6
```

- [ ] **Step 2: Add retrieval mode and simple routing**

Use stdlib `StrEnum`:

```python
from enum import StrEnum


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
```

Keep `--retrieval` as an explicit CLI/API override so the benchmark never depends on router behavior.

- [ ] **Step 3: Implement reciprocal-rank fusion**

```python
def reciprocal_rank_fusion(
    rankings: list[list[str]],
    rank_constant: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rank_constant + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))
```

- [ ] **Step 4: Implement bounded entity resolution and graph expansion**

Entity resolution for this showcase is deterministic:

- Match case-folded exact labels and aliases stored in `entities.aliases_json`.
- Include aliases `httpx`, `httpx.Client`, `proxies`, `app`, `starlette`, and `TestClient` in ingestion.
- Do not use embedding similarity for entity resolution until an evaluation shows exact aliases miss relevant queries.
- Traverse directed edges to depth `3` by default and never above `6`.
- Collect only chunks attached to visited edges and still matching allowed packages and versions.

Each `RetrievedEvidence.origins` value must show whether it came from `lexical`, `vector`, or `graph:<entity-id>`.

- [ ] **Step 5: Implement the unified retrieval function**

Implement `retrieve(connection, question: str, mode: RetrievalMode, packages: set[str], versions: set[str], top_k: int = 6, query_vector: Sequence[float] | None = None, model_id: str | None = None) -> list[RetrievedEvidence]`. Import `Sequence` from `collections.abc`; keep NumPy imports inside vector-only functions so lexical fallback remains importable without the semantic extra.

Behavior:

- `LEXICAL`: return FTS results.
- `VECTOR`: require `query_vector` and `model_id`; return exact vector results.
- `HYBRID`: fuse the first 20 lexical and vector IDs, then return the best six.
- `HYBRID_GRAPH`: start from hybrid candidates, resolve question entities, add chunks from bounded graph paths, fuse once more, and return the best six.
- Never accept a graph-expanded chunk that violates package/version filters.
- When semantic artifacts are unavailable and the user did not explicitly demand vector mode, return lexical/graph evidence with `vector-unavailable` in result metadata; when vector mode was explicit, raise `MissingModelError`.

- [ ] **Step 6: Run retrieval checks**

Run:

```bash
uv run --extra semantic pytest tests/test_retrieval.py -v
uv run ruff check src/openfield/retrieval.py tests/test_retrieval.py
```

Expected: all retrieval tests pass with fake vectors; no test downloads a model.

- [ ] **Step 7: Commit hybrid graph retrieval**

```bash
git add src/openfield/models.py src/openfield/retrieval.py tests/test_retrieval.py
git commit -m "feat: add hybrid graph retrieval"
```

### Task 7: Generate Grounded Answers and Reject Invalid Citations

**Files:**
- Create: `src/openfield/answering.py`
- Modify: `src/openfield/models.py`
- Modify: `src/openfield/cli.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/test_answering.py`

**Interfaces:**
- Consumes: question plus `list[RetrievedEvidence]`.
- Produces: `answer_from_evidence(...) -> Answer`, deterministic abstention, and optional Anthropic generation with bounded attempts.

- [ ] **Step 1: Add only the implemented AI dependency**

Run:

```bash
uv add --optional ai anthropic
```

- [ ] **Step 2: Define answer schemas**

Append to `src/openfield/models.py`:

```python
class Claim(StrictModel):
    text: str
    citation_ids: tuple[str, ...]


class Answer(StrictModel):
    question: str
    claims: tuple[Claim, ...]
    abstained: bool
    limitations: tuple[str, ...]
    retrieval_mode: str
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class Generation(StrictModel):
    text: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
```

- [ ] **Step 3: Write citation, abstention, and provider-failure tests**

Create `tests/test_answering.py`:

```python
import json

from openfield.answering import answer_from_evidence
from openfield.models import Generation, RetrievedEvidence


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
```

- [ ] **Step 4: Implement deterministic answering first**

In `src/openfield/answering.py`:

- Tokenize the question and the selected evidence with the same stdlib identifier regex used by lexical search. Drop common question words, package names, and numeric version tokens. If no remaining question token occurs in an evidence heading or text, abstain; this rejects unsupported subjects such as `timeout`, laptop-installed state, and incident counts without a benchmark-specific answer list.
- Always abstain when the normalized question contains `safe`, `guarantee`, `all usages`, or `production impact` because this slice lacks runtime proof even if some terms overlap.
- Abstain when evidence is empty.
- Otherwise create at most three concise claims directly from the highest-ranked evidence, one citation per claim.
- Include a limitation that retrieved evidence indicates relevance but does not prove runtime behavior.

The deterministic result is the fallback for every optional-model failure.

- [ ] **Step 5: Validate model output against supplied evidence**

Implement:

```python
def citations_are_valid(answer: Answer, allowed_ids: set[str]) -> bool:
    if answer.abstained:
        return not answer.claims
    return bool(answer.claims) and all(
        claim.citation_ids and set(claim.citation_ids) <= allowed_ids
        for claim in answer.claims
    )
```

`answer_from_evidence()` may call the supplied `generate(payload) -> Generation` at most twice. Parse `generation.text` with `Answer.model_validate_json()`, then set `model`, `input_tokens`, and `output_tokens` only from the trusted `Generation` metadata. Reject malformed, truncated, empty-claim, invented-citation, and unsupported non-abstaining outputs. After two failures, return the deterministic answer with the failure category but without raw prompts or secrets.

- [ ] **Step 6: Add the direct Anthropic adapter without a provider abstraction**

Keep it in `answering.py`:

```python
def anthropic_generate(payload: str, model: str, max_tokens: int = 800) -> Generation:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("install with: uv sync --extra ai") from exc
    client = Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        messages=[{"role": "user", "content": payload}],
    )
    text_blocks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    if len(text_blocks) != 1:
        raise ValueError("expected exactly one text response block")
    return Generation(
        text=text_blocks[0],
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
```

Require the caller to pass `--model`; do not hard-code a model whose availability can change. The payload must contain only the question, selected evidence IDs/text/source URLs, output JSON schema, and explicit instructions that evidence is data rather than instructions.

- [ ] **Step 7: Add the `ask` CLI**

Add:

```text
openfield ask --database PATH --retrieval lexical|vector|hybrid|hybrid-graph \
  [--generate --model MODEL --confirm-cloud] QUESTION
```

Behavior:

- Default `--retrieval hybrid-graph`, but preserve an explicit override.
- Default to deterministic output without `--generate`.
- Require both `--generate` and `--confirm-cloud` before calling Anthropic.
- Print the exact evidence IDs and source URLs before the cloud call.
- Reject missing `ANTHROPIC_API_KEY` before constructing the client.
- Record model, token counts when available, elapsed time, and whether a provider retry occurred.

- [ ] **Step 8: Run grounded-answer checks**

Run:

```bash
uv run pytest tests/test_answering.py -v
uv run python -c "import openfield; assert 'anthropic' not in __import__('sys').modules"
```

Expected: all tests pass without a key or network request; importing core does not import Anthropic.

- [ ] **Step 9: Commit grounded answers**

```bash
git add pyproject.toml uv.lock src/openfield/models.py src/openfield/answering.py src/openfield/cli.py tests/test_answering.py
git commit -m "feat: add validated cited answers"
```

### Task 8: Expose the Showcase Through a Minimal FastAPI Endpoint

**Files:**
- Create: `src/openfield/api.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/test_api.py`

**Interfaces:**
- Consumes: a database path and the retrieval/answering functions from Tasks 6-7.
- Produces: `create_app(database: Path) -> FastAPI`, `GET /healthz`, and `POST /ask`.

- [ ] **Step 1: Add only the implemented web dependencies**

Run:

```bash
uv add --optional web fastapi uvicorn
uv add --dev httpx
```

- [ ] **Step 2: Write endpoint tests without sockets or model calls**

Create `tests/test_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from openfield.api import create_app
from openfield.evidence import ingest_demo, open_database
from openfield.models import Report


def seeded_database(tmp_path: Path) -> Path:
    database = tmp_path / "evidence.db"
    connection = open_database(database)
    report = Report.model_validate_json(Path("examples/httpx_028/expected-report.json").read_text())
    ingest_demo(connection, Path("src/openfield/corpus/demo.jsonl"), Path("examples/httpx_028/environment.json"), report)
    connection.close()
    return database


def test_health_and_deterministic_ask(tmp_path: Path) -> None:
    client = TestClient(create_app(seeded_database(tmp_path)))
    assert client.get("/healthz").json() == {"status": "ok"}

    response = client.post(
        "/ask",
        json={
            "question": "What was removed in HTTPX 0.28.0?",
            "retrieval": "lexical",
            "packages": ["httpx"],
            "versions": ["0.28.0"],
            "generate": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["abstained"] is False
    assert body["claims"][0]["citation_ids"] == ["httpx-0.28.0-client-arguments-removed"]


def test_api_refuses_cloud_generation_without_explicit_server_enablement(tmp_path: Path) -> None:
    client = TestClient(create_app(seeded_database(tmp_path), allow_cloud=False))
    response = client.post(
        "/ask",
        json={
            "question": "What changed?",
            "retrieval": "lexical",
            "packages": ["httpx"],
            "versions": ["0.28.0"],
            "generate": True,
        },
    )
    assert response.status_code == 403
```

- [ ] **Step 3: Run tests and verify the API module is absent**

Run:

```bash
uv run --extra web pytest tests/test_api.py -v
```

Expected: collection fails because `openfield.api` does not exist.

- [ ] **Step 4: Implement the narrow HTTP contract**

Create `src/openfield/api.py` with request validation:

```python
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from openfield.retrieval import RetrievalMode


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=3, max_length=500)
    retrieval: RetrievalMode = RetrievalMode.HYBRID_GRAPH
    packages: list[str] = Field(min_length=1, max_length=4)
    versions: list[str] = Field(min_length=1, max_length=8)
    generate: bool = False
    model: str | None = None


def create_app(database: Path, allow_cloud: bool = False) -> FastAPI:
    app = FastAPI(title="Openfield", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/ask")
    def ask(request: AskRequest):
        if request.generate and not allow_cloud:
            raise HTTPException(status_code=403, detail="cloud generation is disabled")
        return run_question(database, request).model_dump(mode="json")

    return app
```

`run_question()` opens a new SQLite connection per request, enforces a maximum `top_k=6` and graph depth `3`, closes the connection in `finally`, and delegates only to existing retrieval/answering functions. Do not add authentication, background jobs, persistence, or deployment configuration to this showcase API.

- [ ] **Step 5: Add an explicit factory for local demo startup**

Implement `app_from_environment()` that requires `OPENFIELD_DATABASE` and reads `OPENFIELD_ALLOW_CLOUD=true` only when deliberately set. Document this command:

```bash
OPENFIELD_DATABASE=/tmp/openfield-evidence.db \
  uv run --extra web uvicorn openfield.api:app_from_environment --factory --host 127.0.0.1 --port 8000
```

Bind to loopback by default. Do not add Docker or public deployment in this plan.

- [ ] **Step 6: Run API and core import checks**

Run:

```bash
uv run --extra web pytest tests/test_api.py -v
uv run python -c "import openfield; assert 'fastapi' not in __import__('sys').modules"
```

Expected: API tests pass without opening a port; core import does not import FastAPI.

- [ ] **Step 7: Commit the API**

```bash
git add pyproject.toml uv.lock src/openfield/api.py tests/test_api.py
git commit -m "feat: expose deterministic RAG API"
```

### Task 9: Build the Controlled 16-Question Evaluation and Benchmark

**Files:**
- Create: `evals/questions.jsonl`
- Create: `src/openfield/eval.py`
- Create: `tests/test_eval.py`
- Create: `benchmarks/results.json`
- Create: `benchmarks/report.md`
- Modify: `src/openfield/cli.py`

**Interfaces:**
- Consumes: the same database, question set, `top_k=6`, and retrieval modes used by the product.
- Produces: per-question raw runs, aggregate evidence recall by hop count, abstention accuracy, citation validity, median/p95 latency, and a vector-only versus hybrid-graph report.

- [ ] **Step 1: Add evaluation schemas**

Append to `src/openfield/models.py`:

```python
class EvaluationCase(StrictModel):
    id: str
    question: str
    hop_count: Literal[0, 1, 2, 3]
    packages: tuple[str, ...]
    versions: tuple[str, ...]
    required_evidence_ids: tuple[str, ...]
    answerable: bool


class EvaluationResult(StrictModel):
    case_id: str
    mode: str
    retrieved_ids: tuple[str, ...]
    citation_ids: tuple[str, ...]
    abstained: bool
    latency_ms: float
```

- [ ] **Step 2: Create the labeled question set**

Create `evals/questions.jsonl` with these 16 cases. Each line is one JSON object using the schema above:

```json
{"id":"single-removed-proxies","question":"Which HTTPX client argument was removed in 0.28.0 for proxy configuration?","hop_count":1,"packages":["httpx"],"versions":["0.28.0"],"required_evidence_ids":["httpx-0.28.0-client-arguments-removed"],"answerable":true}
{"id":"single-proxies-deprecated","question":"When was proxies deprecated and what simple replacement was introduced?","hop_count":1,"packages":["httpx"],"versions":["0.26.0"],"required_evidence_ids":["httpx-0.26.0-proxies-deprecated"],"answerable":true}
{"id":"single-app-deprecated","question":"What explicit transports replace the HTTPX app shortcut?","hop_count":1,"packages":["httpx"],"versions":["0.27.0"],"required_evidence_ids":["httpx-0.27.0-app-deprecated"],"answerable":true}
{"id":"single-starlette-fix","question":"Which Starlette release stopped passing app to httpx.Client?","hop_count":1,"packages":["starlette"],"versions":["0.37.2"],"required_evidence_ids":["starlette-0.37.2-testclient-transport"],"answerable":true}
{"id":"two-direct-usage","question":"Where does the demo project use an HTTPX argument removed in 0.28.0?","hop_count":2,"packages":["httpx"],"versions":["0.28.0"],"required_evidence_ids":["finding:httpx.client.proxies.removed:examples/httpx_028/direct_client.py:3","httpx-0.28.0-client-arguments-removed"],"answerable":true}
{"id":"two-proxy-migration","question":"Why is the proxies call affected and which migration options are documented?","hop_count":2,"packages":["httpx"],"versions":["0.26.0","0.28.0"],"required_evidence_ids":["httpx-0.26.0-proxies-deprecated","httpx-0.28.0-client-arguments-removed"],"answerable":true}
{"id":"two-starlette-app","question":"Which removed HTTPX parameter did Starlette 0.36.3 TestClient pass?","hop_count":2,"packages":["httpx","starlette"],"versions":["0.28.0","0.36.3"],"required_evidence_ids":["httpx-0.28.0-client-arguments-removed","starlette-0.36.3-testclient-httpx-app"],"answerable":true}
{"id":"two-compatible-starlette","question":"What Starlette change avoids the removed HTTPX app argument?","hop_count":2,"packages":["httpx","starlette"],"versions":["0.28.0","0.37.2"],"required_evidence_ids":["httpx-0.28.0-client-arguments-removed","starlette-0.37.2-testclient-transport"],"answerable":true}
{"id":"three-transitive-break","question":"Why can the demo project's tests break even if its own source never calls httpx.Client with app?","hop_count":3,"packages":["httpx","starlette"],"versions":["0.28.0","0.36.3"],"required_evidence_ids":["starlette-0.36.3-testclient-httpx-app","httpx-0.28.0-client-arguments-removed"],"answerable":true}
{"id":"three-remediation-options","question":"For Starlette 0.36.3 with HTTPX 0.28.0, what evidence supports upgrading Starlette rather than changing application source?","hop_count":3,"packages":["httpx","starlette"],"versions":["0.28.0","0.36.3","0.37.2"],"required_evidence_ids":["starlette-0.36.3-testclient-httpx-app","starlette-0.37.2-testclient-transport","httpx-0.28.0-client-arguments-removed"],"answerable":true}
{"id":"three-direct-and-transitive","question":"Which two independent paths can make this demo upgrade relevant?","hop_count":3,"packages":["httpx","starlette"],"versions":["0.28.0","0.36.3"],"required_evidence_ids":["finding:httpx.client.proxies.removed:examples/httpx_028/direct_client.py:3","starlette-0.36.3-testclient-httpx-app","httpx-0.28.0-client-arguments-removed"],"answerable":true}
{"id":"three-provenance","question":"Which sources justify the direct proxies finding and the Starlette TestClient compatibility finding?","hop_count":3,"packages":["httpx","starlette"],"versions":["0.26.0","0.28.0","0.36.3","0.37.2"],"required_evidence_ids":["httpx-0.26.0-proxies-deprecated","httpx-0.28.0-client-arguments-removed","starlette-0.36.3-testclient-httpx-app","starlette-0.37.2-testclient-transport"],"answerable":true}
{"id":"abstain-safe","question":"Is the entire dependency upgrade safe in production?","hop_count":0,"packages":["httpx"],"versions":["0.28.0"],"required_evidence_ids":[],"answerable":false}
{"id":"abstain-installed-version","question":"Which HTTPX version is installed on an arbitrary user's laptop?","hop_count":0,"packages":["httpx"],"versions":["0.28.0"],"required_evidence_ids":[],"answerable":false}
{"id":"abstain-timeout","question":"Did HTTPX 0.28.0 remove the timeout argument?","hop_count":0,"packages":["httpx"],"versions":["0.28.0"],"required_evidence_ids":[],"answerable":false}
{"id":"abstain-production-incidents","question":"How many production incidents did this removal cause?","hop_count":0,"packages":["httpx"],"versions":["0.28.0"],"required_evidence_ids":[],"answerable":false}
```

These cases are a development benchmark, not a statistically strong public claim. Freeze them before tuning retrieval weights. A future held-out set must be separate.

- [ ] **Step 3: Write metric tests before the runner**

Create `tests/test_eval.py`:

```python
from openfield.eval import aggregate
from openfield.models import EvaluationCase, EvaluationResult


def test_aggregate_reports_raw_counts_by_hop_and_abstention() -> None:
    cases = {
        "q1": EvaluationCase(id="q1", question="x", hop_count=2, packages=("httpx",), versions=("0.28.0",), required_evidence_ids=("a", "b"), answerable=True),
        "q2": EvaluationCase(id="q2", question="y", hop_count=0, packages=("httpx",), versions=("0.28.0",), required_evidence_ids=(), answerable=False),
    }
    results = [
        EvaluationResult(case_id="q1", mode="vector", retrieved_ids=("a",), citation_ids=("a",), abstained=False, latency_ms=10),
        EvaluationResult(case_id="q2", mode="vector", retrieved_ids=(), citation_ids=(), abstained=True, latency_ms=20),
    ]
    summary = aggregate(cases, results)
    assert summary["evidence_recall_by_hop"]["2"] == {"found": 1, "required": 2, "rate": 0.5}
    assert summary["abstention"] == {"correct": 1, "total": 1, "rate": 1.0}
    assert summary["latency_ms"]["median"] == 15.0


def test_citation_validity_counts_only_selected_evidence() -> None:
    cases = {
        "q": EvaluationCase(id="q", question="x", hop_count=1, packages=("httpx",), versions=("0.28.0",), required_evidence_ids=("a",), answerable=True)
    }
    results = [
        EvaluationResult(case_id="q", mode="hybrid-graph", retrieved_ids=("a",), citation_ids=("invented",), abstained=False, latency_ms=1)
    ]
    assert aggregate(cases, results)["citation_validity"] == {"valid": 0, "total": 1, "rate": 0.0}
```

- [ ] **Step 4: Implement metrics without an evaluation framework**

In `src/openfield/eval.py` implement:

- JSONL loading through `EvaluationCase.model_validate_json()`.
- One run per `(case, mode)` with `time.perf_counter_ns()`.
- Evidence recall as `len(required & retrieved) / len(required)` with raw found/required counts.
- Correct abstention as `not answerable and abstained`; separately count unnecessary abstentions on answerable cases.
- Citation validity as every answer citation being present in that run's retrieved IDs.
- Median via `statistics.median`.
- p95 as the item at index `ceil(0.95 * n) - 1` in sorted latencies.
- Raw per-question results in JSON before aggregate summaries.
- Group results by retrieval mode before aggregation and write a `summaries_by_mode` object; never combine vector and hybrid-graph numerators into one rate.

Do not use an LLM judge in this plan. The published comparison is retrieval/evidence quality plus deterministic citation and abstention behavior.

- [ ] **Step 5: Add the benchmark command**

Add:

```text
openfield eval --database PATH --questions evals/questions.jsonl \
  --modes vector hybrid-graph --top-k 6 \
  --output benchmarks/results.json --report benchmarks/report.md
```

The command must record:

- Git commit if available.
- Python, Openfield, dependency, model, and corpus identities.
- Hardware/OS from stdlib `platform`.
- `top_k`, retrieval mode, question count, hop-count denominators.
- Cold model preparation separately from warm query timing.
- Median and p95 retrieval latency.
- Evidence recall by hop count, abstention counts, citation validity counts.
- Model/API cost as `0` for the deterministic retrieval benchmark.

- [ ] **Step 6: Run the benchmark twice and verify determinism**

Prepare the semantic model explicitly, then run:

```bash
uv run --extra semantic openfield model prepare --cache-dir .cache/openfield-models
uv run --extra semantic openfield evidence embed \
  --database /tmp/openfield-evidence.db --cache-dir .cache/openfield-models
uv run --extra semantic openfield eval \
  --database /tmp/openfield-evidence.db --questions evals/questions.jsonl \
  --modes vector hybrid-graph --top-k 6 \
  --output /tmp/results-1.json --report /tmp/report-1.md
uv run --extra semantic openfield eval \
  --database /tmp/openfield-evidence.db --questions evals/questions.jsonl \
  --modes vector hybrid-graph --top-k 6 \
  --output /tmp/results-2.json --report /tmp/report-2.md
```

Expected: retrieved IDs and metric numerators/denominators are identical. Timing values may differ. If hybrid graph does not improve multi-hop evidence recall, publish that result and keep the simpler retrieval mode as the recommended default.

- [ ] **Step 7: Save one actual benchmark run**

Copy the second raw result and report only after inspecting every question result:

```bash
cp /tmp/results-2.json benchmarks/results.json
cp /tmp/report-2.md benchmarks/report.md
```

Before committing, replace no values manually. The report generator is the source of all displayed numbers.

- [ ] **Step 8: Commit the evaluation artifact**

```bash
git add src/openfield/models.py src/openfield/eval.py src/openfield/cli.py evals/questions.jsonl tests/test_eval.py benchmarks/results.json benchmarks/report.md
git commit -m "feat: benchmark vector and graph retrieval"
```

### Task 10: Package the Interview Artifact and Run Release-Grade Verification

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `examples/httpx_028/expected-report.json` only if the verified implementation contract changed

**Interfaces:**
- Consumes: verified CLI/API behavior and generated benchmark artifacts.
- Produces: the public two-minute evaluation path and defensible interview narrative.

- [ ] **Step 1: Put measured results first in the README**

README order:

1. One sentence: Openfield connects versioned dependency changes to source usages and retrieves the evidence behind each finding.
2. The generated vector-only versus hybrid-graph table copied from `benchmarks/report.md` with its question count, hardware, model, and date.
3. A terminal example showing the exact deterministic finding and citation.
4. A four-box Mermaid diagram: Analyze -> Evidence graph/index -> Retrieve -> Answer/API.
5. Five-minute quickstart using the owned fixture.
6. What is supported and explicitly unsupported.
7. Evaluation method, raw results link, and failure examples.
8. Privacy/network behavior and optional cloud generation.
9. Design decisions: SQLite versus Neo4j, exact search versus ANN, deterministic routing versus a model router.
10. “What did not work” populated from actual implementation/evaluation evidence.

Do not include a resume metric until `benchmarks/results.json` supports it.

- [ ] **Step 2: Add the interview demonstration commands**

Document this exact sequence:

```bash
uv sync --all-groups --all-extras
uv run openfield analyze examples/httpx_028/direct_client.py \
  --package httpx --from 0.27.2 --to 0.28.0 --root . \
  --output /tmp/openfield-report.json
uv run openfield evidence build --database /tmp/openfield-evidence.db \
  --corpus src/openfield/corpus/demo.jsonl \
  --environment examples/httpx_028/environment.json \
  --report /tmp/openfield-report.json
uv run --extra semantic openfield model prepare --cache-dir .cache/openfield-models
uv run --extra semantic openfield evidence embed \
  --database /tmp/openfield-evidence.db --cache-dir .cache/openfield-models
uv run --extra semantic openfield ask --database /tmp/openfield-evidence.db \
  --retrieval hybrid-graph \
  "Why can Starlette 0.36.3 break with HTTPX 0.28.0?"
OPENFIELD_DATABASE=/tmp/openfield-evidence.db \
  uv run --extra web uvicorn openfield.api:app_from_environment --factory --host 127.0.0.1 --port 8000
```

The demo must show one correct abstention immediately after the answer:

```bash
uv run openfield ask --database /tmp/openfield-evidence.db \
  --retrieval hybrid-graph "Is this entire upgrade safe in production?"
```

- [ ] **Step 3: Verify base and optional installations**

Build distributions and test isolated imports:

```bash
uv build
python3 -m venv /tmp/openfield-core-venv
/tmp/openfield-core-venv/bin/pip install dist/openfield-*.whl
/tmp/openfield-core-venv/bin/python -c "from importlib.resources import files; from openfield.rules import load_pack; assert load_pack('httpx').package == 'httpx'; assert files('openfield').joinpath('corpus', 'demo.jsonl').read_text()"
/tmp/openfield-core-venv/bin/openfield --help
```

Then use `uv` for the full development matrix:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --extra semantic python -c "from fastembed import TextEmbedding"
uv run --extra ai python -c "from anthropic import Anthropic"
uv run --extra web python -c "from openfield.api import create_app"
```

Expected: wheel install and core help work without optional ML/web imports; all tests and formatting checks pass.

- [ ] **Step 4: Run security and boundary checks**

Run targeted tests and inspect output:

```bash
uv run pytest \
  tests/test_analyze.py::test_analyze_never_executes_the_target \
  tests/test_evidence.py::test_fts_query_text_cannot_change_sql \
  tests/test_answering.py::test_invented_citation_falls_back_to_deterministic_answer \
  tests/test_api.py::test_api_refuses_cloud_generation_without_explicit_server_enablement -v
```

Verify that committed JSON/Markdown contains no absolute home-directory paths, API keys, raw private prompts, or copied full upstream documents:

```bash
rg -n '/Users/|ANTHROPIC_API_KEY=|sk-ant-|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY' \
  README.md benchmarks examples evals src tests
```

Expected: no sensitive matches. Documentation may mention the environment variable name without assigning a value.

- [ ] **Step 5: Check every public claim against an artifact**

Create a small table in README with these rows and only verified values:

```text
Claim | Artifact | Verification | Limitation
HTTPX direct usage detection | expected report + test | exact pytest command | direct qualified calls only
Versioned evidence graph | SQLite fixture + path test | provenance test | curated demo corpus
Vector vs hybrid-graph comparison | benchmark results | eval command | 16 development questions
Citation validation | answering tests | invalid-citation test | supplied evidence only
Offline core | import and no-network tests | core wheel smoke test | model/API features are opt-in
```

- [ ] **Step 6: Record the 90-second interview narrative**

Use this sequence in README, adapting only measured numbers:

1. “The problem is not upgrading a package; it is finding which documented changes matter to this code.”
2. Show the deterministic `proxies` finding and its official source.
3. Ask the Starlette/HTTPX question and show the multi-hop evidence path.
4. Show the vector-only versus hybrid-graph result by hop count.
5. Show the safety question correctly abstaining.
6. Explain one measured trade-off and one failure from the benchmark.

- [ ] **Step 7: Commit the completed showcase**

```bash
git add README.md pyproject.toml uv.lock examples/httpx_028/expected-report.json
git commit -m "docs: package the openfield RAG showcase"
```

- [ ] **Step 8: Run the final verification from a clean working tree**

Run:

```bash
git status --short
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
```

Expected: `git status --short` is empty before generated build artifacts; tests, lint, format, and build pass. Report exact test counts, benchmark denominators, artifact paths, and any remaining limitations in the handoff.

## Explicitly Deferred Work

- General recursive repository walking and ignore-file semantics.
- Direct-import aliases, re-exports, instance inference, wrappers, dynamic imports, and `**kwargs` analysis.
- `pyproject.toml`, requirements, `pylock.toml`, or uv metadata importers.
- Automated web fetching or a general crawler; the showcase uses reviewed authored evidence records.
- Additional package packs beyond HTTPX and the narrow Starlette compatibility evidence.
- LLM-assisted rule extraction, model routers, rerankers, agent loops, and chat memory.
- Neo4j, pgvector, Qdrant, ANN indexes, an ORM, a hosted database, Docker, and cloud deployment.
- GitHub Actions integration, PR comments, automated patches, or a GitHub App.
- Claims of production scale, broad package support, user adoption, or statistical superiority.

Add any deferred item only when the benchmark or a real user demonstrates the need.

## Completion Gate

The showcase is complete only when all of the following are true:

- The owned fixture produces the expected reviewed finding without executing target code.
- Every stored graph edge has provenance and repeated ingestion is idempotent.
- Lexical and vector retrieval enforce package/version filters.
- Hybrid graph retrieval exposes the Starlette -> HTTPX multi-hop path without inventing edges.
- Deterministic answers work without model artifacts, a key, or a network connection.
- Generated answers reject invented or unselected citations.
- `/ask` works through FastAPI and cloud generation is disabled by default.
- The same 16 questions run through vector-only and hybrid-graph retrieval with raw results preserved.
- README numbers come directly from the generated benchmark.
- Core wheel installation, full tests, Ruff, formatting, and build all pass.

At that point, the project supports a defensible interview claim such as:

> Built a version-aware RAG system that links Python dependency changes to source usages, combines exact vector search with provenance-bounded graph retrieval, validates claim citations, and compares retrieval quality by hop count, latency, and abstention on a reviewed benchmark.

Replace no nouns or metrics in that sentence with broader claims until new evidence exists.
