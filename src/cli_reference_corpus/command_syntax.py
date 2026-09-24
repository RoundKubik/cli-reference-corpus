"""Recognize documented CLI invocations, not arbitrary prefixes in prose."""
from __future__ import annotations

from functools import lru_cache
import re


def fixed_prefix(template: str) -> str:
    return re.split(r"[<{\[]", template, maxsplit=1)[0].strip()


def syntax_issues(templates: list[str]) -> list[dict]:
    issues = []
    for index, template in enumerate(templates):
        plain = re.sub(r"&<\d+-\d+>|<[^<>]+>", "PARAM", template)
        stack = []
        unbalanced = False
        for char in plain:
            if char in "[{":
                stack.append(char)
            elif char in "]}":
                if not stack or stack.pop() != {"]": "[", "}": "{"}[char]:
                    unbalanced = True
                    break
        if unbalanced or stack:
            issues.append({"cli_index": index, "cli": template, "code": "unbalanced_syntax",
                           "message": "Unbalanced or mismatched []/{} groups in the extracted template."})
        elif syntax_pattern(template) is None:
            issues.append({"cli_index": index, "cli": template, "code": "unsupported_syntax",
                           "message": "The extracted template cannot be interpreted by this syntax matcher."})
    return issues


@lru_cache(maxsize=32768)
def syntax_pattern(template: str) -> re.Pattern | None:
    tokens = re.findall(r"&<\d+-\d+>|<[^<>]+>|[\[\]{}|]|[^\s\[\]{}|]+", template)
    position = 0

    def group(closing: str | None = None) -> str:
        nonlocal position
        choices, atoms = [], []
        while position < len(tokens):
            token = tokens[position]
            position += 1
            if token in {"}", "]"}:
                if token != closing:
                    raise ValueError("Unbalanced CLI syntax")
                break
            if token == "|":
                choices.append("".join(atoms))
                atoms = []
            elif token in {"[", "{"}:
                atom = group("]" if token == "[" else "}")
                atoms.append(f"(?:{atom})" + ("?" if token == "[" else ""))
            elif match := re.fullmatch(r"&<(\d+)-(\d+)>", token):
                if not atoms or not 0 <= int(match[1]) <= int(match[2]):
                    raise ValueError("Invalid repetition")
                atoms[-1] = f"(?:{atoms[-1]}){{{match[1]},{match[2]}}}"
            else:
                atom = r"\S+" if token.startswith("<") and token.endswith(">") else re.escape(token)
                atoms.append(atom + r"(?:\s+|$)")
        else:
            if closing:
                raise ValueError("Unbalanced CLI syntax")
        choices.append("".join(atoms))
        return "|".join(choices)

    try:
        return re.compile(group(), re.IGNORECASE)
    except (ValueError, OverflowError, re.error, RecursionError):
        return None


def matches_invocation(invocation: str, templates: list[str]) -> bool:
    return any(pattern is not None and pattern.fullmatch(invocation.strip())
               for pattern in (syntax_pattern(template) for template in templates))
