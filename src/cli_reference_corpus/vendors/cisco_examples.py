"""Extract prompted commands and documented input from Cisco example blocks."""
from __future__ import annotations

import re

from ..command_syntax import fixed_prefix, matches_invocation
from ..extractors import parse_examples
from ..pdf import Line


def examples(events, clis, warnings, prompt, title=""):
    snippets, block, caption = [], [], []
    # The inverse syntax can remain intact when the printed affirmative form
    # is malformed. Its documented body still identifies an input command.
    clis = [*clis, *(cli[3:] for cli in clis if cli.startswith("no "))]
    prefixes = [fixed_prefix(cli) for cli in clis]
    if title:
        prefixes.append(re.sub(r"\s*\([^)]*\)$", "", title))

    def documented(text):
        return any(text == prefix or text.startswith(prefix + " ") for prefix in prefixes if prefix)

    def flush():
        if not block:
            return
        prompted = parse_examples(block, warnings, prompt=prompt, caption_prefix="!")
        if prompted:
            snippets.extend(prompted)
        else:
            # Learn boot-loader prompt names from a documented invocation, so
            # output labels such as "version_suffix:" are not treated as input.
            colon_lines = [(line.text.strip(), re.match(r"^([\w.-]+):\s*(.+)$", line.text.strip()))
                           for line in block]
            hosts = {match[1] for _, match in colon_lines if match and documented(match[2])}
            if hosts:
                snippets.append([text for text, match in colon_lines if match and match[1] in hosts])
                block.clear()
                return
            commands = [line.text.strip() for line in block
                        if not line.text.strip().startswith("!") and re.search(r"\w", line.text)]
            matched = [text for text in commands
                       if documented(text) or matches_invocation(text, clis)]
            context = " ".join(caption)
            configuration = (any(line.text.strip() == "!" for line in block)
                             or bool(re.search(r"\bconfigur\w*\b", context, re.I))
                             and not re.search(r"\boutput\b", context, re.I))
            if matched:
                # Cisco configuration listings use ! separators. Require a
                # documented command in the block before retaining the listing.
                # Otherwise keep only matching input, never arbitrary output.
                snippets.append(commands if configuration else matched)
        block.clear()

    for event in events:
        mono = isinstance(event, Line) and all(
            span["flags"] & 8 or "Courier" in span["font"] or "Mono" in span["font"]
            for span in event.spans if span["text"].strip()
        )
        if isinstance(event, Line) and (mono or prompt.match(event.text.strip())):
            block.append(event)
        else:
            had_block = bool(block)
            flush()
            if had_block:
                caption.clear()
            if isinstance(event, Line):
                caption.append(event.text)
    flush()
    return snippets
