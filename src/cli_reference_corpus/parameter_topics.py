"""Find parameter topics using only the current manual's vocabulary and metadata."""
from __future__ import annotations

from collections import Counter, defaultdict
import math
import re

from .model import Command, RelatedTopic


def words(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[^\W_]+", text.casefold()))


def contains(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    return any(tokens[start:start + len(phrase)] == phrase for start in range(len(tokens) - len(phrase) + 1))


class ParameterTopicIndex:
    """Document-derived topic anchors, with no device/entity/parameter-name map.

    An anchor must be a complete documented command name and occur in a
    parameter's name or description. Corpus frequency suppresses generic words.
    Rank candidates by similarity of their documented descriptions, with view
    prevalence and outline proximity breaking ties between homonyms.
    """

    def __init__(self, commands: dict[str, Command], aliases: dict[str, list[str]]):
        self.commands = commands
        self.frequency = Counter()
        self.views = Counter(view.casefold() for command in commands.values() for view in set(command.views))
        configuration_views = Counter()
        for command in commands.values():
            templates = {" ".join(cli.casefold().split()) for cli in command.clis}
            # Learn configuration scope from documented inverse template pairs.
            # Neither the inverse keyword nor view names are vendor constants.
            if any(template.partition(" ")[2] in templates for template in templates):
                configuration_views.update({view.casefold() for view in command.views})
        maximum = max(configuration_views.values(), default=0)
        # Tiny excerpts cannot establish a manual-wide scope reliably.
        self.general_views = {view for view, count in configuration_views.items()
                              if maximum >= 3 and count == maximum}
        self.summaries = {}
        for section, command in commands.items():
            vocabulary = set(words(command.title + " " + command.function + " " +
                                   " ".join(p.name + " " + p.info for p in command.parameters)))
            self.frequency.update(vocabulary)
            self.summaries[section] = set(words(command.title + " " + command.function.split("\n")[0] + " " +
                                               " ".join(p.name + " " + p.info.split("\n")[0]
                                                        for p in command.parameters)))
        self.weights = {term: math.log((len(commands) + 1) / (count + 1)) + 1
                        for term, count in self.frequency.items()}
        self.norms = {section: math.sqrt(sum(self.weight(term)**2 for term in summary))
                      for section, summary in self.summaries.items()}
        anchors = defaultdict(dict)
        for alias, targets in aliases.items():
            terms = words(re.sub(r"\s*\([^)]*\)$", "", alias))
            if not terms or (len(commands) >= 100 and
                             not any(self.frequency[term] <= len(commands) * .25 for term in terms)):
                continue
            available = [section for section in targets if section in commands]
            if available:
                # Multiword topic names can be embedded in a longer command
                # heading. Derive those phrases from the manual, never a map.
                phrases = [terms] + [terms[start:] for start in range(1, len(terms) - 1)]
                for phrase in phrases:
                    anchors[phrase].update(dict.fromkeys(available))
        self.anchors = defaultdict(list)
        for terms, targets in anchors.items():
            self.anchors[terms[0]].append((terms, list(targets)))
        for entries in self.anchors.values():
            entries.sort(key=lambda item: (-len(item[0]), item[0]))

    def weight(self, word: str) -> float:
        return self.weights.get(word, math.log(len(self.commands) + 1) + 1)

    def rank(self, source: Command, parameter, section: str) -> tuple:
        target = self.commands[section]
        terms = set(words(parameter.name + " " + parameter.info.split("\n")[0]))
        summary = self.summaries[section]
        numerator = sum(self.weight(word)**2 for word in terms & summary)
        denominator = math.sqrt(sum(self.weight(word)**2 for word in terms)) * self.norms[section]
        overlap = numerator / denominator if denominator else 0
        common_branch = 0
        for left, right in zip(source.section.split("."), section.split(".")):
            if left != right:
                break
            common_branch += 1
        scope = max((self.views[view.casefold()] for view in target.views), default=0)
        same_view = bool({view.casefold() for view in source.views} & {view.casefold() for view in target.views})
        distance = abs(source.start_page - target.start_page) if source.start_page and target.start_page else 0
        return overlap, same_view, scope, common_branch, -distance

    def topics(self, command: Command):
        allowed_views = self.general_views | {view.casefold() for view in command.views}
        parameter_names = [words(parameter.name) for parameter in command.parameters]
        for parameter in command.parameters:
            groups = defaultdict(dict)
            ranks = {}
            for text in (parameter.name, parameter.info):
                tokens = words(text)
                position = 0
                while position < len(tokens):
                    for terms, targets in self.anchors.get(tokens[position], []):
                        if tokens[position:position + len(terms)] != terms:
                            continue
                        for section in targets:
                            if section != command.section:
                                target_views = {view.casefold() for view in self.commands[section].views}
                                if self.general_views and target_views and not target_views & allowed_views:
                                    continue
                                if section not in ranks:
                                    ranks[section] = self.rank(command, parameter, section)
                                groups[terms][section] = ranks[section]
                        position += len(terms)
                        break
                    else:
                        position += 1
            candidates = {}
            for terms, targets in groups.items():
                # Resolve homonyms using documented views and page locations
                # before comparing different topics by textual relevance.
                def target_rank(section):
                    title = re.sub(r"\s*\([^)]*\)$", "", self.commands[section].title)
                    return words(title) == terms, targets[section][1:], targets[section][0]
                ordered = sorted(targets, key=target_rank, reverse=True)
                if len(ordered) > 1 and target_rank(ordered[0]) == target_rank(ordered[1]):
                    continue
                section = ordered[0]
                similarity = targets[section][0]
                if similarity < .15:
                    continue
                support = sum(contains(name, terms) for name in parameter_names)
                score = contains(words(parameter.name), terms), support, similarity
                candidates[section] = max(candidates.get(section, (False, 0, 0)), score)
            ranked = sorted(candidates, key=candidates.get, reverse=True)
            if not ranked:
                continue
            # Do not force a choice when equally supported pages remain.
            if len(ranked) > 1 and candidates[ranked[0]] == candidates[ranked[1]]:
                continue
            target = self.commands[ranked[0]]
            yield RelatedTopic(target.title, f"Parameter {parameter.name}: {parameter.info}", "Parameters",
                               [target.section], reference_kind="parameter_topic")
