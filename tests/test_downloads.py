"""Downloads must follow the requested source, preserve bytes and fail cleanly."""
from email.message import Message
import hashlib
from io import BytesIO
import json
from pathlib import Path
import runpy
import sys
import zipfile

import pytest

from cli_reference_corpus import downloads

ROOT = Path(__file__).parents[1]
PDF = (ROOT / "tests/fixtures/bandwidth.pdf").read_bytes()
CHM = b"ITSF" + bytes(100)
URL = "https://example.org/different-model/Release42.zip"


def package(members):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return stream.getvalue()


def response(monkeypatch, data, *, filename=None):
    requests = []

    def open_url(request, timeout):
        requests.append(request.full_url)
        stream = BytesIO(data)
        stream.geturl = lambda: request.full_url
        stream.headers = Message()
        if filename:
            stream.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return stream

    monkeypatch.setattr(downloads, "urlopen", open_url)
    return requests


@pytest.mark.parametrize("script, content, filename", [
    ("fetch_cloudengine.py", PDF, "Different CloudEngine.pdf"),
    ("fetch_campus.py", PDF, "Different Campus.pdf"),
    ("fetch_ne40e.py", CHM, "Different NE40E.chm"),
])
def test_each_script_accepts_a_single_url_for_another_model(tmp_path, monkeypatch, script, content, filename):
    calls = response(monkeypatch, package({filename: content}))
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [script, URL])
    runpy.run_path(str(ROOT / "scripts" / script), run_name="__main__")
    outputs = list((tmp_path / "data/manuals").glob("*" + Path(filename).suffix))
    assert len(outputs) == 1
    assert outputs[0].read_bytes() == content
    metadata = json.loads(outputs[0].with_suffix(".source.json").read_text())
    assert metadata["source_url"] == URL
    assert metadata["archive_member"] == filename
    assert metadata["document_sha256"] == hashlib.sha256(content).hexdigest()
    assert calls == [URL]


@pytest.mark.parametrize("suffix, data", [(".pdf", PDF), (".chm", CHM)])
def test_direct_document_auto_format_and_content_disposition(tmp_path, monkeypatch, suffix, data):
    response(monkeypatch, data, filename="another-device" + suffix)
    output = downloads.fetch_document(URL, destination=tmp_path)
    assert output == tmp_path / ("another-device" + suffix)
    assert output.read_bytes() == data


def test_auto_filename_never_uses_remote_paths(tmp_path, monkeypatch):
    response(monkeypatch, PDF, filename="../../unsafe.pdf")
    output = downloads.fetch_document(URL, destination=tmp_path)
    assert output == tmp_path / "unsafe.pdf"


def test_huawei_page_resolves_its_own_document_id(tmp_path, monkeypatch):
    calls = response(monkeypatch, PDF)
    url = "https://support.huawei.com/enterprise/en/doc/EDOC1234567890"
    output = downloads.fetch_document(url, destination=tmp_path)
    assert output.name == "EDOC1234567890.pdf"
    assert "nid=EDOC1234567890&partNo=6001" in calls[0]
    assert json.loads(output.with_suffix(".source.json").read_text())["source_url"] == url


def test_zip_selection_and_optional_checksums(tmp_path, monkeypatch):
    data = package({"chapter.pdf": PDF, "Device Command Reference.pdf": PDF})
    response(monkeypatch, data)
    output = downloads.fetch_document(URL, tmp_path / "manual.pdf",
                                      sha256=hashlib.sha256(data).hexdigest(),
                                      document_sha256=hashlib.sha256(PDF).hexdigest())
    assert output.read_bytes() == PDF
    assert json.loads(output.with_suffix(".source.json").read_text())["archive_member"] == "Device Command Reference.pdf"


def test_ambiguous_archive_requires_member_and_extracts_only_selected_bytes(tmp_path, monkeypatch):
    data = package({"../outside.pdf": PDF, "chapter.pdf": PDF})
    response(monkeypatch, data)
    with pytest.raises(ValueError, match="--member"):
        downloads.fetch_document(URL, tmp_path / "manual.pdf")
    assert list(tmp_path.iterdir()) == []
    output = downloads.fetch_document(URL, tmp_path / "manual.pdf", member="../outside.pdf")
    assert output.read_bytes() == PDF
    assert not (tmp_path.parent / "outside.pdf").exists()


@pytest.mark.parametrize("data, options, error", [
    (b"<html>Login required</html>", {}, "HTML/login"),
    (PDF, {"sha256": "0" * 64}, "Download SHA-256 mismatch"),
    (PDF, {"document_sha256": "0" * 64}, "Document SHA-256 mismatch"),
    (PDF, {"max_bytes": 5}, "exceeds"),
    (PDF, {"member": "manual.pdf"}, "only valid for ZIP"),
    (b"%PDF-1.7 corrupt", {}, "corrupt"),
])
def test_bad_response_does_not_publish_document_or_metadata(tmp_path, monkeypatch, data, options, error):
    response(monkeypatch, data)
    with pytest.raises(ValueError, match=error):
        downloads.fetch_document(URL, tmp_path / "manual.pdf", **options)
    assert list(tmp_path.iterdir()) == []


def test_existing_output_is_preserved_without_downloading(tmp_path, monkeypatch):
    output = tmp_path / "manual.pdf"
    output.write_bytes(PDF)
    calls = response(monkeypatch, b"new")
    with pytest.raises(ValueError, match="already exists"):
        downloads.fetch_document(URL, output)
    assert output.read_bytes() == PDF
    assert calls == []
