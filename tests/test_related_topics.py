"""Retain real source metadata and distinguish references from guessed relationships."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from cli_reference_corpus.markdown import render_command
from cli_reference_corpus.model import Command, Parameter, RelatedTopic
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
    assert [(t.title, t.target_sections) for t in command.related_topics if t.source_section == "Usage Guidelines"] == [
        ("esi dynamic-name", ["1.9664"]), ("evpn redundancy-mode", ["1.9687"]),
    ]
    assert {t.source_section for t in command.related_topics} == {"Usage Guidelines", "Examples"}
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
        "source_section": "Related Topics", "target_sections": [], "target_files": [],
        "reference_kind": "documented_reference",
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
                      related_topics=[RelatedTopic("peer", "Sets a peer.", "Related Topics", ["2"], ["2_peer.json"])])
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


@pytest.mark.parametrize("value", ["peer", ["peer"], [{"title": "peer", "target_sections": "2"}],
                                   [{"title": "peer", "target_files": "2_peer.json"}]])
def test_malformed_related_topics_are_rejected(value):
    record = Command("sample", "1", 1, 1).to_dict()
    record["related_topics"] = value
    with pytest.raises(ValueError):
        Command.from_dict(record)


@pytest.mark.parametrize("text, expected", [
    ("Run display ip routing-table to check routes.", ["display ip routing-table"]),
    ("The display ip routing-table and reset bgp commands help troubleshoot.",
     ["display ip routing-table", "reset bgp"]),
    ("Use display ip routing-table, reset bgp, and peer.",
     ["display ip routing-table", "reset bgp", "peer"]),
    ("See also display ip routing-table.", ["display ip routing-table"]),
    ("Enter `display ip routing-table` before proceeding.", ["display ip routing-table"]),
    ("Execute the display ip routing-\ntable <address>.", ["display ip routing-table"]),
    ("The PEER command selects a neighbor.", ["peer"]),
    ("A peer exists. A display is attached. Run peer-group. Run unknown-command.", []),
    ("Run the unknown peer command.", []),
])
def test_command_mentions_use_known_complete_names_and_command_context(text, expected):
    index = RelatedTopicIndex.from_outline([
        Heading("1", "sample", 1), Heading("2", "display", 2),
        Heading("3", "display ip routing-table", 3), Heading("4", "reset bgp", 4),
        Heading("5", "peer", 5),
    ])
    command = Command("sample", "1", 1, 1, usage_guidelines=text)
    index.enrich(command)
    assert [t.title.casefold() for t in command.related_topics] == expected
    before = command.to_dict()
    index.enrich(command)
    assert command.to_dict() == before


def test_mentions_in_additional_page_text_and_direct_external_references_survive():
    index = RelatedTopicIndex.from_commands([Command("peer", "2", 2, 2)])
    command = Command("sample", "1", 1, 1, extra="Examples (source text):\nSee peer.",
                      related_topics=[RelatedTopic("external", "", "See Also", ["9.2"])])
    index.enrich(command)
    assert [(t.title, t.source_section, t.target_sections) for t in command.related_topics] == [
        ("external", "See Also", ["9.2"]), ("peer", "ExtraInfo", ["2"]),
    ]


def test_legacy_related_topic_without_target_files_is_readable():
    record = Command("sample", "1", 1, 1).to_dict()
    record["related_topics"] = [{"title": "peer", "target_sections": ["2"]}]
    assert Command.from_dict(record).related_topics[0].target_files == []


def test_unknown_long_command_and_ordinary_prose_never_fall_back_to_short_prefix():
    commands = [Command(name, str(i), i, i) for i, name in enumerate(
        ["sample", "port", "more", "port trunk allow-pass vlan"], 1)]
    source = commands[0]
    source.usage_guidelines = (
        "Run the port trunk allow-pass command. Run more than one command. "
        "Run the port unknown-feature command."
    )
    source.related_topics = [RelatedTopic("port", "run the port", "Usage Guidelines", ["2"])]
    index = RelatedTopicIndex.from_commands(commands)
    index.enrich(source)
    assert [(t.title, t.target_sections) for t in source.related_topics] == [("port trunk allow-pass vlan", ["4"])]
    index.enrich(commands[-1])
    assert not commands[-1].related_topics


def test_ambiguous_command_abbreviation_is_not_consumed_as_short_command_arguments():
    commands = [
        Command("sample", "1", 1, 1, usage_guidelines="Run the port trunk allow-pass command."),
        Command("port", "2", 2, 2, clis=["port <kind> <number>"]),
        Command("port trunk allow-pass vlan (view A)", "3", 3, 3),
        Command("port trunk allow-pass vlan (view B)", "4", 4, 4),
    ]
    RelatedTopicIndex.from_commands(commands).enrich(commands[0])
    assert commands[0].related_topics == []


@pytest.mark.parametrize("entity", ["lumennet", "stellar segment"])
def test_parameter_topics_are_learned_from_this_manual_not_entity_or_parameter_names(entity):
    source = Command("attach", "1.1", 1, 1, clis=["attach <opaque>"],
                     function="Attaches a resource.",
                     parameters=[Parameter("opaque", f"Specifies the {entity} identifier.")])
    definition = Command(entity, "1.2", 2, 2, clis=[entity + " <identifier>"],
                         function=f"Creates a {entity} identified by its identifier.",
                         parameters=[Parameter("identifier", f"Specifies the {entity} identifier.")])
    distractor = Command("start", "2.1", 3, 3, clis=["start"], function="Starts a diagnostic test.")
    index = RelatedTopicIndex.from_commands([source, definition, distractor])
    index.enrich(source)
    topic, = source.related_topics
    assert topic.reference_kind == "parameter_topic"
    assert topic.target_sections == ["1.2"]
    assert "opaque" in topic.description


def test_example_homonyms_prefer_documented_view_and_general_title():
    source = Command("sample", "1", 1, 1, views=["ordinary view"], examples=[["[DEVICE] quit"]])
    general = Command("quit", "2", 2, 2, clis=["quit"], views=["All views"])
    specialized = Command("quit (special view)", "3", 3, 3, clis=["quit"], views=["special view"])
    index = RelatedTopicIndex.from_commands([source, general, specialized])
    index.enrich(source)
    assert source.related_topics[0].target_sections == ["2"]
    source.views = ["special view"]
    index.enrich(source)
    assert source.related_topics[0].target_sections == ["3"]


@pytest.mark.parametrize("family", [
    "huawei-cloudengine-9800-8800-6800-v300r024c00",
    "huawei-campus-s1720-s2700-s5700-s6720-v200r011c10",
    "huawei-ne40e-v800r024c00spc500",
])
def test_real_huawei_parameter_topics_include_vlan_and_exclude_unrelated_short_commands(family):
    fixture = json.loads((ROOT / "tests/fixtures/related-topics-records.json").read_text())[family]
    commands = [Command.from_dict(entry["record"], title=entry["title"], section=entry["section"],
                                  start_page=entry["first_page"], end_page=entry["last_page"])
                for entry in fixture["commands"]]
    source = next(c for c in commands if c.title == "port trunk allow-pass vlan")
    index = RelatedTopicIndex.from_commands(commands)
    index.enrich(source)
    topic_targets = {target for t in source.related_topics if t.reference_kind == "parameter_topic"
                     for target in t.target_sections}
    vlan = next(c for c in commands if c.title in {"vlan", "vlan (system view)"})
    assert vlan.section in topic_targets
    unrelated = {c.section for c in commands if c.title.casefold().split(" (")[0] in {"port", "start", "more", "mode"}}
    assert not unrelated & {section for t in source.related_topics for section in t.target_sections}
    assert source.section not in {section for t in source.related_topics for section in t.target_sections}


def test_parameter_topics_respect_documented_configuration_scope():
    source = Command("attach", "1", 1, 1, views=["attachment view"],
                     parameters=[Parameter("opaque", "Specifies the lumennet identifier."),
                                 Parameter("peer-address", "Specifies the peer address.")])
    definition = Command("lumennet", "2", 2, 2, views=["root configuration"],
                         clis=["lumennet <id>", "remove lumennet <id>"],
                         function="Creates a lumennet identified by its identifier.")
    other = Command("resource", "3", 3, 3, views=["root configuration"],
                    clis=["resource <id>", "remove resource <id>"])
    another = Command("profile", "5", 5, 5, views=["root configuration"],
                      clis=["profile <id>", "remove profile <id>"])
    unrelated = Command("peer-address", "4", 4, 4, views=["telemetry destination"],
                        clis=["peer-address <address>", "remove peer-address <address>"],
                        function="Specifies the peer address.")
    index = RelatedTopicIndex.from_commands([source, definition, other, another, unrelated])
    index.enrich(source)
    assert {s for t in source.related_topics for s in t.target_sections} == {"2"}
    source.views = ["telemetry destination"]
    index.enrich(source)
    assert {s for t in source.related_topics for s in t.target_sections} == {"2", "4"}
