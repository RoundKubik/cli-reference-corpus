"""References must identify loadable JSON files and survive repeated enrichment."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli_reference_corpus.cli import main
from cli_reference_corpus.corpus import CorpusWriter
from cli_reference_corpus.enrichment import enrich_corpus
from cli_reference_corpus.model import Command, RelatedTopic
from cli_reference_corpus.parser import ParseResult
from cli_reference_corpus.storage import write_json

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "tests/fixtures/bandwidth.pdf"


@pytest.mark.parametrize("schema", ["repository", "paper"])
def test_existing_json_corpus_enrichment_preserves_content_and_resolves_files(tmp_path, schema):
    commands = [
        Command("sample", "1", 1, 1, usage_guidelines="Use peer.",
                related_topics=[RelatedTopic("outside", "External reference", "See Also", ["9"])]),
        Command("peer (view A)", "2", 2, 2),
        Command("peer (view B)", "3", 3, 3),
    ]
    for command in commands:
        command.clis = [command.title]
        command.function = "Description."
        command.views = ["System view"]
    original = tmp_path / "original"
    CorpusWriter(ParseResult(commands=commands), SOURCE, schema).write(original)
    before = {path.relative_to(original): path.read_bytes() for path in original.rglob("*") if path.is_file()}
    # The PDF is deliberately not located beside the corpus: enrichment needs only JSON.
    output = tmp_path / "enriched"
    assert main(["enrich-related", str(original / "manifest.json"), "-o", str(output)]) == 0
    manifest = json.loads((output / "manifest.json").read_text())
    validator = Draft202012Validator(json.loads((ROOT / "schemas" / f"{schema}.schema.json").read_text()))
    for entry in manifest["commands"]:
        data = json.loads((output / entry["file"]).read_text())
        previous = json.loads((original / entry["file"]).read_text())
        assert {k: v for k, v in data.items() if k != "related_topics"} == {
            k: v for k, v in previous.items() if k != "related_topics"
        }
        assert not list(validator.iter_errors(data))
    data = json.loads((output / manifest["commands"][0]["file"]).read_text())
    outside, peer = data["related_topics"]
    assert outside["target_sections"] == ["9"]
    assert outside["target_files"] == []
    assert peer["target_sections"] == ["2", "3"]
    assert peer["target_files"] == ["2_peer_view_A.json", "3_peer_view_B.json"]
    for filename in peer["target_files"]:
        assert (output / "cmd_corpus" / filename).is_file()
    markdown = (output / manifest["commands"][0]["markdown_file"]).read_text()
    assert "JSON files: 2\\_peer\\_view\\_A.json" in markdown
    report = json.loads((output / "validation.json").read_text())
    assert report["related_topics"] == 2
    second = tmp_path / "second"
    enrich_corpus(output, second)
    assert {path.relative_to(output): path.read_bytes() for path in output.rglob("*") if path.is_file()} == {
        path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()
    }
    assert before == {path.relative_to(original): path.read_bytes() for path in original.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="already exists"):
        enrich_corpus(original, output)


def test_pdf_export_populates_only_available_target_filenames(tmp_path):
    commands = [Command("sample", "1", 1, 1, related_topics=[
        RelatedTopic("peer", "", "Usage Guidelines", ["2", "9"]),
    ]), Command("peer", "2", 2, 2)]
    output = tmp_path / "parsed"
    CorpusWriter(ParseResult(commands=commands), SOURCE).write(output)
    data = json.loads((output / "cmd_corpus/1_sample.json").read_text())
    assert data["related_topics"][0]["target_files"] == ["2_peer.json"]
    assert data["related_topics"][0]["target_sections"] == ["2", "9"]


def test_enrichment_requires_manifest_and_publishes_no_partial_corpus(tmp_path):
    source = tmp_path / "command.json"
    write_json(source, Command("sample", "", 0, 0).to_dict())
    output = tmp_path / "out"
    assert main(["enrich-related", str(source), "-o", str(output)]) == 1
    assert not output.exists()
