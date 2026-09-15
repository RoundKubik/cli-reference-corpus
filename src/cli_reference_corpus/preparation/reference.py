"""Walk only the child topics of an explicitly selected Huawei reference book."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .html import HTMLArticle
from .topics import HTMLTopic


@dataclass(frozen=True)
class ReferenceContents:
    root: Path
    entry_point: str

    def topics(self) -> list[HTMLTopic]:
        pending = [self.resolve(self.root, self.entry_point)]
        seen, topics = set(), []
        while pending:
            path = pending.pop()
            if path in seen:
                continue
            seen.add(path)
            article = HTMLArticle.read(path, self.root)
            title = article.body.h1.get_text(" ", strip=True)
            is_command = bool(article.body.select_one(".clifunc, .cliformat"))
            topics.append(HTMLTopic(path, title, is_command))
            children = self.children(article)
            if is_command and children:
                raise ValueError(f"Command topic unexpectedly has child topics: {path}")
            pending.extend(reversed(children))
        if not any(topic.is_command for topic in topics):
            raise ValueError("Selected reference book contains no command topics")
        return topics

    def children(self, article: HTMLArticle) -> list[Path]:
        links = article.body.select("ul.ullinks > dl > dt > a[href], ul.ullinks > li > a[href], ul.ullinks > li > strong > a[href]")
        return [self.resolve(article.path.parent, link["href"]) for link in links]

    def resolve(self, directory: Path, link: str) -> Path:
        url = urlsplit(link.replace("\\", "/"))
        if url.scheme or url.netloc:
            raise ValueError(f"External child link in reference contents: {link}")
        path = (directory / unquote(url.path)).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Reference topic leaves the extraction directory: {link}")
        if not path.is_file():
            raise ValueError(f"Missing reference topic: {path}")
        return path
