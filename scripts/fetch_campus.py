#!/usr/bin/env python3
"""Prepare the pinned Campus Switch reference PDF from Huawei's public archive."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

import pymupdf

from cli_reference_corpus.storage import file_hash, write_json

URL = ('https://download.huawei.com/edownload/e/download.do?actionFlag=download'
       '&nid=EDOC1000178165&partNo=6001&mid=SUPE_DOC')
DOCUMENT_URL = 'https://support.huawei.com/enterprise/en/doc/EDOC1000178165'
ARCHIVE_SHA256 = '8197cc1965622aa836e4394f89158d06f6a6d20af64ef04c9270850147d94ed0'
PDF_SHA256 = '95cedc55ff1dcc50c8d63fa926134105282a7f82a850518c88d9eff4b6db1a53'
MEMBER = 'S1720, S2700, S5700, and S6720 V200R011C10 Command Reference.pdf'


def download(destination: Path) -> None:
    request = urllib.request.Request(URL, headers={'User-Agent': 'cli-reference-corpus/0.2'})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open('xb') as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)


def extract(archive: Path, destination: Path) -> None:
    if file_hash(archive) != ARCHIVE_SHA256:
        raise ValueError('Archive checksum mismatch')
    with zipfile.ZipFile(archive) as package, package.open(MEMBER) as source:
        with destination.open('xb') as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
    if file_hash(destination) != PDF_SHA256:
        raise ValueError('Original PDF checksum mismatch')


def select_pages(source: Path, destination: Path, include_upgrade: bool) -> dict:
    with pymupdf.open(source) as document:
        original_pages = len(document)
        outline = document.get_toc()
        upgrade_page = next(page for level, title, page in outline
                            if level == 1 and title == '19 Upgrade-compatible Commands Reference')
        retained_pages = original_pages if include_upgrade else upgrade_page - 1
        if not include_upgrade:
            document.delete_pages(retained_pages, original_pages - 1)
            document.set_toc([entry for entry in outline if entry[2] <= retained_pages])
            metadata = document.metadata
            metadata['subject'] = ('Locally selected original Huawei PDF pages; '
                                   'chapter 19 Upgrade-compatible Commands Reference excluded.')
            document.set_metadata(metadata)
        document.save(destination, garbage=1, deflate=True)
    return {
        'document_url': DOCUMENT_URL, 'download_url': URL,
        'archive_sha256': ARCHIVE_SHA256, 'original_pdf_member': MEMBER,
        'original_pdf_sha256': PDF_SHA256, 'original_pdf_pages': original_pages,
        'pdf_sha256': file_hash(destination), 'retained_pages': retained_pages,
        'original_page_range': [1, retained_pages],
        'excluded_original_page_range': [] if include_upgrade else [upgrade_page, original_pages],
        'include_upgrade': include_upgrade,
        'origin': 'Original Huawei PDF pages; no HTML conversion, OCR or text reflow.',
        'scope': ('Complete reference.' if include_upgrade else
                  'Front matter and chapters 1–18; chapter 19 excluded by the project scope. '
                  'The original printed contents still lists chapter 19.'),
    }


def prepare(output: Path, source_map: Path, archive: Path | None, include_upgrade: bool) -> None:
    if output.exists() or source_map.exists():
        raise ValueError('Output PDF or source map already exists')
    with tempfile.TemporaryDirectory(prefix='campus-reference-') as temporary:
        root = Path(temporary)
        if archive is None:
            archive = root / 'reference.zip'
            download(archive)
        original, selected = root / 'original.pdf', root / 'selected.pdf'
        extract(archive, original)
        metadata = select_pages(original, selected, include_upgrade)
        output.parent.mkdir(parents=True, exist_ok=True)
        source_map.parent.mkdir(parents=True, exist_ok=True)
        with selected.open('rb') as source, output.open('xb') as destination:
            shutil.copyfileobj(source, destination)
        write_json(source_map, metadata)
    print(f"Prepared {metadata['retained_pages']} pages: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Previously downloaded official ZIP; otherwise download it')
    parser.add_argument('-o', '--output', type=Path, required=True)
    parser.add_argument('--source-map', type=Path, required=True)
    parser.add_argument('--include-upgrade', action='store_true', help='Also retain chapter 19')
    args = parser.parse_args()
    try:
        prepare(args.output, args.source_map, args.archive, args.include_upgrade)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Preparation failed: {error}\n')


if __name__ == '__main__':
    main()
