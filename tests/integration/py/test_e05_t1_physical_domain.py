""": physical admission precedes every public continuation.

Domains: March ADR-0068, polarization ADR-0076, finite line shifts ADR-0070,
and positive cell lengths / positive-definite reciprocal metric. Authored
inputs and physical invariants supply expectations, never computed outputs.
The saved editing-range witnesses live in test_e05_t1_saved_range.py.
"""

import os
import re
import shutil
from pathlib import Path

import edi as model
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
OPERATIONS = ('load', 'calculate', 'fit', 'save')
# Field, raw token, independently invalid physical domain. Every axis component
# is exercised on both sides of the declared Miller-index representation bound.
BAD = [
    ('march_r', '0'),
    ('march_r', '-0.25'),
    ('march_random_fract', '-0.1'),
    ('march_random_fract', '1.1'),
    ('axis', '0 0 0'),
    *[
        (field, token)
        for field in ('index_h', 'index_k', 'index_l')
        for token in ('-1001', '1001', '0.5')
    ],
    *[(f'length_{axis}', token) for axis in 'abc' for token in ('0', '-0.25')],
    *[(f'angle_{axis}', token) for axis in ('alpha', 'beta', 'gamma') for token in ('0', '180')],
    ('metric', '10 10 170'),
    ('setup_polarization_coefficient', '-0.1'),
    ('setup_polarization_coefficient', '1.1'),
    ('setup_monochromator_twotheta', '-0.1'),
    ('setup_monochromator_twotheta', '180.1'),
    ('calib_sample_displacement', 'nan'),
    ('calib_sample_transparency', 'inf'),
    ('shift_pair', '1e308'),
    *[
        (field, token)
        for field in ('march_r', 'march_random_fract')
        for token in ('nan', 'inf', '-inf')
    ],
]


def _input(root, field='', token='', *, fraction='0.3'):
    # A private copy of the declared LiF fitting corpus; only the tested physical
    # fields and the explicit one-iteration minimizer condition change.
    corpus = Path(
        os.environ.get('EDI_CRYSTA_CORPUS_ROOT', str(ROOT / 'build/crysta-src/tests/fitting'))
    )
    shutil.copytree(corpus / 'lif-xray-s1/project', root)
    structure_path = root / 'structures/lif.edi'
    experiment_path = root / 'experiments/cu_ka.edi'
    structure = structure_path.read_text()
    experiment = experiment_path.read_text()
    if field.startswith(('length_', 'angle_')):
        structure = re.sub(rf'(?m)^_cell\.{field} .+$', f'_cell.{field} {token}', structure)
    if field in {'metric', 'triclinic'}:
        structure = structure.replace('"F m -3 m"', '"P 1"')
        structure = re.sub(
            r'(?m)^_space_group\.(coord_system_code|it_number) .+\n?', '', structure
        )
        lines = structure.splitlines()
        tags = [line for line in lines if line.startswith('_atom_site.')]
        for index, line in enumerate(lines):
            values = line.split()
            if values and values[0] in {'Li1', 'F1'}:
                values[tags.index('_atom_site.wyckoff_letter')] = 'a'
                values[tags.index('_atom_site.multiplicity')] = '1'
                lines[index] = ' '.join(values)
        structure = '\n'.join(lines) + '\n'
    if field == 'metric':
        for axis, angle in zip(('alpha', 'beta', 'gamma'), token.split(), strict=True):
            structure = re.sub(
                rf'(?m)^_cell\.angle_{axis} .+$', f'_cell.angle_{axis} {angle}', structure
            )
    experiment = experiment.replace('lif 0.02', 'lif 0.02()')
    for name, default in (
        ('setup_polarization_coefficient', '0.375'),
        ('setup_monochromator_twotheta', '31.25'),
        ('calib_sample_displacement', '0.125'),
        ('calib_sample_transparency', '-0.0625'),
    ):
        invalid = field == name or (field == 'shift_pair' and name.startswith('calib_sample_'))
        value = token if invalid else default
        experiment = re.sub(rf'(?m)^_instrument\.{name} .+\n?', '', experiment)
        experiment += f'\n_instrument.{name} {value}\n'
    axis = ['0', '0', '1']
    if field == 'axis':
        axis = token.split()
    elif field in {'index_h', 'index_k', 'index_l'}:
        axis[('index_h', 'index_k', 'index_l').index(field)] = token
    ratio = token if field == 'march_r' else '0.73'
    fraction = token if field == 'march_random_fract' else fraction
    experiment += (
        '\nloop_\n_preferred_orientation.structure_id\n_preferred_orientation.march_r'
        '\n_preferred_orientation.march_random_fract\n_preferred_orientation.index_h'
        '\n_preferred_orientation.index_k\n_preferred_orientation.index_l\n'
        f'lif {ratio} {fraction} {" ".join(axis)}\n'
    )
    structure_path.write_text(structure)
    experiment_path.write_text(experiment)
    analysis = root / 'analysis/analysis.edi'
    analysis.write_text(analysis.read_text() + '\n_minimizer.max_iterations 1\n')
    return root


