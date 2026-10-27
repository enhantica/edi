"""Merge the declared catalogue without refreshing unrelated frozen witnesses."""

import json
from pathlib import Path

HERE = Path(__file__).parent
SELECTION = HERE.parent / 'example_catalogue/catalogue-selection.json'


def selected_ids():
    return [row['id'] for row in json.loads(SELECTION.read_text())['cases']]


def refresh_paths():
    # The four-pattern LATP fixture was deliberately rebuilt from the selected template.
    return {
        f'docs/user/cli/{case}/project'
        for case in [
            *selected_ids(),
            'pd-xray-cwl_latp_scan-4f',
            *json.loads((SELECTION.parent / 'single-crystal-renames.json').read_text())['ids'],
        ]
    }


def load(path):
    return json.loads(path.read_text().split('var frozen = ', 1)[1].rsplit(';', 1)[0])


def merge_category(path, fresh):
    retained = load(path)
    paths = refresh_paths()
    previous = {row['id']: row for row in retained['projects']}
    paths |= {row['path'] for row in fresh['projects'] if row['id'] not in previous}
    retained['projects'] = [
        row if row['path'] in paths else previous[row['id']] for row in fresh['projects']
    ]
    retained['corpus'] = [row for row in retained['corpus'] if row['project'] not in paths]
    retained['corpus'] += [row for row in fresh['corpus'] if row['project'] in paths]
    retained['catalogue_ids'] = selected_ids()
    return retained


def merge_display(path, sources, cases):
    retained = load(path)
    paths = refresh_paths()
    previous = {row['path'] for row in retained['cases']}
    paths |= {row['path'] for row in cases if row['path'] not in previous}
    retained['cases'] = [row for row in retained['cases'] if row['path'] not in paths]
    retained['cases'] += [row for row in cases if row['path'] in paths]
    retained['sources'] = {
        key: value
        for key, value in retained['sources'].items()
        if not any(key.startswith(path + '/') for path in paths)
    }
    retained['sources'].update({
        key: value
        for key, value in sources.items()
        if any(key.startswith(path + '/') for path in paths)
    })
    return retained['sources'], retained['cases']
