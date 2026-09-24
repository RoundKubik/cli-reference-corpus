# Campus Switch Command Reference

Source: official Huawei **S1720, S2700, S5700, and S6720 V200R011C10 Command
Reference**, issue 14, dated 2021-10-20, document **EDOC1000178165**.
The shared manual explicitly includes the requested S1720, S2700 and S5700
families; it also covers S6720. Records are not filtered by individual switch
model. Model-specific restrictions in the source still apply.

- [Huawei document page](https://support.huawei.com/enterprise/en/doc/EDOC1000178165)
- [Official PDF archive](https://download.huawei.com/edownload/e/download.do?actionFlag=download&nid=EDOC1000178165&partNo=6001&mid=SUPE_DOC)
- Input: `data/manuals/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf`
- Corpus: `output/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10/cmd_corpus/`

## Retained scope

The archive contains a complete PDF and separate chapter PDFs. The complete
publisher PDF has 11,594 pages. The project retains its first **11,349 pages**:
front matter and chapters 1–18. Chapter 19, **Upgrade-compatible Commands
Reference**, is excluded, consistent with the project scope. Its 201 command
bookmarks are not expected in this corpus. The original printed table of contents
still lists that excluded chapter; PDF bookmarks for it have been removed.

The retained chapters cover basic configuration, device and interface management,
Ethernet switching, IP services, unicast and multicast routing, MPLS, VPN,
WLAN-AC, reliability, user access/authentication, security, QoS, network
management/monitoring, Free Mobility and VXLAN. They contain **5,989 command
descriptions**. Introductory Command Support sections remain in the PDF but do
not become command records. The additional leaf bookmark `8.2.1 MLD Configuration
Commands` is also a model-support matrix, as verified on physical page 4747.

Pages retain the publisher's layout, text and images. There is no HTML conversion,
OCR or whole-manual Markdown export. PDF physical page numbers remain the same as
in the original full PDF. Every command is exported as JSON and its English
Markdown rendering.

## Provenance and verification

- [Original and retained PDF hashes and page selection](../reports/sources/campus-pdf.json)
- [Comparison of every retained page with the original](../reports/coverage/campus-source-to-pdf.json)
- [Command-bookmark coverage and the support-matrix exception](../reports/coverage/campus-outline.json)
- [Independent census of printed command descriptions](../reports/coverage/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.json)
- [JSON/Markdown and schema verification](../reports/coverage/corpus-verification.json)

The corpus has 5,989 JSON/Markdown pairs and 11,851 CLI templates. Every JSON
record passes the repository schema; 560 records carry extraction warnings.
The three empty-example findings have been reviewed: two commands with empty
`<>` / `[]` prompts are now extracted, and `port media type` correctly retains
an empty array because its source prints `Example: None`. See the
[extraction review](../reports/coverage/extraction-warning-review.md).
Full titles are taken from matching PDF bookmarks to avoid inserting spaces at
printed line breaks.

Coverage is measured against the retained reference chapters. A command record's
presence does not certify semantic accuracy of every extracted field or support
on every switch model. Extraction warnings remain in the corpus validation report.

## Reproduce

Run from the project directory. Use new output paths or remove the previous
result first; the scripts refuse to overwrite existing outputs.

```bash
.venv/bin/python scripts/fetch_campus.py \
  -o data/manuals/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf \
  --source-map reports/sources/campus-pdf.json

.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf \
  --parser campus-switch --workers 8 -o output/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10 \
  --source-url https://support.huawei.com/enterprise/en/doc/EDOC1000178165

.venv/bin/python scripts/audit_coverage.py --corpus huawei-campus-s1720-s2700-s5700-s6720-v200r011c10
```

The download script verifies pinned SHA-256 hashes for the archive and its full
PDF member. It stores downloaded/extracted intermediates in a temporary directory
and removes them after preparation. To reuse a downloaded archive, pass
`--archive /path/to/reference.zip`.

To repeat the page-selection audit with an extracted original full PDF:

```bash
.venv/bin/python scripts/audit_pdf_selection.py \
  --original /tmp/original-campus-command-reference.pdf \
  --selected data/manuals/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf \
  --source-map reports/sources/campus-pdf.json \
  -o reports/coverage/campus-source-to-pdf.json
```