def _use(project, operation, destination):
    if operation == 'calculate':
        project.analysis.calculate()
        assert np.isfinite(project.experiments[0].data.intensity_calc).all(), (
            ' an admitted physical control must calculate finite intensities'
        )
    elif operation == 'fit':
        result = project.analysis.fit()
        assert result is not None, ' physical controls must reach the actual fit entry'
    elif operation == 'save':
        project.save_as(destination)
        restored = model.Project.load(destination)
        actual = restored.experiments[0].preferred_orientation['lif'].march_random_fract
        original = project.experiments[0].preferred_orientation['lif'].march_random_fract
        assert actual.value == original.value, (
            ' physically admitted orientation must survive saving and reloading exactly'
        )


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize(
    ('field', 'token'), BAD, ids=[f'{field}={token.replace(" ", "_")}' for field, token in BAD]
)
def test_physical_domain_refuses_at_load_before_any_continuation(
    tmp_path, field, token, operation
):
    source = _input(tmp_path / 'input', field, token)
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*.edi')}
    stages = []

    def attempt():
        project = model.Project.load(source)
        stages.append('loaded')
        _use(project, operation, tmp_path / 'output')

    with pytest.raises(model.ValidationError) as caught:
        attempt()
    assert not stages, (
        ' physical-domain input must fail at load, never first at Calculate, Fit or Save'
    )
    assert caught.value.diagnostics, (
        ' physical-domain refusal must carry structured diagnostic evidence'
    )
    assert any(
        str(item.severity).lower().endswith('error') for item in caught.value.diagnostics
    ), ' a physical-domain violation must carry error severity rather than a warning'
    assert before == {p.relative_to(source): p.read_bytes() for p in source.rglob('*.edi')}, (
        ' domain refusal must never clamp or rewrite the saved input'
    )
    assert not (tmp_path / 'output').exists(), (
        ' refused physical input must never publish a continuation output'
    )


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('fraction', ['0', '0.3', '1'])
@pytest.mark.parametrize('geometry', ['cubic', 'triclinic'])
def test_physical_endpoints_and_nonidentity_control_reach_each_continuation(
    tmp_path, fraction, operation, geometry
):
    field = 'triclinic' if geometry == 'triclinic' else ''
    project = model.Project.load(_input(tmp_path / 'input', field, fraction=fraction))
    actual = project.experiments[0].preferred_orientation['lif'].march_random_fract.value
    assert actual == pytest.approx(float(fraction), rel=0, abs=0), (
        ' valid physical endpoints and a nonidentity interior must be admitted unchanged'
    )
    _use(project, operation, tmp_path / 'output')


def _edit(project, field, raw_value):
    row = project.experiments[0].preferred_orientation['lif']
    if field == 'axis':
        row.index_h, row.index_k, row.index_l = (0, 0, 0)
    elif field in {'index_h', 'index_k', 'index_l'}:
        setattr(row, field, float(raw_value) if raw_value == '0.5' else int(raw_value))
    elif field in {'march_r', 'march_random_fract'}:
        getattr(row, field).value = float(raw_value)
    elif field.startswith(('length_', 'angle_')):
        getattr(project.structure.cell, field).value = float(raw_value)
    elif field == 'shift_pair':
        for name in ('calib_sample_displacement', 'calib_sample_transparency'):
            getattr(project.experiments[0].instrument, name).value = float(raw_value)
    else:
        getattr(project.experiments[0].instrument, field).value = float(raw_value)


@pytest.mark.parametrize('operation', ['calculate', 'fit', 'save'])
@pytest.mark.parametrize(
    ('field', 'token'),
    [(field, token) for field, token in BAD if field != 'metric'],
    ids=[f'{field}={token.replace(" ", "_")}' for field, token in BAD if field != 'metric'],
)
def test_programmatic_physical_domain_cannot_escape_any_consumer(
    tmp_path, field, token, operation
):
    # P1 keeps every cell angle independent; cubic symmetry legitimately projects
    # dependent angles back to their constraint, which cannot witness this domain.
    project = model.Project.load(_input(tmp_path / 'valid', 'triclinic'))
    destination = tmp_path / 'invalid-output'

    def attempt():
        # Early rejection at an editing entrance is legitimate. A live parameter
        # handle that permits the edit must still meet the common use guard.
        _edit(project, field, token)
        _use(project, operation, destination)

    with pytest.raises((ValueError, TypeError)):
        attempt()
    assert not destination.exists(), (
        ' a physical-domain mutation must never publish an unusable saved project'
    )
