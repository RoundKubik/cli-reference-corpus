"""Validated, lazy access to standalone command JSON and corpus manifests."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterator

from .model import Command
from .storage import read_json


def natural_key(value) -> list[tuple[int, int | str]]:
    return [
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"(\d+)", str(value))
    ]


@dataclass(frozen=True)
class CommandRecord:
    value: Path | dict
    metadata: dict = field(default_factory=dict)

    def command(self, warnings: dict[str, list[str]]) -> Command:
        data = read_json(self.value) if isinstance(self.value, Path) else self.value
        command = Command.from_dict(
            data,
            title=self.metadata.get("title", ""),
            section=self.metadata.get("section", ""),
            start_page=self.metadata.get("first_page", 0),
            end_page=self.metadata.get("last_page", 0),
        )
        command.warnings = warnings.get(command.section, [])
        return command


@dataclass(frozen=True)
class ManifestEntries:
    root: Path
    manifest: dict

    def records(self) -> list[CommandRecord]:
        entries = self.manifest["commands"]
        if not isinstance(entries, list):
            raise ValueError("manifest.commands must be an array")
        records = []
        seen = set()
        for entry in entries:
            path = self.entry_path(entry)
            if path in seen:
                raise ValueError("Manifest paths must be unique and inside the corpus directory")
            self.validate_metadata(entry)
            seen.add(path)
            records.append(CommandRecord(path, entry))
        return records

    def entry_path(self, entry: dict) -> Path:
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
            raise ValueError("Manifest command requires a file path")
        path = (self.root / entry["file"]).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Manifest paths must be unique and inside the corpus directory")
        return path

    def validate_metadata(self, entry: dict) -> None:
        for key in ("title", "section"):
            if key in entry and not isinstance(entry[key], str):
                raise ValueError(f"Manifest {key} must be a string")
        for key in ("first_page", "last_page"):
            if key in entry and (type(entry[key]) is not int or entry[key] < 1):
                raise ValueError(f"Manifest {key} must be a positive integer")


@dataclass(frozen=True)
class CorpusInput:
    manifest: dict
    records: list[CommandRecord]
    warnings: dict[str, list[str]]

    @classmethod
    def open(cls, source: Path) -> CorpusInput:
        manifest, records = cls.read_records(source)
        if not records:
            raise ValueError("No command JSON records found")
        warnings = cls.read_warnings(source) if manifest else {}
        return cls(manifest, records, warnings)

    @staticmethod
    def read_records(source: Path) -> tuple[dict, list[CommandRecord]]:
        if source.is_dir() and (source / "manifest.json").is_file():
            source = source / "manifest.json"
        if source.is_dir():
            folder = source / "cmd_corpus" if (source / "cmd_corpus").is_dir() else source
            paths = sorted(folder.rglob("*.json"), key=natural_key)
            return {}, [
                CommandRecord(path) for path in paths
                if path.name not in {"validation.json", "manifest.json"}
            ]
        data = read_json(source)
        if isinstance(data, dict) and "commands" in data and "CLIs" not in data:
            return data, ManifestEntries(source.parent.resolve(), data).records()
        records = data if isinstance(data, list) else [data]
        return {}, [CommandRecord(record) for record in records]

    @staticmethod
    def read_warnings(source: Path) -> dict[str, list[str]]:
        path = (source if source.is_dir() else source.parent) / "validation.json"
        if not path.exists():
            return {}
        report = read_json(path)
        if not isinstance(report, dict) or not isinstance(report.get("issues", []), list):
            raise ValueError("Invalid validation report")
        warnings = {}
        for issue in report.get("issues", []):
            if not isinstance(issue, dict) or not isinstance(issue.get("section"), str):
                raise ValueError("Invalid validation issue")
            messages = issue.get("warnings")
            if not isinstance(messages, list) or any(not isinstance(w, str) for w in messages):
                raise ValueError("Invalid validation issue")
            warnings[issue["section"]] = messages
        return warnings

    def commands(self) -> Iterator[Command]:
        for record in self.records:
            yield record.command(self.warnings)
