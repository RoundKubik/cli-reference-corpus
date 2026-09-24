"""Download a selected manual without assuming its device model or release."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
import zipfile

import pymupdf

from .storage import file_hash, write_json


def download_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must be an HTTP(S) download URL or Huawei EDOC document page")
    # These document pages identify Huawei's downloadable package. Keep direct
    # download URLs (including partNo and signed query parameters) unchanged.
    if parsed.hostname == "support.huawei.com":
        match = re.fullmatch(r"/enterprise/(?:en|zh)/doc/(EDOC\d+)/?", parsed.path)
        if match:
            return ("https://download.huawei.com/edownload/e/download.do?actionFlag=download"
                    f"&nid={match[1]}&partNo=6001&mid=SUPE_DOC")
    return url


def copy_limited(source, destination, limit: int) -> None:
    total = 0
    while chunk := source.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            raise ValueError(f"Document exceeds --max-bytes ({limit})")
        destination.write(chunk)


def check_hash(path: Path, expected: str | None, label: str) -> None:
    if expected is not None and file_hash(path) != expected.lower():
        raise ValueError(f"{label} SHA-256 mismatch")


def archive_member(package: zipfile.ZipFile, suffix: str, member: str | None) -> zipfile.ZipInfo:
    candidates = [entry for entry in package.infolist()
                  if not entry.is_dir() and Path(entry.filename).suffix.lower() == suffix]
    if member:
        candidates = [entry for entry in candidates if entry.filename == member]
    elif len(candidates) > 1:
        complete = [entry for entry in candidates
                    if re.search(r"command reference\.pdf$", entry.filename, re.IGNORECASE)]
        if len(complete) == 1:
            candidates = complete
    if len(candidates) != 1:
        available = "\n".join(entry.filename for entry in package.infolist()
                              if not entry.is_dir() and Path(entry.filename).suffix.lower() == suffix)
        raise ValueError(f"Select exactly one {suffix} document with --member. Available members:\n{available}")
    return candidates[0]


def validate_document(path: Path, suffix: str) -> None:
    with path.open("rb") as stream:
        signature = stream.read(8)
    if suffix == ".chm" and signature[:4] == b"ITSF":
        return
    if suffix == ".pdf" and signature.startswith(b"%PDF-"):
        try:
            with pymupdf.open(path) as document:
                if document.is_pdf and len(document) > 0:
                    return
        except RuntimeError as error:
            raise ValueError("Downloaded PDF is corrupt or incomplete") from error
    raise ValueError(f"Response is not a valid {suffix} document; it may be an HTML/login page. "
                     "Use a direct public download URL.")


def fetch_document(url: str, output: Path | None = None, *, member: str | None = None,
                   sha256: str | None = None, document_sha256: str | None = None,
                   source_map: Path | None = None, max_bytes: int = 4 * 1024**3,
                   destination: Path = Path("data/manuals"), preferred_format: str = ".pdf") -> Path:
    output = Path(output) if output is not None else None
    destination = output.parent if output else Path(destination)
    source_map = Path(source_map) if source_map else None
    resolved = download_url(url)
    suffix = output.suffix.lower() if output else None
    if suffix is not None and suffix not in {".pdf", ".chm"}:
        raise ValueError("Output must end in .pdf or .chm (also selects the document type inside ZIP)")
    if max_bytes < 1:
        raise ValueError("--max-bytes must be positive")
    for value in (sha256, document_sha256):
        if value is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("SHA-256 must contain exactly 64 hexadecimal characters")
    for path in (output, source_map or (output.with_suffix(".source.json") if output else None)):
        if path is not None and path.exists():
            raise ValueError(f"Output already exists: {path}")
    destination.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "cli-reference-corpus/0.3"}
    if (urlsplit(resolved).hostname or "").endswith(".huawei.com"):
        headers["Cookie"] = "supportelang=en; lang=en"
    with tempfile.TemporaryDirectory(prefix=".manual-", dir=destination) as temporary:
        root = Path(temporary)
        payload, document = root / "download", root / "document"
        with urlopen(Request(resolved, headers=headers), timeout=120) as response:
            final_url = response.geturl()
            filename = response.headers.get_filename() or Path(unquote(urlsplit(final_url).path)).name
            with payload.open("wb") as stream:
                copy_limited(response, stream, max_bytes)
        check_hash(payload, sha256, "Download")
        selected_member = None
        if zipfile.is_zipfile(payload):
            with zipfile.ZipFile(payload) as package:
                if suffix is None:
                    formats = {Path(entry.filename).suffix.lower() for entry in package.infolist()
                               if not entry.is_dir() and (not member or entry.filename == member)} & {".pdf", ".chm"}
                    if not formats:
                        raise ValueError("ZIP contains no matching PDF/CHM document")
                    suffix = preferred_format if preferred_format in formats else sorted(formats)[0]
                selected = archive_member(package, suffix, member)
                selected_member = selected.filename
                filename = Path(selected.filename.replace("\\", "/")).name
                if selected.file_size > max_bytes:
                    raise ValueError("Extracted document exceeds --max-bytes")
                # Never extract archive paths: stream only the selected member.
                with package.open(selected) as source, document.open("wb") as stream:
                    copy_limited(source, stream, max_bytes)
        else:
            if member:
                raise ValueError("--member is only valid for ZIP downloads")
            document = payload
            if suffix is None:
                with payload.open("rb") as stream:
                    signature = stream.read(8)
                suffix = ".chm" if signature.startswith(b"ITSF") else ".pdf"
        validate_document(document, suffix)
        check_hash(document, document_sha256, "Document")
        if output is None:
            if Path(filename).suffix.lower() != suffix:
                identifier = re.search(r"EDOC\d+", url, re.IGNORECASE)
                filename = (identifier[0] if identifier else "manual-" + hashlib.sha256(url.encode()).hexdigest()[:12]) + suffix
            filename = re.sub(r"[^\w.()-]+", "_", Path(filename.replace("\\", "/")).name).strip("._")
            output = destination / filename
        source_map = source_map or output.with_suffix(".source.json")
        if output.resolve() == source_map.resolve():
            raise ValueError("Output document and source map must be different files")
        for path in (output, source_map):
            if path.exists():
                raise ValueError(f"Output already exists: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "source_url": url, "download_url": resolved, "final_url": final_url,
            "download_sha256": file_hash(payload), "archive_member": selected_member,
            "document_file": output.name, "document_sha256": file_hash(document),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }
        # Stage each file on its destination filesystem; never replace an existing file.
        with tempfile.TemporaryDirectory(prefix=".source-", dir=source_map.parent) as mapping_dir:
            mapping = Path(mapping_dir) / "source.json"
            write_json(mapping, metadata)
            os.link(document, output)
            try:
                os.link(mapping, source_map)
            except OSError:
                output.unlink()
                raise
    return output


def add_url_arguments(parser: argparse.ArgumentParser, *, output: bool = True, source_map: bool = True) -> None:
    parser.add_argument("source_url", nargs="?", help="Documentation URL (alternative to --url)")
    parser.add_argument("--url", help="Direct PDF/CHM/ZIP URL or Huawei EDOC document page")
    if output:
        parser.add_argument("-o", "--output", type=Path, help="Output .pdf or .chm for --url")
    if source_map:
        parser.add_argument("--source-map", type=Path, help="Provenance JSON (default: OUTPUT.source.json)")
    parser.add_argument("--member", help="Exact ZIP member path when the package contains several manuals")
    parser.add_argument("--sha256", help="Optional SHA-256 of the HTTP response payload")
    parser.add_argument("--document-sha256", help="Optional SHA-256 of the selected PDF/CHM")
    parser.add_argument("--max-bytes", type=int, default=4 * 1024**3,
                        help="Maximum download and extracted document size (default: 4 GiB)")


def supplied_url(args, parser: argparse.ArgumentParser) -> str | None:
    if args.url and args.source_url:
        parser.error("Supply the URL once, as a positional argument or --url")
    url = args.url or args.source_url
    if not url and any((args.member, args.sha256, args.document_sha256)):
        parser.error("--member/--sha256/--document-sha256 require a URL")
    return url


def fetch_from_arguments(args, parser: argparse.ArgumentParser, *, preferred_format: str = ".pdf") -> Path:
    return fetch_document(args.url, args.output, member=args.member, sha256=args.sha256,
                          document_sha256=args.document_sha256, source_map=args.source_map,
                          max_bytes=args.max_bytes, destination=args.destination or Path("data/manuals"),
                          preferred_format=preferred_format)
