# Corpus coverage audit

Audit date: 2026-09-14. NE40E was regenerated from the complete ordinary Command
Reference; CloudEngine and Cisco retain their verified original PDF inputs.
Campus Switch was added from original Huawei V200R011C10 PDF pages, with the
Upgrade-compatible chapter excluded.
Cisco Catalyst 9500 IOS XE 17.15.x was added from its complete original Cisco PDF.

The scan found no missing **dedicated command descriptions** in the five retained
PDFs. This does **not** establish complete or correct extraction of their contents,
or coverage of every command mentioned in the manuals or supported by the devices.
Concrete content losses were confirmed in the Cisco corpus.

## Structural census

| Corpus | PDF pages scanned | Printed command descriptions | Corpus records | Unmatched descriptions |
| --- | ---: | ---: | ---: | ---: |
| CloudEngine | 12,269 | 6,672 | 6,672 | 0 |
| NE40E Command Reference | 30,291 | 14,551 | 14,551 | 0 |
| Cisco Catalyst 9300 | 2,642 | 1,343 | 1,343 | 0 |
| Cisco Catalyst 9500 | 2,592 | 1,321 | 1,321 | 0 |
| Campus S1720/S2700/S5700/S6720 | 11,349 | 5,989 | 5,989 | 0 |

Reports with a source-page-to-record inventory:
[CloudEngine](huawei-cloudengine-9800-8800-6800-v300r024c00.json), [NE40E](huawei-ne40e-v800r024c00spc500.json),
[Catalyst 9300](cisco-catalyst9300-iosxe-17.15.x.json), [Catalyst 9500](cisco-catalyst9500-iosxe-17.15.x.json),
[Campus Switch](huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.json).

The census reads every PDF page through PyMuPDF, independently of bookmarks and
production parser profiles. For Huawei it tracks printed numbered headings and
Function/Format sections; for Cisco it tracks 21-point printed headings and the
subsequent Syntax Description / Command Modes / Command Default sections. Wrapped
Cisco headings are joined. Dedicated descriptions are then matched to manifests
by section ID (Huawei) or start page (Cisco).

As a cross-check, CloudEngine contains exactly 6,672 bold 13-point labels for each
of Function, Format, Views, Usage Guidelines and Example. NE40E has a separate
source-to-PDF-to-corpus audit: all 14,833 topics in the official CHM reference
outline are in the prepared PDF, and its 14,551 command topics are matched to
individual records. See [source coverage](ne40e-source-to-corpus.json),
[rendering map](../sources/ne40e-rendering.json) and
[text/word-wrap review](../sources/ne40e-text-review.json).
Additional low-size occurrences of Function/Format can be table or prose text.

This remains a typography-based audit. It cannot prove that every possible layout,
embedded image, syntactic alternative or reference to another command was covered.

## Confirmed extraction problems

After regeneration with parser 0.3.0/schema v3, `ExtraInfo` preserves the extracted
source example text, captions and output in all corpora, including the examples
below. The remaining empty-example findings refer to the structured `Examples`
CLI array. Huawei access metadata and explicit related sections are retained;
`related_topics` also captures named references in primary fields. See
[additional-information rules](../../docs/additional-information.md).

- **Missing examples with hostless prompts.** On physical Cisco PDF page 303,
  `macro description` has `(config-if)# macro description duplex settings` in its
  Example section, but the JSON has an empty `Examples` array. On page 529,
  `clear ipv6 access-list` has `# clear ipv6 access-list marketing`, also omitted.
  The production prompt pattern requires a hostname before the prompt.
- **Missing examples without prompts.** Pages 572–574 contain configuration examples
  for `ip nat inside source`, while its JSON has an empty `Examples` array. These
  are command blocks without a hostname/prompt, currently excluded from the CLI array
  but retained in `ExtraInfo`.
- **Corrupted syntax.** On page 570, the visually verified heading `Dynamic NAT`
  is a subsection caption. The first `ip nat inside source` CLI template includes
  this caption and misorders fragments of the syntax. The record exists, but this
  template is not a faithful representation of the printed command.

Relevant records:
[macro description](../../output/cisco-catalyst9300-iosxe-17.15.x/cmd_corpus/6.1.36_macro_description.json),
[clear ipv6 access-list](../../output/cisco-catalyst9300-iosxe-17.15.x/cmd_corpus/7.1.2_clear_ipv6_access-list.json),
[ip nat inside source](../../output/cisco-catalyst9300-iosxe-17.15.x/cmd_corpus/7.1.36_ip_nat_inside_source.json).
Source: [Cisco PDF](../../data/manuals/cisco-catalyst9300-iosxe-17.15.x.pdf).
Page numbers above are physical PDF pages, starting at 1.

