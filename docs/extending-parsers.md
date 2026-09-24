# Adding a vendor or a new layout

`BasePDFParser` handles opening PDFs, page ranges, a bounded queue of page-reading
workers, command boundaries, field accumulation, bookmark coverage checks, and the
`Command` model. JSON and Markdown use this model independently of the profile.
To support a different layout, describe its differences in a subclass; no changes
to the CLI or exporters are required.

Implementations:

- [`BasePDFParser`](../src/cli_reference_corpus/parser.py) — the shared algorithm and `CommandBuilder`.
- [`HuaweiPDFParser`](../src/cli_reference_corpus/vendors/huawei.py) — numbering,
  headers and footers, synthetic italics, `undo`, and Huawei prompts.
  `CloudEngineParser` and `NE40EParser` inherit these rules; `NE40ERenderedParser`
  defines margins for the intermediate PDF generated from CHM.
- [`CiscoIOSParser`](../src/cli_reference_corpus/vendors/cisco.py) — an example for
  unnumbered commands with bookmarks, italic arguments, `Syntax Description`,
  `Command Modes`, and `Router(config)#`. Tested on a synthetic PDF. A real
  IOS/NX-OS PDF requires checking font sizes, heading positions, and tables.
- `CiscoCatalystParser` (`--parser cisco-catalyst`) — a profile for Catalyst 9300
  and 9500 IOS XE 17.15.x PDFs: side headings, tables with horizontal borders,
  wrapped titles, and syntax fragments. Tested against original PDF pages.

## Minimal subclass

Create `my_parser.py` in the current directory:

```python
from cli_reference_corpus.vendors.cisco import CiscoIOSParser

class MyCiscoParser(CiscoIOSParser):
    header_margin = 60
    footer_margin = 45
    section_aliases = {
        **CiscoIOSParser.section_aliases,
        "Application Notes": "Usage Guidelines",
        "Command Syntax": "Format",
    }
```

```bash
PYTHONPATH=. .venv/bin/python -m cli_reference_corpus parse manual.pdf \
  --parser my_parser:MyCiscoParser --workers 4 -o output/my-cisco
# Each command's JSON and Markdown are now in output/my-cisco/cmd_corpus/.
```

Or call the parser directly:

```python
from my_parser import MyCiscoParser
from cli_reference_corpus.corpus import write_corpus
from pathlib import Path

if __name__ == "__main__":  # Required when workers > 1 in a user script.
    source = Path("manual.pdf")
    result = MyCiscoParser().parse(source, workers=4)
    write_corpus(result, source, Path("output/my-cisco"), "repository")
```

## Extension points

| Method / attribute | When to override |
| --- | --- |
| `header_margin`, `footer_margin`, `footer_pattern` | Page headers, footers, and margins |
| `read_page(page, header, footer)` | Two columns, borderless tables, or special text ordering |
| `table_options` | `Page.find_tables` arguments, such as line detection strategies |
| `outline_entries(doc)` | Bookmarks do not correspond to commands, or a different ID scheme is needed |
| `command_heading(event, page, outline)` | Numbered/unnumbered headings, size, or coordinates |
| `section_aliases`, `field_min_size`, `field_heading(event)` | Command section names and formatting |
| `add_preamble(builder, event)` | Description and syntax before the first named section |
| `keyword_span(span)` | Distinguishing arguments from literals by font style |
| `condition_prefixes`, `inverse_keywords` | Conditional variants and inverse commands |
| `parse_formats`, `parse_parameters`, `parse_views`, `parse_examples` | Grammar of individual fields |
| `paragraphs(events)` | Paragraphs, lists, and text tables |
| `create_builder(heading)`, `build_command(builder)` | Substantially different description structure |
| `in_section(id, selected)` | Section hierarchy differs from `1.2.3` |

`command_heading` returns `Heading(section, title, page, level)` or `None`.
Chapter sections can also be returned as boundaries: `build_command` skips
records without Function/Format. The next chapter heading closes the preceding
command. Unnumbered bookmarks receive stable hierarchical IDs by default;
Huawei retains the document's section numbers. Titles are not used as unique
keys: commands with the same name in different views remain separate records.

Intermediate events are `Line(text, spans, bbox, page, block)` and
`Table(rows, bbox, page)`. Coordinates and pages refer to the source document;
physical page numbers are 1-based. All fields are collected in `Command`;
`usage_guidelines` is serialized as `UsageGuidelines`. Mark uncertain extraction
results in `warnings`. Shared completeness and syntax checks from `model.validate`
run for every profile.

`read_page` also runs in child processes; the other methods run sequentially in
the main process. The class must be in an importable module, and its instance
must be picklable. Do not store an open `pymupdf.Document` in the instance.
External class names are supplied explicitly by the user; the JSON corpus does
not load profile code.

## Scaling limits

Memory used for page extraction is bounded by batches of `workers * 4`; processes
use independent PDF documents. Completed command objects and the report are still
collected in memory, so this is not a fully streaming corpus parser. For very
large collections, process individual chapters with `--section` and export them
separately. Markdown reads one record at a time, making two passes for the table
of contents and the body.

Inheritance does not eliminate differences between PDFs. Scans without a text
layer require OCR, which may lose argument formatting. For a new vendor, first
check a few real pages with long syntax, continued tables, commands sharing the
same name, and examples; then run a complete parse and review the report.

## Tested extension example

In `tests/test_extensions.py`, `CustomCiscoParser` adds one section alias and
filters a line in `read_page`. The test creates a two-page PDF with unnumbered
bookmarks, checks exact Function/CLIs/ParaDef/Views/Examples/UsageGuidelines values
and Markdown, and runs with `workers=1` and `workers=2`.
This checks the subclass interface; it does not replace testing on a real Cisco PDF.

Internal composition and module responsibilities: [code-structure.md](code-structure.md).
