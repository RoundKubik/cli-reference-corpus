"""Source topics and checks on their pages after browser printing."""
from dataclasses import dataclass
from pathlib import Path
import re

from ..storage import file_hash
from .html import HTMLArticle
from .text_coverage import compare_text, source_text
from .topics import HTMLTopic


@dataclass(frozen=True)
class BrowserTopic:
    topic: HTMLTopic
    number: int
    markup: str
    text: str
    headings: set[str]
    images: int

    @property
    def section(self) -> str:
        return f"1.{self.number}"

    @classmethod
    def prepare(cls, topic: HTMLTopic, number: int, root: Path):
        article = HTMLArticle.read(topic.path, root)
        original = source_text(article.body)
        images = len(article.body.find_all("img"))
        article.prepare(f"1.{number}", topic.title, preserve_tables=True)
        if len(article.body.find_all("img")) != images:
            raise ValueError(f"Image lost while preparing {topic.path}")
        return cls(topic, number, str(article.body), original, article.headings(), images)

    def mapping(self, document, first: int, last: int, root: Path) -> dict:
        pages = [document[index] for index in range(first, last)]
        coverage = compare_text(self.text, "\n".join(page.get_text() for page in pages))
        if coverage["missing_character_count"]:
            raise ValueError(f"Printed text loss in {self.topic.path}: {coverage}")
        printed_headings = set()
        for page in pages:
            for text, size, bold in page_lines(page):
                if bold and size >= 12.5:
                    printed_headings.add(text)
        if missing := self.headings - printed_headings:
            raise ValueError(f"Printed headings missing in {self.topic.path}: {missing}")
        return {
            "section": self.section, "is_command": self.topic.is_command,
            "title": self.topic.title,
            "html_file": self.topic.path.relative_to(root).as_posix(),
            "html_sha256": file_hash(self.topic.path),
            "first_page": first + 1, "last_page": last,
            "page_height": 842, "section_headings_verified": sorted(self.headings),
            "image_references": self.images, "text_coverage": coverage,
        }


def page_lines(page):
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            yield ("".join(span["text"] for span in spans).strip(),
                   max(span["size"] for span in spans), any(span["flags"] & 16 for span in spans))


@dataclass(frozen=True)
class BrowserPages:
    document: object
    topics: list[BrowserTopic]
    root: Path

    def mapping(self) -> list[dict]:
        starts = []
        for number, page in enumerate(self.document):
            for text, size, bold in page_lines(page):
                if size >= 15.5 and bold and (match := re.match(r"^(1\.\d+)\s", text)):
                    starts.append((match[1], number))
        if [section for section, _ in starts] != [topic.section for topic in self.topics]:
            raise ValueError(f"Printed topic order/count differs in batch starting at {self.topics[0].section}: expected {len(self.topics)}, found {len(starts)}")
        boundaries = [page for _, page in starts] + [len(self.document)]
        return [topic.mapping(self.document, boundaries[index], boundaries[index + 1], self.root)
                for index, topic in enumerate(self.topics)]