**281 Catalyst 9300 records** have empty `Examples` although a printed Example/Examples
section was detected. This is a review queue, not a claim that all 281 have the
same cause. In total 616 Cisco records have empty examples; some have no separately
labelled example section. Eight records have no extracted CLI template. Structural
counts do not detect these issues, and the current validation report does not warn
on every missing example or incorrectly ordered template.

**Catalyst 9500:** all 1,321 descriptions are represented. Eight records have empty
CLI syntax, eleven have empty command modes, and 120 have empty examples despite
a printed Example/Examples section. All JSON/Markdown pairs match exactly; nineteen
records fail the strict schema. These findings are review items, not proof that
the fields are absent from the original PDF. [Source and reproduction](../../docs/cisco.md).

The new NE40E corpus also has one empty `Examples` field despite a printed
Example section: `dcn security-mode enable`, physical page 1,083. The source shows
`default.cfg` content without a device prompt; the current example extractor
omits that block. The command record and its syntax are present. This is a
field-extraction limitation, not a missing command or an incomplete input PDF.

Campus Switch has **three records** with empty `Examples` despite a printed
Example section: `port media type` (page 1594),
`display snmp-agent trap feature-name cfgmgr all` (page 9589), and
`snmp-agent trap enable feature-name cfgmgr` (page 9594). These remain a field-level
review queue; their command records and syntax are present. All 5,989 Campus JSON
records pass the schema, and all Markdown pairs match their JSON and metadata.

## Additional-information verification

All 29,876 records now have additional source text. There are 33,645 related-topic
entries across 15,697 records, including explicit numbered Huawei references and
Cisco related-command tables. Every non-empty `target_sections` value points to
an existing command record in these full corpora; unresolved named targets remain
empty rather than being guessed. The page census found no empty additional or
structured related fields where the checked source section headings were present.

Core command fields match the previous corpora. Seventeen NE40E titles differ only
in whitespace normalization; filenames and section IDs are unchanged. All JSON/MD
pairs match. [Rules and per-corpus counts](../../docs/additional-information.md).

## Limits of the source set

- **NE40E:** the retained PDF is locally prepared from the complete ordinary
  V800R024C00SPC500 Command Reference in official Huawei Product Documentation.
  It includes introductory/group topics and configuration commands such as
  `interface`, `bgp`, `ospf` and `system-view`. The sibling Debugging Command
  Reference is a separate book. Coverage applies to this reference and version.
  Source hashes and the HTML-to-PDF map are retained outside `data`.
- **Campus Switch:** all dedicated descriptions in retained chapters 2–18 are
  represented. Chapter 19 Upgrade-compatible (201 command bookmarks) is excluded.
  The original printed contents still lists that chapter. The common manual also
  includes S6720; records are not filtered by switch model. `Command Support`
  bookmarks and the misnamed model-support matrix `8.2.1 MLD Configuration Commands`
  are not command descriptions. See [bookmark audit](campus-outline.json),
  [original-page comparison](campus-source-to-pdf.json) and [source details](../../docs/campus.md).
- **Cisco Catalyst 9300:** a command mentioned in an example or Related Commands table need not
  have a dedicated description in this book. For example, the NAT examples mention
  `ip route` and `access-list`, but the corpus has no standalone general descriptions
  for those commands. The separate `ip route static bfd` entry is not a substitute
  for the general `ip route` command.
- **CloudEngine:** the last page points to an external "List of unsupported
  commands.xlsx". Its contents are not in this PDF or in this corpus.
- `undo`/`no` forms and syntax alternatives are usually stored in `CLIs` within one
  record, rather than as separate JSON files. Filename count is not syntax count.

## Reproduce

From the project directory:

```bash
.venv/bin/python scripts/audit_coverage.py
# Or audit a single retained manual:
.venv/bin/python scripts/audit_coverage.py --corpus cisco-catalyst9300-iosxe-17.15.x
```

The script writes only coverage reports. It neither reparses nor changes the corpora.
It discovers all `output/*/manifest.json` files and uses the recorded parser module
to select Huawei or Cisco page typography. `--corpus` takes the full directory name,
including models and software version; `--device` remains an argument alias.
The next correction should address Cisco prompt handling and syntax ordering,
then regenerate the affected pairs and repeat this census and field-level checks.
