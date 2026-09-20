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
    elapsed_ms: float = Field(default=0.0, ge=0)
    provider_retried: bool = False


class Generation(StrictModel):
    text: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)


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
