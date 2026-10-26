"""Experiment descriptions migrate without changing any scientific input bytes."""

import hashlib
import importlib
import json
import re
import shutil
import warnings
from operator import itemgetter
from pathlib import Path

import pytest
import yaml

from tests.fixtures import cif_import_cases as case
from tests.fixtures.cif_import_baseline.generate_metadata import scalars

BASE = Path(__file__).resolve().parents[2] / 'fixtures/cif_import_baseline'
PINS = json.loads((BASE / 'metadata-before.json').read_text())
FIELDS = re.compile(
    r'^_(?:experiment_type\.(?:dimensionality|polarisation)|'
    r'instrument\.(?:name|facility))\b[^\n]*\n?',
    re.MULTILINE,
)
RETIRED = re.compile(
    r'^_metadata\.(dimensionality|polarisation|instrument|facility|purpose)\b', re.MULTILINE
)


@pytest.mark.parametrize('row', PINS['records'], ids=itemgetter('path'))
def test_each_tracked_record_migrates_all_experiments_and_preserves_scientific_bytes(
    tmp_path, row
):
    record = case.ROOT / row['path']
    assert not RETIRED.search(record.read_text()), (
        'Every tracked project record drops the retired project-level description tags'
    )
    for experiment in row['experiments']:
        path = case.ROOT / experiment['path']
        assert (
            hashlib.sha256(FIELDS.sub('', path.read_text()).encode()).hexdigest()
            == experiment['scientific_sha256']
        ), 'The textual migration preserves every scientific and fit-setting byte'
        values = case.columns(path.read_text())
        for tag, expected in experiment['expected'].items():
            assert [case.decoded(v) for v in values.get(case.key(tag), [])] == [expected], (
                'Every experiment receives its own declared description: ' + tag
            )
    project = importlib.import_module(case.API).Project.load(record.parent)
    project.save_as(tmp_path / 'saved')
    for experiment in row['experiments']:
        saved = tmp_path / 'saved/experiments' / Path(experiment['path']).name
        values = case.columns(saved.read_text())
        for tag, expected in experiment['expected'].items():
            assert [case.decoded(v) for v in values.get(case.key(tag), [])] == [expected], (
                'Loading and saving must retain every migrated description '
                'including explicit unknowns'
            )
    assert not RETIRED.search((tmp_path / 'saved/project.edi').read_text()), (
        'The writer never recreates retired project metadata'
    )


@pytest.mark.parametrize(
    ('kind', 'value'), [('dimensionality', '2D'), ('polarisation', 'polarised')]
)
def test_legacy_selectors_refuse_unadmitted_values_atomically(tmp_path, kind, value):
    api = importlib.import_module(case.API)
    source = case.project_input('structure', case.STRUCTURE, tmp_path)
    record = source / 'project.edi'
    record.write_text(record.read_text() + '\n_metadata.' + kind + ' ' + value + '\n')
    with pytest.raises(
        (ValueError, RuntimeError), match=r'(?i)' + kind + '.*' + value + '|' + value + '.*' + kind
    ):
        api.Project.load(source)


@pytest.mark.parametrize(('probe', 'polarisation'), [('neutron', '.'), ('xray', 'unpolarised')])
def test_experiment_polarisation_is_validated_against_its_probe(probe, polarisation):
    text = (
        case.ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi'
    ).read_text()
    text = text.replace('radiation_probe neutron', 'radiation_probe ' + probe)
    text += (
        '_experiment_type.dimensionality 1d\n_experiment_type.polarisation ' + polarisation + '\n'
    )
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)polarisation'):
        importlib.import_module(case.API).ExperimentFactory.from_cif_str(text)


