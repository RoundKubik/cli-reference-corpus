"""Read CHM outline depths independently of HTML child-link navigation."""
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


@dataclass(frozen=True)
class ContentsEntry:
    depth: int
    title: str
    local: str


class ContentsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parameters = None
        self.entries = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "ul":
            self.depth += 1
        elif tag == "object" and attributes.get("type", "").lower() == "text/sitemap":
            self.parameters = {}
        elif tag == "param" and self.parameters is not None:
            self.parameters[attributes.get("name", "").lower()] = attributes.get("value", "")

    def handle_endtag(self, tag):
        if tag == "ul":
            self.depth -= 1
        elif tag == "object" and self.parameters is not None:
            self.entries.append(ContentsEntry(
                self.depth, self.parameters.get("name", ""), self.parameters.get("local", ""),
            ))
            self.parameters = None


@dataclass(frozen=True)
class BookOutline:
    root: Path
    entry_point: str

    def entries(self) -> list[ContentsEntry]:
        files = sorted(self.root.glob("*.hhc"))
        if len(files) != 1:
            raise ValueError("Expected exactly one CHM table of contents (.hhc)")
        parser = ContentsParser()
        parser.feed(files[0].read_text(encoding="utf-8-sig"))
        selected, depth = [], None
        for entry in parser.entries:
            local = entry.local.replace("\\", "/").split("#")[0].removeprefix("./")
            if depth is None and local == self.entry_point:
                depth = entry.depth
            elif depth is not None and entry.depth <= depth:
                break
            if depth is not None:
                selected.append(ContentsEntry(entry.depth, entry.title, local))
        if not selected:
            raise ValueError(f"Reference entry point absent from CHM outline: {self.entry_point}")
        return selected

    def verify(self, topics) -> dict:
        entries = self.entries()
        expected = {entry.local for entry in entries if entry.local}
        actual = {topic.path.relative_to(self.root.resolve()).as_posix() for topic in topics}
        if expected != actual:
            raise ValueError(f"CHM outline differs from reference child links: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
        return {"outline_entries": len(entries), "unique_html_topics": len(expected),
                "missing_topics": [], "extra_topics": []}
