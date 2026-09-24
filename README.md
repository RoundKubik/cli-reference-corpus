# CLI Reference Corpus

A documentation parser for Huawei CloudEngine, Huawei NE40E, Cisco Catalyst,
and Huawei Campus Switch S1720/S2700/S5700/S6720.
Each command is saved separately as NAssim-format JSON and a readable Markdown
rendering with the same basename. All renderer labels, headings, and messages
are in English; the original command text is preserved. No combined Markdown
file is generated for the entire manual.

## Workspace layout

```text
data/manuals/
  huawei-cloudengine-9800-8800-6800-v300r024c00.pdf
  huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf
  huawei-ne40e-v800r024c00spc500.rendered.pdf
  cisco-catalyst9300-iosxe-17.15.x.pdf
  cisco-catalyst9500-iosxe-17.15.x.pdf
output/
  huawei-cloudengine-9800-8800-6800-v300r024c00/
  huawei-campus-s1720-s2700-s5700-s6720-v200r011c10/
  huawei-ne40e-v800r024c00spc500/
  cisco-catalyst9300-iosxe-17.15.x/
  cisco-catalyst9500-iosxe-17.15.x/
```

Corpus names include the vendor, model or model families, and software version.
Shared references list all families; the corpus is not filtered by a specific
chassis. Model, version, and source mappings are stored in the
[source registry](reports/sources/command-references.json).
Each corpus directory contains `manifest.json`, `validation.json`, and
`cmd_corpus/` with individual `<section>_<command>.json` and `.md` pairs.

`data` contains only the five PDFs. Archives, CHM files, intermediate metadata,
and the Upgrade-compatible reference have been removed. Complete corpora and PDFs
are stored locally; `data/manuals/` and `output/` are excluded from Git.
`benchmarks/` and `research/` are in the parent directory and belong to the
configuration dependency research project.

## Sources and coverage

| Corpus | Document | PDF origin |
| --- | --- | --- |
| CloudEngine 9800/8800/6800 V300R024C00 | CloudEngine 9800, 8800, and 6800 V300R024C00 Command Reference, EDOC1100439391, issue 01 (2025-01-21) | Original Huawei PDF, 12,269 pages |
| NE40E V800R024C00SPC500 | NE40E V800R024C00SPC500 Command Reference, from package EDOC1100423401 | Complete PDF generated locally from the official CHM, 30,291 pages |
| Catalyst 9300 IOS XE 17.15.x | Command Reference, Cisco IOS XE 17.15.x (Catalyst 9300 Switches) | Original Cisco PDF, 2,642 pages |
| Catalyst 9500 IOS XE 17.15.x | Command Reference, Cisco IOS XE 17.15.x (Catalyst 9500 Switches) | Original Cisco PDF, 2,592 pages |
| Campus S1720/S2700/S5700/S6720 V200R011C10 | S1720, S2700, S5700, and S6720 V200R011C10 Command Reference, EDOC1000178165, issue 14 (2021-10-20) | 11,349 original Huawei pages; chapter 19, Upgrade-compatible, excluded |

