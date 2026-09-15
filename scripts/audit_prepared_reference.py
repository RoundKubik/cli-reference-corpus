#!/usr/bin/env python3
"""Check that every command in a prepared reference PDF has a corpus record."""
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(title: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", title).split())


def audit(source_map: Path, pdf: Path, corpus: Path) -> dict:
    preparation = read_json(source_map)
    manifest = read_json(corpus / "manifest.json")
    topics = preparation.get("topics", preparation.get("commands", []))
    expected = {topic["section"]: topic for topic in topics if topic.get("is_command", True)}
    records = manifest["commands"]
    actual = {record["section"]: record for record in records}
    issues = []
    if not expected:
        issues.append({"kind": "empty_source_command_inventory"})
    with pdf.open("rb") as source:
        digest = hashlib.sha256()
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    pdf_hash = digest.hexdigest()
    if pdf_hash != preparation["pdf_sha256"] or pdf_hash != manifest["source_sha256"]:
        issues.append({"kind": "source_pdf_hash_mismatch"})
    if len(actual) != len(records):
        issues.append({"kind": "duplicate_corpus_sections"})
    for section in sorted(expected.keys() - actual.keys()):
        issues.append({"kind": "missing_command", "section": section, "title": expected[section]["title"]})
    for section in sorted(actual.keys() - expected.keys()):
        issues.append({"kind": "unexpected_command", "section": section, "title": actual[section]["title"]})
    for section in expected.keys() & actual.keys():
        topic, record = expected[section], actual[section]
        if normalized(topic["title"]) != normalized(record["title"]):
            issues.append({"kind": "title_mismatch", "section": section, "expected": topic["title"], "actual": record["title"]})
        if record["first_page"] != topic["first_page"] or not topic["first_page"] <= record["last_page"] <= topic["last_page"]:
            issues.append({"kind": "page_mismatch", "section": section})
        for key in ("file", "markdown_file"):
            if not (corpus / record[key]).is_file():
                issues.append({"kind": "missing_file", "section": section, "file": record[key]})
    return {
        "source_pdf": pdf.name, "source_sha256": pdf_hash,
        "reference_topics": len(topics),
        "source_command_topics": len(expected), "corpus_records": len(records),
        "chm_outline_check": preparation.get("outline_check"),
        "issues": issues,
        "scope": "Source-topic and file coverage; does not certify semantic correctness of extracted fields.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-map", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.source_map, args.pdf, args.corpus)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Source commands: {report['source_command_topics']}; corpus: {report['corpus_records']}; issues: {len(report['issues'])}")
    raise SystemExit(bool(report["issues"]))


if __name__ == "__main__":
    main()
