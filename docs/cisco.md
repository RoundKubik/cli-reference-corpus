# Cisco Catalyst Command Reference corpora

Both corpora use complete original Cisco PDFs for **IOS XE 17.15.x**. They cover
different switch families; shared command descriptions are retained in each corpus.

| Model family | Corpus directory under `output/` | PDF pages | JSON/Markdown pairs |
| --- | --- | ---: | ---: |
| Catalyst 9300 | `cisco-catalyst9300-iosxe-17.15.x` | 2,642 | 1,343 |
| Catalyst 9500 | `cisco-catalyst9500-iosxe-17.15.x` | 2,592 | 1,321 |

Official sources:

- [Catalyst 9300 PDF](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9300/software/release/17-15/command_reference/b_1715_9300_cr.pdf)
- [Catalyst 9500 document page](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-15/command_reference/b_1715_9500_cr.html)
- [Catalyst 9500 PDF](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-15/command_reference/b_1715_9500_cr.pdf)

The local PDF names match their corpus directories, with the `.pdf` suffix.
URLs, models, software versions and SHA256 hashes are recorded in the
[source registry](../reports/sources/command-references.json). Each corpus manifest
also records the source PDF filename, hash, document title and URL.

## Catalyst 9500 source and generation

The complete PDF was downloaded on 2026-09-14. No pages or command chapters were
removed. Its title page identifies IOS XE 17.15.x and first publication on
2024-08-14. The original PDF's `subject` metadata still mentions 17.10.x; the
version used for naming comes from the title page and official document URL.
The original PDF bytes are preserved.

SHA256: `6e71ec7ecf69d4d4199d6188bd0615ee66e57753ec781999848c09aa04132038`.

From the project directory, with a new output directory:

```bash
.venv/bin/python -m cli_reference_corpus parse \
  data/manuals/cisco-catalyst9500-iosxe-17.15.x.pdf \
  --parser cisco-catalyst --workers 8 \
  -o output/cisco-catalyst9500-iosxe-17.15.x \
  --source-url https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst9500/software/release/17-15/command_reference/b_1715_9500_cr.pdf

.venv/bin/python scripts/audit_coverage.py --corpus cisco-catalyst9500-iosxe-17.15.x
```

The parser creates one JSON record and its English Markdown rendering for every
command description. It does not create a Markdown copy of the whole manual.

## Verification and limits

The independent page census found 1,321 dedicated command descriptions and matched
all of them to corpus records. All saved Markdown files match their JSON and
manifest metadata; there are no missing or extra files.

There are 2,217 extracted CLI templates and 553 records with extraction warnings.
Nineteen records fail the strict JSON schema: eight have no extracted syntax and
eleven have no extracted command mode. Six records have empty function text, which
the schema permits. In 120 records an Example/Examples section is detected in the
PDF while the extracted examples are empty. These are field-level review items;
the source must be inspected before assigning a cause to each case.

See the [Catalyst 9500 census](../reports/coverage/cisco-catalyst9500-iosxe-17.15.x.json),
[validation report](../output/cisco-catalyst9500-iosxe-17.15.x/validation.json),
[pair/schema verification](../reports/coverage/corpus-verification.json), and
[shared coverage notes](../reports/coverage/README.md).
Structural coverage does not prove complete or correct extraction of every field,
or coverage of commands outside this version's reference.

Schema v3 retains the complete extracted example sections in `ExtraInfo`, including
the cases whose structured `Examples` arrays are empty. Related-command tables are
also exported as structured `related_topics`; raw related text remains in
`ExtraInfo`. [Extraction rules](additional-information.md).
