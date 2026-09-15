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

References come from two sources:

- Explicit `Related Commands`, `Related Topics`, `Related Information`, and
  `See Also` sections. Tables and plain lists retain their descriptions, including
  unresolved references to commands outside the selected manual.
- Named-command phrases in Function, Usage Guidelines and parameter descriptions,
  such as `run the esi dynamic-name command`. These are included when the named
  command matches an outline title or its alias without a trailing view qualifier.
  Casual mentions, chapter-title aliases and references to the current command are not added by this rule.

Numbered Huawei lists are split into individual topics, retaining each printed
section ID as a direct reference, including targets outside a partial corpus.
Repeated references are combined per title and source section. If a name matches
several view-specific entries, all matching section IDs are retained. A reference
with syntax arguments may remain unresolved; the parser does not guess its target.
Section IDs refer to the source outline and may be outside a partial parse result.

For NE40E `1.9663 esi dynamic`, the corpus now contains:

```json
"related_topics": [
  {
    "title": "esi dynamic-name",
    "description": "run the esi dynamic-name command\nusing the esi dynamic-name command",
    "source_section": "Usage Guidelines",
    "target_sections": ["1.9664"]
  },
  {
    "title": "evpn redundancy-mode",
    "description": "run the evpn redundancy-mode command",
    "source_section": "Usage Guidelines",
    "target_sections": ["1.9687"]
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

## Current corpora

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
