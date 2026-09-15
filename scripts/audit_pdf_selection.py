#!/usr/bin/env python3
"""Verify retained PDF pages against the original publisher PDF."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from cli_reference_corpus.storage import file_hash, read_json, write_json


@dataclass(frozen=True)
class PDFSelectionAudit:
    original: Path
    selected: Path
    source_map: Path

    def run(self) -> dict:
        metadata = read_json(self.source_map)
        first, last = metadata['original_page_range']
        issues = []
        original_hash, selected_hash = file_hash(self.original), file_hash(self.selected)
        if original_hash != metadata['original_pdf_sha256'] or selected_hash != metadata['pdf_sha256']:
            issues.append({'kind': 'source_hash_mismatch'})
        with pymupdf.open(self.original) as original, pymupdf.open(self.selected) as selected:
            if len(selected) != last - first + 1:
                issues.append({'kind': 'page_count_mismatch'})
            for offset, page in enumerate(selected):
                reference = original[first - 1 + offset]
                for kind, matches in (
                    ('geometry', page.rect == reference.rect),
                    ('text', page.get_text() == reference.get_text()),
                    ('image_count', len(page.get_images()) == len(reference.get_images())),
                ):
                    if not matches:
                        issues.append({'kind': kind + '_mismatch', 'page': offset + 1})
            expected_outline = [[level, title, page - first + 1]
                                for level, title, page in original.get_toc() if first <= page <= last]
            if selected.get_toc() != expected_outline:
                issues.append({'kind': 'outline_mismatch'})
        return {
            'original_pdf_sha256': original_hash, 'selected_pdf_sha256': selected_hash,
            'original_page_range': [first, last], 'pages_checked': last - first + 1,
            'issues': issues,
            'scope': 'Exact extracted text, page geometry, image counts and bookmarks for every retained page.',
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--selected', type=Path, required=True)
    parser.add_argument('--source-map', type=Path, required=True)
    parser.add_argument('-o', '--output', type=Path, required=True)
    args = parser.parse_args()
    report = PDFSelectionAudit(args.original, args.selected, args.source_map).run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, report)
    print(f"Pages checked: {report['pages_checked']}; issues: {len(report['issues'])}")
    raise SystemExit(bool(report['issues']))


if __name__ == '__main__':
    main()
