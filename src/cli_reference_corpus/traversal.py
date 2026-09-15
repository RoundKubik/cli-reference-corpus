"""Page selection and the lifetime of a command spanning several PDF pages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from .pdf import Line, Table, document_events

if TYPE_CHECKING:
    from .parser import BasePDFParser, CommandBuilder, Heading, ParseResult


@dataclass(frozen=True)
class PageRange:
    first: int
    last: int

    @classmethod
    def checked(cls, first: int, last: int | None, page_count: int) -> PageRange:
        last = page_count if last is None else last
        if not 1 <= first <= last <= page_count:
            raise ValueError(f"Page range must satisfy 1 <= first <= last <= {page_count}")
        return cls(first, last)

    def for_section(self, section: str | None, outline: list[Heading], page_count: int) -> PageRange:
        if not section:
            return self
        for index, heading in enumerate(outline):
            if heading.section != section:
                continue
            end = next(
                (entry.page for entry in outline[index + 1:] if entry.level <= heading.level),
                page_count,
            )
            first, last = max(self.first, heading.page), min(self.last, end)
            if first > last:
                raise ValueError("Section is outside the requested page range")
            return PageRange(first, last)
        return self

    def expected_sections(self, outline: list[Heading], include: Callable[[str], bool]) -> list[str]:
        sections = []
        for index, heading in enumerate(outline):
            is_leaf = index + 1 == len(outline) or outline[index + 1].level <= heading.level
            if is_leaf and self.first <= heading.page <= self.last and include(heading.section):
                sections.append(heading.section)
        return sections


@dataclass
class CommandStream:
    """The mutable parsing session; vendor profiles themselves retain no PDF state."""
    profile: BasePDFParser
    result: ParseResult
    section: str | None
    current: CommandBuilder | None = None

    def read(self, document, pages: PageRange, outline: list[Heading], *,
             header: float, footer: float, workers: int, progress=None) -> None:
        events_by_page = document_events(
            document, pages.first, pages.last, header, footer, workers, self.profile
        )
        for page_index, events in events_by_page:
            page = document[page_index]
            self.result.pages_read.append(page_index + 1)
            if not events:
                self.result.textless_pages.append(page_index + 1)
            for event in events:
                self.accept(event, page, outline)
            if progress:
                progress(page_index + 1, pages.last)
        self.finish()
        self.mark_truncated(pages.last, len(document))

    def accept(self, event: Line | Table, page, outline: list[Heading]) -> None:
        heading = self.profile.command_heading(event, page, outline)
        if heading:
            self.finish()
            self.current = self.profile.create_builder(heading)
        elif self.current:
            self.current.add(event)

    def finish(self) -> None:
        if self.current:
            command = self.current.finish()
            if command and self.profile.in_section(command.section, self.section):
                self.result.commands.append(command)

    def mark_truncated(self, last_page: int, page_count: int) -> None:
        if last_page >= page_count or not self.result.commands or not self.current:
            return
        last_command = self.result.commands[-1]
        if last_command.section == self.current.command.section:
            last_command.warnings.append("range_ends_inside_section: command may be incomplete")
