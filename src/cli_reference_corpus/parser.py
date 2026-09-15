"""Vendor-independent PDF traversal and overridable command-building hooks."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Callable

import pymupdf

from .extractors import paragraphs, parse_formats, parse_parameters, parse_examples
from .model import Command, validate
from .pdf import Line, Table, page_events
from .traversal import CommandStream, PageRange
from .related_sections import RELATED_SECTIONS, RelatedSection
from .related_topics import RelatedTopicIndex


@dataclass(frozen=True)
class Heading:
    section: str
    title: str
    page: int
    level: int = 1
    complete: bool = False


@dataclass
class ParseResult:
    commands: list[Command] = field(default_factory=list)
    page_count: int = 0
    pages_read: list[int] = field(default_factory=list)
    textless_pages: list[int] = field(default_factory=list)
    expected_sections: list[str] = field(default_factory=list)
    document_title: str = ""
    parser_profile: str = ""

    def report(self) -> dict:
        found = {c.section for c in self.commands}
        return {
            "pages_in_pdf": self.page_count,
            "pages_read": self.pages_read,
            "textless_pages": self.textless_pages,
            "commands": len(self.commands),
            "templates": sum(len(c.clis) for c in self.commands),
            "parameters": sum(len(c.parameters) for c in self.commands),
            "example_snippets": sum(len(c.examples) for c in self.commands),
            "commands_with_usage_guidelines": sum(bool(c.usage_guidelines) for c in self.commands),
            "commands_with_extra_info": sum(bool(c.extra) for c in self.commands),
            "commands_with_related_topics": sum(bool(c.related_topics) for c in self.commands),
            "related_topics": sum(len(c.related_topics) for c in self.commands),
            "missing_outline_sections": sorted(set(self.expected_sections) - found),
            "issues": [
                {"section": c.section, "title": c.title, "pages": [c.start_page, c.end_page], "warnings": validate(c)}
                for c in self.commands if validate(c)
            ],
        }


class CommandBuilder:
    """One command's raw fields. Profiles may override create_builder for a new grammar."""
    def __init__(self, heading: Heading, parser: BasePDFParser):
        self.heading = heading
        self.command = Command(heading.title, heading.section, heading.page, heading.page)
        self.parser = parser
        self.state = ""
        self.fields: dict[str, list[Line | Table]] = {}
        self.preamble: list[Line | Table] = []

    def add(self, event: Line | Table) -> None:
        self.command.end_page = event.page
        name = self.parser.field_heading(event)
        if name:
            self.state = name
            self.fields.setdefault(name, [])
        elif self.state:
            self.fields[self.state].append(event)
        else:
            self.parser.add_preamble(self, event)

    def finish(self) -> Command | None:
        return self.parser.build_command(self)


