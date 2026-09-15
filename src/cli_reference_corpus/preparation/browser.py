"""Print reference topics in bounded browser batches, preserving source tables."""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from html import escape
import multiprocessing
from pathlib import Path
import shutil
import subprocess
import tempfile

import pymupdf

from .browser_pages import BrowserPages, BrowserTopic
from .html import CSS
from .topics import HTMLTopic

PRINT_CSS = """
@page { size: 595pt 842pt; margin: 55pt 45pt; }
body { margin: 0; overflow-wrap: anywhere; }
table { table-layout: fixed; }
td, th { width: auto; white-space: normal; overflow-wrap: anywhere; }
col, colgroup { width: auto; }
.reference-topic { break-before: page; }
.reference-topic:first-child { break-before: auto; }
img { max-width: 100%; height: auto; }
"""


@dataclass(frozen=True)
class Chrome:
    executable: str

    @classmethod
    def installed(cls):
        for name in ("google-chrome", "chromium", "chromium-browser"):
            if executable := shutil.which(name):
                return cls(executable)
        raise ValueError("Chrome or Chromium is required to prepare the complete reference PDF")

    def version(self) -> str:
        return subprocess.check_output([self.executable, "--version"], text=True).strip()

    def print_pdf(self, html: Path, pdf: Path, profile: Path) -> None:
        arguments = [self.executable, "--headless", "--no-sandbox", "--disable-gpu",
                     "--disable-background-networking", "--no-pdf-header-footer",
                     f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", html.as_uri()]
        result = subprocess.run(arguments, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                timeout=180, text=True)
        if result.returncode or not pdf.is_file():
            raise ValueError(f"Browser PDF printing failed: {result.stderr[-2000:]}")


@dataclass(frozen=True)
class BrowserBatch:
    root: Path
    numbered_topics: list[tuple[int, HTMLTopic]]
    browser: Chrome

    def render(self) -> tuple[bytes, list[dict]]:
        topics = [BrowserTopic.prepare(topic, number, self.root) for number, topic in self.numbered_topics]
        with tempfile.TemporaryDirectory(prefix="cli-reference-browser-") as temporary:
            directory = Path(temporary)
            html, pdf = directory / "topics.html", directory / "topics.pdf"
            html.write_text(self.markup(topics), encoding="utf-8")
            self.browser.print_pdf(html, pdf, directory / "profile")
            with pymupdf.open(pdf) as document:
                mapping = BrowserPages(document, topics, self.root).mapping()
            return pdf.read_bytes(), mapping

    def markup(self, topics: list[BrowserTopic]) -> str:
        base = escape(self.root.as_uri() + "/", quote=True)
        body = "".join(f'<section class="reference-topic">{topic.markup}</section>' for topic in topics)
        return (f'<!doctype html><html><head><meta charset="utf-8"><base href="{base}">'
                f"<style>{CSS}\n{PRINT_CSS}</style></head><body>{body}</body></html>")


def render_book(root: Path, output: Path, topics: list[HTMLTopic], *, title: str,
                browser: Chrome, workers: int = 4, progress=None) -> list[dict]:
    if workers < 1:
        raise ValueError("workers must be positive")
    root = root.resolve()
    numbered = list(enumerate(topics, 1))
    batches = [BrowserBatch(root, numbered[start:start + 100], browser)
               for start in range(0, len(numbered), 100)]
    mapping = []
    with pymupdf.open() as combined, ProcessPoolExecutor(
        max_workers=workers, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for start in range(0, len(batches), workers):
            pending = [pool.submit(batch.render) for batch in batches[start:start + workers]]
            for future in pending:
                data, entries = future.result()
                offset = len(combined)
                with pymupdf.open(stream=data, filetype="pdf") as batch:
                    combined.insert_pdf(batch)
                for entry in entries:
                    entry["first_page"] += offset
                    entry["last_page"] += offset
                mapping.extend(entries)
                if progress:
                    progress(len(mapping), len(topics))
        combined.set_toc([[1, f"{entry['section']} {entry['title']}", entry["first_page"]]
                          for entry in mapping if entry["is_command"]])
        combined.set_metadata({"title": title + " [PDF prepared from official Huawei CHM]",
                               "producer": "cli-reference-corpus / " + browser.version(),
                               "subject": "Locally prepared PDF; source content is the official Huawei Command Reference."})
        combined.save(output, deflate=True, garbage=0)
    return mapping
