"""Publish command pairs and their provenance as one complete corpus."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from . import __version__
from .markdown import render_command
from .model import Command, validate
from .parser import ParseResult
from .storage import file_hash, staged_directory, write_json


@dataclass(frozen=True)
class CommandFiles:
    command: Command
    schema: str

    def filename(self) -> str:
        title = re.sub(r"[^a-zA-Z0-9_-]+", "_", self.command.title).strip("_")[:100]
        section = re.sub(r"[^a-zA-Z0-9_.-]+", "_", self.command.section).strip(".")[:100]
        return f"{section or 'command'}_{title}.json"

    def write(self, directory: Path) -> dict:
        path = directory / self.filename()
        if path.exists():
            raise ValueError(f"Duplicate command section: {self.command.section}")
        data = self.command.to_dict(self.schema)
        write_json(path, data)
        rendered = self.rendered_command(data)
        path.with_suffix(".md").write_text(render_command(rendered), encoding="utf-8")
        return self.manifest_entry(path)

    def rendered_command(self, data: dict) -> Command:
        command = Command.from_dict(
            data,
            title=self.command.title,
            section=self.command.section,
            start_page=self.command.start_page,
            end_page=self.command.end_page,
        )
        command.warnings = validate(self.command)
        return command

    def manifest_entry(self, path: Path) -> dict:
        return {
            "file": f"cmd_corpus/{path.name}",
            "markdown_file": f"cmd_corpus/{path.stem}.md",
            "section": self.command.section,
            "title": self.command.title,
            "first_page": self.command.start_page,
            "last_page": self.command.end_page,
        }


@dataclass(frozen=True)
class CorpusWriter:
    result: ParseResult
    source: Path
    schema: str = "repository"
    source_url: str | None = None

    def write(self, output: Path) -> dict:
        with staged_directory(output) as stage:
            directory = stage / "cmd_corpus"
            directory.mkdir()
            entries = [
                CommandFiles(command, self.schema).write(directory)
                for command in self.result.commands
            ]
            report = self.result.report()
            write_json(stage / "manifest.json", self.manifest(entries))
            write_json(stage / "validation.json", report)
        return report

    def manifest(self, entries: list[dict]) -> dict:
        return {
            "parser_version": __version__,
            "schema_version": 3,
            "schema": self.schema,
            "parser_profile": self.result.parser_profile,
            "source_file": self.source.name,
            "source_sha256": file_hash(self.source),
            "source_url": self.source_url,
            "document_title": self.result.document_title,
            "page_numbering": "physical PDF pages, 1-based",
            "commands": entries,
        }


def write_corpus(
    result: ParseResult,
    source: Path,
    output: Path,
    schema: str,
    source_url: str | None = None,
) -> dict:
    """Compatibility entry point for existing callers and custom profiles."""
    return CorpusWriter(result, source, schema, source_url).write(output)
