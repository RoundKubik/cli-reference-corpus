"""A renamed corpus must retain its vendor-specific independent PDF census."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

from cli_reference_corpus.corpus import CorpusWriter
from cli_reference_corpus.vendors import load_parser

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("audit_coverage", ROOT / "scripts/audit_coverage.py")
audit = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = audit
spec.loader.exec_module(audit)


@pytest.mark.parametrize("fixture,profile", [
    ("cisco-catalyst.pdf", "cisco-catalyst"),
    ("bandwidth.pdf", "cloudengine"),
])
def test_census_uses_manifest_profile_after_rename(tmp_path, fixture, profile):
    source = tmp_path / "data/manuals" / fixture
    source.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/fixtures" / fixture, source)
    result = load_parser(profile).parse(source)
    output = tmp_path / "output/model-and-version"
    CorpusWriter(result, source).write(output)

    report = audit.CoverageAudit(tmp_path, output.name).run()

    assert report["printed_command_descriptions"] == len(result.commands) > 0
    assert report["unmatched_descriptions"] == []
    assert report["unmatched_records"] == []


def test_cli_discovers_multiple_corpora_without_hardcoded_names(tmp_path, monkeypatch):
    names = ["cisco-model-a-version-a", "cisco-model-b-version-b"]
    for name in names:
        folder = tmp_path / "output" / name
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text("{}")
    calls = []

    def run(self):
        calls.append(self.device)
        return {"printed_command_descriptions": 1, "unmatched_descriptions": []}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audit.CoverageAudit, "run", run)
    monkeypatch.setattr(sys, "argv", ["audit_coverage.py"])
    audit.main()

    assert calls == names
    for name in names:
        report = json.loads((tmp_path / "reports/coverage" / f"{name}.json").read_text())
        assert report["printed_command_descriptions"] == 1


@pytest.mark.parametrize("fixture,profile,title,field,report_key", [
    ("bandwidth.pdf", "cloudengine", "bandwidth (VLANIF interface view)", "ExtraInfo",
     "empty_extra_info_with_printed_additional_section"),
    ("cisco-catalyst.pdf", "cisco-catalyst", "database-mapping", "related_topics",
     "empty_related_topics_with_printed_related_section"),
])
def test_census_detects_dropped_additional_fields(tmp_path, fixture, profile, title, field, report_key):
    source = tmp_path / "data/manuals" / fixture
    source.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/fixtures" / fixture, source)
    result = load_parser(profile).parse(source)
    output = tmp_path / "output/model-version"
    CorpusWriter(result, source).write(output)
    assert audit.CoverageAudit(tmp_path, output.name).run()[report_key] == []

    manifest = json.loads((output / "manifest.json").read_text())
    entry = next(entry for entry in manifest["commands"] if entry["title"] == title)
    path = output / entry["file"]
    record = json.loads(path.read_text())
    record[field] = [] if field == "related_topics" else ""
    path.write_text(json.dumps(record))

    gaps = audit.CoverageAudit(tmp_path, output.name).run()[report_key]
    assert any(gap["title"] == title for gap in gaps)
