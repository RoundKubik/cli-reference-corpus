from pathlib import Path

import pytest

from cli_reference_corpus.model import validate
from cli_reference_corpus.pdf import Line
from cli_reference_corpus.vendors.cisco import CiscoCatalystParser
from cli_reference_corpus.vendors.cisco_examples import examples
from cli_reference_corpus.vendors.huawei import CampusSwitchParser

FIXTURES = Path(__file__).parent / 'fixtures'


@pytest.fixture(scope='module')
def cisco_commands():
    result = CiscoCatalystParser().parse(FIXTURES / 'cisco-extraction-regressions.pdf')
    return {command.title: command for command in result.commands}


def test_hostless_prompts_are_preserved(cisco_commands):
    assert cisco_commands['macro description'].examples == [
        ['(config-if)# macro description duplex settings']]
    assert cisco_commands['clear ipv6 access-list'].examples == [
        ['# clear ipv6 access-list marketing']]


def test_nat_templates_follow_visual_order_and_exclude_captions(cisco_commands):
    command = cisco_commands['ip nat inside source']
    assert len(command.clis) == 8
    assert command.clis[0] == (
        'ip nat inside source { list { <access-list-number> <access-list-name> } | route-map <name> } '
        '{ interface <type> <number> | pool <name> } [no-payload] [overload] [c] [ vrf <name> ]')
    assert all(cli.startswith(('ip nat inside source ', 'no ip nat inside source ')) for cli in command.clis)
    assert 'Dynamic NAT' in command.extra
    assert 'Network Static NAT' in command.extra


def test_promptless_configuration_preserves_separate_commands(cisco_commands):
    command = cisco_commands['ip nat inside source']
    assert len(command.examples) == 5
    assert command.examples[0] == [
        'ip nat pool net-209 203.0.113.209 203.0.113.222 prefix-length 28',
        'ip nat inside source list 1 pool net-209',
        'interface ethernet 0', 'ip address 203.0.113.113 255.255.255.240', 'ip nat outside',
        'interface ethernet 1', 'ip address 192.0.2.1 255.255.255.0', 'ip nat inside',
        'access-list 1 permit 192.0.2.1 255.255.255.0',
        'access-list 1 permit 198.51.100.253 255.255.255.0',
    ]


def test_source_omissions_are_not_invented(cisco_commands):
    command = cisco_commands['ip igmp snooping vlan mrouter']
    assert command.clis == []
    assert 'missing_format' in validate(command)
    command = cisco_commands['show license all']
    assert command.views == []
    assert 'Defaults:\nPrivileged EXEC (#)' in command.extra
    assert 'missing_views' in validate(command)


def test_promptless_output_is_not_treated_as_commands():
    def line(text):
        return Line(text, [{'text': text, 'flags': 8, 'font': 'Courier'}], (0, 0, 20, 8), 1, 0)
    prompt = CiscoCatalystParser.prompt
    assert examples([line('Packet counters: 25'), line('!'), line('interface statistics')],
                    ['sample <name>'], [], prompt) == []
    assert examples([line('sample abc'), line('Packet counters: 25')],
                    ['sample <name>'], [], prompt) == [['sample abc']]
    assert examples([line('Router# sample abc'), line('Packet counters: 25')],
                    ['sample <name>'], [], prompt) == [['Router# sample abc']]


def test_campus_empty_prompts_and_explicit_none():
    assert not CampusSwitchParser.prompt.match('[] : indicates the upper ECN threshold')
    commands = {c.title: c for c in CampusSwitchParser().parse(FIXTURES / 'campus-empty-examples.pdf').commands}
    assert commands['port media type'].examples == []
    assert 'Examples (source text):\nNone' in commands['port media type'].extra
    assert commands['display snmp-agent trap feature-name cfgmgr all'].examples == [
        ['<> display snmp-agent trap feature-name cfgmgr all']]
    assert commands['snmp-agent trap enable feature-name cfgmgr'].examples == [[
        '<> system-view',
        '[] snmp-agent trap enable feature-name cfgmgr trap-name hwauthenassociateaccesslimittrap',
    ]]


def test_preamble_note_does_not_turn_description_into_syntax():
    command = CiscoCatalystParser().parse(FIXTURES / 'cisco-preamble-note.pdf').commands[0]
    assert 'To delete the Protocol Independent Multicast (PIM)' in command.function
    assert 'not applicable on C9500X-28C8D' in command.function
    assert command.clis == ['clear ip pim snooping vlan <vlan-id> [neighbor | statistics | mroute [<source-ipgroup-ip>]]']
    assert 'missing_function' not in validate(command)


def test_real_promptless_and_bootloader_variants():
    commands = {c.title: c for c in CiscoCatalystParser().parse(FIXTURES / 'cisco-example-variants.pdf').commands}
    assert commands['arp'].examples == [['Device: arp 172.20.136.8']]
    assert len(commands['snmp-server community'].examples) == 3
    assert commands['snmp-server community'].examples[0] == [
        'RP/0/RP0/CPU0:router(config)# snmp-server community comaccess ro 4']
    assert commands['match client-type'].examples == [[
        'class-map type control subscriber match-all CLASS_1', 'match client-type data']]
    assert len(commands['match client-type'].clis) == 3
    assert commands['description (service template)'].examples[0][1] == 'description label for SVC_2'
    assert commands['random-detect dscp'].examples == [['random-detect dscp percent 8 20 40']]
    assert 'mdt data 228.0.0.0 0.0.0.127 threshold 500 list 101' in commands['mdt data'].examples[0]
    assert '.' not in commands['mdt data'].examples[0]


def test_inverse_template_identifies_example_despite_malformed_affirmative_source():
    command = CiscoCatalystParser().parse(FIXTURES / 'cisco-inverse-example.pdf').commands[0]
    assert command.clis[0].startswith('area nssa commandarea ')
    assert command.examples == [['area 1 nssa']]
    assert 'router ospf 1' in command.extra
