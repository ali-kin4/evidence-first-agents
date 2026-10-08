"""Command-line interface for Evidence First Agents."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .reports import as_json, as_markdown
from .scanner import AgentProjectError, inspect_project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-first-agents",
        description="Inspect agent project instructions, skills, MCP, and approval boundaries.",
    )
    parser.add_argument("project", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument(
        "--workbench", action="store_true",
        help="Open the localhost-only fictional agent-governance training workbench.",
    )
    parser.add_argument("--port", type=int, default=8766, help="Workbench localhost port.")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Format printed to stdout.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.workbench:
        from .workbench_server import serve_workbench

        try:
            serve_workbench(port=args.port)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0
    try:
        report = inspect_project(args.project)
    except (AgentProjectError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    json_text = as_json(report)
    markdown_text = as_markdown(report)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_text, encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown_text, encoding="utf-8")
    print(json_text if args.format == "json" else markdown_text)

    return {
        "ready": 0,
        "warn": 0,
        "fail": 1,
        "blocked": 2,
    }[report["decision"]]

