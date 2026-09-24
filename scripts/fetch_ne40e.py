#!/usr/bin/env python3
"""Download an NE40E manual by URL, or verify a package against a source manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

from fetch_cloudengine import digest
from cli_reference_corpus.downloads import add_url_arguments, fetch_from_arguments, supplied_url


def fetch(destination: Path, manifest: Path) -> Path:
    source = json.loads(manifest.read_text(encoding='utf-8'))
    destination.mkdir(parents=True, exist_ok=True)
    for key in ('archive_file', 'chm_file'):
        if Path(source[key]).name != source[key]:
            raise ValueError('Manifest filenames must be plain basenames')
    chm = destination / source['chm_file']
    archive = destination / source['archive_file']
    archive_limit = source.get('archive_size', 200 * 1024 * 1024)
    if chm.exists():
        if digest(chm) != source['chm_sha256']:
            raise ValueError(f'Existing CHM checksum mismatch: {chm}')
        return chm
    if not archive.exists():
        request = urllib.request.Request(source['download_url'], headers={
            'User-Agent':'cli-reference-corpus/0.2', 'Cookie':'supportelang=en; lang=en'})
        with tempfile.NamedTemporaryFile(dir=destination, delete=False) as temp:
            pending = Path(temp.name)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > archive_limit:
                            raise ValueError('Unexpectedly large archive')
                        temp.write(chunk)
                temp.close()
                if digest(pending) != source['archive_sha256']:
                    raise ValueError('Archive checksum mismatch: upstream changed or returned an error page')
                pending.rename(archive)
            finally:
                pending.unlink(missing_ok=True)
    if digest(archive) != source['archive_sha256']:
        raise ValueError(f'Archive checksum mismatch: {archive}')
    extract_chm(archive, chm, source)
    return chm


def extract_chm(archive: Path, chm: Path, source: dict) -> None:
    with tempfile.NamedTemporaryFile(dir=chm.parent, delete=False) as temp:
        pending = Path(temp.name)
        try:
            with zipfile.ZipFile(archive) as package, package.open(source['chm_member']) as member:
                signature = member.read(4)
                if signature != b'ITSF':
                    raise ValueError('CHM signature mismatch')
                temp.write(signature)
                shutil.copyfileobj(member, temp, length=1024 * 1024)
            temp.close()
            if digest(pending) != source['chm_sha256']:
                raise ValueError('CHM checksum mismatch')
            pending.rename(chm)
        finally:
            pending.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    add_url_arguments(parser)
    parser.add_argument('--destination', type=Path, help='Download directory (URL mode default: data/manuals)')
    parser.add_argument('--manifest', type=Path, help='External source manifest with download URL and SHA-256 checksums')
    args = parser.parse_args()
    args.url = supplied_url(args, parser)
    try:
        if args.url:
            if args.manifest:
                parser.error('Use either --url or --manifest')
            print(fetch_from_arguments(args, parser, preferred_format='.chm'))
        else:
            if not args.manifest or not args.destination:
                parser.error('Supply a documentation URL, or --manifest and --destination')
            print(fetch(args.destination, args.manifest))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Download failed: {error}\n')
