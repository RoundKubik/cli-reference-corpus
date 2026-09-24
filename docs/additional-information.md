# Additional information and related topics

Parser 0.3.0 writes schema version 3. Both JSON formats preserve `ExtraInfo` and
`related_topics`, and each command's Markdown renders these fields in English.
Older JSON without the new field can still be read; it has no related topics.

## ExtraInfo

Recognized sections that are not mapped to primary command fields are retained
with their headings. These include Huawei `Default Level` and `Task Name and
Operations`, and Cisco `Defaults`, `History`, and `Related Commands`. Related
section text is retained even when no target can be resolved.

`Examples (source text)` preserves the complete extracted example section, including
captions, prose, device output, interactive replies and commands without a prompt.
The separate `Examples` array continues to contain the existing extracted CLI
snippets. An empty array no longer means that the entire example section is absent
from the JSON: inspect `ExtraInfo` as well.

Conditional syntax, format tables and unparsed parameter text are also retained
when the corresponding extraction warning occurs. Additional information uses
a Markdown code block so line breaks, table text and device prompts stay visible.
This preserves the PDF text layer, not images or the original page layout.

## related_topics

Each entry contains:

| Field | Meaning |
| --- | --- |
| `title` | Topic or command name as referenced in the source |
| `description` | Description from the related table/list, or the explicit reference phrase |
| `source_section` | Section containing the reference, such as `Related Commands` or `Usage Guidelines` |
| `target_sections` | Explicit numbered references or matching outline section IDs; empty when unresolved |
| `target_files` | JSON filenames relative to `cmd_corpus`, populated only for targets present in the exported corpus |
| `reference_kind` | `documented_reference`, `example_command`, or inferred `parameter_topic` |

References come from these sources:

- Explicit `Related Commands`, `Related Topics`, `Related Information`, and
  `See Also` sections. Tables and plain lists retain their descriptions, including
  unresolved references to commands outside the selected manual.
- Named-command phrases in Function, Usage Guidelines, parameter descriptions and
  ExtraInfo (including retained example prose), such as `run the esi dynamic-name
  command`, `use display ip routing-table`, `see also peer`, quoted command names,
  and lists such as `the peer and reset bgp commands`. Matching ignores case and
  PDF line wrapping, uses complete names, and prefers the longest matching title.
  Names must match an outline title or its alias without a trailing view qualifier.
  Casual mentions, chapter-title aliases and references to the current command are not added by this rule.
- Commands actually executed in Examples. Matching starts after the device prompt
  and checks the documented CLI template when available. It does not treat a
  keyword inside a longer invocation as a separate command.
- Topics mentioned in parameter names/descriptions, even without an explicit
  command reference. Candidate vocabulary comes from the current manual's titles,
  syntax and descriptions. There is no device-, entity- or parameter-name dictionary.
  Topic phrases, their occurrence across the command's parameters, TF-IDF text
  similarity, documented views and outline/page locations select a relevant page.
  Configuration scope is learned from documented inverse syntax pairs and their
  most common view (at least three pages). Inferred targets must belong to that
  general scope or share the source command's view; small excerpts omit this filter.
  Each inferred entry is marked `parameter_topic` and retains the source parameter.
  These are relevance candidates, not verified configuration dependencies.

Numbered Huawei lists are split into individual topics, retaining each printed
section ID as a direct reference, including targets outside a partial corpus.
Repeated references are combined per title and source section. If a name matches
several view-specific entries, all matching section IDs are retained. A reference
with syntax arguments may remain unresolved. A bounded phrase ending in `command`
is resolved as a whole; a unique multiword abbreviation may resolve its complete
documented name. An unknown longer name never falls back to its first/last known
word. In particular, `port trunk allow-pass` must not produce references to `port`.
CLI arguments are checked against the available templates. Homonyms use documented
view context or a matching unqualified title when possible; otherwise ambiguity is
retained for explicit references. Parameter-topic inference does not force an
arbitrary selection when candidates have equal support.
Section IDs refer to the source outline and may be outside a partial parse result.
File names are resolved at export time from the commands actually being written;
targets outside a partial export have no file name. Multiple view-specific targets
retain all matching file names. These are plain strings, not clickable links.
Older JSON without `target_files` is still readable; both schemas accept the
additional field without requiring it in legacy records.

