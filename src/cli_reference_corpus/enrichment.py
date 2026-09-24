"""Add documentation references to an existing corpus without rereading its PDF."""
from __future__ import annotations

from pathlib import Path

from .corpus import CommandFiles, resolve_topic_files
from .corpus_input import CorpusInput
from .markdown import render_command
from .model import validate
from .related_topics import RelatedTopicIndex
from .command_syntax import syntax_issues
from .storage import read_json, staged_directory, write_json


def enrich_corpus(source: str | Path, output: str | Path) -> dict:
    source, output = Path(source), Path(output)
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a new directory.")
    corpus = CorpusInput.open(source)
    if not corpus.manifest:
        raise ValueError("Enrichment requires a corpus directory or manifest.json with command section IDs")
    commands = list(corpus.commands())
    sections = [command.section for command in commands]
    if not all(sections) or len(set(sections)) != len(sections):
        raise ValueError("Enrichment requires unique, nonempty command section IDs")
    index = RelatedTopicIndex.from_commands(commands)
    for command in commands:
        index.enrich(command)
        command.warnings = [warning for warning in command.warnings
                            if not warning.startswith(("unbalanced_syntax:", "unsupported_syntax:"))]
        command.warnings = validate(command)
    resolve_topic_files(commands)
    counts = {
        "commands": len(commands),
        "commands_with_related_topics": sum(bool(c.related_topics) for c in commands),
        "related_topics": sum(len(c.related_topics) for c in commands),
    }
    root = source if source.is_dir() else source.parent
    report_path = root / "validation.json"
    report = read_json(report_path) if report_path.exists() else {}
    report.update(counts)
    report["issues"] = [{"section": command.section, "title": command.title,
                         "pages": [command.start_page, command.end_page], "warnings": command.warnings}
                        for command in commands if command.warnings]
    with staged_directory(output) as stage:
        directory = stage / "cmd_corpus"
        directory.mkdir()
        entries = []
        for record, command in zip(corpus.records, commands):
            # Retain schema, extension fields and all original command content.
            data = read_json(record.value) if isinstance(record.value, Path) else dict(record.value)
            data["related_topics"] = [topic.to_dict() for topic in command.related_topics]
            data["syntax_issues"] = syntax_issues(command.clis)
            files = CommandFiles(command, corpus.manifest.get("schema", "repository"))
            path = directory / files.filename()
            if path.exists():
                raise ValueError(f"Duplicate command filename: {path.name}")
            write_json(path, data)
            path.with_suffix(".md").write_text(render_command(command), encoding="utf-8")
            entries.append({**record.metadata, **files.manifest_entry(path)})
        write_json(stage / "manifest.json", {**corpus.manifest, "commands": entries})
        write_json(stage / "validation.json", report)
    return counts