class BasePDFParser(ABC):
    """Subclass to describe a manual family; parsing and export need no vendor switches.

    Instances passed to workers must be pickleable (define subclasses in importable
    modules; do not retain open PDF handles). All extraction hooks run in order in
    the parent process except read_page, which also runs in PDF reader workers.
    """
    name = "base"
    header_margin = 50.0
    footer_margin = 40.0
    footer_pattern = None
    table_options: dict = {}
    section_aliases: dict[str, str] = {
        key: key for key in ("Function", "Format", "Parameters", "Views", "Usage Guidelines", "Examples")
    }
    section_aliases.update({key: key for key in RELATED_SECTIONS})
    field_min_size = 11.5
    condition_prefixes: tuple[str, ...] = ()
    inverse_keywords: tuple[str, ...] = ()
    prompt = re.compile(r"(?!)")
    caption_prefix = "#"

    def read_page(self, page, header: float, footer: float) -> list[Line | Table]:
        """Override for columns, borderless tables, page filtering, or another layout."""
        return page_events(page, header, footer, footer_pattern=self.footer_pattern, table_options=self.table_options)

    def outline_entries(self, doc) -> list[Heading]:
        """Stable hierarchy IDs for unnumbered bookmarks, e.g. 2.3.1."""
        counters: list[int] = []
        result = []
        for level, title, page in doc.get_toc():
            if page <= 0:
                continue
            counters = counters[:level]
            counters.extend([0] * (level - len(counters)))
            counters[-1] += 1
            result.append(Heading(".".join(map(str, counters)), title.strip(), page, level))
        return result

    @abstractmethod
    def command_heading(self, event: Line | Table, page, outline: list[Heading]) -> Heading | None:
        """Identify a command/chapter boundary, returning its stable ID and title."""

    def field_heading(self, event: Line | Table) -> str | None:
        if isinstance(event, Line) and event.bold and event.size >= self.field_min_size:
            return self.section_aliases.get(event.text.strip())
        return None

    def add_preamble(self, builder: CommandBuilder, event: Line | Table) -> None:
        builder.preamble.append(event)

    def create_builder(self, heading: Heading) -> CommandBuilder:
        return CommandBuilder(heading, self)

    def paragraphs(self, events) -> str:
        return paragraphs(events)

    def keyword_span(self, span: dict) -> bool:
        return bool(span["flags"] & 16)

    def parse_formats(self, events, warnings) -> list[str]:
        return parse_formats(events, warnings, keyword_span=self.keyword_span,
                             condition_prefixes=self.condition_prefixes, inverse_keywords=self.inverse_keywords)

    def parse_parameters(self, events, warnings):
        return parse_parameters(events, warnings)

    def parse_views(self, events) -> list[str]:
        return [v.strip(" .•●") for v in re.split(r"[,;\n]+", self.paragraphs(events)) if v.strip(" .•●")]

    def parse_examples(self, events, warnings) -> list[list[str]]:
        return parse_examples(events, warnings, prompt=self.prompt, caption_prefix=self.caption_prefix)

    def build_command(self, builder: CommandBuilder) -> Command | None:
        fields, c = builder.fields, builder.command
        if "Function" not in fields and "Format" not in fields:
            return None
        c.function = self.paragraphs(fields.get("Function", []))
        c.clis = self.parse_formats(fields.get("Format", []), c.warnings)
        c.views = self.parse_views(fields.get("Views", []))
        c.parameters = self.parse_parameters(fields.get("Parameters", []), c.warnings)
        c.examples = self.parse_examples(fields.get("Examples", []), c.warnings)
        c.usage_guidelines = self.paragraphs(fields.get("Usage Guidelines", []))
        c.extra = self.additional_information(fields, c.warnings)
        c.related_topics = [topic for name, events in fields.items() if name in RELATED_SECTIONS
                            for topic in RelatedSection(name).read(events)]
        return c

    def additional_information(self, fields: dict, warnings: list[str]) -> str:
        primary = {"Function", "Format", "Parameters", "Views", "Usage Guidelines", "Examples"}
        parts = [name + ":\n" + self.paragraphs(RelatedSection.content(events))
                 for name, events in fields.items() if name not in primary and events]
        if any(w.startswith("conditional_format") for w in warnings):
            parts.append("Format applicability (source text):\n" + self.paragraphs(fields.get("Format", [])))
        elif any(w.startswith("table_in_format") for w in warnings):
            parts.append("Format (source text):\n" + self.paragraphs(fields.get("Format", [])))
        if any(w.startswith("unparsed_parameter") for w in warnings):
            parts.append("Parameters (source text):\n" + self.paragraphs(fields.get("Parameters", [])))
        if fields.get("Examples"):
            source = "\n".join(event.text.strip() if isinstance(event, Line) else self.paragraphs([event])
                               for event in RelatedSection.content(fields["Examples"]))
            parts.append("Examples (source text):\n" + source)
        return "\n\n".join(parts)

    def in_section(self, sid: str, selected: str | None) -> bool:
        return not selected or sid == selected or sid.startswith(selected + ".")

    def parse(self, path: str | Path, *, section: str | None = None, first_page: int = 1,
              last_page: int | None = None, header_margin: float | None = None,
              footer_margin: float | None = None, workers: int = 1,
              progress: Callable[[int, int], None] | None = None) -> ParseResult:
        """Parse physical pages (1-based); bounded batches keep PDF extraction scalable."""
        if workers < 1:
            raise ValueError("workers must be positive")
        header = self.header_margin if header_margin is None else header_margin
        footer = self.footer_margin if footer_margin is None else footer_margin
        result = ParseResult(parser_profile=f"{type(self).__module__}:{type(self).__qualname__}")
        with pymupdf.open(path) as doc:
            if not doc.is_pdf:
                raise ValueError("Input must be a PDF file")
            if doc.needs_pass:
                raise ValueError("Encrypted PDF requires an unlocked local copy")
            result.page_count = len(doc)
            result.document_title = doc.metadata.get("title", "") or ""
            pages = PageRange.checked(first_page, last_page, len(doc))
            outline = self.outline_entries(doc)
            pages = pages.for_section(section, outline, len(doc))
            result.expected_sections = pages.expected_sections(
                outline, lambda section_id: self.in_section(section_id, section)
            )
            CommandStream(self, result, section).read(
                doc, pages, outline,
                header=header, footer=footer, workers=workers, progress=progress,
            )
            related = RelatedTopicIndex.from_outline(outline)
            for command in result.commands:
                related.enrich(command)
        if not result.commands:
            raise ValueError("No command sections found. Use a Command Reference PDF with a text layer; check parser profile, section, page range and margins. Scans require OCR first.")
        return result


def parse_pdf(path: str | Path, **kwargs) -> ParseResult:
    """Backward-compatible entry point for Huawei references."""
    from .vendors.huawei import HuaweiPDFParser
    return HuaweiPDFParser().parse(path, **kwargs)
