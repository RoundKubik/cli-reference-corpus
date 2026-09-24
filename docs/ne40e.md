# Huawei NE40E Command Reference

Input file: `data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf`.
It contains the standard **NE40E V800R024C00SPC500 Command Reference** from the
official [Huawei documentation package](https://support.huawei.com/enterprise/en/doc/EDOC1100423401).
[Online reference](https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981).

The PDF was prepared locally from CHM: HTML topics were printed in batches using
Chrome and merged into a single **30,291-page** document. This is not an original
Huawei PDF. The entire Command Reference section was selected: **14,833 topics**,
including **14,551 command descriptions** and 282 introductory/grouping topics.
The adjacent Debugging Command Reference is excluded. This reference replaces
the previous Diagnose manual.

## Source document verification

- The traversal of child HTML topics was independently checked against the CHM
  table of contents (`.hhc`): 14,833 unique topics, with no missing or extra topics.
- Each topic's HTML SHA-256 and corresponding physical PDF pages were recorded.
  Topic order, section headings, and text after printing were checked.
- All 2,508 image references resolve to local files; HTML preparation preserves
  images and original tables. The final PDF also contains 2,508 images.
- A character-frequency check of letters and digits found no deficit in any
  topic. Word-count differences caused by line wrapping were reviewed separately.
  These checks detect text loss, but do not prove that every table fragment is
  ordered correctly or constitute a visual review of every page.

Provenance and verification results are stored outside `data`:

- [Package, URL, and checksums](../reports/sources/ne40e-download.json).
- [HTML → PDF map and printing results](../reports/sources/ne40e-rendering.json).
- [Word wrapping and image checks](../reports/sources/ne40e-text-review.json).
- [Source command comparison with the corpus](../reports/coverage/ne40e-source-to-corpus.json).
- [Independent PDF page audit](../reports/coverage/huawei-ne40e-v800r024c00spc500.json).

Each topic starts on a new page and receives a generated section number `1.N`.
PDF bookmarks point to command descriptions; introductory topics are also
included in the PDF. Corpus page numbers refer to the prepared PDF, not the
pagination of the online reference.

## Generating the corpus from PDF

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf \
  --parser ne40e-rendered --workers 8 -o output/huawei-ne40e-v800r024c00spc500 \
  --source-url 'https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981'
```

The parser reads the PDF itself. HTML and CHM are used only to prepare and verify
the source. Complete command titles are read from PDF bookmarks so that wrapped
headings do not introduce spaces within names. Each command in
`output/huawei-ne40e-v800r024c00spc500/cmd_corpus/` has a JSON file and an English
Markdown rendering. No combined reference Markdown file is generated. Extraction
warnings are saved in `validation.json` and the command Markdown files. The
result contains 14,551 pairs and 33,151 CLI templates; all records pass JSON Schema
validation. There are extraction warnings for 379 commands. Page 19,559 is empty
after printing, which is also recorded in the report; source text checks found
no loss of content for that topic.

## Reproducing the PDF

Additional requirements are `7z`, Chrome/Chromium, and the `.[prepare]` dependencies.
Store the archive and extracted CHM in a temporary directory: only final PDFs
remain in `data`. Existing output files and directories are not overwritten.

```bash
.venv/bin/python scripts/fetch_ne40e.py \
  --manifest reports/sources/ne40e-download.json --destination /tmp/ne40e-source

.venv/bin/python scripts/chm_to_pdf.py \
  '/tmp/ne40e-source/NE40E V800R024C00SPC500 Product Documentation.chm' \
  -o /tmp/ne40e-command-reference.rendered.pdf \
  --title 'Huawei NE40E V800R024C00SPC500 Command Reference' \
  --entry-point software/nev8r10_vrpv8r16/user/ne/dc_ne_title_cli.html \
  --renderer chrome --workers 4
```

The converter also saves a `.source.json` file alongside the new PDF. When moving
the final PDF into `data/manuals`, preserve the map in `reports/sources`.
The map records the Chrome version and preparation module hashes: printing again
may produce a different binary PDF hash. The saved final PDF is sufficient to
reproduce the existing corpus.

```bash
.venv/bin/python scripts/audit_prepared_reference.py \
  --source-map reports/sources/ne40e-rendering.json \
  --pdf data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf \
  --corpus output/huawei-ne40e-v800r024c00spc500 -o reports/coverage/ne40e-source-to-corpus.json
```

Completeness here refers to the selected Command Reference for this NE40E release.
It does not imply coverage of all commands in other software versions or diagnostic
references, or complete semantic accuracy of every JSON field.

## Additional information (schema v3)

`ExtraInfo` now retains Default Level, Task Name and Operations, and the complete
extracted example section with captions and output. `related_topics` captures
explicit named references from the PDF text and resolves matching outline sections.
For `esi dynamic`, these include `esi dynamic-name` and `evpn redundancy-mode`.
[Extraction rules and limitations](additional-information.md).
