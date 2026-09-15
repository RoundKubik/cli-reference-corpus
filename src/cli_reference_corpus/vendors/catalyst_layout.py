"""Geometry of Catalyst pages: text fragments, horizontal tables and side labels."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

import pymupdf

from ..pdf import Line, Table, cell_text, clean

BODY_LEFT = 125


def enclosing_box(boxes) -> tuple[float, float, float, float]:
    boxes = list(boxes)
    return (
        min(box[0] for box in boxes), min(box[1] for box in boxes),
        max(box[2] for box in boxes), max(box[3] for box in boxes),
    )


@dataclass(frozen=True)
class PageLines:
    page: pymupdf.Page
    clip: pymupdf.Rect

    def read(self) -> list[Line]:
        lines = []
        for block_number, block in enumerate(self.page.get_text("dict", clip=self.clip)["blocks"]):
            for raw in block.get("lines", []):
                for spans in self.separated_spans(raw["spans"]):
                    text = clean("".join(span["text"] for span in spans))
                    if text.strip():
                        box = enclosing_box(span["bbox"] for span in spans)
                        lines.append(Line(text, spans, box, self.page.number + 1, block_number))
        return lines

    def separated_spans(self, spans: list[dict]) -> list[list[dict]]:
        """A wide gap can separate two table cells within one PDF text object."""
        runs = [[]]
        for span in spans:
            if runs[-1] and span["bbox"][0] - runs[-1][-1]["bbox"][2] > 8:
                runs.append([])
            runs[-1].append(span)
        return runs


@dataclass(frozen=True)
class HorizontalTables:
    page: pymupdf.Page
    clip: pymupdf.Rect
    lines: list[Line]
    labels: list[Line]

    def extract(self) -> tuple[list[Table], list[Line]]:
        tables = []
        consumed = set()
        for (left, right), heights in self.rules().items():
            for table, row in self.rows(left, right, sorted(heights)):
                tables.append(table)
                consumed.update(id(line) for line in row)
        remaining = [line for line in self.lines if id(line) not in consumed]
        return tables, remaining

    def rules(self) -> dict[tuple[float, float], set[float]]:
        rules = defaultdict(set)
        for drawing in self.page.get_drawings():
            rect = drawing["rect"]
            is_rule = rect.width > 100 and rect.height < 1 and rect.x0 >= 120
            if is_rule and self.clip.y0 < rect.y0 < self.clip.y1:
                edges = round(rect.x0, 1), round(rect.x1, 1)
                rules[edges].add(round((rect.y0 + rect.y1) / 2, 1))
        return rules

    def rows(self, left: float, right: float, heights: list[float]):
        split = None
        for top, bottom in zip(heights, heights[1:]):
            if any(top + 6 < label.bbox[1] < bottom for label in self.labels):
                split = None  # this interval contains another section, not a table row
                continue
            row = self.row_lines(left, right, top, bottom)
            if not row:
                continue
            split = self.column_boundary(row, split)
            if split is None or any(line.bbox[0] < split < line.bbox[2] - 1 for line in row):
                continue
            cells = [
                cell_text(self.page, (left, top, split, bottom)),
                cell_text(self.page, (split, top, right, bottom)),
            ]
            yield Table([cells], (left, top, right, bottom), self.page.number + 1), row

    def row_lines(self, left: float, right: float, top: float, bottom: float) -> list[Line]:
        return [
            line for line in self.lines
            if left <= line.bbox[0] < right and top < (line.bbox[1] + line.bbox[3]) / 2 < bottom
        ]

    def column_boundary(self, row: list[Line], previous: float | None) -> float | None:
        first_y = min(line.bbox[1] for line in row)
        first_line = sorted(
            [line for line in row if abs(line.bbox[1] - first_y) < 3],
            key=lambda line: line.bbox[0],
        )
        if len(first_line) >= 2 and first_line[0].bbox[2] < first_line[1].bbox[0]:
            return first_line[1].bbox[0] - 2
        return previous  # carry the boundary into continuation rows


@dataclass(frozen=True)
class ReadingOrder:
    labels: list[Line]

    def arrange(self, events: list[Line | Table]) -> list[Line | Table]:
        merged = []
        for event in sorted(events, key=self.position):
            if merged and self.same_body_line(merged[-1], event):
                merged.append(self.join(merged.pop(), event))
            else:
                merged.append(event)
        return merged

    def position(self, event: Line | Table) -> tuple[float, float]:
        # Body font boxes can start 2.5pt above their sidebar heading.
        top = event.bbox[1]
        for label in self.labels:
            if event is not label and event.bbox[0] >= BODY_LEFT and abs(top - label.bbox[1]) < 4:
                top = label.bbox[1] + .1
        return top, event.bbox[0]

    def same_body_line(self, previous: Line | Table, current: Line | Table) -> bool:
        return (
            isinstance(previous, Line) and isinstance(current, Line)
            and previous.bbox[0] >= BODY_LEFT and current.bbox[0] >= BODY_LEFT
            and abs(previous.bbox[1] - current.bbox[1]) < 1
        )

    def join(self, previous: Line, current: Line) -> Line:
        parts = sorted([previous, current], key=lambda line: line.bbox[0])
        spans = []
        for part in parts:
            if spans:
                spans.append({**part.spans[0], "text": " "})
            spans.extend(part.spans)
        return Line(
            " ".join(part.text for part in parts),
            spans,
            enclosing_box(part.bbox for part in parts),
            current.page,
            current.block,
        )


@dataclass(frozen=True)
class CatalystPage:
    page: pymupdf.Page
    header: float
    footer: float
    field_heading: Callable[[Line], str | None]

    def events(self) -> list[Line | Table]:
        clip = self.content_box()
        lines = PageLines(self.page, clip).read()
        tables, remaining = HorizontalTables(self.page, clip, lines, self.labels(lines)).extract()
        return ReadingOrder(self.labels(remaining)).arrange([*remaining, *tables])

    def content_box(self) -> pymupdf.Rect:
        if self.header < 0 or self.footer < 0 or self.header + self.footer >= self.page.rect.height:
            raise ValueError("Invalid page margins")
        return pymupdf.Rect(0, self.header, self.page.rect.width, self.page.rect.height - self.footer)

    def labels(self, lines: list[Line]) -> list[Line]:
        return [line for line in lines if line.bbox[0] < BODY_LEFT and self.field_heading(line)]
