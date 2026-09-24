#!/usr/bin/env python3
"""Inventory extraction diagnostics and preserve source evidence for their review."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import pymupdf


def read(path):
    return json.loads(path.read_text())


def counts(report):
    return dict(Counter(warning.split(':', 1)[0]
                        for issue in report['issues'] for warning in issue['warnings']))


def review(root, before_root, manuals):
    manifest = read(root / 'manifest.json')
    validation = read(root / 'validation.json')
    entries = {entry['section']: entry for entry in manifest['commands']}
    before = read(before_root / 'validation.json') if before_root else validation
    categories = defaultdict(lambda: {'occurrences': 0, 'commands': set(), 'samples': []})
    missing = []
    with pymupdf.open(manuals / manifest['source_file']) as pdf:
        def evidence(issue):
            entry = entries[issue['section']]
            data = read(root / entry['file'])
            return {
                'section': issue['section'], 'title': entry['title'], 'file': entry['file'],
                'pages': [entry['first_page'], entry['last_page']],
                'warnings': issue['warnings'],
                'source_first_page_text': pdf[entry['first_page'] - 1].get_text(sort=True),
                'function': data['FuncDef'], 'clis': data['CLIs'], 'views': data['ParentView'],
                'extra_info_excerpt': data['ExtraInfo'][:4000],
            }

        for issue in validation['issues']:
            for warning in issue['warnings']:
                category = categories[warning.split(':', 1)[0]]
                category['occurrences'] += 1
                if len(category['samples']) < 3 and issue['section'] not in category['commands']:
                    sample = evidence(issue)
                    sample['warning'] = warning
                    category['samples'].append(sample)
                category['commands'].add(issue['section'])
            if any(w in {'missing_format', 'missing_views', 'missing_function'} for w in issue['warnings']):
                item = evidence(issue)
                item['field_review'] = {}
                defaults = re.search(r'(?:^|\n)Defaults:\n(.*?)(?:\n\n[A-Z][^\n]*:\n|\Z)',
                                     item['extra_info_excerpt'], re.S)
                for warning in issue['warnings']:
                    if warning == 'missing_views':
                        item['field_review'][warning] = (
                            'Source prints mode text under Command Default; preserved in ExtraInfo.'
                            if defaults and re.search(r'EXEC|configuration', defaults[1])
                            else 'No mode extracted; see the accompanying source review.')
                    elif warning == 'missing_format':
                        item['field_review'][warning] = (
                            'No syntax extracted; compare the source evidence with the accompanying review. '
                            'Mentions and examples are not substituted for a complete template.')
                    elif warning == 'missing_function':
                        item['field_review'][warning] = (
                            'No function extracted; see the accompanying source review.')
                missing.append(item)
    for category in categories.values():
        category['commands'] = len(category['commands'])
    return {
        'corpus': root.name, 'source_file': manifest['source_file'],
        'source_sha256': manifest['source_sha256'], 'commands': validation['commands'],
        'commands_with_warnings_before': len(before['issues']),
        'commands_with_warnings_after': len(validation['issues']),
        'warning_counts_before': counts(before), 'warning_counts_after': counts(validation),
        'categories': dict(categories), 'missing_field_reviews': missing,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpora', type=Path, default=Path('output'))
    parser.add_argument('--before', type=Path)
    parser.add_argument('--manuals', type=Path, default=Path('data/manuals'))
    parser.add_argument('-o', '--output', type=Path, default=Path('reports/coverage/extraction-warning-review.json'))
    args = parser.parse_args()
    corpora = []
    for manifest in sorted(args.corpora.glob('*/manifest.json')):
        root = manifest.parent
        previous = args.before / root.name if args.before else None
        if previous and not (previous / 'validation.json').exists():
            previous = None
        corpora.append(review(root, previous, args.manuals))
    report = {
        'scope': 'Inventory of every retained warning; three source samples per category and corpus; '
                 'individual source evidence for every missing primary field.',
        'limitations': 'Category review is not semantic verification of every parameter or syntax token. '
                      'Source omissions and mislabeled sections remain visible as nonfatal warnings.',
        'corpora': corpora,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
