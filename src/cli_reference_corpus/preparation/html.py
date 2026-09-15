"""Prepare Huawei HTML for printing without changing command content."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup, Tag

CSS = '''
body { font-family: sans-serif; font-size: 10pt; line-height: 1.2; }
h1 { font-size: 16pt; font-weight: bold; margin: 0 0 14pt 0; }
h2 { font-size: 13pt; font-weight: bold; margin: 14pt 0 7pt 0; }
h3,h4 { font-size: 11pt; font-weight: bold; }
p { margin: 0 0 8pt 0; }
pre, p.screenline { font-family: monospace; font-size: 8pt; white-space: pre-wrap; margin: 0; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0; }
td,th { border: 0.5pt solid black; padding: 4pt; vertical-align: top; }
td p,th p { margin: 0 0 2pt 0; }
'''


@dataclass
class HTMLArticle:
    soup: BeautifulSoup
    body: Tag
    path: Path
    root: Path

    @classmethod
    def read(cls, path: Path, root: Path) -> HTMLArticle:
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        body = soup.select_one(".articleBoxWithoutHead") or soup.body
        if body is None or body.h1 is None:
            raise ValueError(f"No article/title in {path}")
        return cls(soup, body, path, root)

    def prepare(self, section: str, title: str, *, preserve_tables: bool = False) -> None:
        self.body.h1.clear()
        self.body.h1.string = f"{section} {title}"
        for tag in list(self.body.select("script, style, link, iframe, object")):
            tag.decompose()
        if not preserve_tables:
            self.flatten_output_tables()
        self.remove_web_markup()
        self.split_example_lines()
        self.resolve_images()

    def headings(self) -> set[str]:
        return {heading.get_text(" ", strip=True) for heading in self.body.find_all("h2")}

    def flatten_output_tables(self) -> None:
        # Captioned output tables can restart pagination. Parameter tables must
        # retain their geometry for the downstream PDF parser.
        for table in list(self.body.find_all("table")):
            if table.find_parent(class_="cliparam") is not None:
                continue
            rows = self.soup.new_tag("div")
            if table.caption:
                rows.append(self.paragraph(table.caption.get_text(" ", strip=True)))
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"], recursive=False)
                paragraph = self.paragraph(" | ".join(cell.get_text(" ", strip=True) for cell in cells))
                for image in reversed(row.find_all("img")):
                    paragraph.insert(0, image.extract())
                rows.append(paragraph)
            table.replace_with(rows)

    def remove_web_markup(self) -> None:
        for group in list(self.body.select("thead, tbody, tfoot")):
            group.unwrap()
        for superscript in list(self.body.select(".cliformat sup, .cliformat sub")):
            superscript.unwrap()
        for link in list(self.body.find_all("a")):
            link.unwrap()
        for tag in self.body.find_all(True):
            for attribute in ("id", "name", "style"):
                # Vendor styles may hide conditional text; retain all published text.
                tag.attrs.pop(attribute, None)

    def split_example_lines(self) -> None:
        # Story cannot paginate a tall <pre>; make each physical line pageable.
        for pre in list(self.body.select(".cliexample pre")):
            block = self.soup.new_tag("div")
            for line in pre.get_text().splitlines():
                paragraph = self.paragraph(line or " ")
                paragraph["class"] = "screenline"
                block.append(paragraph)
            pre.replace_with(block)

    def resolve_images(self) -> None:
        for image in list(self.body.find_all("img")):
            source = (self.path.parent / image.get("src", "")).resolve()
            if source.is_file() and source.is_relative_to(self.root.resolve()):
                image["src"] = source.relative_to(self.root.resolve()).as_posix()
            else:
                image.replace_with(image.get("alt", "[Image unavailable]"))

    def paragraph(self, text: str) -> Tag:
        paragraph = self.soup.new_tag("p")
        paragraph.string = text
        return paragraph
