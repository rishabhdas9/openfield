import argparse
import os
import sqlite3
import sys
import tokenize
from functools import partial
from pathlib import Path

from packaging.version import InvalidVersion
from pydantic import ValidationError

from openfield.analyze import analyze_source
from openfield.answering import answer_from_evidence, anthropic_generate
from openfield.eval import load_cases, run_benchmark, write_results
from openfield.evidence import ingest_demo, open_database
from openfield.models import Report, Upgrade
from openfield.report import build_report, write_report
from openfield.retrieval import (
    MODEL_ID,
    MissingModelError,
    RetrievalMode,
    embed_database,
    fastembed_vectors,
    prepare_model,
    retrieve,
)
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
    embed = evidence_subparsers.add_parser("embed", help="Embed an existing evidence database.")
    embed.add_argument("--database", type=Path, required=True)
    embed.add_argument("--cache-dir", type=Path, required=True)
    model = subparsers.add_parser("model", help="Manage optional local models.")
    model_subparsers = model.add_subparsers(dest="model_command", required=True)
    prepare = model_subparsers.add_parser("prepare", help="Download the configured model.")
    prepare.add_argument("--cache-dir", type=Path, required=True)
    ask = subparsers.add_parser("ask", help="Answer a question from local evidence.")
    ask.add_argument("--database", type=Path, required=True)
    ask.add_argument(
        "--retrieval",
        choices=[mode.value for mode in RetrievalMode],
        default=RetrievalMode.HYBRID_GRAPH.value,
    )
    ask.add_argument("--cache-dir", type=Path, default=Path(".cache/openfield"))
    ask.add_argument("--generate", action="store_true")
    ask.add_argument("--model")
    ask.add_argument("--confirm-cloud", action="store_true")
    ask.add_argument("question")
    evaluate = subparsers.add_parser("eval", help="Run the controlled retrieval benchmark.")
    evaluate.add_argument("--database", type=Path, required=True)
    evaluate.add_argument("--questions", type=Path, required=True)
    evaluate.add_argument(
        "--modes",
        nargs="+",
        choices=[RetrievalMode.VECTOR.value, RetrievalMode.HYBRID_GRAPH.value],
        required=True,
    )
    evaluate.add_argument("--top-k", type=int, default=6)
    evaluate.add_argument(
        "--cache-dir", type=Path, default=Path(".cache/openfield-models")
    )
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "model":
        try:
            prepare_model(args.cache_dir)
        except (MissingModelError, OSError, ValueError) as exc:
            print(f"openfield: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.command == "evidence":
        try:
            if args.evidence_command == "build":
                report = Report.model_validate_json(args.report.read_text(encoding="utf-8"))
                connection = open_database(args.database)
                try:
                    ingest_demo(connection, args.corpus, args.environment, report)
                finally:
                    connection.close()
            else:
                connection = open_database(args.database)
                try:
                    embed_database(connection, args.cache_dir)
                finally:
                    connection.close()
        except (MissingModelError, OSError, ValueError, ValidationError) as exc:
            print(f"openfield: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.command == "ask":
        try:
            if not args.database.is_file():
                raise ValueError(f"database is not a file: {args.database}")
            mode = RetrievalMode(args.retrieval)
            connection = open_database(args.database)
            try:
                rows = connection.execute(
                    "SELECT DISTINCT package, version FROM chunks WHERE package != 'environment'"
                ).fetchall()
                packages = {row["package"] for row in rows}
                versions = {row["version"] for row in rows}
                query_vector = None
                if mode is not RetrievalMode.LEXICAL:
                    try:
                        query_vector = fastembed_vectors(
                            [args.question], args.cache_dir, local_only=True
                        )[0]
                    except MissingModelError:
                        if mode is RetrievalMode.VECTOR:
                            raise
                evidence = retrieve(
                    connection,
                    args.question,
                    mode,
                    packages,
                    versions,
                    query_vector=query_vector,
                    model_id=MODEL_ID if query_vector is not None else None,
                )
            finally:
                connection.close()

            generate = None
            if args.generate:
                if not args.confirm_cloud:
                    raise ValueError("--generate requires --confirm-cloud")
                if not args.model:
                    raise ValueError("--generate requires --model")
                if not os.environ.get("ANTHROPIC_API_KEY"):
                    raise ValueError("ANTHROPIC_API_KEY is not set")
                for item in evidence:
                    print(f"evidence {item.id} {item.source_url}", file=sys.stderr)
                generate = partial(anthropic_generate, model=args.model)
            answer = answer_from_evidence(args.question, evidence, mode.value, generate)
            print(answer.model_dump_json(indent=2))
        except (MissingModelError, OSError, ValueError, ValidationError, sqlite3.Error) as exc:
            print(f"openfield: {exc}", file=sys.stderr)
            return 2
        return 0
    if args.command == "eval":
        try:
            result = run_benchmark(
                args.database,
                load_cases(args.questions),
                [RetrievalMode(mode) for mode in args.modes],
                args.top_k,
                args.cache_dir,
            )
            write_results(result, args.output, args.report)
        except (MissingModelError, OSError, ValueError, ValidationError, sqlite3.Error) as exc:
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
