#!/usr/bin/env python3
"""Render downloaded Huawei CHM command topics as a traceable intermediate PDF.

This changes layout only; command fields are extracted later by the PDF parser.
Requires 7z and the optional `prepare` dependencies. Never executes CHM scripts.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

import pymupdf

from cli_reference_corpus.preparation.chm import CHMContents, render_topics, render_selected_topics
from cli_reference_corpus.preparation.browser import Chrome, render_book
from cli_reference_corpus.preparation.contents import BookOutline
from cli_reference_corpus.preparation.reference import ReferenceContents
from cli_reference_corpus.storage import file_hash, write_json


def digest(path) -> str:
    return file_hash(Path(path))


def progress(number: int, total: int) -> None:
    if number % 50 == 0 or number == total:
        print(f"Rendered CHM topics: {number}/{total}", flush=True)


def source_metadata(chm: Path, pdf: Path, mapping: list[dict], entry_point: str | None = None,
                    renderer_name: str | None = None) -> dict:
    return {
        "mapping_version": 2,
        "source_format": "official Huawei CHM",
        "pdf_origin": "locally prepared from official CHM",
        "chm_file": chm.name,
        "chm_sha256": digest(chm),
        "pdf_sha256": digest(pdf),
        "renderer": renderer_name or "PyMuPDF " + pymupdf.VersionBind,
        "topics": mapping,
        "entry_point": entry_point,
        "topic_count": len(mapping),
        "command_count": sum(entry["is_command"] for entry in mapping),
        "topics_with_text_differences": sum(bool(entry["text_coverage"]["missing_word_count"]) for entry in mapping),
        "renderer_script_sha256": digest(Path(__file__)),
        "preparation_modules_sha256": {
            path.name: digest(path) for path in sorted(
                (Path(__file__).parents[1] / "src/cli_reference_corpus/preparation").glob("*.py")
            )
        },
        "topics_with_taller_pages": sum(entry["page_height"] > 842 for entry in mapping),
        "scope": (
            "All topics under the selected reference entry point, including introductory text."
            if entry_point else "Command topics present in CHM table of contents; non-command topics omitted."
        ),
    }


def convert(chm: Path, output: Path, *, title: str, entry_point: str | None = None,
            renderer: str = "chrome", workers: int = 4) -> Path:
    if output.exists() or output.with_suffix(".source.json").exists():
        raise ValueError("Output PDF or source mapping already exists")
    if not shutil.which("7z"):
        raise ValueError("7z is required to unpack CHM (Debian/Ubuntu: 7zip package)")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nassim-chm-") as temporary:
        root = Path(temporary) / "html"
        root.mkdir()
        subprocess.run(
            ["7z", "x", "-y", f"-o{root}", str(chm.resolve())],
            check=True, stdout=subprocess.DEVNULL,
        )
        pending = Path(temporary) / "rendered.pdf"
        outline_check = None
        contents = ReferenceContents(root, entry_point) if entry_point else CHMContents(root)
        topics = contents.topics()
        if entry_point:
            outline_check = BookOutline(root, entry_point).verify(topics)
            print(f"Verified reference topics against CHM outline: {len(topics)}", flush=True)
        renderer_name = None
        if renderer == "chrome":
            browser = Chrome.installed()
            mapping = render_book(root, pending, topics, title=title, browser=browser,
                                  workers=workers, progress=progress)
            renderer_name = browser.version()
        else:
            mapping = render_selected_topics(root, pending, topics, title=title, progress=progress)
        metadata = source_metadata(chm, pending, mapping, entry_point, renderer_name)
        metadata["outline_check"] = outline_check
        with output.open("xb") as destination, pending.open("rb") as source:
            shutil.copyfileobj(source, destination)
        write_json(output.with_suffix(".source.json"), metadata)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chm", type=Path)
    parser.add_argument("-o", "--output", required=True, type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--entry-point", help="Local HTML path of the reference book inside the CHM; include all its child topics")
    parser.add_argument("--renderer", choices=["chrome", "pymupdf"], default="chrome", help="Chrome preserves long reference text and source tables; PyMuPDF is the legacy renderer")
    parser.add_argument("--workers", type=int, default=4, help="Number of browser printing processes")
    args = parser.parse_args()
    try:
        print(convert(args.chm, args.output, title=args.title, entry_point=args.entry_point,
                      renderer=args.renderer, workers=args.workers))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Conversion failed: {error}\n")
