#!/usr/bin/env python3
"""Download and verify the exact public Huawei reference used by this project."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tempfile
import urllib.request
import zipfile

DOCUMENT_ID = "EDOC1100439391"
URL = "https://download.huawei.com/edownload/e/download.do?actionFlag=download&nid=EDOC1100439391&partNo=6001&mid=SUPE_DOC"
ARCHIVE_SHA256 = "6c80ce0b356c3efde4d1298198623a406658fc6d56b911608ed90d6fdd9835f1"
PDF_SHA256 = "af8546aa428648f4acc9edf7ddb10910b6629da13056681abb1d87553134f17a"
MEMBER = "CloudEngine 9800, 8800, and 6800 V300R024C00 Command Reference.pdf"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    pdf = destination / "huawei-cloudengine-9800-8800-6800-v300r024c00.pdf"
    archive = destination / "cloudengine-v300r024c00.zip"
    if pdf.exists():
        if digest(pdf) != PDF_SHA256:
            raise ValueError(f"Existing PDF checksum mismatch: {pdf}")
        return pdf
    if not archive.exists():
        request = urllib.request.Request(URL, headers={"User-Agent": "cli-reference-corpus/0.1", "Cookie": "supportelang=en; lang=en"})
        with tempfile.NamedTemporaryFile(dir=destination, delete=False) as temp:
            pending = Path(temp.name)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > 200 * 1024 * 1024:
                            raise ValueError("Unexpectedly large download")
                        temp.write(chunk)
                temp.close()
                if digest(pending) != ARCHIVE_SHA256:
                    raise ValueError("Archive checksum mismatch: Huawei may have updated the document, or returned an HTML/login page")
                pending.rename(archive)
            finally:
                pending.unlink(missing_ok=True)
    if digest(archive) != ARCHIVE_SHA256:
        raise ValueError(f"Archive checksum mismatch: {archive}")
    # Extract a single known member; never trust arbitrary archive paths.
    with zipfile.ZipFile(archive) as source:
        data = source.read(MEMBER)
    if not data.startswith(b"%PDF-") or hashlib.sha256(data).hexdigest() != PDF_SHA256:
        raise ValueError("PDF checksum mismatch")
    pdf.write_bytes(data)
    return pdf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("data/manuals"))
    args = parser.parse_args()
    try:
        print(fetch(args.destination))
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
        parser.exit(1, f"Download failed: {error}\n")