@pytest.mark.parametrize('selection', ['lbco', 'mixed', 'purpose-only'])
def test_legacy_records_convert_once_and_save_only_experiment_fields(tmp_path, capfd, selection):
    matches = [
        r
        for r in PINS['records']
        if (
            'lbco-hrpt_start-2' in r['path']
            if selection == 'lbco' and case.API == 'edi'
            else 'lab6-echidna-fcj' in r['path']
            if selection == 'lbco'
            else 'pd-neut-xray-cwl_pbso4-d1a-lab' in r['path']
            if selection == 'mixed'
            else 'fitted-auto-chebyshev' in r['path']
        )
    ]
    if not matches:
        pytest.skip('This repository carries no project of the selected legacy shape')
    row = matches[0]
    source = tmp_path / 'legacy'
    shutil.copytree((case.ROOT / row['path']).parent, source)
    (source / 'project.edi').write_text(row['legacy_record'])
    for path in (source / 'experiments').glob('*.edi'):
        path.write_text(FIELDS.sub('', path.read_text()))
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        project = importlib.import_module(case.API).Project.load(source)
    notes = [str(w.message) for w in caught] + capfd.readouterr().err.splitlines()
    for name in RETIRED.findall(row['legacy_record']):
        assert sum('_metadata.' + name in n for n in notes) == 1, (
            'Each retired tag emits one load warning naming that tag'
        )
    project.save_as(tmp_path / 'saved')
    assert not RETIRED.search((tmp_path / 'saved/project.edi').read_text()), (
        'A legacy record is converted on read and saved without its retired tags'
    )
    for experiment in row['experiments']:
        values = case.columns(
            (tmp_path / 'saved/experiments' / Path(experiment['path']).name).read_text()
        )
        for tag, expected in experiment['expected'].items():
            if selection == 'mixed' and tag in {'_instrument.name', '_instrument.facility'}:
                wanted = '?'
            else:
                wanted = expected
            assert [case.decoded(v) for v in values.get(case.key(tag), [])] == [wanted], (
                'Legacy descriptions are assigned per experiment and mixed '
                'probes do not inherit one instrument'
            )
    with warnings.catch_warnings(record=True) as reopened:
        warnings.simplefilter('always')
        importlib.import_module(case.API).Project.load(tmp_path / 'saved')
    assert not any('_metadata.' in str(w.message) for w in reopened), (
        'A reopened migrated project has no retired-tag warning'
    )


def test_migration_ledger_covers_exactly_the_frozen_pre_move_population():
    manifest = case.ROOT / 'tests/fixtures/metadata_migration.tsv'
    assert manifest.is_file(), (
        'The visible migration ledger records every original project and experiment'
    )
    text = manifest.read_text()
    for row in PINS['records']:
        for experiment in row['experiments']:
            assert experiment['path'] in text or (
                Path(experiment['path']).name in text and str(Path(row['path']).parent) in text
            ), 'Every pre-move experiment appears in the migration ledger'


def test_example_facets_follow_the_pre_move_catalogue_and_each_experiment():
    if case.API != 'edi':
        pytest.skip('The application catalogue belongs to the product repository')
    current = json.loads((case.ROOT / 'app/examples/metadata.json').read_text())
    for name, entry in PINS['catalogue']['examples'].items():
        actual = current['examples'][name]['values']
        expected = dict(entry['values'])
        expected['dimensionality'] = ['1d']
        expected['polarisation'] = ['unpolarised'] if expected['probe'] == ['neutron'] else ['.']
        if name == 'pd-neut-xray-cwl_pbso4-d1a-lab':
            expected['instruments'] = ['?', 'D1A']
            expected['facilities'] = ['?', 'ILL']
            expected['polarisation'] = ['.', 'unpolarised']
        assert {k: sorted(v) for k, v in actual.items()} == {
            k: sorted(v) for k, v in expected.items()
        }, (
            'Every bundled example preserves its facets through the '
            'declared experiment-level conversion'
        )


@pytest.mark.parametrize('probe', ['neutron', 'xray'])
def test_description_members_expose_the_effective_probe_defaults(probe):
    text = (
        case.ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi'
    ).read_text()
    text = text.replace('radiation_probe neutron', 'radiation_probe ' + probe)
    obj = importlib.import_module(case.API).ExperimentFactory.from_cif_str(text)
    assert obj.experiment_type.dimensionality == '1d', (
        'Omitted dimensionality exposes its effective one-dimensional value'
    )
    assert obj.experiment_type.polarisation == ('unpolarised' if probe == 'neutron' else '.'), (
        'Omitted polarisation exposes the effective value of this radiation probe'
    )
    assert obj.instrument.name == '?', 'An omitted instrument exposes a declared unknown'
    assert obj.instrument.facility == '?', 'An omitted facility exposes a declared unknown'


def test_registry_keeps_verification_as_a_declared_catalogue_flag():
    expected = {
        Path(row['path']).parts[3]
        for row in PINS['records']
        if row['path'].startswith('docs/user/cli/')
        and scalars(row['legacy_record']).get('_metadata.purpose') == 'verification'
    }
    registry = yaml.safe_load((case.ROOT / 'docs/user/cli/projects.yml').read_text())
    actual = {row['id'] for row in registry['projects'] if row.get('verification') is True}
    assert expected, 'The frozen CLI records include real verification projects'
    assert actual == expected, (
        'Every retired verification purpose becomes an explicit boolean catalogue flag'
    )
    bundled = json.loads((case.ROOT / 'app/examples/metadata.json').read_text())['examples']
    assert not actual.intersection(bundled), (
        'The app catalogue excludes projects marked for verification'
    )
