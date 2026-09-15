"""Read explicit related-command/topic lists, preserving their source descriptions."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from .model import RelatedTopic
from .pdf import Line, Table, unwrap

RELATED_SECTIONS = {"Related Commands", "Related Topics", "Related Information", "See Also"}


@dataclass
class RelatedSection:
    name: str
    topics: list[RelatedTopic] = field(default_factory=list)
    description_column: float | None = None
    previous: Line | None = None

    @staticmethod
    def content(events: list[Line | Table]) -> list[Line | Table]:
        content = []
        for event in events:
            if isinstance(event, Line):
                chapter = (event.size >= 24 or re.match(r"^P\s+A\s+R\s+T\b", event.text)
                           or (event.size >= 14 and event.text.strip() == "About This Chapter"))
                if chapter:
                    break
            content.append(event)
        return content

    def read(self, events: list[Line | Table]) -> list[RelatedTopic]:
        for event in self.content(events):
            if isinstance(event, Table):
                for row in event.rows:
                    self.table_row(row)
                self.previous = None
            else:
                self.line(event)
        return self.topics

    def table_row(self, row: list[str | None]) -> None:
        cells = [unwrap(cell or "") for cell in row]
        if not cells or self.is_header(" ".join(cells)):
            return
        title, description = cells[0], "\n".join(cells[1:])
        if title:
            self.topics.append(RelatedTopic(title, description, self.name))
        elif self.topics and description:
            self.topics[-1].description += "\n" + description

    @staticmethod
    def is_header(text: str) -> bool:
        return text.casefold() in {"command description", "topic description", "description command",
                                   "description topic", "command", "topic", "description"}

    def line(self, event: Line) -> None:
        if re.match(r"^(?:P\s+A\s+R\s+T\b|Table\s+\d+[:.])", event.text):
            self.previous = None
            return  # part separators and table captions are not related topics
        if self.is_header(unwrap(event.text)):
            for span in event.spans:
                if span["text"].strip().casefold() == "description":
                    self.description_column = span["bbox"][0]
            self.previous = None
            return
        if self.description_column is None or (self.previous and event.page != self.previous.page):
            # Mirrored Cisco page margins shift both columns on a page break.
            self.description_column = self.column_from_gap(event) or self.description_column
        if self.description_column is None:
            # A plain list has one topic per printed paragraph; wrapped lines continue it.
            title, description = unwrap(event.text).lstrip("•● "), ""
        else:
            left, right = [], []
            for span in event.spans:
                target = left if span["bbox"][0] < self.description_column - 1 else right
                target.append(span["text"])
            title, description = unwrap("".join(left)), unwrap("".join(right))
        new_paragraph = (self.previous is None or event.text.lstrip().startswith(("•", "●"))
                         or event.page != self.previous.page
                         or event.bbox[1] - self.previous.bbox[3] > 4)
        if title and (not self.topics or new_paragraph):
            self.topics.append(RelatedTopic(title, description, self.name))
        elif self.topics:
            topic = self.topics[-1]
            topic.title = self.join(topic.title, title)
            topic.description = self.join(topic.description, description)
        self.previous = event

    @staticmethod
    def column_from_gap(event: Line) -> float | None:
        # Some Cisco related tables omit column headings and horizontal rules.
        spans = [span for span in event.spans if span["text"].strip()]
        for left, right in zip(spans, spans[1:]):
            gap = right["bbox"][0] - left["bbox"][2]
            command_to_prose = left["flags"] & 16 and not right["flags"] & (16 | 2 | 8)
            if gap > 8 or (gap > 4 and command_to_prose):
                return right["bbox"][0]
        return None

    @staticmethod
    def join(previous: str, following: str) -> str:
        separator = "" if previous.endswith("-") else " "
        return (previous + separator + following).strip() if following else previous
