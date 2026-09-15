import json
from pathlib import Path

import pymupdf
import pytest
from jsonschema import validate as validate_json

from cli_reference_corpus.cli import main, write_corpus
from cli_reference_corpus.markdown import export_markdown, render_command
from cli_reference_corpus.model import Command, Parameter
from cli_reference_corpus.parser import BasePDFParser
from cli_reference_corpus.vendors import load_parser
from cli_reference_corpus.vendors.cisco import CiscoIOSParser, CiscoCatalystParser
from cli_reference_corpus.vendors.huawei import CloudEngineParser, NE40EParser

FIXTURE = Path(__file__).parent / 'fixtures' / 'bandwidth.pdf'


class CustomCiscoParser(CiscoIOSParser):
    # A downstream profile requires no edit of the parser, CLI or exporter.
    section_aliases = {**CiscoIOSParser.section_aliases, 'Application Notes': 'Usage Guidelines'}

    def read_page(self, page, header, footer):
        # This override must be honored by both the sequential and process readers.
        return [e for e in super().read_page(page, header, footer)
                if getattr(e, 'text', '') != 'IGNORE THIS LINE']


def make_cisco(path):
    with pymupdf.open() as doc:
        for name in ['description', 'shutdown']:
            page = doc.new_page()
            def put(y, text, font='hebo', size=12, x=45):
                page.insert_text((x, y), text, fontname=font, fontsize=size)
            put(80, name, size=16)
            put(110, 'Configures the interface.', font='helv', size=10)
            put(140, name + ' ', size=10)
            if name == 'description':
                put(140, 'text', font='heit', size=10, x=101)
            put(170, 'Syntax Description')
            if name == 'description':
                for y in (185, 210, 240):
                    page.draw_line((45,y),(530,y))
                for x in (45,150,530):
                    page.draw_line((x,185),(x,240))
                put(201, 'Parameter', size=10, x=50)
                put(201, 'Description', size=10, x=155)
                put(226, 'text', font='helv', size=10, x=50)
                put(226, 'Interface description.', font='helv', size=10, x=155)
            else:
                put(200, 'None', font='helv', size=10)
            put(270, 'Command Modes')
            put(295, 'Interface configuration', font='helv', size=10)
            put(325, 'Application Notes')
            put(350, 'Use on an interface.', font='helv', size=10)
            put(375, 'IGNORE THIS LINE', font='helv', size=10)
            put(405, 'Examples')
            put(435, 'Router(config)# interface GigabitEthernet0/1', font='cour', size=9)
            put(450, f'Router(config-if)# {name}' + (' uplink' if name == 'description' else ''), font='cour', size=9)
        doc.set_toc([[1, 'description', 1], [1, 'shutdown', 2]])
        doc.save(path)


@pytest.mark.parametrize('workers', [1, 2])
def test_subclass_end_to_end_and_worker_hooks(tmp_path, workers):
    pdf = tmp_path / 'cisco.pdf'
    make_cisco(pdf)
    result = CustomCiscoParser().parse(pdf, workers=workers)
    assert len(result.commands) == 2
    assert result.report()['missing_outline_sections'] == []
    c = result.commands[0]
    assert c.clis == ['description <text>']
    assert c.function == 'Configures the interface.'
    assert c.views == ['Interface configuration']
    assert c.parameters == [Parameter('text', 'Interface description.')]
    assert c.usage_guidelines == 'Use on an interface.'
    assert c.examples == [['Router(config)# interface GigabitEthernet0/1', 'Router(config-if)# description uplink']]
    assert result.report()['issues'] == []
    output = tmp_path / 'corpus'
    write_corpus(result, pdf, output, 'repository')
    md = tmp_path / 'cisco.md'
    assert export_markdown(output, md) == 2
    assert 'description <text>' in md.read_text()
    assert 'Use on an interface.' in md.read_text()


