"""Both file decoders admit only Auto omission of a series basis, then derive it."""

import json
import re
import shutil
from pathlib import Path

import edi as engine
import numpy as np
import pytest

HERE = Path(__file__).resolve().parents[2] / 'fixtures/background_estimate/basis-loader'
INPUTS = json.loads((HERE / 'inputs.json').read_text())
OMISSIONS = [
    ('polynomial', 'origin'),
    ('chebyshev', 'x_min'),
    ('chebyshev', 'x_max'),
    ('chebyshev', 'both'),
]
ENTRIES = ['directory', 'experiment-path', 'experiment-text']


def fixture(destination, beam, kind, missing=(), mode='auto', replacements=None):
    shutil.copytree(HERE / beam, destination)
    spec = INPUTS[beam]
    file = destination / 'experiments' / (spec['experiment'] + '.edi')
    text = file.read_text()
    if kind == 'chebyshev':
        text = text.replace('_background.type polynomial', '_background.type chebyshev')
        text = re.sub(
            r'(?m)^_background\.origin .*$',
            f'_background.x_min {spec["x_min"]}\n_background.x_max {spec["x_max"]}',
            text,
        )
    text = text.replace('_background_estimate.mode auto', '_background_estimate.mode ' + mode)
    for field in missing:
        text, count = re.subn(r'(?m)^_background\.' + field + r' .*\n', '', text)
        assert count == 1, 'The raw loader stimulus must remove exactly one declared basis tag'
    for field, value in (replacements or {}).items():
        text, count = re.subn(
            r'(?m)^_background\.' + field + r' .*$',
            '_background.' + field + ' ' + str(value),
            text,
        )
        assert count == 1, (
            'The numeric refusal stimulus must replace exactly its declared basis tag'
        )
    file.write_text(text)
    return file


def load(directory, entry, complete):
    if entry == 'directory':
        return engine.Project.load(directory)
    file = next((directory / 'experiments').glob('*.edi'))
    if entry == 'experiment-path':
        experiment = engine.ExperimentFactory.from_cif_path(file)
    else:
        experiment = engine.ExperimentFactory.from_cif_str(file.read_text())
    project = engine.Project.load(complete)
    project.experiment = experiment
    return project


def rows(experiment):
    return [
        (row.id, row.order, row.coef.value, row.coef.free) for row in experiment.background_terms
    ]


def constants(experiment):
    return {
        field: getattr(experiment, 'background_' + field) for field in ['origin', 'x_min', 'x_max']
    }


def settings(directory, beam):
    text = (directory / 'experiments' / (INPUTS[beam]['experiment'] + '.edi')).read_text()
    return dict(
        line.split(maxsplit=1)
        for line in text.splitlines()
        if line.startswith('_background_estimate.')
    )


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize(('kind', 'omitted'), OMISSIONS)
@pytest.mark.parametrize('entry', ENTRIES)
def test_raw_auto_basis_omission_derives_before_consumption_and_saves_current_rows(
    tmp_path, beam, kind, omitted, entry
):
    missing = ['x_min', 'x_max'] if omitted == 'both' else [omitted]
    complete = tmp_path / 'complete'
    fixture(complete, beam, kind)
    # A complete file must reach the same decoder first: an unrelated factory
    # or setup refusal cannot be counted as an absent-basis product failure.
    control = load(complete, entry, complete)
    input_dir = tmp_path / 'raw-input'
    file = fixture(input_dir, beam, kind, missing)
    raw = file.read_bytes()
    for field in missing:
        assert ('_background.' + field + ' ').encode() not in raw, (
            'The supported file form must genuinely omit the basis tag before any load'
        )
    project = load(input_dir, entry, complete)
    assert file.read_bytes() == raw, 'Loading an Auto omission must not rewrite the user input'
    expected = constants(control.experiment)
    grid = INPUTS[beam]['included']
    for field in missing:
        expected[field] = (
            (grid[0] + grid[-1]) / 2
            if field == 'origin'
            else grid[0]
            if field == 'x_min'
            else grid[-1]
        )
        setattr(control.experiment, 'background_' + field, expected[field])
    control.analysis.calculate()
    expected_rows = rows(control.experiment)
    project.analysis.calculate()
    assert constants(project.experiment) == expected, (
        'First calculation or fit must derive only omitted constants from included samples'
    )
    actual = rows(project.experiment)
    assert [(r[0], r[1], r[3]) for r in actual] == [(r[0], r[1], r[3]) for r in expected_rows], (
        'Raw Auto loading must match explicit-basis row identities and flags'
    )
    np.testing.assert_allclose(
        [r[2] for r in actual],
        [r[2] for r in expected_rows],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Raw Auto omission must match the explicit-basis coefficient seam',
    )
    saved = tmp_path / 'saved'
    project.save_as(saved)
    receipt = settings(saved, beam)
    assert receipt['_background_estimate.mode'] == 'auto', (
        'Derived Auto input files must save without silently changing estimation mode'
    )
    for name in ['inputs_digest', 'points_digest']:
        assert re.fullmatch(r'[0-9a-f]{16}', receipt['_background_estimate.' + name]), (
            'A consumed raw omission must save nonempty current input and row provenance'
        )
    loaded = engine.Project.load(saved)
    before = rows(loaded.experiment)
    assert constants(loaded.experiment) == expected, (
        'Save and reload must retain every derived basis constant exactly'
    )
    np.testing.assert_allclose(
        [r[2] for r in before],
        [r[2] for r in actual],
        rtol=1e-11,
        atol=1e-8,
        err_msg='Saved raw-omission rows must retain every estimated coefficient through reload',
    )
    loaded.analysis.calculate()
    assert rows(loaded.experiment) == before, (
        'Unchanged reload and calculation must retain saved Auto rows without re-estimating'
    )
    loaded.save_as(tmp_path / 'again')
    assert settings(tmp_path / 'again', beam) == receipt, (
        'An unchanged derived project must keep both saved provenance digests exactly'
    )


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize(('kind', 'omitted'), OMISSIONS)
@pytest.mark.parametrize('entry', ENTRIES)
def test_manual_files_still_require_each_basis_constant(tmp_path, beam, kind, omitted, entry):
    complete = tmp_path / 'complete'
    fixture(complete, beam, kind, mode='manual')
    load(complete, entry, complete)
    missing = ['x_min', 'x_max'] if omitted == 'both' else [omitted]
    file = fixture(tmp_path / 'invalid', beam, kind, missing, mode='manual')
    raw = file.read_bytes()
    with pytest.raises((ValueError, RuntimeError)) as caught:
        load(tmp_path / 'invalid', entry, complete)
    message = str(caught.value).lower()
    assert 'background' in message, 'Manual missing-basis refusal must identify the background'
    assert any(field in message for field in missing), (
        'Manual refusal must identify its missing basis constant'
    )
    assert file.read_bytes() == raw, 'A refused Manual file must remain byte-identical'


