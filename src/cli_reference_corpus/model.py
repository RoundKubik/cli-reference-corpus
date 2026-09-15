"""NAssim's published corpus and paper-schema serialization and checks."""
from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass
class Parameter:
    name: str
    info: str


@dataclass
class RelatedTopic:
    title: str
    description: str = ""
    source_section: str = ""
    target_sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title, "description": self.description,
            "source_section": self.source_section, "target_sections": self.target_sections,
        }


@dataclass
class Command:
    title: str
    section: str
    start_page: int
    end_page: int
    clis: list[str] = field(default_factory=list)
    function: str = ""
    views: list[str] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    examples: list[list[str]] = field(default_factory=list)
    extra: str = ""
    warnings: list[str] = field(default_factory=list)
    usage_guidelines: str = ""
    related_topics: list[RelatedTopic] = field(default_factory=list)

    def to_dict(self, schema: str = "repository") -> dict:
        if schema not in {"repository", "paper"}:
            raise ValueError(f"Unknown schema: {schema}")
        view_key = "ParentView" if schema == "repository" else "ParentViews"
        parameter_key = "Parameters" if schema == "repository" else "Paras"
        data = {
            "CLIs": self.clis,
            "FuncDef": self.function,
            view_key: self.views,
            "ParaDef": [{parameter_key: p.name, "Info": p.info} for p in self.parameters],
            "Examples": self.examples,
            "UsageGuidelines": self.usage_guidelines,
            "ExtraInfo": self.extra,
            "related_topics": [topic.to_dict() for topic in self.related_topics],
        }
        if schema == "repository":
            data = {"PageTitle": self.title, **data}
        return data


    @classmethod
    def from_dict(cls, data: dict, *, title: str = "", section: str = "",
                  start_page: int = 0, end_page: int = 0) -> Command:
        """Read either NAssim schema, including v1 records without UsageGuidelines.

        Legacy ExtraInfo is preserved verbatim: third-party corpora do not guarantee
        that it contains usage text. Only the explicit migration of our v0.1 export
        may move that text into UsageGuidelines.
        """
        if not isinstance(data, dict):
            raise ValueError("Command must be a JSON object")
        repo = "ParentView" in data
        view_key, parameter_key = ("ParentView", "Parameters") if repo else ("ParentViews", "Paras")
        if "ParentView" in data and "ParentViews" in data:
            raise ValueError("Ambiguous command: both ParentView and ParentViews")
        fields = CommandFields(data)
        clis = fields.strings(data.get("CLIs"), "CLIs")
        views = fields.strings(data.get(view_key), view_key)
        parameters = fields.parameters(parameter_key)
        examples = data.get("Examples")
        if not isinstance(examples, list):
            raise ValueError("Examples must be an array of snippets")
        return cls(
            title=fields.string("PageTitle", title or (clis[0] if clis else "Command")),
            section=section,
            start_page=start_page,
            end_page=end_page,
            clis=clis,
            function=fields.string("FuncDef"),
            views=views,
            parameters=parameters,
            examples=[fields.strings(snippet, "Examples snippet") for snippet in examples],
            extra=fields.string("ExtraInfo", ""),
            usage_guidelines=fields.string("UsageGuidelines", ""),
            related_topics=fields.related_topics(),
        )


@dataclass(frozen=True)
class CommandFields:
    """Read the typed fields of a command without changing its original JSON."""
    data: dict

    def string(self, key: str, default=None) -> str:
        value = self.data.get(key, default)
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        return value

    def strings(self, value, key: str) -> list[str]:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"{key} must be an array of strings")
        return list(value)

    def parameters(self, name_key: str) -> list[Parameter]:
        rows = self.data.get("ParaDef")
        if not isinstance(rows, list):
            raise ValueError("ParaDef must be an array")
        parameters = []
        for row in rows:
            if not self.is_parameter(row, name_key):
                raise ValueError(f"ParaDef entries require string {name_key} and Info")
            parameters.append(Parameter(row[name_key], row["Info"]))
        return parameters

    def related_topics(self) -> list[RelatedTopic]:
        rows = self.data.get("related_topics", [])
        if not isinstance(rows, list):
            raise ValueError("related_topics must be an array")
        topics = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("related_topics entries must be objects")
            fields = CommandFields(row)
            topics.append(RelatedTopic(
                fields.string("title"), fields.string("description", ""),
                fields.string("source_section", ""),
                fields.strings(row.get("target_sections", []), "target_sections"),
            ))
        return topics

    def is_parameter(self, row, name_key: str) -> bool:
        return (
            isinstance(row, dict)
            and isinstance(row.get(name_key), str)
            and isinstance(row.get("Info"), str)
        )


def validate(command: Command) -> list[str]:
    """Check extraction completeness and obvious template defects, not device behavior."""
    problems = list(command.warnings)
    if not command.title:
        problems.append("missing_title")
    if not command.clis:
        problems.append("missing_format")
    if not command.function:
        problems.append("missing_function")
    if not command.views:
        problems.append("missing_views")
    documented = " ".join(p.name for p in command.parameters)
    for cli in command.clis:
        # Remove placeholders and Huawei repetition notation before checking grouping.
        plain = re.sub(r"&<\d+-\d+>|<[^<>]+>", "PARAM", cli)
        stack = []
        for char in plain:
            if char in "[{":
                stack.append(char)
            elif char in "]}":
                if not stack or stack.pop() != {"]": "[", "}": "{"}[char]:
                    problems.append(f"unbalanced_syntax: {cli}")
                    break
        else:
            if stack:
                problems.append(f"unbalanced_syntax: {cli}")
        for name in re.findall(r"(?<!&)<([^<>]+)>", cli):
            if not re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", documented):
                problems.append(f"undocumented_parameter: {name}")
    return list(dict.fromkeys(problems))
