from pathlib import Path
import json

import pymupdf
import pytest

from cli_reference_corpus.cli import main, write_corpus
from cli_reference_corpus.model import Command, Parameter, validate
from cli_reference_corpus.parser import parse_pdf
from cli_reference_corpus.pdf import Line, template

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def bandwidth():
    return parse_pdf(FIXTURES / "bandwidth.pdf", section="2.4.3.1")


def test_real_pdf_cross_page_command(bandwidth):
    assert len(bandwidth.commands) == 1
    c = bandwidth.commands[0]
    assert c.title == "bandwidth (VLANIF interface view)"
    assert c.clis == ["bandwidth <bandwidth>", "undo bandwidth"]
    assert c.function == (
        "The bandwidth command sets the bandwidth of a VLANIF interface.\n"
        "The undo bandwidth command deletes the configured bandwidth of a VLANIF interface.\n"
        "By default, the bandwidth of a VLANIF interface is 1000 Mbits/s."
    )
    assert c.views == ["VLANIF interface view"]
    assert c.parameters == [Parameter("bandwidth", "Specifies the bandwidth of a VLANIF interface.\nThe value ranges from 1 to 1000000, in Mbits/s.")]
    assert c.examples == [["<HUAWEI> system-view", "[~HUAWEI] vlan 2", "[*HUAWEI-vlan2] quit",
                           "[*HUAWEI] interface vlanif 2", "[*HUAWEI-Vlanif2] bandwidth 10000"]]
    assert validate(c) == []
    assert bandwidth.report()["missing_outline_sections"] == []
    assert (c.start_page, c.end_page) == (1, 2)


def test_actual_corpus_and_paper_schemas(bandwidth):
    c = bandwidth.commands[0]
    repo = c.to_dict()
    assert set(repo) == {"PageTitle", "CLIs", "FuncDef", "ParentView", "ParaDef", "Examples", "ExtraInfo", "UsageGuidelines", "related_topics"}
    assert set(repo["ParaDef"][0]) == {"Parameters", "Info"}
    paper = c.to_dict("paper")
    assert set(paper) == {"CLIs", "FuncDef", "ParentViews", "ParaDef", "Examples", "UsageGuidelines", "ExtraInfo", "related_topics"}
    assert set(paper["ParaDef"][0]) == {"Paras", "Info"}
    with pytest.raises(ValueError, match="schema"):
        c.to_dict("unknown")


def test_table_ligatures_and_comma_separated_views():
    result = parse_pdf(FIXTURES / "bandwidth.pdf", section="2.4.3.2")
    assert result.commands[0].parameters[0].info.startswith("Specifies a delay time")
    result = parse_pdf(FIXTURES / "bandwidth.pdf", section="2.4.3.3")
    assert result.commands[0].views == ["VLAN range view", "VLAN view"]


def test_model_applicability_is_not_a_command():
    result = parse_pdf(FIXTURES / "link-type.pdf", section="2.4.3.32")
    c = result.commands[0]
    assert c.clis == ["port link-type access", "port link-type hybrid", "port link-type trunk",
                      "undo port link-type", "port link-type dot1q-tunnel"]
    assert "For CE8855" in c.extra
    assert "Format applicability" in c.extra
    assert "conditional_format: applicability retained in ExtraInfo" in validate(c)


def test_real_wrapped_syntax_and_multipage_parameter_table():
    result = parse_pdf(FIXTURES / "vlan-mapping.pdf", section="2.4.3.36")
    c = result.commands[0]
    assert len(c.clis) == 9
    assert c.clis[1] == "port vlan-mapping vlan <vlan-id1> inner-vlan <vlan-id5> map-vlan <vlan-id3> [ map-inner-vlan <vlan-id4> ] [ remark-8021p <8021p-value> ]"
    assert c.clis[3] == "port vlan-mapping vlan <vlan-id1> inner-vlan <vlan-id5> to <vlan-id6> map-vlan <vlan-id3> [ remark-8021p <8021p-value> ]"
    assert {p.name for p in c.parameters} >= {"to vlan-id2", "to vlan-id6", "map-vlan vlan-id3", "remark-8021p 8021p-value"}
    assert not validate(c)
    assert c.examples
    serialized = json.dumps(c.to_dict())
    assert "Copyright" not in serialized
    assert "Issue 01" not in serialized
    assert "<vlan->" not in serialized


def test_template_font_boundaries_repetition_and_wrapping():
    def line(parts):
        spans = [{"text": t, "flags": 16 if bold else 4} for t, bold in parts]
        return Line("".join(t for t, _ in parts), spans, (0, 0, 0, 0), 1, 0)
    lines = [line([("vlan ", True), ("{ vlan-", False)]),
             line([("id1 [ ", False), ("to ", True), ("vlan-id2 ] } &<1-10>", False)])]
    assert template(lines) == "vlan { <vlan-id1> [ to <vlan-id2> ] } &<1-10>"


