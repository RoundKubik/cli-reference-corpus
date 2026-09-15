"""English Markdown views of commands, independent of PDF and vendor profiles."""
from __future__ import annotations

from dataclasses import dataclass
import html
from pathlib import Path
import re
from typing import TextIO
from urllib.parse import urlsplit

from .corpus_input import CorpusInput, natural_key
from .model import Command
from .storage import staged_text


def prose(text: str) -> str:
    """Keep source text literal: placeholders/markup must remain visible to readers."""
    escaped = html.escape(text, quote=False)
    return re.sub(r"([\\`*_{}\[\]#!|>~+-])", r"\\\1", escaped)


def code_block(text: str) -> str:
    longest_run = max((len(match[0]) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}text\n{text}\n{fence}"


@dataclass(frozen=True)
class CommandMarkdown:
    command: Command
    anchor: str | None = None

    def render(self) -> str:
        parts = [
            *self.heading(),
            "### Function", prose(self.command.function) or "Not specified.",
            "### Syntax", *self.syntax(),
            "### Modes / Views", self.views(),
            "### Parameters", self.parameters(),
            "### Usage Guidelines", prose(self.command.usage_guidelines) or "Not specified in JSON.",
            "### Examples", *self.examples(),
            *self.related_topics(),
            *self.notes(),
        ]
        return "\n\n".join(parts) + "\n"

    def heading(self) -> list[str]:
        parts = [f'<a id="{self.anchor}"></a>'] if self.anchor else []
        parts.append("## " + prose(" ".join(self.command.title.splitlines())))
        if self.command.section:
            parts.append("Section: " + prose(self.command.section))
        if self.command.start_page:
            parts.append(f"PDF pages: {self.command.start_page}–{self.command.end_page} (1-based).")
        return parts

    def syntax(self) -> list[str]:
        return [code_block(cli) for cli in self.command.clis] or ["Not extracted."]

    def views(self) -> str:
        return "\n".join("- " + prose(view) for view in self.command.views) or "Not specified."

    def parameters(self) -> str:
        if not self.command.parameters:
            return "No parameters, or parameters were not extracted."
        rows = ["| Parameter | Description / Values |", "| --- | --- |"]
        for parameter in self.command.parameters:
            cells = [
                prose(value).replace("\r\n", "\n").replace("\n", "<br>")
                for value in (parameter.name, parameter.info)
            ]
            rows.append("| " + " | ".join(cells) + " |")
        return "\n".join(rows)

    def examples(self) -> list[str]:
        return [code_block("\n".join(snippet)) for snippet in self.command.examples] or ["Not extracted."]

    def notes(self) -> list[str]:
        parts = []
        if self.command.extra:
            parts.extend(["### Additional Information", code_block(self.command.extra)])
        if self.command.warnings:
            warnings = "\n".join("- " + prose(warning) for warning in self.command.warnings)
            parts.extend(["### Extraction Warnings", warnings])
        return parts

    def related_topics(self) -> list[str]:
        if not self.command.related_topics:
            return []
        rows = []
        for topic in self.command.related_topics:
            text = prose(topic.title) + " — Source section: " + prose(topic.source_section)
            if topic.description:
                text += ". " + prose(topic.description).replace("\n", " ")
            if topic.target_sections:
                text += ". Reference sections: " + ", ".join(prose(s) for s in topic.target_sections)
            else:
                text += ". Target not resolved in the reference outline."
            rows.append("- " + text)
        return ["### Related Topics", "\n".join(rows)]


@dataclass(frozen=True)
class MarkdownDocument:
    corpus: CorpusInput
    title: str | None = None

    def write(self, stream: TextIO) -> None:
        self.write_heading(stream)
        self.write_contents(stream)
        for number, command in enumerate(self.corpus.commands(), 1):
            stream.write(render_command(command, anchor=f"command-{number}") + "\n")

    def write_heading(self, stream: TextIO) -> None:
        heading = self.title or self.corpus.manifest.get("document_title") or "Command Corpus"
        if not isinstance(heading, str):
            raise ValueError("Document title must be a string")
        stream.write("# " + prose(" ".join(heading.splitlines())) + "\n\n")
        stream.write(f"Commands: {len(self.corpus.records)}.\n\n")
        url = self.corpus.manifest.get("source_url")
        if isinstance(url, str) and urlsplit(url).scheme in {"https", "http"}:
            stream.write("Source: " + prose(url) + "\n\n")

    def write_contents(self, stream: TextIO) -> None:
        stream.write("## Contents\n\n")
        for number, command in enumerate(self.corpus.commands(), 1):
            label = prose(" ".join(command.title.splitlines()))
            stream.write(f"- [{label}](#command-{number})\n")
        stream.write("\n")


def render_command(command: Command, *, anchor: str | None = None) -> str:
    return CommandMarkdown(command, anchor).render()


def export_markdown(source: str | Path, output: str | Path, *, title: str | None = None) -> int:
    """Render a JSON record, array, directory or manifest without overwriting output."""
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError(f"Output already exists: {output}")
    corpus = CorpusInput.open(source)
    with staged_text(output) as stream:
        MarkdownDocument(corpus, title).write(stream)
    return len(corpus.records)
