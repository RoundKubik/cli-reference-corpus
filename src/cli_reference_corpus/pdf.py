"""Geometry-aware PDF reading; retain font information and ruled table cells."""
from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import re
import unicodedata

import pymupdf

_worker_document = None
_worker_reader = None


def _open_worker(path: str, reader) -> None:
    global _worker_document, _worker_reader
    _worker_document = pymupdf.open(path)
    _worker_reader = reader
    if hasattr(pymupdf, "no_recommend_layout"):
        pymupdf.no_recommend_layout()


def _read_worker(args: tuple[int, float, float]) -> list[Line | Table]:
    index, header, footer = args
    return _worker_reader.read_page(_worker_document[index], header, footer)


def document_events(doc: pymupdf.Document, first: int, last: int, header: float, footer: float, workers: int, reader):
    """Read pages in order with bounded memory; MuPDF workers use separate processes."""
    if workers == 1:
        for index in range(first - 1, last):
            yield index, reader.read_page(doc[index], header, footer)
        return
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"),
                             initializer=_open_worker, initargs=(str(doc.name), reader)) as pool:
        # Submit only a bounded batch; Executor.map otherwise eagerly queues a large PDF.
        for start in range(first - 1, last, workers * 4):
            indices = list(range(start, min(start + workers * 4, last)))
            values = pool.map(_read_worker, [(i, header, footer) for i in indices])
            yield from zip(indices, values)


def clean(text: str) -> str:
    return unicodedata.normalize("NFKC", text).replace("\u00ad", "").replace("\u00a0", " ")


def unwrap(text: str) -> str:
    """Join physical lines, retaining hyphens already present in the source."""
    return re.sub(r"\s+", " ", re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "-", clean(text))).strip()


def cell_text(page: pymupdf.Page, cell: tuple | None) -> str | None:
    if cell is None:
        return None
    # Plain-text clipping can leak a ligature component from the neighboring cell
    # (e.g. get -> geti). Structured spans retain the actual visible cell text.
    data = page.get_text("dict", clip=pymupdf.Rect(cell))
    return "\n".join("".join(span["text"] for span in line["spans"])
                     for block in data["blocks"] for line in block.get("lines", []))


@dataclass
class Line:
    text: str
    spans: list[dict]
    bbox: tuple
    page: int
    block: int

    @property
    def bold(self) -> bool:
        return any(s["flags"] & 16 for s in self.spans)

    @property
    def size(self) -> float:
        return max((s["size"] for s in self.spans), default=0)


@dataclass
class Table:
    rows: list[list[str | None]]
    bbox: tuple
    page: int


def page_events(page: pymupdf.Page, header_margin: float, footer_margin: float, *, footer_pattern=None,
                table_options: dict | None = None) -> list[Line | Table]:
    if header_margin < 0 or footer_margin < 0 or header_margin + footer_margin >= page.rect.height:
        raise ValueError("Invalid page margins")
    bottom = page.rect.height - footer_margin
    # The profile can identify a footer above the ordinary crop boundary.
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            value = "".join(s["text"] for s in line["spans"])
            if line["bbox"][1] > page.rect.height * .8 and (footer_pattern is not None and footer_pattern.search(value)):
                bottom = min(bottom, line["bbox"][1] - 2)
    clip = pymupdf.Rect(0, header_margin, page.rect.width, bottom)
    tables = page.find_tables(clip=clip, **(table_options or {})).tables
    # Use table geometry, but read each cell in PDF text order. Table.extract()
    # may reorder overlapping ligature glyphs ("Specifies" -> "Specifeis").
    events: list[Line | Table] = [
        Table([[cell_text(page, cell) for cell in row.cells] for row in t.rows], tuple(t.bbox), page.number + 1)
        for t in tables
    ]
    for block_index, block in enumerate(page.get_text("dict", clip=clip)["blocks"]):
        for line in block.get("lines", []):
            box = pymupdf.Rect(line["bbox"])
            center = (box.tl + box.br) / 2
            if any(pymupdf.Rect(t.bbox).contains(center) for t in tables):
                continue
            spans = line["spans"]
            text = clean("".join(s["text"] for s in spans))
            if text.strip():
                events.append(Line(text, spans, tuple(box), page.number + 1, block_index))
    return sorted(events, key=lambda e: (round(e.bbox[1], 1), e.bbox[0]))


def template(lines: list[Line], *, keyword_span=None) -> str:
    """Wrap argument tokens; a profile supplies keyword/argument span classification."""
    keyword_span = keyword_span or (lambda span: bool(span["flags"] & 16))
    chars: list[str] = []
    bold: list[bool] = []
    for line in lines:
        if chars:
            # A parameter may be hyphenated over a PDF line boundary.
            if not (chars[-1] == "-" and len(chars) > 1 and chars[-2].isalnum()):
                chars.append(" ")
                bold.append(True)
        for span in line.spans:
            value = clean(span["text"])
            chars.extend(value)
            bold.extend([keyword_span(span)] * len(value))
    text = "".join(chars)
    # Protect repetition notation and existing placeholders, retain punctuation verbatim.
    token = re.compile(r"&<\d+-\d+>|<[^<>]+>|[\w][\w./:-]*", re.UNICODE)
    result, cursor = [], 0
    for match in token.finditer(text):
        result.append(text[cursor:match.start()])
        value = match.group()
        if not value.startswith(("<", "&<")) and not any(bold[match.start():match.end()]):
            value = f"<{value}>"
        result.append(value)
        cursor = match.end()
    result.append(text[cursor:])
    return re.sub(r"\s+", " ", "".join(result)).strip()
