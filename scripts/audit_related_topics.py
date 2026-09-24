#!/usr/bin/env python3
"""Compare stored references with current rules across complete local corpora."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from cli_reference_corpus.command_syntax import syntax_issues
from cli_reference_corpus.corpus_input import CorpusInput
from cli_reference_corpus.related_topics import INFERRED_SECTIONS, RelatedTopicIndex
from cli_reference_corpus.storage import write_json


def audit(root: Path, sample_limit: int = 20) -> dict:
    corpus = CorpusInput.open(root)
    commands = list(corpus.commands())
    index = RelatedTopicIndex.from_commands(commands)
    entries = {entry["section"]: entry for entry in corpus.manifest["commands"]}
    totals = Counter()
    kinds = Counter()
    parameter_targets = Counter()
    samples = []
    for number, command in enumerate(commands, 1):
        before = {target for topic in command.related_topics for target in topic.target_sections}
        index.enrich(command)
        after = {target for topic in command.related_topics for target in topic.target_sections}
        added, removed = after - before, before - after
        totals["commands"] += 1
        totals["related_topics"] += len(command.related_topics)
        totals["commands_with_related_topics"] += bool(command.related_topics)
        totals["commands_with_changed_targets"] += bool(added or removed)
        totals["added_target_sections"] += len(added)
        totals["removed_target_sections"] += len(removed)
        totals["syntax_issues"] += len(syntax_issues(command.clis))
        for topic in command.related_topics:
            topic.target_files = list(dict.fromkeys(
                Path(entries[section]["file"]).name for section in topic.target_sections
                if section in entries and section != command.section
            ))
            kinds[topic.reference_kind] += 1
            if topic.source_section in INFERRED_SECTIONS:
                assert command.section not in topic.target_sections, (root, command.section, topic.title)
                assert all(section in entries for section in topic.target_sections), (root, command.section, topic.title)
            for section in topic.target_sections:
                if section in entries:
                    assert (root / entries[section]["file"]).is_file(), entries[section]
                    totals["verified_target_files"] += 1
                else:
                    totals["external_numbered_references"] += 1
            if topic.reference_kind == "parameter_topic":
                parameter_targets.update(topic.target_sections)
        if (added or removed) and (len(samples) < sample_limit or command.title == "port trunk allow-pass vlan"):
            samples.append({
                "file": entries[command.section]["file"], "title": command.title,
                "added_targets": [{"section": section, "title": entries[section]["title"]}
                                  for section in sorted(added) if section in entries],
                "removed_targets": [{"section": section, "title": entries[section]["title"]}
                                    for section in sorted(removed) if section in entries],
                "parameter_topics": [topic.to_dict() for topic in command.related_topics
                                     if topic.reference_kind == "parameter_topic"],
            })
        if number % 500 == 0:
            print(f"{root.name}: {number}/{len(commands)}", flush=True)
    return {
        "corpus": root.name, "source_sha256": corpus.manifest.get("source_sha256"),
        "counts": dict(totals), "reference_kinds": dict(kinds),
        "most_common_parameter_targets": [
            {"section": section, "title": entries[section]["title"], "references": count}
            for section, count in parameter_targets.most_common(30)
        ],
        "change_samples": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpora", type=Path, nargs="+")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--sample-limit", type=int, default=20)
    args = parser.parse_args()
    report = {
        "scope": "All records; before/after target comparison, file existence, self-reference and syntax checks.",
        "limitations": "Parameter topics are lexical relevance candidates derived from the manual. "
                       "Structural checks do not prove semantic precision or recall; regression tests cover reviewed examples.",
        "corpora": [audit(root, args.sample_limit) for root in args.corpora],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    print(args.output)


if __name__ == "__main__":
    main()
