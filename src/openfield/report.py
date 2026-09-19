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
