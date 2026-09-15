"""Reusable field extractors; vendor conventions are explicit arguments."""
from __future__ import annotations

import re
from .model import Parameter
from .pdf import Line, Table, template, unwrap

def paragraphs(events: list[Line | Table]) -> str:
    parts: list[str] = []
    previous: Line | None = None
    for event in events:
        if isinstance(event, Table):
            parts.append("\n" + "\n".join(" | ".join(unwrap(x or "") for x in row) for row in event.rows) + "\n")
            previous = None
            continue
        separator = " "
        if previous is None or (event.page == previous.page and event.bbox[1] - previous.bbox[3] > 4):
            separator = "\n"
        if previous and previous.text.rstrip().endswith("-"):
            separator = ""
        parts.extend([separator, event.text.strip()])
        previous = event
    return "".join(parts).strip()


def parse_formats(events: list[Line | Table], warnings: list[str], *,
                  keyword_span=None, condition_prefixes=(), inverse_keywords=()) -> list[str]:
    groups: list[list[Line]] = []
    in_note = False
    force_new = False
    for event in events:
        if isinstance(event, Table):
            warnings.append("table_in_format: review manually")
            continue
        if event.text.strip().startswith(condition_prefixes) or in_note:
            in_note = not event.text.strip().endswith(":")
            force_new = True
            warnings.append("conditional_format: applicability retained in ExtraInfo")
            continue
        if not groups:
            groups.append([event])
            force_new = False
            continue
        prev = groups[-1][-1]
        # Wrapped lines have normal leading; independent templates have paragraph spacing.
        new = force_new or (event.page == prev.page and event.bbox[1] - prev.bbox[3] > 4)
        if event.page != prev.page and not force_new:
            # Page breaks erase paragraph spacing. A repeated initial keyword is evidence
            # of a new template; otherwise preserve a continuation and report it.
            first = groups[-1][0].text.strip().split()[0]
            new = event.bold and event.text.strip().split()[0] in {first, *inverse_keywords}
            if not new:
                warnings.append("format_crosses_page: check template boundary")
        force_new = False
        if new:
            groups.append([event])
        else:
            groups[-1].append(event)
    for group in groups:
        if not any(line.bold for line in group):
            warnings.append("format_without_bold_keywords: typography may be lost")
    return list(dict.fromkeys(template(group, keyword_span=keyword_span) for group in groups if group))


def parse_parameters(events: list[Line | Table], warnings: list[str]) -> list[Parameter]:
    result: list[Parameter] = []
    for event in events:
        if isinstance(event, Line):
            if event.text.strip().lower() not in {"none", "none.", "-"}:
                warnings.append("unparsed_parameter_text: " + event.text.strip())
            continue
        for row in event.rows:
            cells = [unwrap(x or "") for x in row]
            if not any(cells):
                continue
            if cells[0].lower() in {"parameter", "parameters"} and any(x.lower() in {"description", "value"} for x in cells[1:]):
                continue
            if len(cells) < 2:
                warnings.append("unrecognized_parameter_table")
                continue
            name, info = cells[0], "\n".join(x for x in cells[1:] if x)
            if not name:
                if result:
                    result[-1].info += "\n" + info
                else:
                    warnings.append("orphan_parameter_continuation: " + info)
            elif result and result[-1].name == name and event.page > 1:
                result[-1].info += "\n" + info
            else:
                result.append(Parameter(name, info))
    return result


def parse_examples(events: list[Line | Table], warnings: list[str], *, prompt, caption_prefix="#") -> list[list[str]]:
    snippets: list[list[str]] = []
    snippet: list[str] = []
    previous: Line | None = None
    for event in events:
        if isinstance(event, Table):
            previous = None
            continue
        text = event.text.strip()
        if text.startswith(caption_prefix) if caption_prefix else False:
            if snippet:
                snippets.append(snippet)
                snippet = []
            previous = None
        elif prompt.match(text):
            snippet.append(text)
            previous = event
        elif previous is not None and snippet:
            # Only an indented monospace physical continuation can join a CLI.
            mono = all("Mono" in s["font"] or "Courier" in s["font"] or s["flags"] & 8 for s in event.spans)
            if mono and event.bbox[0] > previous.bbox[0] + 5 and event.page == previous.page and event.bbox[1] - previous.bbox[3] < 4:
                snippet[-1] += ("" if snippet[-1].endswith("-") else " ") + text
                warnings.append("wrapped_example: check command continuation")
                previous = event
            else:
                previous = None  # command output, prose, or an interactive response
    if snippet:
        snippets.append(snippet)
    return snippets

