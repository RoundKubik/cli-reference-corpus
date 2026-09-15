"""Resolve explicit source references without inventing dependency relationships."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from .model import Command, RelatedTopic
from .pdf import unwrap


def topic_key(title: str) -> str:
    return unwrap(title).casefold()


def title_aliases(title: str) -> set[str]:
    title = topic_key(title)
    return {title, re.sub(r"\s+\([^)]*\)$", "", title)}


@dataclass(frozen=True)
class RelatedTopicIndex:
    sections: dict[str, list[str]]

    @classmethod
    def from_outline(cls, outline) -> RelatedTopicIndex:
        sections = defaultdict(list)
        for index, heading in enumerate(outline):
            if index + 1 < len(outline) and outline[index + 1].level > heading.level:
                continue  # chapter titles are not command-name aliases
            for alias in title_aliases(heading.title):
                if heading.section not in sections[alias]:
                    sections[alias].append(heading.section)
        return cls(dict(sections))

    def enrich(self, command: Command) -> None:
        command.related_topics = [declared for topic in command.related_topics
                                  for declared in self.declared_topics(topic)]
        own_names = title_aliases(command.title)
        sources = {
            "Function": command.function,
            "Usage Guidelines": command.usage_guidelines,
            "Parameters": "\n".join(parameter.info for parameter in command.parameters),
        }
        for section, text in sources.items():
            for title, evidence in self.named_commands(text):
                key = topic_key(title)
                if key in self.sections and key not in own_names:
                    command.related_topics.append(RelatedTopic(title, evidence, section))
        unique = {}
        for topic in command.related_topics:
            if not topic.target_sections or topic.source_section != "Related Topics":
                topic.target_sections = [section for section in self.sections.get(topic_key(topic.title), [])
                                         if section != command.section]
            key = (topic_key(topic.title), topic.source_section)
            if key not in unique:
                unique[key] = topic
            elif topic.description and topic.description not in unique[key].description:
                unique[key].description += "\n" + topic.description
        command.related_topics = list(unique.values())

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

    @staticmethod
    def named_commands(text: str):
        # Overlapping lookahead lets the nearer "the" win over an earlier article.
        pattern = r"(?=(\b(?:the|run|using|use)\s+(?:the\s+)?((?:(?!\bthe\b|[.!?]\s).){1,160}?)\s+commands?\b))"
        for match in re.finditer(pattern, text, re.IGNORECASE):
            yield unwrap(match[2]), unwrap(match[1])
