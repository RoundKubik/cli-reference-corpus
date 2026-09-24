"""Resolve explicit source references without inventing dependency relationships."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import re

from .model import Command, RelatedTopic
from .pdf import unwrap
from .command_syntax import fixed_prefix, matches_invocation
from .parameter_topics import ParameterTopicIndex

INFERRED_SECTIONS = {"Function", "Usage Guidelines", "Parameters", "ExtraInfo", "Examples"}
PROMPT = re.compile(r"^(?:<[^<>\s]+>|\[[^\[\]\s]+\]|[\w.-]+(?:\([^\n)]*\))?[#>])\s*(.+)$")


def topic_key(title: str) -> str:
    return unwrap(title).casefold()


def title_aliases(title: str) -> set[str]:
    title = topic_key(title)
    return {title, re.sub(r"\s+\([^)]*\)$", "", title)}


@dataclass(frozen=True)
class RelatedTopicIndex:
    sections: dict[str, list[str]]
    commands: dict[str, Command] = field(default_factory=dict, repr=False, compare=False)
    _names: dict = field(init=False, repr=False, compare=False)
    _abbreviations: dict = field(init=False, repr=False, compare=False)
    _parameter_topics: ParameterTopicIndex = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        # A token trie avoids scanning every outline title for every paragraph.
        names = {}
        abbreviations = defaultdict(dict)
        for name in self.sections:
            node = names
            for token in self.tokens(name):
                node = node.setdefault(token[0].casefold(), {})
            node[None] = name
            words = name.split()
            for length in range(2, len(words)):
                for section in self.sections[name]:
                    abbreviations[" ".join(words[:length])].setdefault(section, name)
        object.__setattr__(self, "_names", names)
        object.__setattr__(self, "_abbreviations", {
            prefix: next(iter(targets.values())) for prefix, targets in abbreviations.items() if len(targets) == 1
        })
        object.__setattr__(self, "_parameter_topics", ParameterTopicIndex(self.commands, self.sections))

    @staticmethod
    def tokens(text: str):
        return list(re.finditer(r"\w+(?:[-./:]\w+)*|[^\w\s]", text))

    @classmethod
    def from_commands(cls, commands) -> RelatedTopicIndex:
        sections = defaultdict(list)
        commands = list(commands)
        for command in commands:
            aliases = title_aliases(command.title)
            aliases.update(topic_key(fixed_prefix(cli)) for cli in command.clis if fixed_prefix(cli))
            for alias in sorted(aliases):
                if command.section and command.section not in sections[alias]:
                    sections[alias].append(command.section)
        return cls(dict(sections), {command.section: command for command in commands})

    @classmethod
    def from_outline(cls, outline, commands=()) -> RelatedTopicIndex:
        sections = defaultdict(list)
        for index, heading in enumerate(outline):
            if index + 1 < len(outline) and outline[index + 1].level > heading.level:
                continue  # chapter titles are not command-name aliases
            for alias in sorted(title_aliases(heading.title)):
                if heading.section not in sections[alias]:
                    sections[alias].append(heading.section)
        parsed = cls.from_commands(commands)
        for alias, targets in parsed.sections.items():
            for section in targets:
                if section not in sections[alias]:
                    sections[alias].append(section)
        return cls(dict(sections), parsed.commands)

    def enrich(self, command: Command) -> None:
        # Recompute generated references, so corrected matching rules remove old
        # false positives instead of preserving them forever on re-enrichment.
        command.related_topics = [declared for topic in command.related_topics
                                  if topic.source_section not in INFERRED_SECTIONS
                                  for declared in self.declared_topics(topic)]
        own_names = title_aliases(command.title)
        own_names.update(topic_key(fixed_prefix(cli)) for cli in command.clis if fixed_prefix(cli))
        sources = {
            "Function": command.function,
            "Usage Guidelines": command.usage_guidelines,
            "Parameters": "\n".join(parameter.info for parameter in command.parameters),
            "ExtraInfo": command.extra,
        }
        for section, text in sources.items():
            for title, evidence, targets in self.named_commands(text):
                key = topic_key(title)
                targets = self.context_targets(title, targets, command)
                targets = [target for target in targets if target != command.section]
                if targets and key not in own_names:
                    command.related_topics.append(RelatedTopic(title, evidence, section, targets))
        for snippet in command.examples:
            for line in snippet:
                prompt = PROMPT.match(line.strip())
                if prompt:
                    resolved = self.resolve_reference(unwrap(prompt[1]), invocation=True)
                    if resolved:
                        title, targets = resolved
                        targets = self.context_targets(title, targets, command)
                        targets = [target for target in targets if target != command.section]
                        if targets and topic_key(title) not in own_names:
                            command.related_topics.append(RelatedTopic(
                                title, line, "Examples", targets, reference_kind="example_command"))
        command.related_topics.extend(self._parameter_topics.topics(command))
        unique = {}
        for topic in command.related_topics:
            if not topic.target_sections:
                topic.target_sections = [section for section in self.sections.get(topic_key(topic.title), [])
                                         if section != command.section]
            key = (topic_key(topic.title), topic.source_section, topic.reference_kind)
            if key not in unique:
                unique[key] = topic
            else:
                existing = unique[key]
                existing.target_sections = list(dict.fromkeys(existing.target_sections + topic.target_sections))
                existing.target_files = list(dict.fromkeys(existing.target_files + topic.target_files))
                if topic.description and topic.description not in existing.description:
                    existing.description = "\n".join(filter(None, [existing.description, topic.description]))
        command.related_topics = list(unique.values())

    def context_targets(self, title: str, targets: list[str], source: Command) -> list[str]:
        if len(targets) <= 1:
            return targets
        views = {topic_key(view) for view in source.views}
        same_view = [section for section in targets if section in self.commands
                     and views & {topic_key(view) for view in self.commands[section].views}]
        if same_view:
            return same_view
        exact_title = [section for section in targets if section in self.commands
                       and topic_key(self.commands[section].title) == topic_key(title)]
        return exact_title or targets

    @staticmethod
    def declared_topics(topic: RelatedTopic) -> list[RelatedTopic]:
        # Huawei numbered lists may have ordinary line leading and wrapped names.
        # A printed section ID is a direct reference, even outside a partial corpus.
        if not re.match(r"^\d+(?:\.\d+)+\s+", topic.title):
            return [topic]
        starts = list(re.finditer(r"(?:^|\s)(\d+(?:\.\d+)+)\s+", topic.title))
        topics = []
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(topic.title)
            title = topic.title[match.end():end].strip()
            if title:
                topics.append(RelatedTopic(title, topic.description, topic.source_section, [match[1]]))
        return topics

    def named_commands(self, text: str):
        text = unwrap(text)
        phrases = []
        handled = set()
        pattern = r"(?=(\b(?:the|run|using|use)\s+(?:the\s+)?((?:(?!\bthe\b|[.!?]\s).){1,160}?)\s+commands?\b))"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            phrases.append(match.span(2))
            if match.span(2) in handled:
                continue
            handled.add(match.span(2))
            resolved = self.resolve_reference(match[2], abbreviations=True)
            if resolved:
                yield resolved[0], match[1], resolved[1]
            else:
                parts = re.split(r"\s*,\s*(?:(?:and|or)\s+)?|\s+(?:and|or)\s+", match[2], flags=re.IGNORECASE)
                resolved_parts = [self.resolve_reference(part, abbreviations=True) for part in parts]
                if len(parts) > 1 and all(resolved_parts):
                    for title, targets in resolved_parts:
                        yield title, match[1], targets

        candidates = list(self.mentions(text))
        # Adjacent names in a list share the explicit command cue.
        groups = []
        for candidate in candidates:
            if groups and re.fullmatch(r"\s*(?:,\s*(?:(?:and|or)\s+)?|(?:and|or)\s+)",
                                       text[groups[-1][-1][1]:candidate[0]], re.IGNORECASE):
                groups[-1].append(candidate)
            else:
                groups.append([candidate])
        for group in groups:
            start, end = group[0][0], group[-1][1]
            # A bounded command phrase is resolved as a whole, never by taking
            # its first or last known word when the complete name is unknown.
            if any(left <= start and end <= right for left, right in phrases):
                continue
            prefix = re.search(r"\b(?:run|execute|use|using|see(?: also)?|refer to)\s+(?:the\s+)?"
                               r"(?:(?:undo|no)\s+)?$", text[:start], re.IGNORECASE)
            suffix = re.match(r"\s+commands?\b", text[end:], re.IGNORECASE)
            quoted = (len(group) == 1 and start > 0 and end < len(text)
                      and (text[start - 1], text[end]) in {
                          ("`", "`"), ('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"),
                      })
            if not (prefix or suffix or quoted):
                continue
            if prefix and not (suffix or quoted):
                # Bare invocations need a clear end. A following unknown keyword
                # is not evidence for the shorter command ("run more than ...").
                tail = text[end:]
                if tail and not re.match(r"\s*(?:[.,;:!?]|$)|\s+(?:to|before|after)\b|\s+<[^<>]+>", tail):
                    continue
            evidence = text[prefix.start() if prefix else start:end + (suffix.end() if suffix else 0)]
            for begin, finish in group:
                title = text[begin:finish]
                yield title, evidence, self.sections[topic_key(title)]

    def resolve_reference(self, phrase: str, *, abbreviations: bool = False, invocation: bool = False):
        name = topic_key(phrase)
        if name in self.sections:
            targets = self.sections[name]
            if invocation:
                targets = [section for section in targets if section not in self.commands
                           or matches_invocation(name, self.commands[section].clis)]
            return (name, targets) if targets else None
        base = re.sub(r"^(?:undo|no|default)\s+", "", name)
        if base in self.sections:
            return base, self.sections[base]
        if abbreviations and name in self._abbreviations:
            full = self._abbreviations[name]
            return full, self.sections[full]
        if not invocation and not re.search(r"<[^<>]+>|\b\d", name):
            # Ordinary words in an unknown command name must not be consumed
            # as arbitrary argument values of a shorter command's template.
            return None
        # Argument-bearing references must match a documented CLI template.
        # Example commands are also matched only at the start, never at a word
        # inside the invocation (e.g. VLAN in "port trunk allow-pass vlan 10").
        match = next(self.mentions(name), None)
        if match and match[0] == 0:
            alias = name[:match[1]]
            targets = []
            for section in self.sections[alias]:
                command = self.commands.get(section)
                if command and matches_invocation(name, command.clis):
                    targets.append(section)
                elif invocation and command is None and re.fullmatch(r"(?:\s+(?:\d[\w./:-]*|<[^<>]+>))*", name[match[1]:]):
                    targets.append(section)
            if targets:
                return alias, targets
        return None

    def mentions(self, text: str):
        """Match complete names, preferring the longest name at each position."""
        tokens = self.tokens(text)
        position = 0
        while position < len(tokens):
            node = self._names
            best = None
            for end in range(position, len(tokens)):
                node = node.get(tokens[end][0].casefold())
                if node is None:
                    break
                if None in node:
                    start_char, end_char = tokens[position].start(), tokens[end].end()
                    if topic_key(text[start_char:end_char]) == node[None]:
                        best = end, start_char, end_char
            if best is None:
                position += 1
            else:
                end, start_char, end_char = best
                yield start_char, end_char
                position = end + 1