def test_validation_detects_bad_syntax_missing_fields_and_parameter():
    c = Command("demo", "1.1.1", 1, 1, clis=["demo [ <value> }", "demo { all"])
    warnings = validate(c)
    assert "missing_function" in warnings
    assert "missing_views" in warnings
    assert "undocumented_parameter: value" in warnings
    assert sum(w.startswith("unbalanced_syntax") for w in warnings) == 2


def test_no_text_pdf_and_wrong_page_range(tmp_path):
    source = tmp_path / "scan.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(source)
    with pytest.raises(ValueError, match="text layer"):
        parse_pdf(source)
    with pytest.raises(ValueError, match="Page range"):
        parse_pdf(source, first_page=0)
    with pytest.raises(ValueError, match="margins"):
        parse_pdf(source, header_margin=900)


def test_absent_section_fails():
    with pytest.raises(ValueError, match="No command"):
        parse_pdf(FIXTURES / "bandwidth.pdf", section="9.99")


def test_page_range_truncation_is_reported():
    r = parse_pdf(FIXTURES / "bandwidth.pdf", section="2.4.3.1", last_page=1)
    warnings = validate(r.commands[0])
    assert "missing_format" in warnings
    assert "range_ends_inside_section: command may be incomplete" in warnings


def test_export_and_refusal_to_overwrite(tmp_path, bandwidth):
    output = tmp_path / "corpus"
    write_corpus(bandwidth, FIXTURES / "bandwidth.pdf", output, "repository")
    files = list((output / "cmd_corpus").glob("*.json"))
    assert len(files) == 1
    assert json.loads(files[0].read_text())["CLIs"] == ["bandwidth <bandwidth>", "undo bandwidth"]
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(manifest["source_sha256"]) == 64
    assert manifest["commands"][0]["first_page"] == 1
    markdown = output / manifest["commands"][0]["markdown_file"]
    assert markdown == files[0].with_suffix(".md")
    assert "bandwidth <bandwidth>" in markdown.read_text()
    assert "Usage Scenario" in markdown.read_text()
    assert "PDF pages: 1–2" in markdown.read_text()
    assert json.loads((output / "validation.json").read_text())["issues"] == []
    with pytest.raises(ValueError, match="already exists"):
        write_corpus(bandwidth, FIXTURES / "bandwidth.pdf", output, "repository")
    assert files[0].exists()


def test_cli_strict_exports_diagnostics(tmp_path):
    output = tmp_path / "strict"
    code = main([str(FIXTURES / "link-type.pdf"), "--section", "2.4.3.32", "-o", str(output), "--strict", "--quiet"])
    assert code == 2
    assert (output / "validation.json").is_file()
    markdown = next((output / "cmd_corpus").glob("*.md")).read_text()
    assert "conditional\\_format" in markdown


def test_cli_success_and_failure(tmp_path):
    assert main([str(FIXTURES / "bandwidth.pdf"), "--section", "2.4.3.1", "-o", str(tmp_path / "ok"), "--strict", "--quiet"]) == 0
    assert main([str(tmp_path / "missing.pdf"), "-o", str(tmp_path / "fail"), "--quiet"]) == 1
    assert not (tmp_path / "fail").exists()


def test_parallel_reader_matches_sequential(bandwidth):
    result = parse_pdf(FIXTURES / "bandwidth.pdf", section="2.4.3.1", workers=2)
    assert [c.to_dict() for c in result.commands] == [c.to_dict() for c in bandwidth.commands]
    assert result.report() == bandwidth.report()


def test_nonpositive_workers():
    with pytest.raises(ValueError, match="workers"):
        parse_pdf(FIXTURES / "bandwidth.pdf", workers=0)


def test_conditional_first_template_remains_one_wrapped_command():
    r = parse_pdf(FIXTURES / 'mac-address.pdf', section='2.4.1.3')
    c = r.commands[0]
    assert c.clis[0] == (
        'display mac-address dynamic [ slot <slot-id> ] { interface { <interface-type> '
        '<interface-number> | <interface-name> } vlan <vlan-id> | vlan <vlan-id> '
        '[ interface { <interface-type> <interface-number> | <interface-name> } ] } [ verbose ]'
    )
    assert len(c.clis) == 15
    assert validate(c) == ['conditional_format: applicability retained in ExtraInfo']


def test_table_clipping_does_not_leak_neighboring_ligatures():
    c = parse_pdf(FIXTURES / 'tftp.pdf', section='2.1.2.97').commands[0]
    names = {p.name for p in c.parameters}
    assert {'get', 'put'} <= names
    assert not {'geti', 'puti'} & names
    assert next(p for p in c.parameters if p.name == 'get').info.startswith('Specifies the downloading')
