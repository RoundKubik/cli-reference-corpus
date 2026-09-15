"""Paginate one HTML topic and assemble PDFs with bounded font deduplication."""
from __future__ import annotations

from dataclasses import dataclass, field
import io
from pathlib import Path

import pymupdf

from .html import CSS, HTMLArticle


@dataclass(frozen=True)
class TopicPDF:
    article: HTMLArticle
    archive: pymupdf.Archive

    def render(self) -> tuple[bytes, int]:
        for height in (842, 1684, 3368, 6736):
            data = self.at_height(height)
            if data is not None and not (self.article.headings() - self.rendered_headings(data)):
                return data, height
        raise ValueError("Topic cannot be rendered without missing headings")

    def at_height(self, height: int) -> bytes | None:
        story = pymupdf.Story(html=str(self.article.body), user_css=CSS, archive=self.archive)
        stream = io.BytesIO()
        writer = pymupdf.DocumentWriter(stream)
        layout = TopicPage(height)
        try:
            story.write(writer, layout.rectangles)
        except ValueError:
            writer.end_page()
            writer.close()
            return None
        writer.close()
        return stream.getvalue()

    def rendered_headings(self, data: bytes) -> set[str]:
        headings = set()
        with pymupdf.open(stream=data, filetype="pdf") as document:
            for page in document:
                for block in page.get_text("dict")["blocks"]:
                    for line in block.get("lines", []):
                        if any(span["size"] >= 12.5 and span["flags"] & 16 for span in line["spans"]):
                            headings.add("".join(span["text"] for span in line["spans"]).strip())
        return headings


@dataclass(frozen=True)
class TopicPage:
    height: int

    def rectangles(self, number: int, filled):
        if number >= 100:
            raise ValueError("Pagination exceeds 100 pages")
        return (
            pymupdf.Rect(0, 0, 595, self.height),
            pymupdf.Rect(45, 55, 550, self.height - 55),
            None,
        )


@dataclass
class PDFAssembly:
    combined: pymupdf.Document
    batch: pymupdf.Document
    outline: list = field(default_factory=list)

    def append(self, data: bytes, heading: str, *, bookmark: bool = True) -> tuple[int, int]:
        with pymupdf.open(stream=data, filetype="pdf") as topic:
            first = len(self.combined) + len(self.batch) + 1
            self.batch.insert_pdf(topic)
            if bookmark:
                self.outline.append([1, heading, first])
            return first, len(self.combined) + len(self.batch)

    def flush(self) -> None:
        # Comparing fonts across thousands of topics is expensive. Deduplicate
        # only within a bounded batch, then append the packed result.
        if not len(self.batch):
            return
        data = self.batch.tobytes(deflate=True, garbage=4)
        with pymupdf.open(stream=data, filetype="pdf") as packed:
            self.combined.insert_pdf(packed)
        self.batch.delete_pages(0, len(self.batch) - 1)

    def save(self, output: Path, title: str) -> None:
        self.flush()
        self.combined.set_toc(self.outline)
        self.combined.set_metadata({
            "title": title + " [PDF rendered locally from official CHM]",
            "producer": "cli-reference-corpus CHM renderer / PyMuPDF",
            "subject": "Intermediate rendering, not an original Huawei PDF",
        })
        self.combined.save(output, deflate=True, garbage=0)
