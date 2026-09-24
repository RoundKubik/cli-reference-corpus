#!/usr/bin/env python3
"""Verify command pairs, schemas, provenance, and exported reference filenames."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import jsonschema

from cli_reference_corpus.corpus_input import CorpusInput
from cli_reference_corpus.markdown import render_command
from cli_reference_corpus.storage import file_hash


def read(path):
    return json.loads(path.read_text())


def verify(root, manuals, schema, before=None):
    corpus = CorpusInput.open(root)
    manifest = corpus.manifest
    entries = {entry['section']: entry for entry in manifest['commands']}
    expected = {name for entry in entries.values() for name in (entry['file'], entry['markdown_file'])}
    actual = {str(path.relative_to(root)) for path in (root / 'cmd_corpus').iterdir() if path.is_file()}
    result = {
        'pairs': len(entries), 'pdf_hash_matches': file_hash(manuals / manifest['source_file']) == manifest['source_sha256'],
        'missing_files': sorted(expected - actual), 'extra_files': sorted(actual - expected),
        'markdown_mismatches': [], 'records_with_cyrillic': [], 'schema_errors': [],
        'core_field_changes': [], 'title_whitespace_normalizations': [],
        'commands_with_extra_info': 0, 'commands_with_related_topics': 0, 'related_topics': 0,
        'related_targets_without_corpus_records': [], 'incorrect_target_files': [],
    }
    validator = jsonschema.Draft202012Validator(schema)
    for command in corpus.commands():
        entry = entries[command.section]
        data = read(root / entry['file'])
        errors = [error.message for error in validator.iter_errors(data)]
        if errors:
            result['schema_errors'].append({'section': command.section, 'errors': errors})
        if (root / entry['markdown_file']).read_text() != render_command(command):
            result['markdown_mismatches'].append(entry['markdown_file'])
        if re.search('[\u0400-\u04ff]', json.dumps(data, ensure_ascii=False)):
            result['records_with_cyrillic'].append(entry['file'])
        if before and (before / entry['file']).exists():
            old = read(before / entry['file'])
            changed = [key for key in data if key not in {'related_topics', 'syntax_issues', 'ExtraInfo'}
                       and old.get(key) != data[key]]
            if changed:
                result['core_field_changes'].append({'section': command.section, 'fields': changed})
        result['commands_with_extra_info'] += bool(command.extra)
        result['commands_with_related_topics'] += bool(command.related_topics)
        result['related_topics'] += len(command.related_topics)
        for raw_topic, topic in zip(data.get('related_topics', []), command.related_topics):
            targets = [Path(entries[section]['file']).name for section in topic.target_sections
                       if section in entries and section != command.section]
            # Older corpora may lack target_files; validate every exported field.
            if 'target_files' in raw_topic and topic.target_files != list(dict.fromkeys(targets)):
                result['incorrect_target_files'].append({'section': command.section, 'topic': topic.title})
            for section in topic.target_sections:
                if section not in entries:
                    result['related_targets_without_corpus_records'].append({'section': command.section, 'target': section})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpora', type=Path, default=Path('output'))
    parser.add_argument('--before', type=Path)
    parser.add_argument('--manuals', type=Path, default=Path('data/manuals'))
    parser.add_argument('-o', '--output', type=Path, default=Path('reports/coverage/corpus-verification.json'))
    args = parser.parse_args()
    report = {}
    for manifest in sorted(args.corpora.glob('*/manifest.json')):
        root = manifest.parent
        schema = read(Path('schemas') / (read(manifest)['schema'] + '.schema.json'))
        previous = args.before / root.name if args.before else None
        report[root.name] = verify(root, args.manuals, schema, previous)
        print(root.name, report[root.name]['pairs'], 'pairs;', len(report[root.name]['schema_errors']), 'schema failures', flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    assert all(result['pdf_hash_matches'] and not any(result[key] for key in (
        'missing_files', 'extra_files', 'markdown_mismatches', 'incorrect_target_files',
        'related_targets_without_corpus_records')) for result in report.values()), 'Corpus integrity check failed'


if __name__ == '__main__':
    main()
