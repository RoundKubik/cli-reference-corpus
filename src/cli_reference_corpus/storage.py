"""UTF-8 JSON and staged output publication shared by the exporters."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterator, TextIO


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid JSON in {path}: {error}") from error


def write_json(path: Path, data) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@contextmanager
def staged_directory(output: Path) -> Iterator[Path]:
    if output.exists():
        raise ValueError(f"Output already exists: {output}. Choose a new directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".nassim-", dir=output.parent))
    try:
        yield stage
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


@contextmanager
def staged_text(output: Path) -> Iterator[TextIO]:
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=output.parent, delete=False
        ) as stream:
            pending = Path(stream.name)
            yield stream
        # Publish without overwriting, including when a concurrent writer wins.
        os.link(pending, output)
    finally:
        if pending:
            pending.unlink(missing_ok=True)
