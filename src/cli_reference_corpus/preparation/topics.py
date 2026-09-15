"""Render one source topic and record its physical PDF pages."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..storage import file_hash
from .html import HTMLArticle
from .rendering import PDFAssembly, TopicPDF
from .text_coverage import source_text, text_coverage


@dataclass(frozen=True)
class HTMLTopic:
    path: Path
    title: str
    is_command: bool = True

    def render(self, root: Path, number: int, archive, assembly: PDFAssembly) -> dict:
        section = f"1.{number}"
        article = HTMLArticle.read(self.path, root)
        original_text = source_text(article.body)
        article.prepare(section, self.title)
        try:
            data, height = TopicPDF(article, archive).render()
        except ValueError as error:
            raise ValueError(f"Topic cannot be rendered without missing headings: {number} {self.path}") from error
        first, last = assembly.append(data, f"{section} {self.title}", bookmark=self.is_command)
        return {
            "section": section,
            "is_command": self.is_command,
            "title": self.title,
            "html_file": self.path.relative_to(root).as_posix(),
            "html_sha256": file_hash(self.path),
            "first_page": first,
            "last_page": last,
            "page_height": height,
            "section_headings_verified": sorted(article.headings()),
            "text_coverage": text_coverage(original_text, data),
        }
