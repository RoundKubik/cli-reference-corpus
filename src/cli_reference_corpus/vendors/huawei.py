"""Numbered English Huawei reference layout (CloudEngine and NE40E families)."""
from dataclasses import replace
import re
from ..parser import BasePDFParser, Heading
from ..pdf import Line, unwrap


class HuaweiPDFParser(BasePDFParser):
    name = "huawei"
    prefer_bookmark_titles = False
    header_margin = 75
    footer_margin = 45
    heading_pattern = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")
    footer_pattern = re.compile(r"^Issue |Copyright © Huawei")
    section_aliases = {
        **BasePDFParser.section_aliases,
        "Default Level": "Default Level",
        "Task Name and Operations": "Task Name and Operations",
        "Example": "Examples",
    }
    condition_prefixes = ("For ",)
    inverse_keywords = ("undo",)
    prompt = re.compile(r"^(?:<[^<>\s]+>|\[[~*]?[^\[\]\s]+\])\s*\S")

    def outline_entries(self, doc):
        entries = []
        for level, title, page in doc.get_toc():
            match = self.heading_pattern.match(unwrap(title))
            if match and page > 0:
                entries.append(Heading(match[1], match[2], page, level))
        return entries

    def command_heading(self, event, page, outline):
        if isinstance(event, Line) and event.bold and event.size >= 12 and event.bbox[0] < page.rect.width * .24:
            match = self.heading_pattern.match(event.text.strip())
            if match:
                if self.prefer_bookmark_titles:
                    bookmark = next((entry for entry in outline
                                     if entry.section == match[1] and entry.page == event.page), None)
                    if bookmark:
                        return replace(bookmark, complete=True)
                return Heading(match[1], match[2], event.page, match[1].count(".") + 1)
        return None

    def add_preamble(self, builder, event):
        if not builder.heading.complete and isinstance(event, Line) and event.bold and event.size >= 12:
            builder.command.title += " " + event.text.strip()


class CloudEngineParser(HuaweiPDFParser):
    name = "cloudengine"


class CampusSwitchParser(HuaweiPDFParser):
    """Campus V200 references include non-command 'Command Support' bookmarks."""
    name = "campus-switch"
    prefer_bookmark_titles = True

    def outline_entries(self, doc):
        return [heading for heading in super().outline_entries(doc)
                if heading.section != "1" and heading.title != "Command Support"
                # V200R011C10 labels this support matrix with the chapter title.
                and (heading.section, heading.title) != ("8.2.1", "MLD Configuration Commands")]


class NE40EParser(HuaweiPDFParser):
    name = "ne40e"


class NE40ERenderedParser(NE40EParser):
    """Layout produced by scripts/chm_to_pdf.py, distinct from Huawei's original PDFs."""
    name = "ne40e-rendered"
    prefer_bookmark_titles = True
    # The intermediate has no running headers or footers.
    header_margin = 0
    footer_margin = 0