def test_plugin_loading():
    assert isinstance(load_parser('ne40e'), NE40EParser)
    assert isinstance(load_parser('cloudengine'), CloudEngineParser)
    assert isinstance(load_parser('cisco-catalyst'), CiscoCatalystParser)
    assert isinstance(load_parser('test_extensions:CustomCiscoParser'), CustomCiscoParser)
    for name in ['missing', 'pathlib:Path', 'missing_module:Foo', 'cli_reference_corpus.parser:BasePDFParser']:
        with pytest.raises(ValueError):
            load_parser(name)


@pytest.mark.parametrize('workers', [1, 2])
def test_real_catalyst_layout(tmp_path, workers):
    pdf = FIXTURE.parent / 'cisco-catalyst.pdf'
    result = CiscoCatalystParser().parse(pdf, workers=workers)
    commands = {c.title: c for c in result.commands}
    assert len(commands) == 6
    assert not result.report()['missing_outline_sections']
    c = commands['broadcast-underlay']
    assert c.clis == ['broadcast-underlay <multicast-ip>', 'no broadcast-underlay <multicast-ip>']
    assert c.function.endswith('use the no form of this command.')
    assert len(c.views) == 2
    assert c.parameters[0].name == 'multicast-ip'
    assert c.parameters[0].info.startswith('IP address of the multicast group')
    assert c.usage_guidelines.startswith('Use this command to enable')
    c = commands['database-mapping']
    assert len(c.parameters) == 6
    assert len(c.clis) == 2 and c.clis[0].startswith('database-mapping <eid-prefix>')
    assert commands['first-packet-petr'].clis[0].startswith('first-packet-petr remote-locator-set')
    assert commands['show lisp instance-id ipv4 database'].views == ['Privileged EXEC (#)']
    assert commands['show platform hardware fed switch active fwd-asic resource tcam utilization'].clis
    assert len(commands['Keepalive (template)'].clis) == 2
    out = tmp_path / 'cisco'
    write_corpus(result, pdf, out, 'repository')
    assert len(list((out / 'cmd_corpus').glob('*.json'))) == 6
    assert len(list((out / 'cmd_corpus').glob('*.md'))) == 6
    assert not list(out.glob('*.md'))


@pytest.mark.parametrize('schema', ['repository', 'paper'])
def test_usage_and_json_schema_round_trip(tmp_path, schema):
    c = CloudEngineParser().parse(FIXTURE, section='2.4.3.1').commands[0]
    assert 'Usage Scenario' in c.usage_guidelines
    assert 'Default Level:\n2: Configuration level' in c.extra
    data = c.to_dict(schema)
    definition = json.loads((Path(__file__).parents[1] / 'schemas' / f'{schema}.schema.json').read_text())
    validate_json(data, definition)
    assert Command.from_dict(data, title=c.title).to_dict(schema) == data
    source = tmp_path / 'command.json'
    source.write_text(json.dumps(data))
    out = tmp_path / 'command.md'
    assert main(['markdown', str(source), '-o', str(out)]) == 0
    assert 'Usage Scenario' in out.read_text()
    del data['UsageGuidelines']
    assert Command.from_dict(data).usage_guidelines == ''


def test_markdown_literals_and_fences():
    c = Command('x [view]', '1', 2, 3, clis=['x <value> | ```'],
                function='<script>alert(1)</script> *literal*',
                parameters=[Parameter('a|b', 'line1\nline2 <value>')],
                usage_guidelines='Use <value>.', examples=[['```', 'Router# x']], extra='More info.')
    text = render_command(c)
    assert '````text\nx <value> | ```\n````' in text
    assert '&lt;script&gt;' in text and '<script>' not in text
    assert '| a\\|b | line1<br>line2 &lt;value&gt; |' in text
    assert '\\*literal\\*' in text


