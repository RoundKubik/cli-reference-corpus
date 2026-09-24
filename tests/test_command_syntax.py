"""Malformed templates are retained and diagnosed, not fatal to the pipeline."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli_reference_corpus.command_syntax import matches_invocation, syntax_issues
from cli_reference_corpus.corpus import CorpusWriter
from cli_reference_corpus.enrichment import enrich_corpus
from cli_reference_corpus.model import Command, Parameter
from cli_reference_corpus.parser import ParseResult

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("invocation, accepted", [
    ("port trunk allow-pass vlan 2 to 10 100 200", True),
    ("port trunk allow-pass vlan all", True),
    ("port trunk allow-pass", False),
    ("port trunk allow-pass vlan", False),
    ("port trunk allow-pass vlan " + " ".join(["2"] * 41), False),
])
def test_template_grammar_matches_complete_invocations(invocation, accepted):
    template = "port trunk allow-pass vlan { { { <vlan-id1> [ to <vlan-id2> ] } &<1-40> } | all }"
    assert bool(matches_invocation(invocation, [template])) == accepted


@pytest.mark.parametrize("schema", ["repository", "paper"])
def test_invalid_cli_does_not_stop_export_or_enrichment(tmp_path, schema):
    broken = "sample [ <value> }"
    commands = [
        Command("sample", "1", 1, 1, clis=[broken, "sample <value>"], function="A sample.",
                views=["System view"], parameters=[Parameter("value", "A value.")]),
        Command("next", "2", 2, 2, clis=["next"], function="Next command.", views=["System view"]),
    ]
    output = tmp_path / "corpus"
    CorpusWriter(ParseResult(commands=commands), ROOT / "tests/fixtures/bandwidth.pdf", schema).write(output)
    record = json.loads((output / "cmd_corpus/1_sample.json").read_text())
    assert record["CLIs"] == [broken, "sample <value>"]
    assert record["syntax_issues"] == [{"cli_index": 0, "cli": broken, "code": "unbalanced_syntax",
                                         "message": "Unbalanced or mismatched []/{} groups in the extracted template."}]
    validator = Draft202012Validator(json.loads((ROOT / "schemas" / f"{schema}.schema.json").read_text()))
    assert not list(validator.iter_errors(record))
    assert (output / "cmd_corpus/2_next.json").exists()
    assert "Syntax issue in template 1" in (output / "cmd_corpus/1_sample.md").read_text()
    assert enrich_corpus(output, tmp_path / "copy")["commands"] == 2
    assert json.loads((tmp_path / "copy/cmd_corpus/1_sample.json").read_text())["syntax_issues"] == record["syntax_issues"]


def test_uninterpretable_repetition_is_a_nonfatal_issue():
    issues = syntax_issues(["peer { <name> } &<3-1>", "peer <name>"])
    assert [issue["cli_index"] for issue in issues] == [0]
    assert issues[0]["code"] == "unsupported_syntax"


def test_zero_minimum_repetition_from_huawei_manual_is_valid():
    template = "undo priority [ <priority> ] &<0-3>"
    assert syntax_issues([template]) == []
    assert matches_invocation("undo priority", [template])
    assert matches_invocation("undo priority 1 2 3", [template])
    assert not matches_invocation("undo priority 1 2 3 4", [template])


def test_documented_large_repetition_is_not_an_artificial_syntax_error():
    templates = ['dcn vlan { <beginVlan> [ to <endVlan> ] } &<1-4094>']
    assert syntax_issues(templates) == []
    assert matches_invocation('dcn vlan 1 to 20 30', templates)
    assert syntax_issues(['sample { <value> } &<1-999999999999999999999>'])
