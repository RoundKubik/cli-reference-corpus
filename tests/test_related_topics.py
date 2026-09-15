"""Retain real source metadata and distinguish references from guessed relationships."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli_reference_corpus.markdown import render_command
from cli_reference_corpus.model import Command, RelatedTopic
from cli_reference_corpus.parser import Heading
from cli_reference_corpus.pdf import Table
from cli_reference_corpus.related_sections import RelatedSection
from cli_reference_corpus.related_topics import RelatedTopicIndex
from cli_reference_corpus.vendors import load_parser

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("workers", [1, 2])
def test_ne40e_esi_preserves_access_metadata_caption_and_named_references(workers):
    result = load_parser("ne40e-rendered").parse(ROOT / "tests/fixtures/ne40e-esi.pdf", workers=workers)
    command = result.commands[0]
    assert "Default Level:\n2: Configuration level" in command.extra
    assert "Task Name | Operations\nbgp | write" in command.extra
    assert "# Bind a dynamic ESI instance to an Eth-Trunk interface." in command.extra
    assert command.examples[0][-1] == "[*HUAWEI-Eth-Trunk10] esi dynamic esi1"
    assert [(t.title, t.target_sections) for t in command.related_topics] == [
        ("esi dynamic-name", ["1.9664"]), ("evpn redundancy-mode", ["1.9687"]),
    ]
    assert all(t.source_section == "Usage Guidelines" for t in command.related_topics)
    assert "### Related Topics" in render_command(command)
    assert "Reference sections: 1.9664" in render_command(command)


def test_cisco_unruled_related_table_preserves_wrapped_description():
    result = load_parser("cisco-catalyst").parse(ROOT / "tests/fixtures/cisco-catalyst.pdf")
    command = next(c for c in result.commands if c.title == "database-mapping")
    topic, = [t for t in command.related_topics if t.source_section == "Related Commands"]
    assert topic.title == "eid-table vrf vrf-name"
    assert topic.description == (
        "Associates the instance-service instantiation with a virtual routing and forwarding "
        "(VRF) table or default table through which the endpoint identifier address space is reachable."
    )
    assert "Related Commands:" in command.extra


def test_cisco_related_table_without_header_preserves_wrapped_command():
    result = load_parser("cisco-catalyst").parse(ROOT / "tests/fixtures/cisco-related-no-header.pdf")
    topics = [t for t in result.commands[0].related_topics if t.source_section == "Related Commands"]
    assert [(t.title, t.description) for t in topics] == [
        ("aaa new-model", "Enables the AAA access control model."),
        ("ldap server", "Defines an LDAP server."),
    ]


def test_cisco_related_columns_follow_narrow_gaps_and_mirrored_page_margins():
    result = load_parser("cisco-catalyst").parse(ROOT / "tests/fixtures/cisco-related-no-header.pdf")
    topics = [t for c in result.commands for t in c.related_topics if t.source_section == "Related Commands"]
    assert all(t.description for t in topics)
    assert not any(word in t.title for t in topics for word in ("Displays", "Configures", "Sets"))
    assert any(t.title == "show access-session" and t.description.startswith("Displays") for t in topics)
    assert any(t.title == "tunnel type capwap" and t.description.startswith("Configures") for t in topics)


def test_related_topics_table_retains_unknown_target_and_description_continuation():
    events = [Table([["Topic", "Description"], ["external topic", "First line"], [None, "Continuation"]],
                    (0, 0, 100, 60), 1)]
    topic, = RelatedSection("Related Topics").read(events)
    assert topic.to_dict() == {
        "title": "external topic", "description": "First line\nContinuation",
        "source_section": "Related Topics", "target_sections": [],
    }


def test_campus_numbered_related_topics_are_separate_direct_references():
    result = load_parser("campus-switch").parse(ROOT / "tests/fixtures/campus-related.pdf")
    command = next(c for c in result.commands if c.section == "7.4.2")
    topics = [t for t in command.related_topics if t.source_section == "Related Topics"]
    assert [(t.title, t.target_sections) for t in topics] == [
        ("area (OSPF)", ["7.4.4"]), ("ospf", ["7.4.67"]),
    ]
    assert "Related Topics:" in command.extra
    # The source reference remains useful when the target is outside the excerpt.
    assert "7.4.67" not in {c.section for c in result.commands}


def test_related_topics_stop_before_the_next_campus_chapter():
    result = load_parser("campus-switch").parse(ROOT / "tests/fixtures/campus-related-boundary.pdf")
    command = next(c for c in result.commands if c.section == "5.17.19")
    topics = [t for t in command.related_topics if t.source_section == "Related Topics"]
    assert [(t.title, t.target_sections) for t in topics] == [
        ("l2protocol-tunnel", ["5.17.11"]), ("l2protocol-tunnel vlan", ["5.17.15"]),
    ]
    assert "About This Chapter" not in command.extra
    assert "IP Service Commands" not in command.extra


def test_reference_resolution_keeps_homonyms_and_excludes_casual_mentions():
    index = RelatedTopicIndex.from_outline([
        Heading("1", "sample", 1), Heading("2", "peer (view A)", 2), Heading("3", "peer (view B)", 3),
    ])
    command = Command("sample", "1", 1, 1, usage_guidelines=(
        "The sample command is local. The peer command sets a peer. A peer exists. "
        "Use the following command. The sample command does not imply a dependency."
    ))
    index.enrich(command)
    assert [(t.title, t.target_sections) for t in command.related_topics] == [("peer", ["2", "3"])]


@pytest.mark.parametrize("schema", ["repository", "paper"])
def test_additional_information_and_topics_round_trip_both_schemas(schema):
    command = Command("sample", "1", 1, 1, clis=["sample"], views=["System view"],
                      extra="Default Level:\n2: Configuration level",
                      related_topics=[RelatedTopic("peer", "Sets a peer.", "Related Topics", ["2"])])
    record = command.to_dict(schema)
    validator = Draft202012Validator(json.loads((ROOT / "schemas" / f"{schema}.schema.json").read_text()))
    assert list(validator.iter_errors(record)) == []
    assert Command.from_dict(record).to_dict(schema) == record
    assert "Default Level:" in render_command(Command.from_dict(record))
    assert "Sets a peer." in render_command(Command.from_dict(record))


def test_old_record_without_related_topics_still_renders():
    record = Command("sample", "1", 1, 1).to_dict()
    del record["related_topics"]
    assert Command.from_dict(record).related_topics == []
    assert "### Related Topics" not in render_command(Command.from_dict(record))


@pytest.mark.parametrize("value", ["peer", ["peer"], [{"title": "peer", "target_sections": "2"}]])
def test_malformed_related_topics_are_rejected(value):
    record = Command("sample", "1", 1, 1).to_dict()
    record["related_topics"] = value
    with pytest.raises(ValueError):
        Command.from_dict(record)
