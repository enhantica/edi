"""Gate 1 refuses each missing record input, including an artefact of the last case."""

import json

import pytest
import yaml

from tests.fixtures.tutorial_cases.contract import CASES, records
from tests.fixtures.tutorial_cases.controls import (
    complete_metadata_tree,
    overlay,
    writable,
    write_json,
)


@pytest.fixture(scope='module')
def complete_tree(tmp_path_factory):
    return complete_metadata_tree(tmp_path_factory.mktemp('record-controls') / 'complete')


@pytest.mark.parametrize('case', [CASES[0], CASES[-1]])
@pytest.mark.parametrize(
    'missing',
    [
        'project',
        'structure',
        'experiment',
        'outline',
        'pin',
        'pin-commit',
        'pin-reason',
        'python',
        'app',
        'app_docs',
        'cli_docs',
        'tags',
    ],
)
def test_record_checker_names_every_missing_field_and_artefact(
    complete_tree, tmp_path, case, missing
):
    baseline = records(complete_tree, json_output=False)
    assert baseline.returncode == 0, (
        'Gate 1 control: a complete metadata-only tree must pass before one input is removed: '
        + baseline.stdout
        + baseline.stderr
    )
    root = overlay(complete_tree, tmp_path / 'damaged')
    directory = 'docs/user/cli/' + case
    if missing == 'project':
        writable(root, directory + '/project/project.edi').unlink()
    elif missing in {'structure', 'experiment'}:
        category = directory + '/project/' + missing + 's'
        for path in (complete_tree / category).glob('*.edi'):
            writable(root, category + '/' + path.name).unlink()
    elif missing == 'outline':
        relative = 'docs/user/cli/projects.yml'
        doc = yaml.safe_load((root / relative).read_text())
        row = next(row for row in doc['projects'] if row['id'] == case)
        row.pop('diffraction-lib', None)
        row.pop('follows-diffraction-lib', None)
        writable(root, relative).write_text(yaml.safe_dump(doc))
    elif missing.startswith('pin'):
        relative = directory + '/expected.json'
        doc = json.loads((root / relative).read_text())
        if missing == 'pin':
            doc['source'].pop('pins')
        else:
            doc['source']['pins'].pop(missing.removeprefix('pin-'))
        write_json(root, relative, doc)
    elif missing == 'app':
        relative = 'app/tutorials/manifest.json'
        doc = json.loads((root / relative).read_text())
        doc['tutorials'] = [entry for entry in doc['tutorials'] if entry['id'] != case]
        write_json(root, relative, doc)
    elif missing == 'tags':
        relative = 'app/examples/metadata.json'
        doc = json.loads((root / relative).read_text())
        doc['examples'][case]['values'].pop('purpose')
        write_json(root, relative, doc)
    else:
        relative = {
            'python': 'docs/user/tutorials/' + case + '.ipynb',
            'app_docs': 'docs/user/app/' + case + '.md',
            'cli_docs': directory + '/index.md',
        }[missing]
        writable(root, relative).unlink()
    run = records(root, json_output=False)
    assert run.returncode != 0, (
        'Gate 1: a removed case input must make the public checker fail: ' + case + ' ' + missing
    )
    assert case in run.stdout + run.stderr, (
        'Gate 1: refusal must identify the incomplete case, including one after all earlier cases'
    )
