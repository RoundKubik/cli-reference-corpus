# Corpus coverage audit

Initial audit: 2026-09-14. Cisco and Campus corrections and repeat audits: 2026-09-24. NE40E was regenerated from the complete ordinary Command
Reference; CloudEngine and Cisco retain their verified original PDF inputs.
Campus Switch was added from original Huawei V200R011C10 PDF pages, with the
Upgrade-compatible chapter excluded.
Cisco Catalyst 9500 IOS XE 17.15.x was added from its complete original Cisco PDF.

The scan found no missing **dedicated command descriptions** in the five retained
PDFs. This does **not** establish complete or correct extraction of their contents,
or coverage of every command mentioned in the manuals or supported by the devices.
Previously confirmed Cisco content losses have been corrected; source defects
and the remaining field-level limitations are documented below.

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

## Extraction corrections and reviewed source limitations

The [extraction review](extraction-warning-review.md) records fixes, source evidence,
and the remaining warning categories. Both Cisco corpora and Campus were rebuilt
from their complete retained PDFs, with no missing descriptions or new schema
failures.

Cisco now supports hostless prompts, routed processor prompts, boot-loader prompts,
and promptless configuration examples. Individual PDF spans are ordered by their
visual positions; NAT captions and preamble notes no longer contaminate CLI syntax.
Five missing Catalyst 9500 function paragraphs were recovered, and `no-match`
forms are exported as separate templates. Full source examples remain in `ExtraInfo`.

| Corpus | Empty examples with a printed heading before | After | Explanation of remaining cases |
| --- | ---: | ---: | --- |
| Catalyst 9300 | 281 | 6 | Five source captions without commands, one log-only example |
| Catalyst 9500 | 120 | 4 | Three source captions without commands, one log-only example |
| Campus Switch | 3 | 1 | `port media type` explicitly prints `Example: None` |

Campus examples with `<>` and `[]` prompts are recovered; output legends beginning
with `[] :` are not treated as commands. NE40E `dcn security-mode enable` remains
an empty structured example because its source is promptless `default.cfg` content;
that text remains in `ExtraInfo`, as documented in the earlier review.

All 42 Cisco schema failures were checked against their source pages: 16 descriptions
lack a standalone syntax block, 21 print mode text under Command Default, and 5
omit a labelled mode section. These records remain exported with warnings.
Each Cisco corpus also has one function paragraph absent in the source. Missing
fields are not filled with guesses from command names or examples.

The [warning inventory](extraction-warning-review.json) covers every retained
warning and provides source samples for each category. Continued/borderless tables,
parameter-name discrepancies, font ambiguity, and malformed printed syntax remain
limitations. Review does not imply that every field is semantically correct.

## Additional-information verification

All 29,876 records retain additional source text. JSON/Markdown pairs, PDF hashes,
schema failures, reference targets, and exported filenames are checked in the
[current verification report](corpus-verification.json). The three regenerated
corpora retain their section IDs and source page mappings. Core field changes
are recorded explicitly; unchanged CloudEngine and NE40E pairs were also checked.

The page census found no missing additional or structured related sections where
the checked source headings were present. [Extraction rules](../../docs/additional-information.md).

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
The prompt and syntax corrections are covered by real-page regression tests;
remaining source omissions and field limitations are tracked in the extraction review.
