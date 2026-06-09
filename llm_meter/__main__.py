from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .analyzer import analyze_lines, format_text


def iter_input(path: str):
    if path == "-":
        yield from sys.stdin
        return
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        yield from handle


def cmd_analyze(args: argparse.Namespace) -> int:
    report = analyze_lines(iter_input(args.path))
    if args.json:
        print(json.dumps(report.to_dict(top=args.top), indent=2, ensure_ascii=False))
    else:
        print(format_text(report, top=args.top))
    return 0 if report.parsed else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-meter",
        description="Analyze OpenAI-compatible API gateway access logs.",
    )
    parser.add_argument("--version", action="version", version=f"llm-meter {__version__}")

    sub = parser.add_subparsers(dest="command")
    analyze = sub.add_parser("analyze", help="analyze an access log file or stdin")
    analyze.add_argument("path", help="log path, or '-' for stdin")
    analyze.add_argument("--json", action="store_true", help="emit JSON")
    analyze.add_argument("--top", type=int, default=10, help="top N rows per section")
    analyze.set_defaults(func=cmd_analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