`enrich-related CORPUS -o NEW_DIRECTORY` runs the same reference extraction on
existing JSON using the manifest's command titles and section IDs as the index.
It requires no PDF and supports both repository and paper records. It preserves
original command content, source metadata, warnings and explicit references outside
the corpus, writes new JSON/Markdown pairs, and updates related-topic counts in
`validation.json`. Automatically generated references are rebuilt so old false
positives are removed when the rules change. Repeating enrichment does not duplicate references. Existing
output directories are not overwritten.

## CLI syntax diagnostics

Both schemas accept `syntax_issues`, an array of objects containing `cli_index`
(zero-based), `cli`, `code`, and `message`. The original template is always retained.
Unbalanced groups or syntax unsupported by the matcher become diagnostics; they
do not abort PDF parsing, JSON export or related-topic enrichment. The remaining
templates and commands are still processed. Normal parsing returns success after
export; the existing optional `--strict` exit code is reported only after export.
This validates the extracted template grammar, not parameter ranges or device behavior.
Older records without this field remain readable; diagnostics are recomputed from
their `CLIs` during export/enrichment.

For NE40E `1.9663 esi dynamic`, the corpus now contains:

```json
"related_topics": [
  {
    "title": "esi dynamic-name",
    "description": "run the esi dynamic-name command\nusing the esi dynamic-name command",
    "source_section": "Usage Guidelines",
    "target_sections": ["1.9664"],
    "target_files": ["1.9664_esi_dynamic-name.json"]
  },
  {
    "title": "evpn redundancy-mode",
    "description": "run the evpn redundancy-mode command",
    "source_section": "Usage Guidelines",
    "target_sections": ["1.9687"],
    "target_files": ["1.9687_evpn_redundancy-mode.json"]
  }
]
```

These are references stated in the documentation, not inferred configuration
dependencies. The prepared NE40E PDF has no original HTML link destinations;
this extraction does not reconstruct them or invent URLs. It also does not claim
to capture every possible textual form of a cross-reference.

## Checks

`validation.json` counts records with additional information and related topics.
The independent page census checks for empty extra information or missing
structured related sections when their headings are printed in the PDF.
Schema validation checks the types of the new fields. Regression tests use actual
NE40E pages and Cisco related tables with and without column headers, including
wrapped names and chapter boundaries, as well as unknown targets, homonyms and legacy JSON.

`scripts/audit_related_topics.py CORPUS... -o REPORT.json` compares old and recomputed
targets for every record, checks generated targets and self-references, counts
syntax issues, and retains change samples for review. The regression fixtures also
cover the same VLAN example in CloudEngine, Campus and NE40E, ordinary prose matching
short command names, and an invented topic name to check that inference is learned
from the supplied documentation. Corpus-wide structural checks do not establish
semantic precision/recall for all inferred topics; the audit report states that limit.

## Corpus verification

The CloudEngine corpus was rebuilt from the complete source PDF and refreshed in
its original output directory: 6,672 commands, 29,856 related-topic entries and
39,430 target-file references. Every JSON record passed the repository schema;
every Markdown file matched its JSON, and primary command fields were unchanged.
The `port trunk allow-pass vlan` record includes
`2.4.3.49_vlan_system_view.json`, inferred from the documented parameters, and no
longer links to the unrelated `port` commands.

See [the reference audit](../reports/coverage/related-topics-audit.json) for
recomputed references across all five corpora. That reference refresh replaced CloudEngine output. A subsequent
[extraction correction](../reports/coverage/extraction-warning-review.md) rebuilt
both Cisco corpora and Campus in their original directories.

### Historical baseline

The following counts describe the previously generated corpora, before the expanded
mention recognition and `target_files` enrichment. Run `enrich-related` to produce
an updated copy of an existing corpus.

| Corpus | Records with ExtraInfo | Records with related_topics | Related-topic entries |
| --- | ---: | ---: | ---: |
| `cisco-catalyst9300-iosxe-17.15.x` | 1,343 | 664 | 1,851 |
| `cisco-catalyst9500-iosxe-17.15.x` | 1,321 | 659 | 1,924 |
| `huawei-campus-s1720-s2700-s5700-s6720-v200r011c10` | 5,989 | 4,522 | 11,772 |
| `huawei-cloudengine-9800-8800-6800-v300r024c00` | 6,672 | 3,085 | 5,642 |
| `huawei-ne40e-v800r024c00spc500` | 14,551 | 6,767 | 12,456 |

All 29,876 JSON/Markdown pairs were checked. No primary command fields changed;
17 NE40E titles had only repeated whitespace normalized. The existing Cisco schema
failures remain (23 for Catalyst 9300 and 19 for Catalyst 9500); the added fields
introduce no new schema failures.
