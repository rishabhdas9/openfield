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
