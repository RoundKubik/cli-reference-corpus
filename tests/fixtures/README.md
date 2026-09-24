Real PDF excerpts from Huawei's **CloudEngine 9800, 8800, and 6800 V300R024C00
Command Reference**, EDOC1100439391, issue 01 (2025-01-21).
Source: https://support.huawei.com/enterprise/en/doc/EDOC1100439391
Full-file checksum and download URL: `../../scripts/fetch_cloudengine.py`.

These are original PDF pages extracted with PyMuPDF `insert_pdf`, preserving
embedded fonts, drawings, tables and text. They are not synthetic or HTML prints.
Outline entries were rebased to excerpt page numbers.

| Fixture | Physical pages in full reference | Tested behavior |
| --- | --- | --- |
| bandwidth.pdf | 1899–1902 | Command crossing a page, ligatures, views |
| link-type.pdf | 1952–1955 | Model-specific applicability inside Format |
| vlan-mapping.pdf | 1959–1963 | Wrapped keywords/arguments, multi-page parameter table |
| mac-address.pdf | 1686–1695 | Wrapped first template following model applicability notes |
| tftp.pdf | 359–360 | Cell clipping must not leak ligature characters from a neighbor |

Copyright © Huawei Technologies Co., Ltd.; original documentation notices apply.

`ne40e-ospfv3.html` is an original HTML topic from the official CHM archive
**NE40E V800R024C10SPC500 Diagnose**, EDOC1100463228. Source: https://support.huawei.com/enterprise/en/doc/EDOC1100463228. CHM member:
`diagnose/8090/DISPLAY-OSPFV3-ROUTING-AGE(OSPFCOMMOM).html`.
It tests local HTML → PDF rendering of superscript repetition, a multi-page
parameter table and a long captioned output table. It is not an original PDF.

`ne40e-mpls.html`: original topic `vrp/mpls_switch-l2vc_pesudo.html` from
**NE40E V800R023C10SPC500 Upgrade compatible Commands**, EDOC1100364536
(https://support.huawei.com/enterprise/en/doc/EDOC1100364536). Tests that a long parameter row cannot
silently remove following Views/Usage Guidelines sections during PDF rendering;
the renderer retries with a taller page and preserves an explicit mapping.

`cisco-catalyst.pdf`: original pages 63–66, 82–83, 111–112, 213–214 and 2099
from Cisco Catalyst 9300 IOS XE 17.15.x Command Reference. Fonts and drawings
are retained; bookmarks are rebased. Covers side labels, horizontally ruled
parameter tables, multiline headings, syntax fragments and inverse commands.
Source: https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/command_reference/b_1715_9300_cr.pdf
Copyright Cisco Systems, Inc.; original documentation notices apply.

`campus-interfaces.pdf` contains physical pages 1429–1433 of the original
**S1720, S2700, S5700, and S6720 V200R011C10 Command Reference**, issue 14
(2021-10-20), EDOC1000178165. Source:
https://support.huawei.com/enterprise/en/doc/EDOC1000178165.
Original full-PDF SHA-256:
`95cedc55ff1dcc50c8d63fa926134105282a7f82a850518c88d9eff4b6db1a53`.
The fixture retains the Command Support heading and three command descriptions;
bookmarks point to the corresponding pages of this five-page extract.

`campus-mld.pdf` contains physical pages 4747–4750 of that same original PDF.
It retains the support matrix misleadingly titled `8.2.1 MLD Configuration
Commands` and the complete `8.2.2 display default-parameter mld` description.

`ne40e-esi.pdf`: physical pages 19701–19703 and 19738–19739 of the locally prepared
NE40E V800R024C00SPC500 Command Reference. Original source topics: `esi dynamic`,
`esi dynamic-name`, and `evpn redundancy-mode`. The excerpt preserves their section
IDs and rebases page destinations. Tests access metadata, example captions,
named references and serial/parallel extraction. Full PDF SHA256:
`71d6075723cd8798691f8f0160dc9d5a4b50bc4d5b42736d330927e85493d4d6`.

`cisco-related-no-header.pdf`: original physical pages 2070, 2073, 2075–2076 and 2111 of the Catalyst 9500
IOS XE 17.15.x PDF, SHA256
`6e71ec7ecf69d4d4199d6188bd0615ee66e57753ec781999848c09aa04132038`.
Tests the `aaa local authentication` related-command table without column headings,
including the wrapped `aaa new-model` title, narrow column gaps and mirrored margins
on a page break. Source:
https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-15/command_reference/b_1715_9500_cr.pdf

`related-topics-records.json`: extracted records for `port trunk allow-pass vlan`
and potential target/distractor pages from the CloudEngine, Campus and NE40E manuals
listed above. Each record retains its source PDF filename, section ID and physical
page range. It covers false short-prefix references, VLAN parameter-topic retrieval,
view-specific homonyms and example commands. The source text is preserved; existing
related topics are cleared so tests exercise extraction rather than saved results.

`campus-related.pdf`: original physical pages 3299–3302 of the Campus V200R011C10
PDF, retaining `abr-summary (OSPF area)` and its numbered Related Topics list.
Tests adjacent references `7.4.4 area (OSPF)` and `7.4.67 ospf` as separate targets,
including a target outside the excerpt. Source and original PDF checksum are the
same as for `campus-interfaces.pdf` above.

`campus-related-boundary.pdf`: original pages 2442–2444 of the Campus PDF.
The last `stp snooping enable` description is followed by a large chapter title and
chapter contents. Tests that these are not collected as related topics or extra
information for the preceding command.

`cisco-extraction-regressions.pdf`: original Catalyst 9300 IOS XE 17.15.x physical
pages 303, 529, 570–574, 885, and 2362. Tests hostless prompts, promptless NAT
configuration blocks, geometric syntax ordering, subsection captions, missing
source syntax, and a source mode mislabeled as Command Default. Bookmarks are
rebased to excerpt pages; the source and copyright are the same as for
`cisco-catalyst.pdf` above.

`cisco-preamble-note.pdf`: original Catalyst 9500 physical page 881. A small bold
Note label precedes the function paragraph and must not start CLI syntax.
Source and checksum are the same as for `cisco-related-no-header.pdf` above.

`campus-empty-examples.pdf`: physical pages 1594–1595, 9589–9590, and 9594–9595 of
the retained Campus PDF (before the excluded chapter). Tests the explicit
`Example: None` and examples with empty `<>` / `[]` device prompts. Source and
checksum are the same as for `campus-interfaces.pdf` above.

`cisco-example-variants.pdf`: original Catalyst 9300 physical pages 1152–1153,
1367–1368, 1478–1479, 2089, 2109, and 2232. Tests configuration listings, source
example/template disagreements, `no-match` syntax boundaries, boot-loader prompts,
and routed processor prompts. Source and copyright are the same as for
`cisco-catalyst.pdf` above.

`cisco-inverse-example.pdf`: original Catalyst 9300 physical pages 1524–1525.
The printed affirmative `area nssa` template is malformed, while the inverse
form remains usable to recognize the promptless example on the next page.
The malformed source syntax is retained rather than silently repaired.