def test_markdown_manifest_order_diagnostics_and_legacy(tmp_path):
    corpus = tmp_path / 'data'
    corpus.mkdir()
    record = Command('same', '', 0, 0, clis=['x'], function='F', views=['V'], extra='Legacy information').to_dict()
    del record['UsageGuidelines']
    for name in ['z.json', 'a.json']:
        (corpus / name).write_text(json.dumps(record))
    manifest = {'document_title': 'Title', 'commands': [
        {'file':'z.json','section':'1','first_page':3,'last_page':4},
        {'file':'a.json','section':'2','first_page':8,'last_page':9}]}
    (corpus / 'manifest.json').write_text(json.dumps(manifest))
    (corpus / 'validation.json').write_text(json.dumps({'issues':[{'section':'1','warnings':['Check extraction']}]}))
    out = tmp_path / 'out.md'
    assert export_markdown(corpus, out) == 2
    text = out.read_text()
    assert text.index('3–4') < text.index('8–9')
    assert 'command-1' in text and 'command-2' in text
    assert 'Check extraction' in text and 'Legacy information' in text
    with pytest.raises(ValueError, match='exists'):
        export_markdown(corpus, out)
    manifest['commands'][0]['file'] = '../outside.json'
    (corpus / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='inside'):
        export_markdown(corpus, tmp_path / 'bad.md')


@pytest.mark.parametrize('bad', [{'CLIs':'bad'}, {'CLIs':[],'ParentView':[],'FuncDef':4}, 'text', None])
def test_malformed_json_does_not_publish(tmp_path, bad):
    source = tmp_path / 'input.json'
    source.write_text(json.dumps(bad))
    out = tmp_path / 'bad.md'
    assert main(['markdown', str(source), '-o', str(out)]) == 1
    assert not out.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['input.json']


def test_natural_directory_and_json_array(tmp_path):
    folder=tmp_path/'commands';folder.mkdir()
    for name in ['10', '2']:
        (folder/f'{name}.json').write_text(json.dumps(Command(name,'',0,0).to_dict()))
    export_markdown(folder,tmp_path/'directory.md')
    assert (tmp_path/'directory.md').read_text().index('## 2') < (tmp_path/'directory.md').read_text().index('## 10')
    array=tmp_path/'array.json'
    array.write_text(json.dumps([Command('a','',0,0).to_dict(),Command('b','',0,0).to_dict('paper')]))
    assert export_markdown(array,tmp_path/'array.md') == 2


@pytest.mark.parametrize('workers', [1, 2])
def test_campus_reference_keeps_commands_and_excludes_support_bookmarks(workers):
    parser = load_parser('campus-switch')
    result = parser.parse(FIXTURE.parent / 'campus-interfaces.pdf', workers=workers)
    assert [command.section for command in result.commands] == ['4.1.2', '4.1.3', '4.1.4']
    assert result.report()['missing_outline_sections'] == []
    bandwidth = result.commands[1]
    assert bandwidth.clis == ['bandwidth <bandwidth>', 'undo bandwidth']
    assert 'Ethernet interface view' in bandwidth.views
    assert bandwidth.parameters[0].name == 'bandwidth'
    assert bandwidth.examples
    assert bandwidth.usage_guidelines
    assert result.commands[2].clis == ['description <description>', 'undo description']


def test_campus_misnamed_support_matrix_is_not_a_missing_command():
    result = load_parser('campus-switch').parse(FIXTURE.parent / 'campus-mld.pdf')
    assert [command.section for command in result.commands] == ['8.2.2']
    assert result.report()['missing_outline_sections'] == []
    assert result.commands[0].clis == ['display default-parameter mld']
    assert result.commands[0].examples


def test_campus_outline_accepts_line_breaks_inside_bookmark_titles():
    with pymupdf.open() as document:
        document.new_page()
        document.set_toc([[1, '2.8.32 set save-configuration backup-to-server\nserver', 1]])
        headings = load_parser('campus-switch').outline_entries(document)
    assert len(headings) == 1
    assert headings[0].section == '2.8.32'
    assert headings[0].title == 'set save-configuration backup-to-server server'
