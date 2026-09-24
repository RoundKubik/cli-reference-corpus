# Tasks

- [x] Extensible PDF parser with Huawei and Cisco profiles.
- [x] `UsageGuidelines` in the model, both JSON schemas, and Markdown.
- [x] Five input Command Reference PDFs: CloudEngine, NE40E, Campus, and Cisco Catalyst 9300 and 9500.
- [x] Remove Upgrade-compatible from the input data and output corpora.
- [x] Automatically export a separate JSON + Markdown pair for each command.
- [x] Remove combined manual Markdown files from output.
- [x] Verify pairs, PDF checksums, and JSON Schema compliance; record the results in the README and corpus reports.
- [x] Review extraction warnings, including 23 incomplete Catalyst 9300 records and 19 Catalyst 9500 records.

NE40E has been replaced with the complete standard Command Reference
V800R024C00SPC500 from the official Huawei package. The PDF includes 14,833 topics;
the CHM table of contents and the printed descriptions of 14,551 commands were
independently checked. The provenance map is stored in reports/sources.
Warning categories and missing primary fields have been reviewed; the corpora have not been validated on hardware.

- [x] Independently compare the printed command descriptions in all PDFs with the corpora.
- [x] Fix missing Cisco examples without a hostname / prompt and the ordering of syntax fragments (`ip nat inside source`); see reports/coverage/README.md.

- [x] Replace NE40E Diagnose with the complete standard Command Reference and verify CHM → PDF → corpus consistency.
- [x] Preserve complete titles from the prepared PDF's bookmarks without spaces introduced by line wrapping.
- [x] Preserve the original default.cfg example without a prompt for NE40E `dcn security-mode enable` in ExtraInfo; the CLI Examples array remains empty.

- [x] Add Campus Switch S1720/S2700/S5700/S6720 V200R011C10: the fourth PDF and a separate corpus of 5,989 pairs.
- [x] Exclude the Upgrade-compatible chapter from the Campus PDF and corpus; compare the retained pages with the original.
- [x] Handle Command Support bookmarks, MLD table 8.2.1, and wrapped titles in the campus-switch profile.

- [x] Review the three empty Campus Examples arrays where the PDF has an Example section; see reports/coverage/huawei-campus-s1720-s2700-s5700-s6720-v200r011c10.json.

- [x] Add the complete Cisco Catalyst 9500 IOS XE 17.15.x Command Reference: 1,321 JSON + Markdown pairs.
- [x] Include models and versions in all corpus and PDF names; update paths and the audit.

- [x] Preserve Default Level, Task Name and Operations, and other additional sections in ExtraInfo.
- [x] Preserve the complete Examples text, including captions and output, in ExtraInfo; the CLI Examples array remains a separate representation.
- [x] Add related_topics from explicit related sections and named command mentions; rebuild all five corpora using schema v3.

Review and correction results (2026-09-24): [extraction warning review](reports/coverage/extraction-warning-review.md).
Source omissions and the documented extraction limitations remain visible as warnings.
