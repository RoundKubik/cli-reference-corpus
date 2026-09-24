# Extraction warning review

Review date: 2026-09-24. This closes the three open review/correction items in
[TASKS.md](../../TASKS.md). The review inventories all retained diagnostics,
examines source samples for every diagnostic category, and checks every Cisco
record with a missing primary field. It does not certify every parameter or
syntax token, or validate commands on devices.

The machine-readable [warning inventory and source evidence](extraction-warning-review.json)
includes counts, filenames, physical page ranges, source text, and extracted
fields. The [pair/schema verification](corpus-verification.json) and refreshed
page censuses cover the resulting corpora.

## Corrected extraction behavior

- Cisco prompts without hostnames, such as `(config-if)#` and `#`, are accepted.
  Routed processor prompts such as `RP/0/RP0/CPU0:router(config)#` are also accepted.
- Boot-loader prompt names are learned from documented invocations in an example
  block. This recovers `Device: arp ...` without treating unrelated output labels
  such as `version_suffix:` as commands.
- Promptless input is recognized from the command's documented title and syntax,
  including inverse syntax. Configuration listings identified by their captions
  or `!` separators retain surrounding configuration commands. Other blocks retain
  only recognized input; output remains in `ExtraInfo`.
- Cisco fragments on the same visual line are ordered by individual span positions.
  On Catalyst 9300 physical page 570, `ip nat inside source` now has eight templates
  in the printed order. `Dynamic NAT`, `Static NAT`, `Port Static NAT`, and
  `Network Static NAT` are retained as captions in `ExtraInfo`.
- Small Note labels no longer start a syntax block. Five Catalyst 9500 function
  paragraphs have been recovered. Release/model captions also remain outside CLI
  templates, and `no-match` starts a separate template.
- Huawei examples accept empty `<>` and `[]` prompts followed by command text.
  Output legends such as `[] : indicates the upper ECN threshold` are excluded.
- Valid repetition such as the NE40E `&<1-4094>` syntax is no longer rejected by
  an artificial matcher limit. Unsupported or malformed templates still produce
  diagnostics without stopping export.

These rules use PDF layout and documentation content. They do not substitute a
manually written command or a parameter-to-document lookup table.

## All 42 Cisco schema failures reviewed

The same 23 Catalyst 9300 and 19 Catalyst 9500 records still fail the strict
schema. Their causes are in the source; retaining warnings preserves that fact.
No missing template or mode was invented to make schema validation pass.

| Source condition | Catalyst 9300 | Catalyst 9500 | Treatment |
| --- | ---: | ---: | --- |
| No standalone syntax block | 8 | 8 | Keep `CLIs` empty and `missing_format` |
| Mode text printed under `Command Default` | 11 | 10 | Preserve in `ExtraInfo`; retain `missing_views` |
| No labelled mode section | 4 | 1 | Retain `missing_views` |
| Total records failing the schema | 23 | 19 | Export normally with diagnostics |

The eight missing syntax records per corpus include `ip igmp snooping vlan mrouter`,
`show loopdetect`, `collect counter`, `match transport`, both `show flow monitor`
entries, and `debug ilpower powerman`. The remaining entry is `show switch` on
9300 and `show processes memory platform` on 9500. Mentions in prose and examples
do not provide a complete syntax specification.

The mislabeled modes occur in `auto qos voip`, `show bootflash:`, five licensing
commands, and three `show tech-support` variants in both corpora; 9300 also has
`power inline`. Source labels and their text are retained literally. The missing
mode sections are `show platform software fed switch active sgacl port` in both
corpora, plus `switch priority` and both `switch renumber` entries on 9300.

Each corpus also has one `missing_function` record: `show platform software fed
switch active ifm mappings` starts directly with syntax in the source. The schema
permits empty function text. The five other missing function cases on 9500 were
parser errors caused by preamble notes and have been corrected.

## Empty examples after correction

| Corpus | Previously empty despite an example heading | Now empty | Source review |
| --- | ---: | ---: | --- |
| Catalyst 9300 | 281 | 6 | Five captions without command text; one log-only example |
| Catalyst 9500 | 120 | 4 | Three captions without command text; one log-only example |
| Campus | 3 | 1 | Explicit `Example: None` |

The remaining Cisco caption-only cases are `monitor capture export`,
`auto qos classify`, and `version`, plus both `switch renumber` entries on 9300.
Their source example sections contain prose but no command block. The
`device-tracking logging` examples contain event log output, which is preserved
in `ExtraInfo` and is not executable input.

Campus `port media type` explicitly prints `Example: None` on physical page 1595;
its empty array is correct. `display snmp-agent trap feature-name cfgmgr all`
(pages 9589–9590) and `snmp-agent trap enable feature-name cfgmgr` (pages 9594–9595)
now contain the documented commands with empty device prompts.

The separate NE40E `dcn security-mode enable` example is `default.cfg` content
without a prompt. Its previously reviewed source-text preservation in `ExtraInfo`
remains unchanged.

## Other warning categories

| Diagnostic | Review finding and disposition |
| --- | --- |
| `conditional_format` | Documented model/release conditions; preserve applicability text and retain the warning. |
| `format_crosses_page` | Page breaks obscure template boundaries; sampled continuations exist in the PDF. Keep the diagnostic rather than split on page boundaries. |
| `format_without_bold_keywords` | Source typography varies, including ordinary-font Cisco keywords and Campus blocks. Retain the warning; font evidence alone does not prove a malformed command. |
| `unparsed_parameter_text` | Includes borderless/continued tables, notes, and no-parameter prose variants. Text remains in `ExtraInfo`; structured parameter coverage is still limited. |
| `undocumented_parameter` | Exact names may differ because of wrapping, source spelling, incomplete tables, or font classification. This warning does not establish that the source omits the parameter. |
| `unbalanced_syntax` | Printed defects and extraction ambiguity remain. Keep the extracted template and `syntax_issues`; do not repair brackets by guessing. |
| `wrapped_example` | Physical continuations were joined; the warning retains that uncertainty. |
| `table_in_format` | Campus `display ospf brief` has tabular material in the collected Format section. Preserve the source text for review. |

All categories remain visible in `validation.json` and command Markdown. This
review closes the inventory and diagnosis task; it does not claim those broader
extraction limitations have all been eliminated.

## Reproduction

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_corpora.py
.venv/bin/python scripts/review_extraction_warnings.py
.venv/bin/python scripts/audit_coverage.py --corpus cisco-catalyst9300-iosxe-17.15.x
.venv/bin/python scripts/audit_coverage.py --corpus cisco-catalyst9500-iosxe-17.15.x
.venv/bin/python scripts/audit_coverage.py --corpus huawei-campus-s1720-s2700-s5700-s6720-v200r011c10
```

The saved before/after counts use the pre-correction corpus snapshots. A future
run without `--before` inventories the current corpus on both sides. The
verification script fails on broken pairs, hashes, or reference filenames; known
source-related schema failures are recorded separately in its report.
