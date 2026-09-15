"""Cisco IOS conventions and the Catalyst 9300/9500 reference profile."""
from __future__ import annotations

import re

from ..parser import BasePDFParser
from ..pdf import Line
from .catalyst_layout import CatalystPage


class CiscoIOSParser(BasePDFParser):
    """Extensible IOS example; custom manuals can override typography and headings."""
    name = "cisco"
    field_min_size = 10
    section_aliases = {
        **BasePDFParser.section_aliases,
        "Description": "Function",
        "Syntax": "Format",
        "Syntax Description": "Parameters",
        "Command Modes": "Views",
        "Command Mode": "Views",
        "Usage Guidelines": "Usage Guidelines",
        "Example": "Examples",
        "Command Default": "Defaults",
        "Defaults": "Defaults",
        "Command History": "History",
        "Related Commands": "Related Commands",
    }
    inverse_keywords = ("no", "default")
    prompt = re.compile(r"^[\w.-]+(?:\([^\n)]*\))?[#>]\s*\S")
    caption_prefix = "!"

    def command_heading(self, event, page, outline):
        if not isinstance(event, Line) or not event.bold or event.size < 14:
            return None
        # Page matching distinguishes homonyms and excludes printed contents.
        return next((
            heading for heading in outline
            if heading.page == event.page and self.heading_matches(heading.title, event.text.strip())
        ), None)

    def heading_matches(self, title: str, text: str) -> bool:
        return title == text

    def keyword_span(self, span):
        # Cisco marks arguments italic; ordinary punctuation is not an argument.
        return not bool(span["flags"] & 2)

    def build_command(self, builder):
        self.read_preamble(builder)
        return super().build_command(builder)

    def read_preamble(self, builder) -> None:
        # IOS often prints description and syntax without Function/Format labels.
        description, syntax = [], []
        in_syntax = False
        for event in self.preamble_events(builder):
            if self.starts_syntax(event, description):
                in_syntax = True
            (syntax if in_syntax else description).append(event)
        if description:
            builder.fields.setdefault("Function", description)
        if syntax:
            builder.fields.setdefault("Format", syntax)

    def preamble_events(self, builder):
        return builder.preamble

    def starts_syntax(self, event, description) -> bool:
        return isinstance(event, Line) and event.bold and event.size < 14


class CiscoCatalystParser(CiscoIOSParser):
    """Catalyst IOS XE: side labels, horizontal tables and split text objects."""
    name = "cisco-catalyst"
    footer_margin = 55
    no_parameters = re.compile(
        r"This command has no (?:arguments or keywords|keywords or arguments)\."
    )

    def outline_entries(self, doc):
        entries = super().outline_entries(doc)
        # Keep chapter boundaries so their prose cannot leak into prior commands.
        first = next((
            heading.page for heading in entries
            if heading.level == 2 and heading.title.endswith(" Commands")
        ), None)
        return [
            heading for heading in entries
            if (first is None or heading.page >= first)
            and heading.level <= 3 and heading.title != "Information About Tracing"
        ]

    def heading_matches(self, title: str, text: str) -> bool:
        return (
            title == text
            or title.startswith(text + " ")
            or title.replace(" ", "") == text.replace(" ", "")
        )

    def read_page(self, page, header, footer):
        return CatalystPage(page, header, footer, self.field_heading).events()

    def build_command(self, builder):
        title = builder.command.title
        if title[:1].isupper() and title != "Keepalive (template)":
            return None  # chapter titles / introductory sections
        return super().build_command(builder)

    def read_preamble(self, builder) -> None:
        super().read_preamble(builder)
        builder.preamble = []

    def preamble_events(self, builder):
        # Ignore continuations of a wrapped command heading.
        return [
            event for event in builder.preamble
            if not isinstance(event, Line) or event.size < 14
        ]

    def starts_syntax(self, event, description) -> bool:
        if not isinstance(event, Line):
            return False
        first_word = next((span for span in event.spans if re.search(r"\w", span["text"])), {})
        is_emphasized = bool(first_word.get("flags", 0) & (16 | 8 | 2))
        follows_paragraph = not description or event.bbox[1] - description[-1].bbox[3] > 4
        return is_emphasized and event.size < 14 and follows_paragraph

    def parse_parameters(self, events, warnings):
        parameters = [
            event for event in events
            if not (isinstance(event, Line) and self.no_parameters.fullmatch(event.text.strip()))
        ]
        return super().parse_parameters(parameters, warnings)

    def parse_formats(self, events, warnings):
        # The no/default form can start at ordinary line leading.
        formats, current = [], []
        for event in events:
            if isinstance(event, Line) and current and re.match(r"^(?:no|default)\s", event.text.strip()):
                formats.extend(super().parse_formats(current, warnings))
                current = []
            current.append(event)
        formats.extend(super().parse_formats(current, warnings))
        return list(dict.fromkeys(formats))