Links: [CloudEngine](https://support.huawei.com/enterprise/en/doc/EDOC1100439391),
[NE40E Command Reference](https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981),
[Cisco PDF](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/command_reference/b_1715_9300_cr.pdf).
Checksums of the PDFs used and their source URLs are stored in each corpus's
`manifest.json`.

**NE40E uses the standard Command Reference.** The PDF includes all 14,833 topics
in the selected reference, including 14,551 command descriptions. Its contents
were independently checked against the official CHM table of contents. Section
numbers `1.N` were assigned during PDF preparation; the source topic map and
verification results are preserved. [Details](docs/ne40e.md).
CloudEngine uses a reference shared by several models; commands are not
automatically filtered by chassis. Cisco uses the `cisco-catalyst` profile,
validated against the Catalyst 9300 and 9500 PDFs. [Cisco sources](docs/cisco.md).
Campus Switch uses the `campus-switch` profile: Command Support entries are not
counted as commands. The corpus contains the standard commands from chapters
2–18 of the shared reference, without automatic filtering by model.
[Source and reproduction](docs/campus.md).

## Current results

| Corpus | JSON + Markdown pairs | CLI templates | Commands with warnings |
| --- | ---: | ---: | ---: |
| CloudEngine 9800/8800/6800 V300R024C00 | 6,672 | 15,446 | 551 |
| NE40E V800R024C00SPC500 | 14,551 | 33,151 | 379 |
| Catalyst 9300 IOS XE 17.15.x | 1,343 | 2,234 | 534 |
| Catalyst 9500 IOS XE 17.15.x | 1,321 | 2,206 | 551 |
| Campus S1720/S2700/S5700/S6720 V200R011C10 | 5,989 | 11,851 | 560 |

All 29,876 pairs have been checked: Markdown matches the JSON and metadata, and
PDF checksums match the manifests. No commands are missing relative to the
selected bookmarks; introductory Cisco chapters are excluded from the expected
command list. For NE40E, all commands were also checked against the source
Command Reference: [source-to-corpus verification](reports/coverage/ne40e-source-to-corpus.json).
[Pair and JSON Schema verification](reports/coverage/corpus-verification.json).

Every CloudEngine, NE40E, and Campus Switch record passes JSON Schema validation.
Catalyst 9300 has **23 records** that fail the strict schema: 15 lack a command
mode and 8 lack syntax. Catalyst 9500 has **19 such records**: 11 lack a mode and
8 lack syntax. Source review found 16 missing syntax blocks, 21 mode sections mislabeled as
Command Default, and 5 absent mode sections across the two corpora. These records
are retained with warnings; no syntax or modes are invented. See each corpus's `validation.json` and the
[verification report](reports/coverage/README.md).

## Running the parser

Python 3.10 or later is required. Parsing runs locally without LLMs, API keys,
or network access.

```bash
cd /home/roundkubik/workdir/huawei/cli-reference-corpus
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test,prepare]'
```

For another model or software version, pass its URL to a downloader in `scripts/`:

```bash
.venv/bin/python scripts/fetch_cloudengine.py 'DOCUMENTATION_URL'
.venv/bin/python scripts/fetch_campus.py 'DOCUMENTATION_URL'
.venv/bin/python scripts/fetch_ne40e.py 'DOCUMENTATION_URL'
```

PDF, CHM, ZIP, and Huawei EDOC pages are supported. The file is saved in
`data/manuals`, with its name and format detected automatically. Use `-o` for a
custom filename, `--destination` for the directory, and `--member` to select a
specific document when an archive is ambiguous.
[Download rules and subsequent parsing](docs/downloads.md).

The corpora already exist in the current workspace. The following commands
reproduce them from the five PDFs; output directories must be new. For another
run, use a different `-o` or remove the previous output first.

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-cloudengine-9800-8800-6800-v300r024c00.pdf \
  --parser cloudengine --section 2 --workers 4 -o output/huawei-cloudengine-9800-8800-6800-v300r024c00 \
  --source-url https://support.huawei.com/enterprise/en/doc/EDOC1100439391

.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-ne40e-v800r024c00spc500.rendered.pdf \
  --parser ne40e-rendered --workers 4 -o output/huawei-ne40e-v800r024c00spc500 \
  --source-url 'https://support.huawei.com/hedex/hdx.do?docid=EDOC1100408650&lang=en&id=EN-US_TOPIC_0000001844751981'

.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/cisco-catalyst9300-iosxe-17.15.x.pdf \
  --parser cisco-catalyst --workers 4 -o output/cisco-catalyst9300-iosxe-17.15.x \
  --source-url https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/command_reference/b_1715_9300_cr.pdf
```

For the second Cisco corpus:

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/cisco-catalyst9500-iosxe-17.15.x.pdf \
  --parser cisco-catalyst --workers 8 -o output/cisco-catalyst9500-iosxe-17.15.x \
  --source-url https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-15/command_reference/b_1715_9500_cr.pdf
```

For Campus Switch:

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.pdf \
  --parser campus-switch --workers 8 -o output/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10 \
  --source-url https://support.huawei.com/enterprise/en/doc/EDOC1000178165
```

`parse` automatically creates both representations of each command. A separate
Markdown export of the entire reference is not required.
To render any individual JSON record, use:

```bash
.venv/bin/python -m cli_reference_corpus markdown path/to/command.json -o path/to/command.md
```

Combined corpus Markdown export remains available in the API/CLI for
compatibility, but is not used for the current dataset.

To add related pages to an existing JSON corpus without rereading the PDF:

```bash
.venv/bin/python -m cli_reference_corpus enrich-related \
  output/cisco-catalyst9300-iosxe-17.15.x \
  -o output/cisco-catalyst9300-iosxe-17.15.x-enriched
```

The input must be a corpus directory containing `manifest.json`, or the manifest
itself. The result is a new directory with JSON/Markdown files and updated counts
in `validation.json`. The `related_topics[].target_files` field contains JSON
filenames within `cmd_corpus`, such as `13.1.57_route-map.json`. These files can
be loaded automatically from that directory. Regular `parse` runs populate this
field automatically. If a related command is absent from the selected corpus,
its section number is retained, but no filename is added for the missing file.

## Command format

The default is version 3 of the `repository` schema:

- `PageTitle` — command title;
- `CLIs` — CLI templates, with arguments marked as `<...>`;
- `FuncDef` — function description;
- `ParentView` — command modes/views;
- `ParaDef` — parameters, each with `Parameters` and `Info`;
- `Examples` — lists of CLI input lines, with printed prompts when present;
- `UsageGuidelines` — guidance, prerequisites, and restrictions;
- `ExtraInfo` — command level, access tasks and operations, additional sections,
  syntax applicability conditions, and complete source examples with captions and output.
- `related_topics` — related topics: title, description/quotation, source section,
  resolved reference section numbers (`target_sections`), and available command
  JSON filenames (`target_files`).
- `related_topics[].reference_kind` distinguishes an explicit reference
  (`documented_reference`), a command from an example (`example_command`), and a
  topic from parameter descriptions (`parameter_topic`). Parameter topics are
  selected using the current reference's data, without dictionaries of models
  or entities, or special rules for individual parameter names.
- `syntax_issues` — syntax parsing errors in individual CLI templates: template
  index, original CLI, code, and description. Errors are saved in JSON, the
  command is exported, and processing continues for the remaining pages. These
  diagnostics check the extracted format, not command behavior on a device.

`--schema paper` selects the alternative NAssim field names (`ParentViews`,
`Paras`) without `PageTitle`. In version 3, both variants retain `UsageGuidelines`,
`ExtraInfo`, and `related_topics`.
Schemas are in [schemas/](schemas/). Legacy JSON without `UsageGuidelines` or
`related_topics` is supported. [Additional information extraction rules](docs/additional-information.md).
Markdown is built from the serialized JSON fields; the title, pages, and warnings
are added from extraction metadata.

`manifest.json` maps each command's `file` and `markdown_file` to its title,
section, and physical PDF pages (1-based). `validation.json` contains command,
template, and example counts, missing commands relative to bookmarks, and warnings.
`cmd_corpus/` contains only command pairs; reports are stored one directory above.

## Completeness checks

An audit of every page in all five PDFs found no missing standalone command
descriptions. Cisco prompt handling, promptless examples, and geometric syntax
ordering have been corrected, and both Cisco corpora and Campus were regenerated.
The remaining empty example arrays with printed example headings are 6 for
Catalyst 9300, 4 for Catalyst 9500, and 1 for Campus: source captions without
command text, log-only output, or explicit `None`. Full source example text
remains in `ExtraInfo`.

All 42 Cisco schema failures and all warning categories were reviewed. This does
not establish semantic accuracy of every parameter or template; known limitations
remain documented. See the [review and source evidence](reports/coverage/extraction-warning-review.md)
and [page census](reports/coverage/README.md).

## Tests and limitations

```bash
.venv/bin/python -m pytest -q
```

Tests use real Huawei and Cisco PDF pages to check tables, commands spanning
multiple pages, font-based argument detection, JSON schemas, JSON/MD pairs,
warnings, refusal to overwrite existing output, and identical results with
`workers=1` and `2`. CHM conversion tests require the optional `beautifulsoup4`
dependency (`prepare`). Tests also check the selected reference's boundaries,
consistency with the CHM table of contents, preservation of introductory topics
and images, and detection of lost text. Preparing the complete PDF requires `7z`
and Chrome/Chromium; the PDF parser itself does not use them.

The corpora are preliminary: warnings remain in the reports and command Markdown.
A record's presence and JSON Schema compliance do not establish the semantic
accuracy of every field or whether the command works on hardware. Completeness
relative to bookmarks applies to the selected reference, not every command on
the platform. Scanned PDFs require OCR first. CLI hierarchy, on-device validation,
and NetBERT Mapper are not implemented.

`--strict` saves the output but returns exit code `2` for warnings, missing
commands, or pages without text. Codes `0` and `1` indicate successful export and
a reading/processing error, respectively; argument errors also return code `2`.

## Extending the parser

`BasePDFParser` provides the shared core; Huawei/Cisco profiles are selected with
`--parser`. An external subclass is specified as `module:Class`.
[Instructions](docs/extending-parsers.md).
JSON and Markdown use the shared `Command` model.
Original corpus format: [NAssim](https://github.com/AmyWorkspace/nassim).

Module map and suggested code reading order: [docs/code-structure.md](docs/code-structure.md).
