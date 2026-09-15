#!/usr/bin/env python3
"""Audit printed command descriptions independently of parser profiles/bookmarks.

This is a structural census, not a semantic validator of CLI syntax or examples.
Run from the project directory. Only reports are written; corpora remain untouched.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import unicodedata

import pymupdf

LABELS = {
    "Function", "Format", "Usage Guidelines", "Views", "Syntax Description",
    "Command Modes", "Command Mode", "Command Default", "Examples", "Example",
    "Default Level", "Task Name and Operations", "Related Commands", "Related Topics", "See Also",
}
CISCO_FIELDS = {"Syntax Description", "Command Modes", "Command Mode", "Command Default"}


@dataclass
class PrintedDescription:
    section: str | None
    title: str
    page: int
    fields: Counter = field(default_factory=Counter)

    def is_command(self, device: str) -> bool:
        required = CISCO_FIELDS if device == "cisco" else {"Function", "Format"}
        return bool(required.intersection(self.fields))


@dataclass
class PDFInventory:
    device: str
    descriptions: list[PrintedDescription] = field(default_factory=list)
    labels: Counter = field(default_factory=Counter)
    label_fonts: Counter = field(default_factory=Counter)
    last_heading_bottom: float | None = None

    def read(self, document) -> None:
        for page_number, page in enumerate(document, 1):
            for box, text, size, bold in self.page_lines(page):
                self.accept(page_number, box, text, size, bold)

    def page_lines(self, page):
        lines = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line["spans"]
                text = unicodedata.normalize("NFKC", "".join(s["text"] for s in spans)).strip()
                if text:
                    lines.append((line["bbox"], text, max(s["size"] for s in spans),
                                  any(s["flags"] & 16 for s in spans)))
        return sorted(lines, key=lambda line: (line[0][1], line[0][0]))

    def accept(self, page: int, box, text: str, size: float, bold: bool) -> None:
        numbered = re.match(r"^(\d+(?:\.\d+)+)\s+(.+)$", text)
        if self.device == "cisco":
            is_heading = 20.5 <= size <= 21.5
        else:
            is_heading = bool(numbered and size >= 11.5 and bold)
        if is_heading:
            self.add_heading(page, box, text, numbered[1] if numbered else None)
        elif text in LABELS:
            self.labels[text] += 1
            self.label_fonts[(text, round(size, 2), bold)] += 1
            if self.descriptions:
                self.descriptions[-1].fields[text] += 1

    def add_heading(self, page: int, box, text: str, section: str | None) -> None:
        previous = self.descriptions[-1] if self.descriptions else None
        continuation = (
            self.device == "cisco" and previous and previous.page == page
            and self.last_heading_bottom is not None
            and 0 <= box[1] - self.last_heading_bottom < 10
        )
        if continuation:
            previous.title += " " + text
        else:
            self.descriptions.append(PrintedDescription(section, text, page))
        self.last_heading_bottom = box[3]

    def command_descriptions(self) -> list[PrintedDescription]:
        return [description for description in self.descriptions if description.is_command(self.device)]


@dataclass(frozen=True)
class CoverageAudit:
    root: Path
    device: str

    def run(self) -> dict:
        corpus = self.root / "output" / self.device
        manifest = json.loads((corpus / "manifest.json").read_text())
        source = self.root / "data/manuals" / manifest["source_file"]
        profile_module = manifest["parser_profile"].split(":")[0]
        layout = "cisco" if profile_module == "cli_reference_corpus.vendors.cisco" else "huawei"
        inventory = PDFInventory(layout)
        with pymupdf.open(source) as document:
            inventory.read(document)
            pages = len(document)
        comparisons = self.compare(inventory, manifest["commands"])
        fields = self.field_gaps(corpus, comparisons)
        return {
            "device": self.device, "source_pdf": str(source.relative_to(self.root)),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "pages_scanned": pages, "corpus_records": len(manifest["commands"]),
            "printed_command_descriptions": len(comparisons),
            "unmatched_descriptions": [row for row in comparisons if not row["corpus_files"]],
            "unmatched_records": self.unmatched_records(manifest["commands"], comparisons),
            "standalone_field_labels": dict(inventory.labels),
            "field_label_fonts": [
                {"label": label, "size": size, "bold": bold, "count": count}
                for (label, size, bold), count in inventory.label_fonts.items()
            ],
            **fields,
            "inventory": comparisons,
            "limitations": [
                "Independent of bookmarks and production parser, but typography-based.",
                "Counts dedicated descriptions, not every CLI mentioned in examples or related-command tables.",
                "Does not prove semantic completeness of fields or coverage of the device's full command set.",
                "Prepared PDFs require a separate source-to-PDF audit; this census starts at the PDF.",
            ],
        }

    def compare(self, inventory: PDFInventory, records: list[dict]) -> list[dict]:
        comparisons = []
        for description in inventory.command_descriptions():
            matches = [entry["file"] for entry in records if (
                entry["first_page"] == description.page if inventory.device == "cisco"
                else entry["section"] == description.section
            )]
            comparisons.append({
                "section": description.section, "title": description.title,
                "page": description.page, "fields": dict(description.fields), "corpus_files": matches,
            })
        return comparisons

    def unmatched_records(self, records: list[dict], comparisons: list[dict]) -> list[dict]:
        matched = {path for row in comparisons for path in row["corpus_files"]}
        return [record for record in records if record["file"] not in matched]

    def field_gaps(self, corpus: Path, comparisons: list[dict]) -> dict:
        empty_examples = []
        empty_syntax = []
        empty_additional = []
        empty_related = []
        for row in comparisons:
            for filename in row["corpus_files"]:
                command = json.loads((corpus / filename).read_text())
                reference = {"title": command["PageTitle"], "page": row["page"], "file": filename}
                if not command["Examples"] and {"Example", "Examples"}.intersection(row["fields"]):
                    empty_examples.append(reference)
                if not command["CLIs"]:
                    empty_syntax.append(reference)
                if not command.get("ExtraInfo") and {"Default Level", "Task Name and Operations"}.intersection(row["fields"]):
                    empty_additional.append(reference)
                related = {"Related Commands", "Related Topics", "See Also"}.intersection(row["fields"])
                extracted = {topic["source_section"] for topic in command.get("related_topics", [])}
                if related - extracted:
                    empty_related.append({**reference, "sections": sorted(related - extracted)})
        return {
            "empty_examples_with_printed_example_section": empty_examples,
            "empty_cli_records": empty_syntax,
            "empty_extra_info_with_printed_additional_section": empty_additional,
            "empty_related_topics_with_printed_related_section": empty_related,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    corpora = sorted(path.parent.name for path in Path("output").glob("*/manifest.json"))
    parser.add_argument("--corpus", "--device", dest="device", choices=corpora,
                        help="Corpus directory name; by default audit every corpus in output/")
    parser.add_argument("--output", type=Path, default=Path("reports/coverage"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for device in [args.device] if args.device else corpora:
        report = CoverageAudit(Path.cwd(), device).run()
        destination = args.output / f"{device}.json"
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(device, report["printed_command_descriptions"], "descriptions;",
              len(report["unmatched_descriptions"]), "unmatched;", destination, flush=True)


if __name__ == "__main__":
    main()
