"""Select command topics from CHM contents and keep their source mapping."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup
import pymupdf

from .rendering import PDFAssembly
from .topics import HTMLTopic as CHMTopic
from .reference import ReferenceContents


@dataclass(frozen=True)
class CHMContents:
    root: Path

    def topics(self) -> list[CHMTopic]:
        files = sorted(self.root.glob("*.hhc"))
        if len(files) != 1:
            raise ValueError("Expected exactly one CHM table of contents (.hhc)")
        contents = BeautifulSoup(files[0].read_bytes(), "html.parser")
        topics, seen = [], set()
        for item in contents.find_all("object", attrs={"type": "text/sitemap"}):
            params = self.parameters(item)
            local = params.get("local", "").replace("\\", "/").split("#")[0]
            path = self.topic_path(local)
            if not local or path in seen:
                continue
            seen.add(path)
            raw = path.read_bytes()
            if b'class="clifunc"' in raw and b'class="cliformat"' in raw:
                topics.append(CHMTopic(path, params.get("name", path.stem)))
        if not topics:
            raise ValueError("No Huawei command topics in the CHM contents")
        return topics

    def topic_path(self, local: str) -> Path:
        path = (self.root / local).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("CHM topic path leaves the extraction directory")
        return path

    def parameters(self, item) -> dict[str, str]:
        return {
            parameter.get("name", "").lower(): parameter.get("value", "")
            for parameter in item.find_all("param")
        }


def render_topics(root: Path, output: Path, *, title: str, progress=None,
                  entry_point: str | None = None) -> list[dict]:
    contents = ReferenceContents(root, entry_point) if entry_point else CHMContents(root)
    return render_selected_topics(root, output, contents.topics(), title=title, progress=progress)


def render_selected_topics(root: Path, output: Path, topics: list[CHMTopic], *,
                           title: str, progress=None) -> list[dict]:
    mapping = []
    with pymupdf.open() as combined, pymupdf.open() as batch:
        assembly = PDFAssembly(combined, batch)
        archive = pymupdf.Archive(str(root))
        for number, topic in enumerate(topics, 1):
            mapping.append(topic.render(root, number, archive, assembly))
            if number % 100 == 0:
                assembly.flush()
            if progress:
                progress(number, len(topics))
        assembly.save(output, title)
    return mapping
