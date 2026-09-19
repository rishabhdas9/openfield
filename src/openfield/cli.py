import argparse
import sys
import tokenize
from pathlib import Path

from packaging.version import InvalidVersion
from pydantic import ValidationError

from openfield.analyze import analyze_source
from openfield.evidence import ingest_demo, open_database
from openfield.models import Report, Upgrade
from openfield.report import build_report, write_report
from openfield.rules import applicable_rules, load_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openfield",
        description="Connect Python dependency changes to source usages and evidence.",
    )
    parser.add_argument("--version", action="version", version="openfield 0.1.0")
    subparsers = parser.add_subparsers(dest="command")
    analyze = subparsers.add_parser("analyze", help="Analyze one Python file for upgrade impacts.")
    analyze.add_argument("path", type=Path)
    analyze.add_argument("--package", required=True)
    analyze.add_argument("--from", dest="from_version", required=True)
    analyze.add_argument("--to", dest="to_version", required=True)
    analyze.add_argument("--root", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)
    analyze.add_argument("--overwrite", action="store_true")
    evidence = subparsers.add_parser("evidence", help="Build local evidence stores.")
    evidence_subparsers = evidence.add_subparsers(dest="evidence_command", required=True)
    build = evidence_subparsers.add_parser("build", help="Build the demo evidence database.")
    build.add_argument("--database", type=Path, required=True)
    build.add_argument("--corpus", type=Path, required=True)
    build.add_argument("--environment", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "evidence":
        try:
            report = Report.model_validate_json(args.report.read_text(encoding="utf-8"))
            connection = open_database(args.database)
            try:
                ingest_demo(connection, args.corpus, args.environment, report)
            finally:
                connection.close()
        except (OSError, ValueError, ValidationError) as exc:
            print(f"openfield: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.command != "analyze":
        return 0

    try:
        root = args.root.resolve()
        target = args.path.resolve()
        if not root.is_dir():
            raise ValueError(f"root is not a directory: {args.root}")
        if not target.is_file():
            raise ValueError(f"path is not a file: {args.path}")
        if not target.is_relative_to(root):
            raise ValueError(f"path is outside root: {args.path}")
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"output already exists: {args.output}")

        upgrade = Upgrade(
            package=args.package,
            from_version=args.from_version,
            to_version=args.to_version,
        )
        rules = applicable_rules(load_pack(args.package), upgrade)
        with tokenize.open(target) as source_file:
            source = source_file.read()
        findings, limitations = analyze_source(source, target.relative_to(root).as_posix(), rules)
        report = build_report(
            upgrade,
            findings,
            parsed_files=0 if limitations else 1,
            skipped_files=1 if limitations else 0,
            extra_limitations=limitations,
        )
        write_report(report, args.output)
    except (InvalidVersion, OSError, ValueError) as exc:
        print(f"openfield: {exc}", file=sys.stderr)
        return 2

    return 1 if findings else 0
