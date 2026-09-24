"""Offline command-line entry points. Parsing and publication live in their own modules."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pymupdf

# Preserve imports used by existing scripts and downstream profiles.
from .corpus import write_corpus
from .storage import file_hash
from .vendors import load_parser
from .markdown import export_markdown
from .enrichment import enrich_corpus


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "markdown":
        return markdown_main(argv[1:])
    if argv and argv[0] == "enrich-related":
        return enrichment_main(argv[1:])
    if argv and argv[0] == "parse":
        argv = argv[1:]
    if hasattr(pymupdf, "no_recommend_layout"):
        pymupdf.no_recommend_layout()
    parser = parsing_arguments()
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}. Choose a new directory.")
    try:
        return run_parse(args)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


def run_parse(args: argparse.Namespace) -> int:
    def progress(page: int, end: int) -> None:
        if not args.quiet and (page % 20 == 0 or page == end):
            print(f"PDF page {page}/{end}", file=sys.stderr)

    profile = load_parser(args.parser)
    result = profile.parse(
        args.pdf,
        section=args.section,
        first_page=args.first_page,
        last_page=args.last_page,
        header_margin=args.header_margin,
        footer_margin=args.footer_margin,
        workers=args.workers,
        progress=progress,
    )
    report = write_corpus(result, args.pdf, args.output, args.schema, args.source_url)
    print(json.dumps(parse_summary(args.output, report)))
    has_issues = report["issues"] or report["missing_outline_sections"] or report["textless_pages"]
    return 2 if args.strict and has_issues else 0


def parse_summary(output: Path, report: dict) -> dict:
    return {
        "output": str(output),
        "commands": report["commands"],
        "templates": report["templates"],
        "commands_with_warnings": len(report["issues"]),
        "missing_sections": len(report["missing_outline_sections"]),
    }


def parsing_arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(
        "Parse a command reference PDF into NAssim JSON. "
        "Use `markdown INPUT -o FILE` for Markdown export."
    ))
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--parser", default="huawei", help=(
        "huawei, cloudengine, ne40e, ne40e-rendered, cisco, cisco-catalyst, "
        "or importable module:Class"
    ))
    parser.add_argument("--output", "-o", type=Path, required=True, help="New output directory")
    parser.add_argument("--section", help="Numbered chapter or command, e.g. 2.4.3 (VLAN)")
    parser.add_argument("--first-page", type=int, default=1)
    parser.add_argument("--last-page", type=int)
    parser.add_argument("--schema", choices=["repository", "paper"], default="repository")
    parser.add_argument("--header-margin", type=float, help="Crop top points (default: selected profile)")
    parser.add_argument("--footer-margin", type=float, help="Crop bottom points (default: selected profile)")
    parser.add_argument("--source-url", help="Optional provenance URL, never fetched by the parser")
    parser.add_argument("--workers", type=int, default=1, help="Independent PDF reader processes (default: 1)")
    parser.add_argument("--strict", action="store_true", help=(
        "Export report but exit 2 on any extraction warning or missing section"
    ))
    parser.add_argument("--quiet", action="store_true")
    return parser


def markdown_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render a NAssim JSON record or corpus as readable Markdown.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--title")
    args = parser.parse_args(argv)
    try:
        count = export_markdown(args.input, args.output, title=args.title)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "commands": count}))
    return 0


def enrichment_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=(
        "Resolve command mentions in an existing JSON corpus and write enriched JSON/Markdown pairs."
    ))
    parser.add_argument("input", type=Path, help="Corpus directory or manifest.json")
    parser.add_argument("--output", "-o", type=Path, required=True, help="New output directory")
    args = parser.parse_args(argv)
    try:
        counts = enrich_corpus(args.input, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), **counts}))
    return 0
