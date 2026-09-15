"""Publication must preserve paired views and never leave a partial corpus."""
import json
from pathlib import Path

import pytest

from cli_reference_corpus.corpus import CorpusWriter
from cli_reference_corpus.model import Command
from cli_reference_corpus.parser import ParseResult

SOURCE = Path(__file__).parent / "fixtures" / "bandwidth.pdf"


def command(title="sample", section="1"):
    return Command(
        title, section, 1, 2,
        clis=["sample <value>"],
        function="Sets a sample value.",
        views=["System view"],
        usage_guidelines="Configure before enabling.",
        extra="Additional repository notes.",
    )


@pytest.mark.parametrize("schema", ["repository", "paper"])
def test_paired_views_follow_selected_schema(tmp_path, schema):
    result = ParseResult(commands=[command()])
    output = tmp_path / "corpus"
    CorpusWriter(result, SOURCE, schema).write(output)
    manifest = json.loads((output / "manifest.json").read_text())
    entry = manifest["commands"][0]
    record = json.loads((output / entry["file"]).read_text())
    markdown = (output / entry["markdown_file"]).read_text()
    assert record == result.commands[0].to_dict(schema)
    assert "sample <value>" in markdown
    assert "Configure before enabling." in markdown
    assert "PDF pages: 1–2" in markdown
    assert "Additional repository notes." in markdown
    assert "undocumented\\_parameter: value" in markdown


def test_duplicate_command_does_not_publish_partial_corpus(tmp_path):
    result = ParseResult(commands=[command(), command()])
    with pytest.raises(ValueError, match="Duplicate command section"):
        CorpusWriter(result, SOURCE).write(tmp_path / "corpus")
    assert list(tmp_path.iterdir()) == []


def test_render_failure_cleans_staged_pairs(tmp_path, monkeypatch):
    import cli_reference_corpus.corpus as corpus

    original_render = corpus.render_command

    def fail_on_second(item):
        if item.section == "2":
            raise OSError("Simulated write failure")
        return original_render(item)

    monkeypatch.setattr(corpus, "render_command", fail_on_second)
    result = ParseResult(commands=[command(), command("second", "2")])
    with pytest.raises(OSError, match="Simulated write failure"):
        CorpusWriter(result, SOURCE).write(tmp_path / "corpus")
    assert list(tmp_path.iterdir()) == []