INVALID = [
    (kind, {field: value}, ())
    for kind, field in [('polynomial', 'origin'), ('chebyshev', 'x_min'), ('chebyshev', 'x_max')]
    for value in ['broken-number', 'nan', 'inf', '-inf', '1e309']
]
INVALID += [
    ('polynomial', {'origin': 0}, ()),
    ('chebyshev', {'x_min': 80, 'x_max': 20}, ()),
    ('chebyshev', {'x_min': 20, 'x_max': 20}, ()),
    ('chebyshev', {'x_min': 'nan'}, ('x_max',)),
    ('chebyshev', {'x_max': 'nan'}, ('x_min',)),
]


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize(
    ('kind', 'replacements', 'missing'), INVALID, ids=[str(index) for index in range(len(INVALID))]
)
@pytest.mark.parametrize('entry', ENTRIES)
def test_auto_omission_exception_never_admits_invalid_declared_basis(
    tmp_path, beam, kind, replacements, missing, entry
):
    complete = tmp_path / 'complete'
    fixture(complete, beam, kind)
    load(complete, entry, complete)
    file = fixture(tmp_path / 'invalid', beam, kind, missing, replacements=replacements)
    raw = file.read_bytes()
    with pytest.raises((ValueError, RuntimeError)) as caught:
        load(tmp_path / 'invalid', entry, complete)
    message = str(caught.value).lower()
    assert 'background' in message or 'invalid number' in message, (
        'Invalid declared Auto basis must report a background or numeric parsing reason'
    )
    assert any(field in message for field in [*replacements, *missing]) or any(
        str(value).lower() in message for value in replacements.values()
    ), 'The refusal must identify its basis field, missing companion or invalid numeric token'
    assert file.read_bytes() == raw, (
        'A refused malformed or nonfinite file must remain byte-identical'
    )


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize(('kind', 'omitted'), OMISSIONS)
@pytest.mark.parametrize('mode', ['auto', 'manual'])
def test_save_remains_strict_for_an_unresolved_basis(tmp_path, beam, kind, omitted, mode):
    fixture(tmp_path / 'complete', beam, kind, mode=mode)
    project = engine.Project.load(tmp_path / 'complete')
    missing = ['x_min', 'x_max'] if omitted == 'both' else [omitted]
    for field in missing:
        setattr(project.experiment, 'background_' + field, None)
    before = rows(project.experiment)
    with pytest.raises((ValueError, RuntimeError)) as caught:
        project.save_as(tmp_path / 'invalid-output')
    message = str(caught.value).lower()
    assert 'background' in message, 'Strict saving must name the unresolved background basis'
    assert any(field in message for field in missing), (
        'Strict save refusal must name the missing constant'
    )
    assert rows(project.experiment) == before, (
        'A strict save refusal must not rewrite live background rows'
    )
    assert all(getattr(project.experiment, 'background_' + field) is None for field in missing), (
        'Saving must not silently fill unresolved basis constants as a side effect'
    )
